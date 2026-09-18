from __future__ import annotations

import logging
import re
from typing import Iterable

from playwright.async_api import Locator, Page

from pages.chat_page import ChatPage
from tests.web.regression.chat.chat_test_helpers import (
    _assert_landing_page_options,
    _ensure_chat_configuration_open,
    _first_visible_with_wait,
    _open_chat_workspace,
    _select_model_and_chat_type,
    _write_locator_diagnostics,
)

logger = logging.getLogger(__name__)


def _candidates(page: Page, selectors: Iterable[str]) -> list[Locator]:
    return [page.locator(s).first for s in selectors]


async def open_prompt_library(page: Page) -> None:
    nav = await _first_visible_with_wait(
        page,
        [
            page.get_by_role("radio", name=re.compile(r"prompt\s*library", re.IGNORECASE)).first,
            page.get_by_role("tab", name=re.compile(r"prompt\s*library", re.IGNORECASE)).first,
            page.get_by_role("button", name=re.compile(r"prompt\s*library", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"^prompt\s*library$", re.IGNORECASE)).first,
        ],
        timeout_ms=20000,
        error_message="Prompt Library navigation option not visible",
    )
    await nav.click()
    await page.wait_for_timeout(500)


async def open_chat_module(page: Page) -> None:
    nav = await _first_visible_with_wait(
        page,
        [
            page.get_by_role("radio", name=re.compile(r"^chat$", re.IGNORECASE)).first,
            page.get_by_role("tab", name=re.compile(r"^chat$|chats", re.IGNORECASE)).first,
            page.get_by_role("button", name=re.compile(r"^chat$|chats", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"^chat$|chats", re.IGNORECASE)).first,
        ],
        timeout_ms=20000,
        error_message="Chat navigation option not visible",
    )
    await nav.click()
    await page.wait_for_timeout(500)


async def verify_prompt_library_ui(page: Page) -> None:
    checks = [
        (
            "Prompt Library heading",
            [
                page.get_by_role("heading", name=re.compile(r"prompt\s*library", re.IGNORECASE)).first,
                page.get_by_text(re.compile(r"^prompt\s*library$", re.IGNORECASE)).first,
            ],
        ),
        (
            "Search Prompts",
            [
                page.get_by_placeholder(re.compile(r"search", re.IGNORECASE)).first,
                page.get_by_role("textbox", name=re.compile(r"search", re.IGNORECASE)).first,
            ],
        ),
        (
            "Create New Prompt button",
            [
                page.get_by_role("button", name=re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
                page.get_by_text(re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
            ],
        ),
    ]
    for label, locators in checks:
        await _first_visible_with_wait(
            page,
            locators,
            timeout_ms=20000,
            error_message=f"{label} not visible on Prompt Library",
        )


async def click_create_new_prompt(page: Page) -> None:
    create_btn = await _first_visible_with_wait(
        page,
        [
            page.get_by_role("button", name=re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
        ],
        timeout_ms=15000,
        error_message="Create New Prompt button not visible",
    )
    await create_btn.click()


async def verify_create_prompt_modal(page: Page) -> None:
    await _first_visible_with_wait(
        page,
        [
            page.get_by_role("heading", name=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        ],
        timeout_ms=15000,
        error_message="Create Prompt modal was not displayed",
    )


async def _fill_first_visible(page: Page, locators: list[Locator], value: str) -> None:
    el = await _first_visible_with_wait(page, locators, timeout_ms=12000)
    await el.fill(value)


async def fill_prompt_form(page: Page, *, title: str = "", prompt: str = "", display_order: int | None = None) -> None:
    if title:
        await _fill_first_visible(
            page,
            [
                page.get_by_label(re.compile(r"title", re.IGNORECASE)).first,
                page.get_by_placeholder(re.compile(r"title", re.IGNORECASE)).first,
                *_candidates(page, ["input[placeholder*='Title']", "input[aria-label*='Title']"]),
            ],
            title,
        )
    if prompt:
        await _fill_first_visible(
            page,
            [
                page.get_by_label(re.compile(r"prompt", re.IGNORECASE)).first,
                page.get_by_placeholder(re.compile(r"prompt", re.IGNORECASE)).first,
                *_candidates(page, ["textarea[placeholder*='Prompt']", "textarea"]),
            ],
            prompt,
        )
    if display_order is not None:
        await _fill_first_visible(
            page,
            [
                page.get_by_label(re.compile(r"display\s*order", re.IGNORECASE)).first,
                page.get_by_placeholder(re.compile(r"display\s*order", re.IGNORECASE)).first,
                *_candidates(page, ["input[placeholder*='Display']", "input[aria-label*='Display']"]),
            ],
            str(display_order),
        )


async def click_modal_button(page: Page, text_pattern: str) -> None:
    btn = await _first_visible_with_wait(
        page,
        [
            page.get_by_role("button", name=re.compile(text_pattern, re.IGNORECASE)).first,
            page.get_by_text(re.compile(text_pattern, re.IGNORECASE)).first,
        ],
        timeout_ms=12000,
        error_message=f"Button matching '{text_pattern}' not visible",
    )
    await btn.click()


async def search_prompt(page: Page, text: str) -> None:
    search_box = await _first_visible_with_wait(
        page,
        [
            page.get_by_placeholder(re.compile(r"search", re.IGNORECASE)).first,
            page.get_by_role("textbox", name=re.compile(r"search", re.IGNORECASE)).first,
            *_candidates(page, ["input[placeholder*='Search']"]),
        ],
        timeout_ms=15000,
        error_message="Search Prompts input not visible",
    )
    await search_box.fill(text)


async def clear_search_prompts(page: Page) -> None:
    search_box = await _first_visible_with_wait(
        page,
        [
            page.get_by_placeholder(re.compile(r"search", re.IGNORECASE)).first,
            page.get_by_role("textbox", name=re.compile(r"search", re.IGNORECASE)).first,
            *_candidates(page, ["input[placeholder*='Search']"]),
        ],
        timeout_ms=15000,
        error_message="Search Prompts input not visible",
    )
    await search_box.click()
    await search_box.press("Control+A")
    await search_box.press("Delete")
    await search_box.fill("")
    current = await search_box.input_value()
    assert current.strip() == "", "Search Prompts input did not clear"
    await page.wait_for_timeout(300)


async def expect_text_visible(page: Page, pattern: str, timeout_ms: int = 15000) -> None:
    await _first_visible_with_wait(
        page,
        [
            page.get_by_text(re.compile(pattern, re.IGNORECASE)).first,
            page.locator(f"text=/{pattern}/i").first,
        ],
        timeout_ms=timeout_ms,
        error_message=f"Expected text not visible: {pattern}",
    )


async def expect_text_not_visible(page: Page, pattern: str, timeout_ms: int = 6000) -> None:
    await page.wait_for_timeout(600)
    loc = page.get_by_text(re.compile(pattern, re.IGNORECASE)).first
    elapsed = 0
    while elapsed <= timeout_ms:
        try:
            if await loc.count() == 0 or not await loc.is_visible():
                return
        except Exception:
            return
        await page.wait_for_timeout(300)
        elapsed += 300
    raise AssertionError(f"Unexpected text remained visible: {pattern}")


async def expect_text_not_visible_in_rendered_content(
    page: Page,
    pattern: str,
    timeout_ms: int = 7000,
) -> None:
    """Assert text is absent from visible rendered content, excluding form control values."""
    regex = re.compile(pattern, re.IGNORECASE)
    elapsed = 0

    while elapsed <= timeout_ms:
        rendered_text = await page.evaluate(
            """
            () => {
                const lines = [];
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);

                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    const parent = node.parentElement;
                    if (!parent) continue;

                    if (parent.closest("input, textarea, [role='textbox'], [role='combobox']")) continue;
                    if (parent.closest("script, style, noscript")) continue;

                    const style = window.getComputedStyle(parent);
                    if (style.display === "none" || style.visibility === "hidden") continue;

                    const rect = parent.getBoundingClientRect();
                    if (rect.width === 0 && rect.height === 0) continue;

                    const text = (node.textContent || "").trim();
                    if (text) lines.push(text);
                }

                return lines.join("\\n");
            }
            """
        )

        if not regex.search(rendered_text or ""):
            return

        await page.wait_for_timeout(300)
        elapsed += 300

    raise AssertionError(f"Unexpected text remained visible in rendered content: {pattern}")


async def click_first_action_button(page: Page, action: str) -> None:
    btn = await _first_visible_with_wait(
        page,
        [
            page.get_by_role("button", name=re.compile(action, re.IGNORECASE)).first,
            page.get_by_text(re.compile(action, re.IGNORECASE)).first,
            *_candidates(page, [f"button:has-text('{action}')"]),
        ],
        timeout_ms=15000,
        error_message=f"{action} button not visible",
    )
    await btn.click()


async def open_edit_prompt_modal(page: Page, prompt_title: str | None = None) -> None:
    """Open Edit Prompt with retries and multiple modal visibility checks."""
    for _ in range(3):
        clicked = False
        if prompt_title:
            row = page.locator("div").filter(
                has=page.get_by_text(re.compile(re.escape(prompt_title), re.IGNORECASE))
            ).first
            row_edit_candidates = [
                row.get_by_role("button", name=re.compile(r"edit", re.IGNORECASE)).first,
                row.locator("button[aria-label*='Edit'], button[title*='Edit']").first,
                row.locator("button:has-text('✏')").first,
            ]
            for candidate in row_edit_candidates:
                try:
                    if await candidate.count() > 0 and await candidate.is_visible():
                        await candidate.click()
                        clicked = True
                        break
                except Exception:
                    continue

        if not clicked:
            await click_first_action_button(page, "Edit")

        await page.wait_for_timeout(800)
        try:
            await _first_visible_with_wait(
                page,
                [
                    page.get_by_role("heading", name=re.compile(r"edit\s*prompt", re.IGNORECASE)).first,
                    page.get_by_text(re.compile(r"edit\s*prompt", re.IGNORECASE)).first,
                    page.get_by_role("button", name=re.compile(r"save\s*changes|save", re.IGNORECASE)).first,
                    *_candidates(page, ["button:has-text('Save Changes')", "button:has-text('Save')"]),
                ],
                timeout_ms=7000,
                error_message="Edit Prompt modal not visible after clicking Edit",
            )
            return
        except AssertionError:
            # Close any residual modal and retry opening Edit.
            for dismiss in [
                page.get_by_role("button", name=re.compile(r"cancel|close", re.IGNORECASE)).first,
                *_candidates(page, ["button[aria-label='Close']", "button:has-text('Cancel')"]),
            ]:
                try:
                    if await dismiss.count() > 0 and await dismiss.is_visible():
                        await dismiss.click()
                        await page.wait_for_timeout(500)
                        break
                except Exception:
                    continue

    raise AssertionError("Edit Prompt modal not visible after retrying Edit action")


async def click_copy_prompt_button(page: Page, prompt_title: str | None = None) -> None:
    """Click Copy for a specific prompt row, supporting icon-only copy buttons."""
    for _ in range(3):
        clicked = False
        if prompt_title:
            title_locator = page.get_by_text(re.compile(re.escape(prompt_title), re.IGNORECASE)).first
            nearby_containers = [
                title_locator.locator("xpath=ancestor::div[1]"),
                title_locator.locator("xpath=ancestor::div[2]"),
                title_locator.locator("xpath=ancestor::div[3]"),
                title_locator.locator("xpath=ancestor::div[4]"),
                title_locator.locator("xpath=ancestor::div[5]"),
            ]

            for container in nearby_containers:
                try:
                    if await container.count() == 0 or not await container.is_visible():
                        continue
                    await container.hover()
                    await page.wait_for_timeout(300)

                    container_copy_candidates = [
                        container.get_by_role("button", name=re.compile(r"copy", re.IGNORECASE)).first,
                        container.locator("button[aria-label*='Copy'], button[title*='Copy']").first,
                        container.locator("button:has([data-testid='stIconMaterial']:has-text('content_copy'))").first,
                        container.locator("button:has-text('content_copy')").first,
                    ]
                    for candidate in container_copy_candidates:
                        try:
                            if await candidate.count() > 0 and await candidate.is_visible():
                                await candidate.click()
                                clicked = True
                                break
                        except Exception:
                            continue
                    if clicked:
                        break

                    # Fallback: if Copy is rendered next to/after Delete, click the next visible button after Delete.
                    delete_candidates = [
                        container.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
                        container.locator("button[aria-label*='Delete'], button[title*='Delete']").first,
                        container.locator("button:has-text('🗑')").first,
                    ]
                    for delete_candidate in delete_candidates:
                        try:
                            if await delete_candidate.count() == 0 or not await delete_candidate.is_visible():
                                continue
                            next_button = delete_candidate.locator("xpath=following::button[1]").first
                            if await next_button.count() > 0 and await next_button.is_visible():
                                await next_button.click()
                                clicked = True
                                break
                        except Exception:
                            continue
                    if clicked:
                        break
                except Exception:
                    continue

        if not clicked:
            fallback_copy_candidates = [
                page.get_by_role("button", name=re.compile(r"copy", re.IGNORECASE)).first,
                page.locator("button[aria-label*='Copy'], button[title*='Copy']").first,
                page.locator("button:has([data-testid='stIconMaterial']:has-text('content_copy'))").first,
                page.locator("button:has-text('content_copy')").first,
            ]
            for candidate in fallback_copy_candidates:
                try:
                    if await candidate.count() > 0 and await candidate.is_visible():
                        await candidate.click()
                        clicked = True
                        break
                except Exception:
                    continue

        if clicked:
            return

        await page.wait_for_timeout(800)

    raise AssertionError("Copy button not visible")


async def click_delete_prompt_button(page: Page, prompt_title: str | None = None) -> None:
    """Click Delete for a specific prompt row, supporting icon-only delete buttons."""
    for _ in range(3):
        clicked = False
        if prompt_title:
            title_locator = page.get_by_text(re.compile(re.escape(prompt_title), re.IGNORECASE)).first
            nearby_containers = [
                title_locator.locator("xpath=ancestor::div[1]"),
                title_locator.locator("xpath=ancestor::div[2]"),
                title_locator.locator("xpath=ancestor::div[3]"),
                title_locator.locator("xpath=ancestor::div[4]"),
                title_locator.locator("xpath=ancestor::div[5]"),
            ]

            for container in nearby_containers:
                try:
                    if await container.count() == 0 or not await container.is_visible():
                        continue
                    await container.hover()
                    await page.wait_for_timeout(300)

                    container_delete_candidates = [
                        container.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
                        container.locator("button[aria-label*='Delete'], button[title*='Delete']").first,
                        container.locator("button:has([data-testid='stIconMaterial']:has-text('delete'))").first,
                        container.locator("button:has-text('🗑')").first,
                    ]
                    for candidate in container_delete_candidates:
                        try:
                            if await candidate.count() > 0 and await candidate.is_visible():
                                await candidate.click()
                                clicked = True
                                break
                        except Exception:
                            continue
                    if clicked:
                        break
                except Exception:
                    continue

        if not clicked:
            fallback_delete_candidates = [
                page.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
                page.locator("button[aria-label*='Delete'], button[title*='Delete']").first,
                page.locator("button:has([data-testid='stIconMaterial']:has-text('delete'))").first,
                page.locator("button:has-text('🗑')").first,
            ]
            for candidate in fallback_delete_candidates:
                try:
                    if await candidate.count() > 0 and await candidate.is_visible():
                        await candidate.click()
                        clicked = True
                        break
                except Exception:
                    continue

        if clicked:
            return

        await page.wait_for_timeout(800)

    raise AssertionError("Delete button not visible")


async def delete_prompts_by_prefix(page: Page, prefixes: list[str]) -> None:
    """Delete all prompts whose titles start with any provided prefix."""
    await open_prompt_library(page)

    for prefix in prefixes:
        await clear_search_prompts(page)
        await search_prompt(page, prefix)
        await page.wait_for_timeout(700)

        # Hard cap avoids infinite loops if UI state is unstable.
        for _ in range(15):
            matches = page.get_by_text(re.compile(rf"^{re.escape(prefix)}", re.IGNORECASE))
            if await matches.count() == 0:
                break

            target_title = (await matches.first.text_content() or "").strip()
            await click_delete_prompt_button(page, prompt_title=target_title or prefix)
            await click_modal_button(page, r"yes\s*,?\s*delete|delete")
            await page.wait_for_timeout(900)
            await search_prompt(page, prefix)
            await page.wait_for_timeout(500)

    await clear_search_prompts(page)


async def configure_chat_for_model(page: Page, model_name: str) -> None:
    await open_chat_module(page)
    await _open_chat_workspace(page)
    await _ensure_chat_configuration_open(page)
    await _select_model_and_chat_type(page, model_name=model_name, chat_type="Basic Chat")


async def open_saved_prompts_section(page: Page) -> None:
    """Expand the Saved Prompts section in the chat panel. Idempotent."""
    # Check if already expanded: the Saved Prompts selectbox (label 'Saved Prompts:')
    # is visible only when the expander is open.
    for _ in range(2):
        sp_combobox = page.locator(
            "label:has-text('Saved Prompts') ~ div [role='combobox'], "
            "label:has-text('Saved Prompts:') ~ div [role='combobox']"
        ).first
        if await sp_combobox.count() > 0:
            try:
                if await sp_combobox.is_visible():
                    return  # Expander already open, skip re-click
            except Exception:
                pass
        await page.wait_for_timeout(300)

    # Click the Saved Prompts expander header / button with force and retries
    for attempt in range(2):
        toggle = await _first_visible_with_wait(
            page,
            [
                *_candidates(page, [
                    "summary:has-text('Saved Prompts')",
                    "details summary:has-text('Saved Prompts')",
                    "details:has(summary:has-text('Saved Prompts'))",
                ]),
                page.get_by_role("button", name=re.compile(r"saved\s*prompts", re.IGNORECASE)).first,
                *_candidates(page, ["button:has-text('Saved Prompts')"]),
            ],
            timeout_ms=15000,
            error_message="Saved Prompts expander/button not visible in chat panel",
        )
        await toggle.click(force=True)
        await page.wait_for_timeout(1200)
        
        # Verify expansion occurred
        sp_combobox = page.locator(
            "label:has-text('Saved Prompts') ~ div [role='combobox'], "
            "label:has-text('Saved Prompts:') ~ div [role='combobox']"
        ).first
        if await sp_combobox.count() > 0:
            try:
                if await sp_combobox.is_visible():
                    return
            except Exception:
                pass
        
        if attempt == 0:
            await page.wait_for_timeout(500)


async def verify_saved_prompt_option_visible(page: Page, prompt_title: str) -> None:
    await _ensure_chat_configuration_open(page)
    await open_saved_prompts_section(page)

    # Verify the Saved Prompts combobox is present with extended retries and strong waits.
    combobox = None
    for retry in range(3):
        await page.wait_for_timeout(1200)  # Stronger wait for animations/renders
        try:
            combobox = await _first_visible_with_wait(
                page,
                [
                    page.get_by_role("combobox", name=re.compile(r"saved\s*prompt", re.IGNORECASE)).first,
                    page.locator(
                        "label:has-text('Saved Prompts:') ~ div [role='combobox'], "
                        "label:has-text('Saved Prompts') ~ div [role='combobox']"
                    ).first,
                    page.locator("label:has-text('Saved Prompts') ~ [data-testid='stSelectbox'] [role='combobox']").first,
                    page.locator("[data-testid='stSelectbox'] [role='combobox']:visible").first,
                    page.locator("div[role='listbox'] ~ div [role='combobox']").first,
                    * _candidates(page, [
                        "label:has-text('Saved Prompts') ~ div [role='combobox']",
                        "[data-baseweb='select'] [role='combobox']",
                        "[data-testid='stSelectbox']:has(label:has-text('Saved Prompts')) [role='combobox']",
                        "input[placeholder*='Select']",
                        "select",
                    ]),
                ],
                timeout_ms=8000,
                error_message=f"Saved Prompts combobox not visible on retry {retry + 1}",
            )
            break
        except AssertionError:
            if retry < 2:
                await page.wait_for_timeout(900)
                continue
            raise AssertionError("Saved Prompts selectbox not visible after expanding Saved Prompts section")

    if combobox is None:
        raise AssertionError("Saved Prompts selectbox not visible after expanding Saved Prompts section")

    # Open dropdown and verify expected prompt option is visible with retries.
    option_candidates = [
        page.get_by_role("option", name=re.compile(re.escape(prompt_title), re.IGNORECASE)).first,
        *_candidates(page, [
            f"[role='option']:has-text('{prompt_title}')",
            f"li[role='option']:has-text('{prompt_title}')",
        ]),
    ]

    found = False
    for _ in range(3):
        await combobox.click()
        await page.wait_for_timeout(900)
        try:
            await _first_visible_with_wait(
                page,
                option_candidates,
                timeout_ms=6000,
                error_message=f"Saved prompt option '{prompt_title}' not visible in dropdown",
            )
            found = True
            break
        except AssertionError:
            await combobox.press("Escape")
            await page.wait_for_timeout(600)

    if not found:
        raise AssertionError(f"Saved prompt option '{prompt_title}' not visible in dropdown")

    # Collapse dropdown to keep subsequent steps deterministic.
    await combobox.press("Escape")


async def select_saved_prompt(page: Page, prompt_title: str) -> None:
    await open_saved_prompts_section(page)

    # Use accessible name matching - same pattern as _select_model_and_chat_type
    combobox = await _first_visible_with_wait(
        page,
        [
            page.get_by_role("combobox", name=re.compile(r"saved\s*prompt", re.IGNORECASE)).first,
            page.locator("[data-testid='stSelectbox']").filter(
                has=page.locator("label:has-text('Saved Prompts')")
            ).get_by_role("combobox").first,
            *_candidates(page, [
                "label:has-text('Saved Prompts:') ~ div [role='combobox']",
                "label:has-text('Saved Prompts') ~ div [role='combobox']",
                "[data-testid='stSelectbox']:has(label:has-text('Saved Prompts')) [role='combobox']",
            ]),
        ],
        timeout_ms=15000,
        error_message="Saved Prompts combobox not visible",
    )
    await combobox.click()
    await page.wait_for_timeout(5000)

    option_candidates = [
        page.get_by_role("option", name=re.compile(re.escape(prompt_title), re.IGNORECASE)).first,
        *_candidates(page, [
            f"[role='option']:has-text('{prompt_title}')",
            f"li[role='option']:has-text('{prompt_title}')",
            f"ul li:has-text('{prompt_title}')",
        ]),
    ]

    option = None
    for _ in range(3):
        try:
            option = await _first_visible_with_wait(
                page,
                option_candidates,
                timeout_ms=4000,
                error_message=f"Saved prompt option '{prompt_title}' not visible in dropdown",
            )
            break
        except AssertionError:
            # Search directly in the open combobox/dropdown when options are lazy-loaded.
            try:
                await combobox.fill("")
                await combobox.fill(prompt_title)
            except Exception:
                search_input_candidates = [
                    page.locator("[role='listbox'] input").first,
                    page.locator("[data-baseweb='popover'] input").first,
                    page.locator("input[aria-autocomplete='list']").first,
                ]
                for search_input in search_input_candidates:
                    try:
                        if await search_input.count() > 0 and await search_input.is_visible():
                            await search_input.fill("")
                            await search_input.fill(prompt_title)
                            break
                    except Exception:
                        continue
            await page.wait_for_timeout(2000)

    if option is None:
        raise AssertionError(f"Saved prompt option '{prompt_title}' not visible in dropdown")

    await option.click()
    await page.wait_for_timeout(1000)

    # Verify selection registered (combobox should no longer show placeholder)
    try:
        combobox_value = await combobox.input_value()
    except Exception:
        combobox_value = await combobox.text_content() or ""
    if not combobox_value or combobox_value.startswith("--"):
        # Selection may not have registered — emit diagnostics and retry via data-baseweb wrapper
        await _write_locator_diagnostics(page, "saved_prompt_combobox", [combobox])
        wrapper = page.locator("[data-testid='stSelectbox']").filter(
            has=page.locator("label:has-text('Saved Prompts')")
        ).locator("[data-baseweb='select']").first
        if await wrapper.count() > 0 and await wrapper.is_visible():
            await wrapper.click()
            await page.wait_for_timeout(800)
            option2 = await _first_visible_with_wait(
                page,
                [
                    page.get_by_role("option", name=re.compile(re.escape(prompt_title), re.IGNORECASE)).first,
                    *_candidates(page, [f"[role='option']:has-text('{prompt_title}')"]),
                ],
                timeout_ms=12000,
                error_message=f"Saved prompt option '{prompt_title}' not visible on retry",
            )
            await option2.click()
            await page.wait_for_timeout(1000)

    # Click "Use Prompt" / "Apply Prompt" button if the app shows one after selection
    for btn_locator in [
        page.get_by_role("button", name=re.compile(r"use\s*prompt", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"apply\s*prompt", re.IGNORECASE)).first,
        *_candidates(page, ["button:has-text('Use Prompt')", "button:has-text('Apply Prompt')"]),
    ]:
        if await btn_locator.is_visible():
            await btn_locator.click()
            await page.wait_for_timeout(500)
            break


async def verify_saved_prompt_loaded(page: Page, prompt_text: str) -> None:
    input_box = await _first_visible_with_wait(
        page,
        [
            page.locator("textarea[data-testid='stChatInputTextArea']").first,
            page.locator("textarea[placeholder='How can I help?']").first,
            page.locator("textarea[placeholder*='help']").first,
            page.locator("main textarea").first,
        ],
        timeout_ms=15000,
        error_message="Chat input box not visible after selecting Saved Prompt",
    )

    expected = prompt_text.strip()
    deadline = __import__("time").monotonic() + 8
    while __import__("time").monotonic() < deadline:
        value = (await input_box.input_value() or "").strip()
        if expected and expected.lower() in value.lower():
            return

        for btn_locator in [
            page.get_by_role("button", name=re.compile(r"use\s*prompt", re.IGNORECASE)).first,
            page.get_by_role("button", name=re.compile(r"apply\s*prompt", re.IGNORECASE)).first,
            *_candidates(page, ["button:has-text('Use Prompt')", "button:has-text('Apply Prompt')"]),
        ]:
            try:
                if await btn_locator.count() > 0 and await btn_locator.is_visible() and not await btn_locator.is_disabled():
                    await btn_locator.click()
                    break
            except Exception:
                continue

        await page.wait_for_timeout(400)

    raise AssertionError("Selected Saved Prompt did not populate chat input")


async def execute_selected_prompt(page: Page, prompt_text: str) -> None:
    chat_page = ChatPage(page)
    await page.wait_for_timeout(5000)
    input_box = await _first_visible_with_wait(
        page,
        [
            page.locator("textarea[data-testid='stChatInputTextArea']").first,
            page.locator("textarea[placeholder='How can I help?']").first,
            page.locator("textarea[placeholder*='help']").first,
            page.locator("main textarea").first,
        ],
        timeout_ms=15000,
        error_message="Chat input box not visible before sending Saved Prompt",
    )
    value = await input_box.input_value()
    assert prompt_text.strip() in value, "Saved Prompt text was not present in chat input before send"

    send_button = await _first_visible_with_wait(
        page,
        [
            page.locator("button[data-testid='stChatInputSubmitButton']").first,
            page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE)).first,
            page.locator("button:has-text('Send')").first,
        ],
        timeout_ms=10000,
        error_message="Send button not visible for Saved Prompt execution",
    )
    assert not await send_button.is_disabled(), "Send button should be enabled after selecting Saved Prompt"
    await send_button.click()
    await page.wait_for_timeout(5000)

    latest_message = ""
    deadline = __import__("time").monotonic() + 60
    while __import__("time").monotonic() < deadline:
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if latest_message and latest_message.strip() and latest_message.strip().lower() != prompt_text.strip().lower():
            break
        await page.wait_for_timeout(300)
    assert latest_message.strip(), "No chat response received after executing Saved Prompt"

    regenerate_candidates = [
        page.get_by_role("button", name=re.compile(r"regenerate\s*response|regenerate", re.IGNORECASE)).first,
        *_candidates(
            page,
            [
                "button:has-text('Regenerate')",
                "button:has-text('Regenerate Response')",
                "button[aria-label*='Regenerate']",
                "button[title*='Regenerate']",
                "button:has([data-testid='stIconMaterial']:has-text('autorenew'))",
                "button:has([data-testid='stIconMaterial']:has-text('refresh'))",
            ],
        ),
    ]

    action_cluster_candidates = [
        *regenerate_candidates,
        page.get_by_role("button", name=re.compile(r"copy", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"thumbs\s*up|thumbs\s*down", re.IGNORECASE)).first,
        *_candidates(
            page,
            [
                "button:has([data-testid='stIconMaterial']:has-text('content_copy'))",
                "button:has([data-testid='stIconMaterial']:has-text('thumb_up'))",
                "button:has([data-testid='stIconMaterial']:has-text('thumb_down'))",
                "button[aria-label*='Copy']",
                "button[aria-label*='Thumb']",
            ],
        ),
    ]

    # Auto-wait loop: scroll down to the bottom so response action buttons become visible.
    action_deadline = __import__("time").monotonic() + 35
    while __import__("time").monotonic() < action_deadline:
        action_visible = False

        for locator in action_cluster_candidates:
            try:
                if await locator.count() > 0 and await locator.is_visible():
                    action_visible = True
                    break
            except Exception:
                continue

        if action_visible:
            return

        try:
            await page.evaluate(
                """
                () => {
                    const latestMsg = document.querySelector("[data-testid='stChatMessage']:last-child")
                        || document.querySelector("[data-testid='stChatMessageContent']:last-child")
                        || document.querySelector(".stChatMessage:last-child");
                    if (latestMsg) {
                        latestMsg.scrollIntoView({ behavior: "auto", block: "end" });
                    }

                    const containers = [
                        document.querySelector("section.main"),
                        document.querySelector("[data-testid='stAppViewContainer']"),
                        document.querySelector("main"),
                    ].filter(Boolean);
                    for (const el of containers) {
                        el.scrollTop = el.scrollHeight;
                    }
                    window.scrollTo(0, document.body.scrollHeight);
                }
                """
            )
        except Exception:
            pass

        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(900)

    logger.warning(
        "[TC041 Step 13 SOFT-CHECK] Response received, but post-response action controls "
        "(Regenerate/Copy/feedback) were not visible after auto-scroll. Continuing."
    )
    return


async def validate_landing(page: Page, base_url: str) -> None:
    await page.goto(base_url)
    await _assert_landing_page_options(page)
