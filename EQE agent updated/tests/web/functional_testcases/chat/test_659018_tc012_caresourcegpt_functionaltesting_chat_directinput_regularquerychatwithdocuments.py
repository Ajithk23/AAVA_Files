"""TC-INT-12 — Verify Chat Threads are created when initiating regular query with Chat with Documents using 5-mini INT model via Direct input.

Test Case Name : TC012 - Verify Chat Threads are created when initiating regular query with
                 Chat with Documents  using 5-mini INT model via Direct input
Description    : Verify chat creation - regular query using direct input in "How can I help?"
                 text box in Chat with Documents.
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
from playwright.async_api import Page

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
from utils.test_data_loader import get_chat_int_tc12_inputs as _get_inputs, ChatIntTC12Inputs
from tests.web.functional_testcases.chat.chat_test_helpers import (
    _assert_landing_page_options,
    _ensure_chat_configuration_open,
    _select_model_and_chat_type,
    _select_file_for_chat_context,
    _first_visible_with_wait,
    _write_locator_diagnostics,
    _cleanup_delete_chat_thread,
)
from tests.web.functional_testcases.file_Management.file_management_test_helpers import (
    _navigate_to_file_management,
    _upload_and_verify_tolerant,
    _cleanup_delete_uploaded_file,
    _wait_for_file_ready_status,
)

_TC_NAME = "TC-INT-12"
_TC_INT_12_FILE_PREFIX = "TC-INT-12"

logger = logging.getLogger(__name__)

DEBUG_DIR = PROJECT_ROOT / "reports" / "screenshots"


# ── Direct input helpers ──────────────────────────────────────────────────────

async def _type_regular_query_and_send(page: Page, query: str) -> None:
    """Step 5: Manually input the regular query into the 'How can I help?' text box and click Send.

    Flow:
      1. Locate the 'How can I help?' chat input textarea.
      2. Type the regular query into the textarea.
      3. Verify the full prompt content is displayed in the text box.
      4. Click the Send button to initiate chat.
    """
    # ── Locate the chat input textarea ────────────────────────────────────────
    input_candidates = [
        page.locator("textarea[data-testid='stChatInputTextArea']").first,
        page.locator("textarea[placeholder='How can I help?']").first,
        page.locator("textarea[placeholder*='help']").first,
        page.locator("main textarea").first,
    ]
    try:
        chat_input = await _first_visible_with_wait(
            page,
            input_candidates,
            timeout_ms=20000,
            error_message="'How can I help?' chat input textarea not visible in Chat module",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "chat_input_textarea", input_candidates)
        raise

    # ── Type the regular query ────────────────────────────────────────────────
    await chat_input.click()
    await page.keyboard.press("Control+a")
    await chat_input.fill(query)

    # Event-driven: wait for the textarea value to be populated
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
        pass  # Proceed; assertion below will catch if empty

    # ── Verify the textarea is populated ─────────────────────────────────────
    input_value = await chat_input.input_value()
    assert input_value.strip(), (
        "Chat input was NOT populated after typing the regular query. "
        "Expected the full prompt content to appear in the 'How can I help?' text box."
    )

    # ── Locate and click the Send button ─────────────────────────────────────
    send_button_candidates = [
        page.locator("button[data-testid='stChatInputSubmitButton']").first,
        page.get_by_role("button", name="Send").first,
        page.locator("button:has-text('Send')").first,
    ]
    try:
        send_button = await _first_visible_with_wait(
            page,
            send_button_candidates,
            timeout_ms=12000,
            error_message="Send button not visible after typing the regular query",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "send_button", send_button_candidates)
        raise

    # Wait up to 5s for Send button to become enabled
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not await send_button.is_disabled():
            break
        await page.wait_for_timeout(300)

    assert not await send_button.is_disabled(), (
        "Send button remained disabled after the regular query was typed into the chat input"
    )
    await send_button.click()


async def _wait_for_chat_response(page: Page, chat_page: ChatPage) -> None:
    """Step 6: Wait (up to 120s) for the AI response to appear, then wait for it to fully complete."""
    latest_message = ""
    deadline = time.monotonic() + 120  # 120s ceiling
    while time.monotonic() < deadline:
        if chat_page.page.is_closed():
            raise AssertionError("Chat page was closed while waiting for response")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if latest_message and latest_message.strip():
            break
        await chat_page.page.wait_for_timeout(300)
    assert latest_message is not None and latest_message.strip(), (
        "System did not generate a response after sending the regular query via Direct input"
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
    """Step 7: Verify a chat thread is created and visible in the sidebar."""
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
        "No chat thread was created in the sidebar after sending the regular query via Direct input. "
        "Expected a new thread entry to be visible in the user's thread list."
    )


# ── Main TC flow ──────────────────────────────────────────────────────────────

async def _run_tc_flow(
    docuchat_context: dict,
    td: ChatIntTC12Inputs,
) -> None:
    """Execute all 11 steps for TC-INT-12.

    Flow summary:
      Step  1    : Navigate to INT URL.
      Step  2    : Verify landing page options (Chat, File Management, Prompt Library).
      Step  3    : Navigate to File Management and upload Test.docx.
      Step  4    : Navigate to Chat, click + New Chat, configure 5-mini INT + Chat with Documents.
      Step  5    : Click 'Choose Options' dropdown, select document for Chat Context.
      Step  6    : Manually type the regular query into 'How can I help?' text box and click Send.
      Step  7    : Wait for the system to process and generate a response.
      Step  8    : Verify the chat thread is created and visible in the sidebar.
      Step  9    : Cleanup — delete the chat thread created during this test.
      Step  10   : Cleanup — navigate to File Management and delete the uploaded Test.docx.
      Step  11   : Exit.
    """
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]

    # ── Step 3 helper ─────────────────────────────────────────────────────────
    async def _step_3_navigate_chat_and_configure() -> None:
        # First navigate from File Management to the Chat module, then configure.
        from tests.web.regression.chat.chat_test_helpers import _open_chat_workspace
        await _open_chat_workspace(page)
        # Extra wait after chat type selection — Streamlit re-runs after each widget change
        await page.wait_for_timeout(3000)
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(
            page, model_name=td.model_name, chat_type="Chat with Documents"
        )

    # ── Step 11 helper ────────────────────────────────────────────────────────
    async def _step_11_exit() -> None:
        # Event-driven: ensure DOM is stable before test teardown
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    # ── Execute steps ─────────────────────────────────────────────────────────
    await _run_step(
        1,
        "Open the browser (Chrome/Edge). and Enter URL as https://csgpt.int.ai.caresource.corp/",
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
        logger.info("[TC-INT-12] Waiting up to 4 minutes for Okta sign-in and Streamlit landing page to load...")
        await page.wait_for_function(_STREAMLIT_READY_JS, timeout=240000)
        logger.info("[TC-INT-12] Streamlit landing page ready — URL: %s", page.url)
    except Exception:
        pass  # Proceed regardless; step 2 will verify the landing page

    await _run_step(
        2,
        "Verify the landing page options are displayed (Chat, File Management, Prompt Library)",
        _assert_landing_page_options(page),
        _TC_NAME, page,
    )

    upload_path = td.file_paths[0]
    upload_filename = upload_path.name

    await _run_step(
        3,
        f"Navigate to File Management, upload {upload_filename} and verify it appears in the file table.",
        _navigate_to_file_management(page),
        _TC_NAME, page,
    )
    await _run_step(
        3,
        f"Upload {upload_filename} via Browse Files and verify it is listed in the uploaded files table.",
        _upload_and_verify_tolerant(page, upload_path),
        _TC_NAME, page,
    )
    await _run_step(
        3,
        f"Wait for {upload_filename} to reach 'Ready' status in File Management before proceeding to Chat.",
        _wait_for_file_ready_status(page, upload_filename),
        _TC_NAME, page,
    )

    await _run_step(
        4,
        f"Navigate to the Chat module and click on + New Chat button to initiate a chat.\nGo to Chat Configurations, Select Model {td.model_name} and Chat Type as Chat with Documents.",
        _step_3_navigate_chat_and_configure(),
        _TC_NAME, page,
    )

    await _run_step(
        5,
        "Click on \"Choose Options\" dropdown under the label \"Select Ready Files to Include in Chat Context:\",  select the required document and verify whether they are  visible and accessible. ",
        _select_file_for_chat_context(page, tc_name_prefix=""),
        _TC_NAME, page,
    )

    await _run_step(
        6,
        "Manually input a regular query in  \"How can I help?\" text boxand verify that the full prompt content is automatically displayed in the \"How can I help?\" text box and click on the Send button to initiate chat. ",
        _type_regular_query_and_send(page, td.query),
        _TC_NAME, page,
    )

    await _run_step(
        7,
        "Wait for the system to process the request and generate response. ",
        _wait_for_chat_response(page, chat_page),
        _TC_NAME, page,
    )

    await _run_step(
        8,
        "Observe the chat interface for thread creation.",
        _verify_chat_thread_in_sidebar(page),
        _TC_NAME, page,
    )

    await _run_step(
        9,
        "Cleanup — delete the chat thread created during this test.",
        _cleanup_delete_chat_thread(page),
        _TC_NAME, page,
    )

    await _run_step(
        10,
        f"Cleanup — navigate to File Management and delete the uploaded {upload_filename} file.",
        _cleanup_delete_uploaded_file(page, upload_filename),
        _TC_NAME, page,
    )

    await _run_step(
        11,
        "Exit the application by clicking the browser close button.",
        _step_11_exit(),
        _TC_NAME, page,
    )


# ── Pytest test function ──────────────────────────────────────────────────────

@pytest.mark.chat
@pytest.mark.regression
async def test_tc_int_12_verify_chat_threads_regular_query_chat_with_documents_5mini_int_direct_input(
    docuchat_context,
):
    """TC-INT-12 — Verify Chat Threads are created when initiating regular query with Chat with Documents using 5-mini INT model via Direct input."""
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
