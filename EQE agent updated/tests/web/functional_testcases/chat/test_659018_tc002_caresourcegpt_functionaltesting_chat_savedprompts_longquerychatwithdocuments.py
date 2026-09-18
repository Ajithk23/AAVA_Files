"""TC-INT-02 — Verify Chat Threads are created when initiating long query with Chat with Documents using 5-mini INT model via Saved Prompts.

Test Case Name : TC02 - Verify Chat Threads are created when initiating long query with
                 Chat with Documents using 5-mini INT model via Saved Prompts
Description    : Verify that a chat thread is created when a long query is initiated via a
                 Saved Prompt using Chat with Documents with the 5-mini INT model.
Pre-condition  : User has valid DocuChat access.
Feature        : INT
Environment    : INT
URL            : https://csgpt.int.ai.caresource.corp/
"""
from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path

import pytest
from playwright.async_api import Page, Locator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if __name__ == "__main__":
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    if venv_python.exists() and current_python != venv_python.resolve():
        import subprocess
        raise SystemExit(subprocess.call([str(venv_python), __file__]))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pages.chat_page import ChatPage
from utils.step_runner import run_step as _run_step
from utils.test_data_loader import get_chat_int_tc02_inputs as _get_inputs, ChatIntTC02Inputs
from tests.web.functional_testcases.chat.chat_test_helpers import (
    _assert_landing_page_options,
    _open_chat_workspace,
    _ensure_chat_configuration_open,
    _select_model_and_chat_type,
    _select_file_for_chat_context,
    _first_visible_with_wait,
    _write_locator_diagnostics,
    _cleanup_delete_chat_thread,
    _cleanup_delete_prompt_by_title,
)
from tests.web.functional_testcases.file_Management.file_management_test_helpers import (
    _navigate_to_file_management,
    _upload_and_verify_tolerant,
    _cleanup_delete_uploaded_file,
    _wait_for_file_ready_status,
)

_TC_NAME = "TC-INT-02"
_TC_INT_02_FILE_PREFIX = "TC-INT-02"

logger = logging.getLogger(__name__)

DEBUG_DIR = PROJECT_ROOT / "reports" / "screenshots"


# ── Prompt Library helpers ────────────────────────────────────────────────────

async def _navigate_to_prompt_library_module(page: Page) -> None:
    """Navigate to the Prompt Library module via the sidebar."""
    nav_candidates = [
        page.get_by_role("radio", name=re.compile(r"prompt\s*library", re.IGNORECASE)).first,
        page.locator("[data-testid='stSidebar'] label:has-text('Prompt Library')").first,
        page.locator("[data-testid='stSidebarContent'] label:has-text('Prompt Library')").first,
        page.locator("label:text-is('Prompt Library')").first,
        page.get_by_role("tab", name=re.compile(r"prompt\s*library|prompts?", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"prompt\s*library", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"^prompt\s*library$", re.IGNORECASE)).first,
    ]
    try:
        nav_item = await _first_visible_with_wait(
            page,
            nav_candidates,
            timeout_ms=20000,
            error_message="Prompt Library navigation item not visible in sidebar",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "prompt_library_nav", nav_candidates)
        raise
    await nav_item.click()
    # Event-driven: wait for Streamlit to process the navigation re-run
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass  # networkidle may not fire on SPAs; ready_candidates check below handles this

    # Wait for Prompt Library module to finish loading
    ready_candidates = [
        page.get_by_role("button", name=re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"prompt\s*library", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        ready_candidates,
        timeout_ms=25000,
        error_message="Prompt Library module did not load after navigation",
    )


async def _click_create_new_prompt_button(page: Page) -> None:
    """Click the 'Create New Prompt' button and wait for the dialog to appear."""
    btn_candidates = [
        page.get_by_role("button", name=re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
        page.locator("button:has-text('Create New Prompt')").first,
        page.locator("button:has-text('New Prompt')").first,
        page.get_by_text(re.compile(r"create\s*new\s*prompt", re.IGNORECASE)).first,
    ]
    try:
        btn = await _first_visible_with_wait(
            page,
            btn_candidates,
            timeout_ms=20000,
            error_message="'Create New Prompt' button not visible in Prompt Library",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "create_new_prompt_btn", btn_candidates)
        raise
    await btn.click()

    # Wait for the Create Prompt dialog to open
    dialog_candidates = [
        page.locator("div[data-modal-container='true']").first,
        page.locator("[data-testid='stDialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator("[role='dialog']").first,
        page.locator("[aria-modal='true']").first,
    ]
    await _first_visible_with_wait(
        page,
        dialog_candidates,
        timeout_ms=15000,
        error_message="'Create Prompt' dialog did not appear after clicking button",
    )


async def _verify_create_prompt_dialog_ui(page: Page) -> None:
    """Step 4: Verify all required UI elements in the Create Prompt dialog."""
    # Title field
    title_candidates = [
        page.locator("[role='dialog'] label").filter(has_text=re.compile(r"^title", re.IGNORECASE)).first,
        page.locator("div[data-modal-container='true'] label").filter(has_text=re.compile(r"^title", re.IGNORECASE)).first,
        page.locator("[role='dialog'] input[type='text']").first,
        page.get_by_label(re.compile(r"title", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        title_candidates,
        timeout_ms=15000,
        error_message="Title field not visible in Create Prompt dialog",
    )

    # Description textarea
    desc_candidates = [
        page.locator("[role='dialog'] label").filter(has_text=re.compile(r"description", re.IGNORECASE)).first,
        page.locator("div[data-modal-container='true'] label").filter(has_text=re.compile(r"description", re.IGNORECASE)).first,
        page.locator("[role='dialog'] textarea").first,
        page.get_by_label(re.compile(r"description", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        desc_candidates,
        timeout_ms=15000,
        error_message="Description field not visible in Create Prompt dialog",
    )

    # Display Order field
    display_order_candidates = [
        page.locator("[role='dialog'] label").filter(has_text=re.compile(r"display\s*order", re.IGNORECASE)).first,
        page.locator("div[data-modal-container='true'] label").filter(has_text=re.compile(r"display\s*order", re.IGNORECASE)).first,
        page.locator("[role='dialog'] input[type='number']").first,
        page.get_by_label(re.compile(r"display\s*order", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        display_order_candidates,
        timeout_ms=15000,
        error_message="Display Order field not visible in Create Prompt dialog",
    )

    # Create Prompt submit button
    create_btn_candidates = [
        page.locator("[role='dialog'] button").filter(has_text=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        page.locator("div[data-modal-container='true'] button").filter(has_text=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        page.locator("[role='dialog'] button:has-text('Create Prompt')").first,
    ]
    await _first_visible_with_wait(
        page,
        create_btn_candidates,
        timeout_ms=15000,
        error_message="'Create Prompt' button not visible in dialog",
    )

    # Cancel button
    cancel_candidates = [
        page.locator("[role='dialog'] button:has-text('Cancel')").first,
        page.locator("div[data-modal-container='true'] button:has-text('Cancel')").first,
        page.get_by_role("button", name=re.compile(r"^cancel$", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        cancel_candidates,
        timeout_ms=15000,
        error_message="Cancel button not visible in Create Prompt dialog",
    )


async def _fill_prompt_title_and_description(
    page: Page, title: str, description: str
) -> None:
    """Step 5: Enter title and description in the Create Prompt dialog."""
    # ── Fill Title ────────────────────────────────────────────────────────────
    title_input_candidates = [
        page.locator("[role='dialog'] input[type='text']").first,
        page.locator("div[data-modal-container='true'] input[type='text']").first,
        page.get_by_label(re.compile(r"title", re.IGNORECASE)).first,
        page.locator("[role='dialog'] input").first,
    ]
    title_input: Locator | None = None
    for candidate in title_input_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                title_input = candidate
                break
        except Exception:
            continue
    if title_input is None:
        raise AssertionError("Title input not found in Create Prompt dialog")

    await title_input.click()
    await page.keyboard.press("Control+a")
    await title_input.fill(title)

    # ── Fill Description ─────────────────────────────────────────────────────
    desc_input_candidates = [
        page.locator("[role='dialog'] textarea").first,
        page.locator("div[data-modal-container='true'] textarea").first,
        page.get_by_label(re.compile(r"description", re.IGNORECASE)).first,
    ]
    desc_input: Locator | None = None
    for candidate in desc_input_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                desc_input = candidate
                break
        except Exception:
            continue
    if desc_input is None:
        raise AssertionError("Description textarea not found in Create Prompt dialog")

    await desc_input.click()
    await page.keyboard.press("Control+a")
    await desc_input.fill(description)


async def _enter_display_order_and_create_prompt(
    page: Page, display_order: str, prompt_title: str
) -> None:
    """Step 6: Enter display order, click 'Create Prompt', verify prompt is visible."""
    # ── Fill Display Order ────────────────────────────────────────────────────
    display_order_candidates = [
        page.locator("[role='dialog'] input[type='number']").first,
        page.locator("div[data-modal-container='true'] input[type='number']").first,
        page.get_by_label(re.compile(r"display\s*order", re.IGNORECASE)).first,
    ]
    for candidate in display_order_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click()
                await page.keyboard.press("Control+a")
                await candidate.fill(display_order)
                break
        except Exception:
            continue
    # Display Order may be optional in some app versions; proceed regardless.

    # ── Click Create Prompt button ────────────────────────────────────────────
    create_btn_candidates = [
        page.locator("[role='dialog'] button").filter(has_text=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        page.locator("div[data-modal-container='true'] button").filter(has_text=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"create\s*prompt", re.IGNORECASE)).first,
        page.locator("[role='dialog'] button:has-text('Create Prompt')").first,
    ]
    try:
        create_btn = await _first_visible_with_wait(
            page,
            create_btn_candidates,
            timeout_ms=15000,
            error_message="'Create Prompt' submit button not visible",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "create_prompt_submit_btn", create_btn_candidates)
        raise
    await create_btn.click()

    # Wait for dialog to close (event-driven: dialog disappears from viewport)
    _DIALOG_GONE_JS = """() => {
        const sels = [
            'div[data-modal-container="true"]',
            '[data-testid="stDialog"]',
            '[data-testid="stModal"]',
            '[role="dialog"]',
            '[aria-modal="true"]',
        ];
        for (const s of sels) {
            const el = document.querySelector(s);
            if (el) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) return false;
            }
        }
        return true;
    }"""
    try:
        await page.wait_for_function(_DIALOG_GONE_JS, timeout=15000)
    except Exception:
        pass  # Dialog may close asynchronously; continue to verify prompt

    # Event-driven: wait for Streamlit to finish re-running after prompt creation
    _STREAMLIT_IDLE_JS = """() => {
        const widget = document.querySelector('[data-testid="stStatusWidget"]');
        if (widget) {
            const t = (widget.innerText || '').toLowerCase();
            if (t.includes('running') || t.includes('loading')) return false;
        }
        const spinner = document.querySelector('.stSpinner, [data-testid="stSpinner"]');
        if (spinner) {
            const r = spinner.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return false;
        }
        return true;
    }"""
    try:
        await page.wait_for_function(_STREAMLIT_IDLE_JS, timeout=8000)
    except Exception:
        pass  # Spinner may not always be present; proceed to prompt verification

    # ── Verify newly created prompt is visible in the library ─────────────────
    prompt_pattern = re.compile(re.escape(prompt_title), re.IGNORECASE)
    visible_candidates = [
        page.get_by_text(prompt_pattern).first,
        page.locator("button").filter(has_text=prompt_pattern).first,
        page.locator("[data-testid='stButton'] button").filter(has_text=prompt_pattern).first,
    ]
    try:
        await _first_visible_with_wait(
            page,
            visible_candidates,
            timeout_ms=20000,
            error_message=f"Newly created prompt '{prompt_title}' not visible in Prompt Library after creation",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "verify_prompt_visible", visible_candidates)
        raise


# ── Chat Saved Prompts helpers ────────────────────────────────────────────────

async def _expand_saved_prompts_section(page: Page) -> None:
    """Expand the 'Saved Prompts' collapsible section in the Chat module."""
    expander_candidates = [
        page.get_by_role("button", name=re.compile(r"saved\s*prompts", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"saved\s*prompts", re.IGNORECASE)).first,
        page.locator("summary:has-text('Saved Prompts')").first,
    ]
    expander = await _first_visible_with_wait(
        page,
        expander_candidates,
        timeout_ms=20000,
        error_message="'Saved Prompts' section not visible in Chat module",
    )

    # Only click if the details element is currently collapsed
    details = page.locator("details:has(summary:has-text('Saved Prompts'))").first
    details_count = await details.count()
    # JS that resolves True once any 'Saved Prompts' details element has the open attribute
    _SAVED_PROMPTS_OPEN_JS = """() => {
        const all = document.querySelectorAll('details');
        for (const d of all) {
            const s = d.querySelector('summary');
            if (s && /saved\\s*prompts/i.test(s.textContent || '')) {
                return d.hasAttribute('open');
            }
        }
        return false;
    }"""
    if details_count > 0:
        is_open = await details.get_attribute("open")
        if is_open is None:
            await expander.click()
            # Event-driven: wait for the details element to gain the open attribute
            try:
                await page.wait_for_function(_SAVED_PROMPTS_OPEN_JS, timeout=5000)
            except Exception:
                pass
            # Force open via JS if click didn't work
            is_open = await details.get_attribute("open")
            if is_open is None:
                await details.evaluate("node => node.setAttribute('open', '')")
    else:
        # Tab-style UI (v6.2.0+): click the Saved Prompts tab and wait for Streamlit to render the list
        await expander.click()
        await page.wait_for_timeout(2500)


async def _select_saved_prompt_and_send(
    page: Page, prompt_title: str
) -> None:
    """Step 9: Select the named saved prompt, verify text box auto-fills, click Send.

    Flow (v6.2.0+ tab-style UI):
      1. Click the '-- Select a saved prompt --' selectbox to open the dropdown.
      2. Pick the option whose text matches prompt_title.
      3. Verify the chat textarea is auto-populated.
      4. Click Send.
    """
    prompt_pattern = re.compile(re.escape(prompt_title), re.IGNORECASE)

    # ── Step 1: open the '-- Select a saved prompt --' selectbox ─────────────
    selectbox_candidates = [
        page.get_by_role("combobox", name=re.compile(r"select.*saved.*prompt|saved.*prompt", re.IGNORECASE)).first,
        page.locator("[data-testid='stSelectbox']").filter(
            has=page.get_by_text(re.compile(r"select.*saved.*prompt|saved.*prompt", re.IGNORECASE))
        ).locator("[data-baseweb='select']").first,
        page.locator("[data-baseweb='select']").filter(
            has=page.get_by_text(re.compile(r"select a saved prompt", re.IGNORECASE))
        ).first,
        # Fallback: any selectbox whose current value is the placeholder
        page.locator("input[value=''], [data-baseweb='select'] [aria-selected='false']").first,
        page.get_by_text(re.compile(r"--\s*select a saved prompt\s*--", re.IGNORECASE)).first,
    ]
    try:
        selectbox = await _first_visible_with_wait(
            page,
            selectbox_candidates,
            timeout_ms=20000,
            error_message="'-- Select a saved prompt --' selectbox not visible in Saved Prompts section",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "saved_prompt_selectbox", selectbox_candidates)
        raise
    await selectbox.click()
    await page.wait_for_timeout(600)

    # ── Step 2: pick the matching prompt from the dropdown ────────────────────
    prompt_option_candidates = [
        page.get_by_role("option", name=prompt_pattern).first,
        page.locator("[data-baseweb='menu'] [role='option']").filter(has_text=prompt_pattern).first,
        page.locator("li[role='option']").filter(has_text=prompt_pattern).first,
        page.get_by_text(prompt_pattern).first,
    ]
    try:
        prompt_option = await _first_visible_with_wait(
            page,
            prompt_option_candidates,
            timeout_ms=15000,
            error_message=f"Saved prompt '{prompt_title}' not found in selectbox dropdown",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "saved_prompt_item", prompt_option_candidates)
        raise
    await prompt_option.click()

    # Wait for chat input to be populated (event-driven)
    _INPUT_FILLED_JS = """() => {
        const selectors = [
            'textarea[data-testid="stChatInputTextArea"]',
            'textarea[placeholder*="help"]',
            'main textarea',
        ];
        for (const s of selectors) {
            const el = document.querySelector(s);
            if (el && el.value && el.value.trim().length > 0) return true;
        }
        return false;
    }"""
    try:
        await page.wait_for_function(_INPUT_FILLED_JS, timeout=10000)
    except Exception:
        pass  # Playwright will verify via input_value below

    # Verify textarea was populated
    input_candidates = [
        page.locator("textarea[data-testid='stChatInputTextArea']").first,
        page.locator("textarea[placeholder='How can I help?']").first,
        page.locator("textarea[placeholder*='help']").first,
        page.locator("main textarea").first,
    ]
    chat_input = await _first_visible_with_wait(
        page,
        input_candidates,
        timeout_ms=12000,
        error_message="Chat input textarea not visible after selecting saved prompt",
    )
    input_value = await chat_input.input_value()
    assert input_value.strip(), (
        f"Chat input was NOT auto-populated after selecting saved prompt '{prompt_title}'. "
        "Expected the prompt description to appear in the 'How can I help?' text box."
    )

    # Send button must be enabled (input has content)
    send_button_candidates = [
        page.locator("button[data-testid='stChatInputSubmitButton']").first,
        page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE)).first,
        page.locator("button:has-text('Send')").first,
    ]
    send_button = await _first_visible_with_wait(
        page,
        send_button_candidates,
        timeout_ms=12000,
        error_message="Send button not visible after selecting saved prompt",
    )

    # Wait up to 5s for Send button to enable
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not await send_button.is_disabled():
            break
        await page.wait_for_timeout(300)

    assert not await send_button.is_disabled(), (
        "Send button remained disabled after the saved prompt populated the chat input"
    )
    await send_button.click()


async def _wait_for_chat_response(page: Page, chat_page: ChatPage) -> None:
    """Step 10: Wait (up to 120s) for the AI response to appear, then wait for it to fully complete."""
    latest_message = ""
    deadline = time.monotonic() + 120  # 120s ceiling — long queries may take time
    while time.monotonic() < deadline:
        if chat_page.page.is_closed():
            raise AssertionError("Chat page was closed while waiting for response")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if latest_message and latest_message.strip():
            break
        await chat_page.page.wait_for_timeout(300)
    assert latest_message is not None and latest_message.strip(), (
        "System did not generate a response after sending the long query via Saved Prompts"
    )
    # Fixed 40-second wait to allow the full response to generate before sidebar check
    await chat_page.page.wait_for_timeout(40000)
    # Wait for streaming to fully complete — Streamlit only adds the sidebar thread
    # after the entire response is done. Poll until content stops changing.
    stable_count = 0
    prev_msg = latest_message
    stable_deadline = time.monotonic() + 120.0
    while time.monotonic() < stable_deadline:
        await chat_page.page.wait_for_timeout(2000)
        current = await chat_page.get_latest_message(timeout_ms=1500)
        if current and current.strip() == prev_msg.strip():
            stable_count += 1
            if stable_count >= 2:
                break
        else:
            stable_count = 0
            prev_msg = current or prev_msg


async def _verify_chat_thread_in_sidebar(page: Page) -> None:
    """Step 11: Verify a chat thread is created and visible in the sidebar."""
    sidebar_buttons = page.locator(
        "section[data-testid='stSidebar'] button[data-testid^='stBaseButton-']:not([data-testid='stBaseButton-headerNoPadding'])"
    )

    _action_labels = {
        "➕ new chat", "new chat", "✏️", "🗑️", "🗑",
        "☑️", "✖️", "❌", "select", "cancel", "delete", "edit",
    }

    # Wait up to 60s for a real chat-row thread to appear
    thread_found = False
    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline:
        button_count = await sidebar_buttons.count()
        for index in range(button_count):
            try:
                btn = sidebar_buttons.nth(index)
                if not await btn.is_visible():
                    continue
                text = (await btn.inner_text()).strip()
                normalized = " ".join(text.split()).lower()
                if text and len(text) > 2 and normalized not in _action_labels:
                    thread_found = True
                    break
            except Exception:
                continue
        if thread_found:
            break
        await page.wait_for_timeout(500)

    assert thread_found, (
        "No chat thread was created in the sidebar after sending the long query via Saved Prompts. "
        "Expected a new thread entry to be visible in the user's thread list."
    )


# ── Main TC flow ──────────────────────────────────────────────────────────────

async def _run_tc_flow(
    docuchat_context: dict,
    td: ChatIntTC02Inputs,
) -> None:
    """Execute all 16 steps for TC-INT-02.

    Flow summary:
      Steps 1-2  : Navigate to INT URL, verify landing page.
      Step  3    : Navigate to File Management and upload test_upload.docx.
      Steps 4-7  : Create a saved prompt (long query) in Prompt Library.
      Steps 8-9  : Navigate to Chat, configure 5-mini INT + Chat with Documents, select file.
      Steps 10-12: Use the saved prompt to send the query; verify response and thread creation.
      Step  13   : Cleanup — delete the chat thread created during this test.
      Step  14   : Cleanup — navigate to Prompt Library and delete the created prompt.
      Step  15   : Cleanup — navigate to File Management and delete the uploaded test_upload.docx.
      Step  16   : Exit.
    """
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]
    _file_name = td.file_paths[0].name  # e.g. "test_upload.docx"

    # ── Step 7 helper ─────────────────────────────────────────────────────────
    async def _step_7_navigate_chat_and_configure() -> None:
        await _open_chat_workspace(page)
        # Wait for Streamlit to fully settle after navigating from Prompt Library
        await page.wait_for_timeout(3000)
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(
            page, model_name=td.model_name, chat_type="Chat with Documents"
        )
        # Extra wait after chat type selection — Streamlit re-runs after each widget
        # change, and the Saved Prompts list is populated during the re-run after
        # the chat type is set. Without this wait the selectbox may open before the
        # prompt list has been fetched from the backend.
        await page.wait_for_timeout(3000)

    # ── Step 9 helper ─────────────────────────────────────────────────────────
    async def _step_9_select_saved_prompt_and_send() -> None:
        await _expand_saved_prompts_section(page)
        await _select_saved_prompt_and_send(page, td.prompt_title)

    # ── Step 16 helper ────────────────────────────────────────────────────────
    async def _step_16_exit() -> None:
        # Event-driven: ensure DOM is stable before test teardown
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    # ── Execute steps ─────────────────────────────────────────────────────────
    await _run_step(
        1,
        "Open the browser and navigate to DocuChat INT URL",
        page.goto(settings["base_url"], wait_until="domcontentloaded"),
        _TC_NAME, page,
    )
    chat_page = ChatPage(page, int(settings["timeout_ms"]))

    # Wait up to 4 minutes for Okta sign-in to complete and the Streamlit landing page to load.
    # Instead of checking URL patterns (fragile — SAML ACS URLs bypass them), we wait directly
    # for the sidebar navigation labels (Chat / File Management / Prompt Library) to appear.
    _STREAMLIT_READY_JS = """() => {
        const candidates = [
            ...document.querySelectorAll('[data-testid="stSidebar"] label'),
            ...document.querySelectorAll('[data-testid="stSidebarContent"] label'),
            ...document.querySelectorAll('[data-testid="stSidebar"] [role="radiogroup"] label'),
        ];
        for (const el of candidates) {
            const t = (el.textContent || '').toLowerCase().trim();
            if (t === 'chat' || t.includes('file management') || t.includes('prompt library')) {
                return true;
            }
        }
        return false;
    }"""
    try:
        logger.info("[TC-INT-02] Waiting up to 4 minutes for Okta sign-in and Streamlit landing page to load...")
        await page.wait_for_function(_STREAMLIT_READY_JS, timeout=240000)
        logger.info("[TC-INT-02] Streamlit landing page ready — URL: %s", page.url)
    except Exception:
        pass  # Proceed regardless; step 2 will verify the landing page

    await _run_step(
        2,
        "Verify the landing page options are displayed (Chat, File Management, Prompt Library)",
        _assert_landing_page_options(page),
        _TC_NAME, page,
    )

    await _run_step(
        3,
        "Navigate to File Management, upload test_upload.docx and verify it appears in the file table.",
        _navigate_to_file_management(page),
        _TC_NAME, page,
    )
    await _run_step(
        3,
        "Upload test_upload.docx via Browse Files and verify it is listed in the uploaded files table.",
        _upload_and_verify_tolerant(page, td.file_paths[0]),
        _TC_NAME, page,
    )
    await _run_step(
        3,
        f"Wait for {_file_name} to reach 'Ready' status in File Management before proceeding to Chat.",
        _wait_for_file_ready_status(page, _file_name),
        _TC_NAME, page,
    )

    await _run_step(
        4,
        "Navigate to the Prompt Library module and click 'Create New Prompt' button",
        _navigate_to_prompt_library_module(page),
        _TC_NAME, page,
    )
    # Step 4 also requires clicking Create New Prompt after navigating
    await _run_step(
        4,
        "Click on 'Create New Prompt' button to initiate prompt creation",
        _click_create_new_prompt_button(page),
        _TC_NAME, page,
    )

    await _run_step(
        5,
        "Verify 'Create Prompt' dialog UI — title, description, display order, Create Prompt button, Cancel button are visible and clickable",
        _verify_create_prompt_dialog_ui(page),
        _TC_NAME, page,
    )

    await _run_step(
        6,
        "Enter prompt title and description in the Create Prompt dialog",
        _fill_prompt_title_and_description(page, td.prompt_title, td.prompt_description),
        _TC_NAME, page,
    )

    await _run_step(
        7,
        "Enter Display Order, click 'Create Prompt', verify newly created prompt is visible in the library",
        _enter_display_order_and_create_prompt(page, td.prompt_display_order, td.prompt_title),
        _TC_NAME, page,
    )

    await _run_step(
        8,
        f"Navigate to Chat module, click + New Chat, select Model {td.model_name} and Chat Type as Chat with Documents",
        _step_7_navigate_chat_and_configure(),
        _TC_NAME, page,
    )

    await _run_step(
        9,
        "Click 'Choose Options' dropdown under 'Select Ready Files to Include in Chat Context', select first available document",
        _select_file_for_chat_context(page, tc_name_prefix=""),
        _TC_NAME, page,
    )

    await _run_step(
        10,
        "Navigate to Saved Prompts, select the long prompt, verify full prompt content auto-fills the 'How can I help?' text box, click Send",
        _step_9_select_saved_prompt_and_send(),
        _TC_NAME, page,
    )

    await _run_step(
        11,
        "Wait for the system to process the request and generate a response",
        _wait_for_chat_response(page, chat_page),
        _TC_NAME, page,
    )

    await _run_step(
        12,
        "Observe the chat interface — verify the chat thread is created and visible in the user's thread list",
        _verify_chat_thread_in_sidebar(page),
        _TC_NAME, page,
    )

    await _run_step(
        13,
        "Cleanup — delete the chat thread created during this test.",
        _cleanup_delete_chat_thread(page),
        _TC_NAME, page,
    )

    await _run_step(
        14,
        "Cleanup — navigate to Prompt Library and delete the prompt created during this test.",
        _cleanup_delete_prompt_by_title(page, td.prompt_title),
        _TC_NAME, page,
    )

    await _run_step(
        15,
        f"Cleanup — navigate to File Management and delete the uploaded {_file_name} file.",
        _cleanup_delete_uploaded_file(page, _file_name),
        _TC_NAME, page,
    )

    await _run_step(
        16,
        "Exit the application",
        _step_16_exit(),
        _TC_NAME, page,
    )


# ── Pytest test function ──────────────────────────────────────────────────────

@pytest.mark.chat
@pytest.mark.regression
async def test_tc_int_02_verify_chat_threads_long_query_chat_with_documents_5mini_int_saved_prompts(
    docuchat_context,
):
    """TC-INT-02 — Verify Chat Threads are created when initiating long query with Chat with Documents using 5-mini INT model via Saved Prompts."""
    td = _get_inputs()
    await _run_tc_flow(docuchat_context, td)


if __name__ == "__main__":
    raise SystemExit(
        pytest.main([
            __file__,
            "--env=int",
            "--headless=false",
            "-vv",
            "-s",
            "-p",
            "no:rerunfailures",
            "-p",
            "no:xdist",
        ])
    )
