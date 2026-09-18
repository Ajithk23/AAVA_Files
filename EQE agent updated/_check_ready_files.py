"""Temporary read-only script to inspect the 'Select Ready Files' dropdown in the app."""
import asyncio
import sys
import traceback
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        print("Step 1: Navigating to DocuChat...", flush=True)
        try:
            await page.goto(
                "https://docu-chat.crt.ai.caresource.corp/",
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as e:
            print(f"  Navigation error: {e}", flush=True)

        print(f"  Immediate URL = {page.url}", flush=True)

        # Wait for Okta agentless DSS to complete and redirect back to the app
        print("Step 2: Waiting for auth redirect back to docu-chat...", flush=True)
        try:
            await page.wait_for_url("*docu-chat*", timeout=45000)
            print(f"  Auth OK — URL = {page.url}", flush=True)
        except Exception as e:
            print(f"  Still on auth page after 45s — URL = {page.url} | {e}", flush=True)

        print(f"  Page title = {await page.title()}", flush=True)
        # Extra wait for Streamlit app to fully render
        await page.wait_for_timeout(6000)
        print(f"  After render wait — URL = {page.url}", flush=True)

        # ── Locate all multiselect widgets ──────────────────────────────────
        multiselects = page.locator("[data-testid='stMultiSelect']")
        count = await multiselects.count()
        print(f"\nStep 3: stMultiSelect widgets found = {count}", flush=True)

        for i in range(count):
            try:
                txt = await multiselects.nth(i).inner_text(timeout=3000)
                print(f"  MultiSelect[{i}]: {txt[:150].replace(chr(10),' ')}", flush=True)
            except Exception as e:
                print(f"  MultiSelect[{i}]: error reading — {e}", flush=True)

        # ── Try each multiselect, click to open, read options ───────────────
        print("\nStep 4: Clicking each multiselect to read options...", flush=True)
        for i in range(count):
            try:
                ms = multiselects.nth(i)
                label_text = (await ms.inner_text(timeout=3000))[:80].replace("\n", " ")
                print(f"\n  Clicking MultiSelect[{i}]: {label_text}", flush=True)
                await ms.click(timeout=5000)
                await page.wait_for_timeout(1500)

                # ── Dump the open dropdown HTML to find the right scroll container ──
                await page.screenshot(path="_dropdown_open.png", full_page=False)
                print("  -> Screenshot saved: _dropdown_open.png", flush=True)

                # Print inner HTML of the body after dropdown opens to identify container
                dropdown_html = await page.evaluate("""() => {
                    // Find all scrollable elements visible on page
                    const els = document.querySelectorAll('ul, [role=listbox], [data-baseweb=popover] *, [class*=dropdown] *, [class*=menu] *');
                    let result = [];
                    els.forEach(el => {
                        if (el.scrollHeight > el.clientHeight + 5 || el.children.length > 3) {
                            result.push({
                                tag: el.tagName,
                                role: el.getAttribute('role'),
                                class: el.className.substring(0, 80),
                                childCount: el.children.length,
                                scrollHeight: el.scrollHeight,
                                clientHeight: el.clientHeight,
                                testid: el.getAttribute('data-testid')
                            });
                        }
                    });
                    return result.slice(0, 20);
                }""")
                print(f"  -> Scrollable/menu elements found in DOM:", flush=True)
                for el in dropdown_html:
                    print(f"     {el}", flush=True)

                # Try scrolling via JS on any ul or listbox
                await page.evaluate("""() => {
                    const candidates = [
                        ...document.querySelectorAll('ul[role=listbox], [role=listbox], ul')
                    ];
                    candidates.forEach(el => el.scrollBy(0, 500));
                }""")
                await page.wait_for_timeout(600)
                await page.screenshot(path="_dropdown_scrolled.png", full_page=False)
                print("  -> Screenshot after JS scroll: _dropdown_scrolled.png", flush=True)

                # ── Harvest all options ──────────────────────────────────────
                all_options: list[str] = []
                seen: set[str] = set()

                async def harvest_visible_options():
                    for loc in [
                        page.locator("[data-testid='stMultiSelectOption']"),
                        page.locator("[role='option']"),
                    ]:
                        cnt = await loc.count()
                        if cnt > 0:
                            for k in range(cnt):
                                try:
                                    t = (await loc.nth(k).inner_text(timeout=1500)).strip()
                                    if t and t not in seen:
                                        seen.add(t)
                                        all_options.append(t)
                                except Exception:
                                    pass
                            break

                await harvest_visible_options()

                # Scroll in increments via JS and collect
                for _ in range(20):
                    await page.evaluate("""() => {
                        const candidates = [
                            ...document.querySelectorAll('ul[role=listbox], [role=listbox], ul')
                        ];
                        candidates.forEach(el => el.scrollBy(0, 150));
                    }""")
                    await page.wait_for_timeout(350)
                    prev = len(all_options)
                    await harvest_visible_options()
                    if len(all_options) == prev:
                        break

                print(f"  -> Total unique options found (after scrolling): {len(all_options)}", flush=True)
                for j, txt in enumerate(all_options):
                    print(f"     [{j+1:02d}] {txt}", flush=True)

                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)

            except Exception as e:
                print(f"  MultiSelect[{i}] error: {e}", flush=True)
                traceback.print_exc()

        # ── Also check for any select / listbox elements ────────────────────
        print("\nStep 5: Checking for stSelectbox widgets...", flush=True)
        selects = page.locator("[data-testid='stSelectbox']")
        sc = await selects.count()
        print(f"  stSelectbox count: {sc}", flush=True)
        for i in range(sc):
            try:
                txt = (await selects.nth(i).inner_text(timeout=3000))[:120].replace("\n", " ")
                print(f"  Selectbox[{i}]: {txt}", flush=True)
            except Exception as e:
                print(f"  Selectbox[{i}]: {e}", flush=True)

        print("\nDone. Closing browser.", flush=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())



async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=400)
        page = await browser.new_page()
        print("Navigating to DocuChat...")
        await page.goto("https://docu-chat.crt.ai.caresource.corp/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(4000)

        # Ensure Chat tab is active
        chat_tab = page.locator("button, [role='tab']").filter(has_text="Chat")
        if await chat_tab.count() > 0:
            await chat_tab.first.click()
            await page.wait_for_timeout(2000)

        # ── Find the 'Select Ready Files' multiselect ────────────────────────
        multiselects = page.locator("[data-testid='stMultiSelect']")
        count = await multiselects.count()
        print(f"\nTotal multiselect widgets on page: {count}")

        # Identify ready-files multiselect by proximity to its label
        target_ms = None
        for i in range(count):
            ms = multiselects.nth(i)
            text = await ms.inner_text()
            print(f"  MultiSelect[{i}]: {text[:120].replace(chr(10),' ')}")
            if "choose" in text.lower() or "ready" in text.lower() or "files" in text.lower():
                target_ms = ms

        if target_ms is None and count > 0:
            # Fall back to last multiselect (ready-files is typically last)
            target_ms = multiselects.last

        if target_ms:
            print("\nClicking on the Ready Files multiselect to expand dropdown...")
            await target_ms.click()
            await page.wait_for_timeout(2000)

            # Read options
            opts = page.locator("[data-testid='stMultiSelectOption']")
            n = await opts.count()
            if n == 0:
                # Try generic role=option
                opts = page.locator("[role='option']")
                n = await opts.count()

            print(f"\n=== Ready Files Dropdown — {n} option(s) found ===")
            for j in range(n):
                txt = (await opts.nth(j).inner_text()).strip()
                print(f"  [{j+1:02d}] {txt}")

            if n == 0:
                # Grab visible list items from any open dropdown
                li_opts = page.locator("ul li, [role='listbox'] *")
                n2 = await li_opts.count()
                print(f"  Fallback listbox items: {n2}")
                for j in range(n2):
                    try:
                        txt = (await li_opts.nth(j).inner_text()).strip()
                        if txt:
                            print(f"  [{j+1:02d}] {txt}")
                    except Exception:
                        pass
        else:
            print("Could not locate Ready Files dropdown.")

        await page.wait_for_timeout(2000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
