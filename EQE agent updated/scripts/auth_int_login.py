"""
INT Environment — Manual Login & Storage State Saver
=====================================================
Opens a headed Chromium browser to the INT Okta login page.
Complete the MFA flow manually, and the script saves the authenticated
browser session (cookies/localStorage) to a storage state JSON file.

This saved state is then reused by pytest for headless INT test runs.

Usage:
    python scripts/auth_int_login.py              # default: saves to config/.auth/int_storage_state.json
    python scripts/auth_int_login.py --output path/to/state.json

For Harness CI/CD:
    1. Run this script on a schedule (e.g., every 3-4 hours) on a machine
       where someone can complete MFA, then upload the state file as an artifact.
    2. Or request a service account with MFA exemption from IT/Security.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright
from utils.config_loader import load_config


DEFAULT_STATE_PATH = PROJECT_ROOT / "config" / ".auth" / "int_storage_state.json"
INT_LOGIN_URL = "https://csgpt.int.ai.caresource.corp/"
WAIT_PATTERN = "*csgpt.int.ai.caresource*"
MAX_WAIT_SEC = 300  # 5 minutes max for MFA completion


async def run_login(output_path: Path) -> None:
    config = load_config()
    env_config = config.get("environments", {}).get("int", {})
    login_url = env_config.get("auth", {}).get("login_url", INT_LOGIN_URL)
    wait_pattern = env_config.get("auth", {}).get("wait_for_url_pattern", WAIT_PATTERN)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  INT Environment — Manual Login")
    print("=" * 60)
    print(f"  Login URL : {login_url}")
    print(f"  Save to   : {output_path}")
    print(f"  Timeout   : {MAX_WAIT_SEC}s")
    print()
    print("  A browser window will open. Please complete the Okta")
    print("  login + MFA flow. The session will be saved once the")
    print("  DocuChat app loads successfully.")
    print("=" * 60)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        print("[1/4] Navigating to INT login page...")
        try:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  Navigation note: {e}")

        print(f"  Current URL: {page.url}")
        print()
        print("[2/4] Waiting for you to complete login + MFA...")
        print("       (Complete the Okta flow in the opened browser)")
        print()

        # Wait until the URL shows we're back on the DocuChat app
        start = time.time()
        logged_in = False
        while time.time() - start < MAX_WAIT_SEC:
            current_url = page.url
            # Check if we've landed back on the app (not on Okta)
            if "csgpt.int.ai.caresource" in current_url and "okta" not in current_url:
                # Give the app a moment to fully load
                print(f"  Detected app URL: {current_url}")
                print("  Waiting for app to fully render...")
                await page.wait_for_timeout(5000)
                logged_in = True
                break
            await page.wait_for_timeout(2000)

        if not logged_in:
            print(f"\n  ERROR: Login not completed within {MAX_WAIT_SEC}s.")
            print(f"  Final URL: {page.url}")
            await browser.close()
            sys.exit(1)

        print(f"  App loaded at: {page.url}")
        print(f"  Page title: {await page.title()}")
        print()

        # Save storage state (cookies + localStorage)
        print("[3/4] Saving authenticated session...")
        state = await context.storage_state()

        # Add metadata for freshness tracking
        state["_meta"] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "environment": "int",
            "login_url": login_url,
            "final_url": page.url,
        }

        output_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"  Saved to: {output_path}")
        print()

        print("[4/4] Verifying saved state...")
        # Quick verification: open a new context with the saved state
        verify_context = await browser.new_context(
            storage_state=str(output_path),
            ignore_https_errors=True,
        )
        verify_page = await verify_context.new_page()
        try:
            await verify_page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            await verify_page.wait_for_timeout(5000)
            final_url = verify_page.url
            if "csgpt.int.ai.caresource" in final_url and "okta" not in final_url:
                print(f"  Verification PASSED — session is valid.")
                print(f"  URL: {final_url}")
            else:
                print(f"  WARNING: Verification ended on: {final_url}")
                print(f"  The saved state may not work. Try logging in again.")
        except Exception as e:
            print(f"  Verification error: {e}")
        finally:
            await verify_context.close()

        await browser.close()

    print()
    print("=" * 60)
    print("  Done! You can now run INT tests:")
    print(f"  pytest tests/ --env=int -v")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="INT Okta login & session saver")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help=f"Path to save storage state JSON (default: {DEFAULT_STATE_PATH})",
    )
    args = parser.parse_args()
    asyncio.run(run_login(args.output))


if __name__ == "__main__":
    main()
