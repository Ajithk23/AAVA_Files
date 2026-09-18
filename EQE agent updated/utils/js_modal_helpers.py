"""
utils/js_modal_helpers.py
--------------------------
Reusable JavaScript-injection helpers for interacting with Streamlit modals/dialogs
across all DocuChat test cases (chat, file management, prompt library, and future suites).

Supported modal containers (auto-detected in priority order):
  - div[data-modal-container="true"]   — Streamlit st.dialog / st.modal containers
  - [data-testid="stModal"]            — legacy stModal test-id
  - [role="dialog"]                    — WAI-ARIA dialog role
  - [data-baseweb="modal"]             — Base Web / Streamlit internal
  - [aria-modal="true"]                — any aria-modal marked element

Usage (any test file):
    from utils.js_modal_helpers import (
        js_wait_for_modal,
        js_set_modal_input,
        js_get_modal_input_value,
        js_click_modal_button,
        js_get_modal_text,
    )
"""

from __future__ import annotations

import time

from playwright.async_api import Page

__all__ = [
    "js_wait_for_modal",
    "js_set_modal_input",
    "js_get_modal_input_value",
    "js_click_modal_button",
    "js_get_modal_text",
]

# ---------------------------------------------------------------------------
# Internal CSS selectors for modal containers
# ---------------------------------------------------------------------------
_MODAL_CONTAINER_SELECTORS: list[str] = [
    'div[data-modal-container="true"]',
    '[data-testid="stModal"]',
    '[data-testid="stDialog"]',
    '[data-testid="stPopover"]',
    '[class*="stDialog"]',
    '[role="dialog"]',
    '[data-baseweb="modal"]',
    '[data-baseweb="popover"]',
    '[aria-modal="true"]',
]

_MODAL_INPUT_SELECTORS: list[str] = [
    'div[data-modal-container="true"] input[type="text"]',
    '[data-testid="stModal"] input[type="text"]',
    '[role="dialog"] input[type="text"]',
    '[aria-modal="true"] input[type="text"]',
]

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def js_wait_for_modal(page: Page, timeout_ms: int = 15000) -> bool:
    """Wait for a Streamlit modal/dialog to become visible via JS evaluation.

    Returns True as soon as a visible modal is detected, False if timed out.
    """
    deadline = time.monotonic() + (timeout_ms / 1000)
    selectors_js = ", ".join(f"'{s}'" for s in _MODAL_CONTAINER_SELECTORS)
    while time.monotonic() < deadline:
        found: bool = await page.evaluate(f"""() => {{
            const selectors = [{selectors_js}];
            for (const sel of selectors) {{
                const el = document.querySelector(sel);
                if (el) {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) return true;
                }}
            }}
            return false;
        }}""")
        if found:
            return True
        await page.wait_for_timeout(200)
    return False


async def js_set_modal_input(page: Page, value: str) -> bool:
    """Set a text value in the modal's input field using the React-compatible
    native HTMLInputElement value setter, then fire input + change events.

    Returns True if an input was found and updated, False otherwise.
    """
    selectors_js = ", ".join(f"'{s}'" for s in _MODAL_INPUT_SELECTORS)
    return await page.evaluate(f"""(value) => {{
        const selectors = [{selectors_js}];
        for (const sel of selectors) {{
            const el = document.querySelector(sel);
            if (el && el.offsetParent !== null) {{
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(el, value);
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
        }}
        return false;
    }}""", value)


async def js_get_modal_input_value(page: Page) -> str:
    """Read the current value of the first visible input inside a modal via JS.

    Returns the value string, or empty string if none found.
    """
    selectors_js = ", ".join(f"'{s}'" for s in _MODAL_INPUT_SELECTORS)
    return await page.evaluate(f"""() => {{
        const selectors = [{selectors_js}];
        for (const sel of selectors) {{
            const el = document.querySelector(sel);
            if (el && el.offsetParent !== null) return el.value;
        }}
        return '';
    }}""")


async def js_click_modal_button(page: Page, button_text: str) -> bool:
    """Click a button inside a modal by matching its text content via JS injection.

    The match is case-insensitive and uses substring matching as a fallback.
    Returns True if the button was found and clicked, False otherwise.
    """
    container_selectors_js = ", ".join(f"'{s}'" for s in [*_MODAL_CONTAINER_SELECTORS, "body"])
    return await page.evaluate(f"""(text) => {{
        const containerSelectors = [{container_selectors_js}];
        const lower = text.toLowerCase();
        for (const containerSel of containerSelectors) {{
            const container = document.querySelector(containerSel);
            if (!container) continue;
            const buttons = container.querySelectorAll('button');
            for (const btn of buttons) {{
                const btnText = btn.textContent.trim().toLowerCase();
                if (btnText === lower || btnText.includes(lower)) {{
                    btn.click();
                    return true;
                }}
            }}
        }}
        return false;
    }}""", button_text)


async def js_get_modal_text(page: Page) -> str:
    """Return all visible text content inside a modal via JS evaluation.

    Useful for detecting validation messages, character-limit warnings, etc.
    Returns empty string if no modal is visible.
    """
    selectors_js = ", ".join(f"'{s}'" for s in _MODAL_CONTAINER_SELECTORS)
    return await page.evaluate(f"""() => {{
        const selectors = [{selectors_js}];
        for (const sel of selectors) {{
            const el = document.querySelector(sel);
            if (el) {{
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) return el.innerText || el.textContent || '';
            }}
        }}
        return '';
    }}""")
