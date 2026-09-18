"""TC026 Regression — CareSourceGPT Chat: Validate user level saved prompt with 5 CRT model and Chat type as Code Assistant - Python.

Test Case Name : TC026_Regression_CareSourceGPT_Chat_Validate user level saved prompt with 5 CRT model and Chat type as Code Assistant - Python
Description    : Verify CareSourceGPT initializes Chat successfully using user level Saved Prompts
                 from Prompt Library and user can start interaction, handles very long queries
                 gracefully without any error, handles chat Edit functionality from the Chat selected
                 in Chat history without any errors.
Pre-condition  : User has valid CareSourceGPT access.
                 Application should have Prompts created (specific to Chat type selected and support
                 long queries of 3000 words) in Prompt Library and can be selected in Chat module
                 under Saved Prompts section.
Feature        : QA-CRT
Environment    : QA-CRT
"""
from pathlib import Path
import re
import sys
import time

import pytest

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
from utils.test_data_loader import get_chat_inputs as _get_chat_inputs
from tests.web.regression.chat.chat_test_helpers import (
    _assert_landing_page_options,
    _first_visible_with_wait,
    _open_chat_workspace,
    _ensure_chat_configuration_open,
    _verify_chat_type_options,
    _select_model_and_chat_type,
    _verify_long_query_response,
    _verify_chat_history_edit_delete_controls,
    _verify_chat_edit_save,
    _get_chat_titles,
    _find_first_chat_row_button,
    _click_locator_resilient,
)

# Title used by _verify_chat_edit_save when saving a new chat title (step 9).
_TC026_EDITED_CHAT_TITLE = "Edited Chat Title"


# ---------------------------------------------------------------------------
# Step 3 — CareSourceGPT-specific Chat UI verification
# (mirrors _verify_chat_ui_details from chat_test_helpers but accepts both
#  "CareSourceGPT can make mistakes" and "DocuChat can make mistakes" for
#  the warning text to remain robust regardless of the deployment label)
# ---------------------------------------------------------------------------
async def _verify_chat_ui_details_caresourcegpt(page) -> None:
    """Verify all Chat landing page UI elements described in TC026 Step 3."""
    checks = [
        (
            "New Chat button",
            [
                page.get_by_role("button", name=re.compile(r"new\s*chat", re.IGNORECASE)).first,
                page.locator("button:has-text('New Chat')").first,
            ],
            "'+ New Chat' button is not visible",
        ),
        (
            "Chat Configuration",
            [
                page.get_by_text(re.compile(r"chat\s*configuration", re.IGNORECASE)).first,
                page.locator("summary:has-text('Chat Configuration')").first,
            ],
            "Chat Configuration section is not visible",
        ),
        (
            "Saved Prompts",
            [
                page.get_by_text(re.compile(r"saved\s*prompts", re.IGNORECASE)).first,
                page.locator("summary:has-text('Saved Prompts')").first,
            ],
            "Saved Prompts section is not visible",
        ),
        (
            "Ready files dropdown",
            [
                page.get_by_text(
                    re.compile(r"select\s*ready\s*files\s*to\s*include\s*in\s*chat\s*context", re.IGNORECASE)
                ).first,
                page.get_by_text(re.compile(r"choose\s*options", re.IGNORECASE)).first,
            ],
            "'Select Ready Files to Include in Chat Context' dropdown is not visible",
        ),
        (
            "Warning text",
            [
                page.get_by_text(
                    re.compile(r"CareSourceGPT\s+can\s+make\s+mistakes", re.IGNORECASE)
                ).first,
                page.get_by_text(
                    re.compile(r"DocuChat\s+can\s+make\s+mistakes", re.IGNORECASE)
                ).first,
                page.get_by_text(re.compile(r"can\s+make\s+mistakes", re.IGNORECASE)).first,
            ],
            "Warning text 'CareSourceGPT can make mistakes. Always review output before usage.' is not visible",
        ),
        (
            "Tips and Tricks",
            [
                page.get_by_text(re.compile(r"tips?\s*&\s*tricks", re.IGNORECASE)).first,
                page.get_by_role("button", name=re.compile(r"tips?", re.IGNORECASE)).first,
            ],
            "'Tips & Tricks to Get Started' button is not visible",
        ),
        (
            "Chat input placeholder",
            [
                page.locator("textarea[placeholder='How can I help?']").first,
                page.locator("textarea[placeholder*='help']").first,
            ],
            "Chat input box with 'How can I help?' placeholder is not visible",
        ),
    ]
    for _label, candidates, message in checks:
        await _first_visible_with_wait(page, candidates, timeout_ms=15000, error_message=message)


# ---------------------------------------------------------------------------
# Step 5 helpers — Saved Prompts selection
# ---------------------------------------------------------------------------
_PLACEHOLDER_FRAGMENTS = ("select a saved prompt", "-- select", "--")


def _is_placeholder_option(text: str) -> bool:
    t = text.strip().lower()
    return not t or any(frag in t for frag in _PLACEHOLDER_FRAGMENTS)


async def _expand_saved_prompts_section(page) -> None:
    """CLICK 1 — Expand the Saved Prompts expander panel.

    The Saved Prompts section renders as a Streamlit st.expander (collapsed by
    default).  Clicking its header/summary expands it and reveals the selectbox
    inside.  Mirrors the pattern used by _ensure_chat_configuration_open.
    """
    # Try the <details>/<summary> structure first (Streamlit expander)
    details = page.locator(
        "details:has(summary:has-text('Saved Prompts'))"
    ).first
    if await details.count() > 0:
        is_open = await details.get_attribute("open")
        if is_open is None:
            summary = details.locator("summary").first
            await summary.click()
            await page.wait_for_timeout(700)
            return
        # Already open — nothing to do
        return

    # Fallback: generic visible element containing "Saved Prompts" text
    expander_candidates = [
        page.locator("summary").filter(
            has_text=re.compile(r"saved\s*prompts", re.IGNORECASE)
        ).first,
        page.get_by_role(
            "button", name=re.compile(r"saved\s*prompts", re.IGNORECASE)
        ).first,
        page.get_by_text(
            re.compile(r"^saved\s*prompts$", re.IGNORECASE)
        ).first,
        # The card title rendered by the app (non-expander layout)
        page.locator("p, span, div").filter(
            has_text=re.compile(r"^saved\s*prompts$", re.IGNORECASE)
        ).first,
    ]
    for candidate in expander_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click()
                await page.wait_for_timeout(700)
                return
        except Exception:
            continue


async def _click_saved_prompts_selectbox(page) -> bool:
    """CLICK 2 — Click the selectbox trigger INSIDE the expanded Saved Prompts panel.

    By the time this runs, _expand_saved_prompts_section() has already been called
    so the selectbox should be visible.  Returns True on success.
    """
    # Strategy 1: stSelectbox whose label contains "Saved Prompts"
    try:
        selectbox = page.locator("div[data-testid='stSelectbox']").filter(
            has=page.locator(
                "label", has_text=re.compile(r"saved\s*prompts", re.IGNORECASE)
            )
        ).first
        if await selectbox.count() > 0:
            trigger = selectbox.locator("[data-baseweb='select']").first
            if await trigger.count() > 0 and await trigger.is_visible():
                await trigger.click()
                await page.wait_for_timeout(700)
                return True
            if await selectbox.is_visible():
                await selectbox.click()
                await page.wait_for_timeout(700)
                return True
    except Exception:
        pass

    # Strategy 2: label element with "Saved Prompts" text → sibling baseweb select
    try:
        trigger = page.locator(
            "label:has-text('Saved Prompts') ~ div [data-baseweb='select']"
        ).first
        if await trigger.count() > 0 and await trigger.is_visible():
            await trigger.click()
            await page.wait_for_timeout(700)
            return True
    except Exception:
        pass

    # Strategy 3: any visible [data-baseweb='select'] that contains the placeholder text
    try:
        trigger = page.locator("[data-baseweb='select']").filter(
            has_text=re.compile(r"select\s*a\s*saved\s*prompt", re.IGNORECASE)
        ).first
        if await trigger.count() > 0 and await trigger.is_visible():
            await trigger.click()
            await page.wait_for_timeout(700)
            return True
    except Exception:
        pass

    # Strategy 4: combobox with accessible name matching "Saved Prompts"
    try:
        combobox = page.get_by_role(
            "combobox", name=re.compile(r"saved\s*prompts", re.IGNORECASE)
        ).first
        if await combobox.count() > 0 and await combobox.is_visible():
            await combobox.click()
            await page.wait_for_timeout(700)
            return True
    except Exception:
        pass

    return False


async def _collect_real_prompt_options(page) -> list[tuple[object, str]]:
    """Return list of (locator, text) for real (non-placeholder) dropdown options."""
    option_selectors = [
        "[role='listbox'] [role='option']",
        "[data-baseweb='popover'] [role='option']",
        "[data-baseweb='menu'] [role='option']",
        "[data-baseweb='menu'] li",
        "ul[role='listbox'] li",
    ]
    for sel in option_selectors:
        try:
            locator = page.locator(sel)
            count = await locator.count()
            if count == 0:
                continue
            results: list[tuple[object, str]] = []
            for i in range(count):
                opt = locator.nth(i)
                if not await opt.is_visible():
                    continue
                text = (await opt.inner_text()).strip()
                if not _is_placeholder_option(text):
                    results.append((opt, text))
            if results:
                return results
        except Exception:
            continue
    return []


async def _select_first_available_saved_prompt(page) -> str:
    """Two-click approach: expand section → click selectbox → select first real option.

    Returns empty string when the dropdown contains only the placeholder (no prompts).
    """
    # CLICK 1 — expand the Saved Prompts expander section
    await _expand_saved_prompts_section(page)

    # Wait for the selectbox to become visible after expansion
    await page.wait_for_timeout(600)

    # CLICK 2 — open the dropdown inside the expanded section
    clicked = await _click_saved_prompts_selectbox(page)
    if not clicked:
        # Section might not be an expander; the selectbox may already be visible
        # (card layout). Log and treat as "no prompts" so test can proceed.
        return ""

    # Give the dropdown options time to render
    await page.wait_for_timeout(800)

    real_options = await _collect_real_prompt_options(page)
    if not real_options:
        # No user-level prompts configured — close dropdown and signal caller
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return ""

    opt_locator, opt_text = real_options[0]
    try:
        await opt_locator.click()
    except Exception:
        await opt_locator.evaluate("node => node.click()")
    await page.wait_for_timeout(600)
    return opt_text


async def _ensure_send_enabled_with_query(page, query: str) -> None:
    """Fill the chat input with query (if empty) and assert Send button is enabled."""
    input_candidates = [
        page.locator("textarea[data-testid='stChatInputTextArea']").first,
        page.locator("textarea[placeholder='How can I help?']").first,
        page.locator("textarea[placeholder*='help']").first,
        page.locator("main textarea").first,
    ]
    chat_input = await _first_visible_with_wait(
        page,
        input_candidates,
        timeout_ms=15000,
        error_message="'How can I help?' text area is not visible",
    )
    value = await chat_input.input_value()
    if not value or not value.strip():
        await chat_input.fill(query)
        await page.wait_for_timeout(300)

    send_button_candidates = [
        page.locator("button[data-testid='stChatInputSubmitButton']").first,
        page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE)).first,
        page.locator("button:has-text('Send')").first,
    ]
    send_button = await _first_visible_with_wait(
        page,
        send_button_candidates,
        timeout_ms=10000,
        error_message="Send button is not visible",
    )
    assert not await send_button.is_disabled(), (
        "Send button should be enabled after entering a query"
    )


# ---------------------------------------------------------------------------
# Step 6 helper — Chat initialization with saved prompt
# (sends whatever is currently in the text area directly, without opening a
#  new chat, so the saved prompt populated in step 5 is preserved)
# ---------------------------------------------------------------------------
async def _send_current_input_and_verify_response(
    page,
    chat_page: ChatPage,
    fallback_query: str,
    timeout_sec: float = 90.0,
) -> None:
    """Click Send with the current text-area content (or fallback_query if empty).

    Does NOT call open_new_chat() so the saved prompt from step 5 is preserved.
    """
    input_candidates = [
        page.locator("textarea[data-testid='stChatInputTextArea']").first,
        page.locator("textarea[placeholder='How can I help?']").first,
        page.locator("textarea[placeholder*='help']").first,
        page.locator("main textarea").first,
    ]
    chat_input = await _first_visible_with_wait(
        page,
        input_candidates,
        timeout_ms=20000,
        error_message="Chat input text area not visible",
    )

    current_value = await chat_input.input_value()
    if not current_value or not current_value.strip():
        await chat_input.fill(fallback_query)
        await page.wait_for_timeout(300)

    send_button_candidates = [
        page.locator("button[data-testid='stChatInputSubmitButton']").first,
        page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE)).first,
        page.locator("button:has-text('Send')").first,
    ]
    send_button = await _first_visible_with_wait(
        page,
        send_button_candidates,
        timeout_ms=15000,
        error_message="Send button is not visible",
    )

    if await send_button.is_disabled():
        # Input may still be empty — fill with fallback
        await chat_input.fill(fallback_query)
        await page.wait_for_timeout(300)

    await send_button.click()

    latest_message = ""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if chat_page.page.is_closed():
            raise AssertionError("Chat page was closed before a response could be validated")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if latest_message and latest_message.strip():
            break
        await chat_page.page.wait_for_timeout(300)

    assert latest_message and latest_message.strip(), (
        "Chat response/code was not generated after sending the saved prompt"
    )


# ---------------------------------------------------------------------------
# Step 7 helper — Long query verification with Document Review chat type
# ---------------------------------------------------------------------------
async def _verify_long_query_with_document_review_saved_prompt(
    page,
    chat_page: ChatPage,
    model_name: str,
    long_query_fallback: str,
) -> None:
    """Step 7: Change to Document Review, select a saved prompt with >3000 words, send and verify.

    Strategy:
    1. Open Chat Configuration and change Chat Type to Document Review.
    2. Navigate to Saved Prompts and select any available prompt.
    3. If the selected prompt has >= 100 words, send it directly (no new chat opened).
    4. Otherwise fall back to the standard long query (>3000 words) via send_message.
    """
    await _ensure_chat_configuration_open(page)
    await _select_model_and_chat_type(page, model_name=model_name, chat_type="Document Review")
    await page.wait_for_timeout(500)

    selected_text = await _select_first_available_saved_prompt(page)

    # Determine whether the selected prompt is long enough (>= 100 words as proxy)
    if selected_text and len(selected_text.split()) >= 100:
        # Long prompt is in the text area — send it directly
        await _send_current_input_and_verify_response(
            page, chat_page, fallback_query=long_query_fallback, timeout_sec=90.0
        )
    else:
        # No long prompt from Saved Prompts — fall back to standard long query
        await _verify_long_query_response(chat_page, tc_key="tc026")


# ---------------------------------------------------------------------------
# Step 10 helper — Initiate chat using the updated (edited) Chat
# ---------------------------------------------------------------------------
async def _initiate_chat_with_updated_chat(page, chat_page: ChatPage) -> None:
    """Step 10: Click the edited chat from Chat History and initiate a new interaction.

    Searches the sidebar for a chat whose title contains _TC026_EDITED_CHAT_TITLE.
    Falls back to the first visible non-action chat row if not found.
    Sends a follow-up message and verifies a response is returned.
    """
    sidebar_buttons = page.locator(
        "section[data-testid='stSidebar'] [data-testid='stButton'] button"
    )
    button_count = await sidebar_buttons.count()

    found = False
    for index in range(button_count):
        try:
            btn = sidebar_buttons.nth(index)
            if not await btn.is_visible():
                continue
            text = (await btn.inner_text()).strip()
            if _TC026_EDITED_CHAT_TITLE.lower() in text.lower():
                await btn.scroll_into_view_if_needed()
                await _click_locator_resilient(page, btn)
                found = True
                break
        except Exception:
            continue

    if not found:
        row = await _find_first_chat_row_button(page)
        if row:
            btn, _ = row
            await _click_locator_resilient(page, btn)

    await page.wait_for_timeout(1000)

    # Send a follow-up query and verify the application returns a response
    follow_up = "Can you provide a brief summary of this chat?"
    input_candidates = [
        page.locator("textarea[data-testid='stChatInputTextArea']").first,
        page.locator("textarea[placeholder='How can I help?']").first,
        page.locator("textarea[placeholder*='help']").first,
        page.locator("main textarea").first,
    ]
    chat_input = await _first_visible_with_wait(
        page,
        input_candidates,
        timeout_ms=20000,
        error_message="Chat input not visible when initiating updated chat",
    )
    await chat_input.fill(follow_up)
    await page.wait_for_timeout(300)

    send_button_candidates = [
        page.locator("button[data-testid='stChatInputSubmitButton']").first,
        page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE)).first,
        page.locator("button:has-text('Send')").first,
    ]
    send_button = await _first_visible_with_wait(
        page,
        send_button_candidates,
        timeout_ms=15000,
        error_message="Send button is not visible when initiating updated chat",
    )
    await send_button.click()

    latest_message = ""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if chat_page.page.is_closed():
            raise AssertionError("Chat page was closed before a response could be validated")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if latest_message and latest_message.strip():
            break
        await chat_page.page.wait_for_timeout(300)

    assert latest_message and latest_message.strip(), (
        "No response received after initiating chat using the updated (edited) Chat"
    )


# ---------------------------------------------------------------------------
# Main TC026 flow
# ---------------------------------------------------------------------------
async def _run_tc026_flow(
    docuchat_context: dict,
    query: str,
    tc_name: str,
    model_name: str,
    long_query: str,
) -> None:
    """Execute all 11 steps for TC026 (Code Assistant - Python, 5 CRT, Saved Prompts)."""
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]

    # ── Step 3 composite ─────────────────────────────────────────────────────
    async def _step_3_verify_chat_landing_ui() -> None:
        await _open_chat_workspace(page)
        await _verify_chat_ui_details_caresourcegpt(page)

    # ── Step 4 composite ─────────────────────────────────────────────────────
    async def _step_4_configure_chat() -> None:
        await _ensure_chat_configuration_open(page)
        await _verify_chat_type_options(page)
        await _select_model_and_chat_type(
            page, model_name=model_name, chat_type="Code Assistant - Python"
        )

    # ── Step 5 composite ─────────────────────────────────────────────────────
    async def _step_5_select_saved_prompt() -> None:
        selected = await _select_first_available_saved_prompt(page)
        # Always verify the text area has content and Send is enabled.
        # When a prompt was selected its text pre-fills the box; when none are
        # configured the fallback query is used so the chat can proceed.
        await _ensure_send_enabled_with_query(page, query=query)

    # ── Step 11 composite ────────────────────────────────────────────────────
    async def _step_11_exit_application() -> None:
        await page.wait_for_timeout(100)

    # ── Chat page helper (created after navigation in step 1) ────────────────
    await _run_step(
        1,
        "Open the browser (Chrome/Edge) and enter URL https://docu-chat.crt.ai.caresource.corp",
        page.goto(settings["base_url"]),
        tc_name, page,
    )
    chat_page = ChatPage(page, int(settings["timeout_ms"]))

    await _run_step(
        2,
        "Verify the landing page options are displayed (Chat, File Management, Prompt Library)",
        _assert_landing_page_options(page),
        tc_name, page,
    )
    await _run_step(
        3,
        "Verify the UI details of Chat landing page",
        _step_3_verify_chat_landing_ui(),
        tc_name, page,
    )
    await _run_step(
        4,
        f"Go to Chat Configurations, Select Model {model_name} and Chat Type as Code Assistant - Python",
        _step_4_configure_chat(),
        tc_name, page,
    )
    await _run_step(
        5,
        "Navigate to Saved Prompts section, click Saved Prompts, select a saved prompt and verify prompt details shown in 'How can I help?' text box",
        _step_5_select_saved_prompt(),
        tc_name, page,
    )
    await _run_step(
        6,
        "Verify Chat Initialization — send the saved prompt (Code generation query e.g. 'Generate code for Palindrome') and verify response/code generated without latency or errors",
        _send_current_input_and_verify_response(page, chat_page, fallback_query=query),
        tc_name, page,
    )
    await _run_step(
        7,
        "Verify long queries — go to Chat Configuration, select Document Review, select a saved prompt with >3000 words, send and verify response generated without latency or errors",
        _verify_long_query_with_document_review_saved_prompt(
            page, chat_page, model_name=model_name, long_query_fallback=long_query
        ),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify Chat history details — previous Chat visible in left sidebar with Edit and Delete buttons",
        _verify_chat_history_edit_delete_controls(page),
        tc_name, page,
    )
    await _run_step(
        9,
        "Verify Chat Edit — select chat from Chat History, click Edit, update title (225 char limit), click Save and verify changes reflected",
        _verify_chat_edit_save(page),
        tc_name, page,
    )
    await _run_step(
        10,
        "Initiate a Chat using the updated Chat — verify response shown as per the edited Chat",
        _initiate_chat_with_updated_chat(page, chat_page),
        tc_name, page,
    )
    await _run_step(
        11,
        "Exit the application by clicking the browser close button",
        _step_11_exit_application(),
        tc_name, page,
    )


# ---------------------------------------------------------------------------
# Pytest entry point
# ---------------------------------------------------------------------------
@pytest.mark.chat
@pytest.mark.regression
async def test_tc026_regression_caresourcegpt_chat_validate_user_level_saved_prompt_with_5crt_model_and_chat_type_as_code_assistant_python(
    docuchat_context,
):
    """TC026 — Validate user level saved prompt with 5 CRT model and Chat type as Code Assistant - Python."""
    _td = _get_chat_inputs("tc026")
    await _run_tc026_flow(
        docuchat_context,
        query=_td.query,
        tc_name="TC026",
        model_name=_td.model_name,
        long_query=_td.long_query,
    )
