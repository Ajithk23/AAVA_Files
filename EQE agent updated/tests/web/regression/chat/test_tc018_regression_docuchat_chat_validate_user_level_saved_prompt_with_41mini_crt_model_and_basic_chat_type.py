"""TC018 Regression — DocuChat Chat: Validate user level saved prompt with 4.1 mini CRT model and Basic Chat type.

Test Case Name : TC018_Regression_DocuChat_Chat_Validate user level saved prompt with
                 4.1 mini CRT model and Basic Chat type
Description    : Verify DocuChat initializes Chat successfully using user level Saved Prompts
                 from Prompt Library and user can start interaction, handles very long queries
                 gracefully without any error, handles chat Edit functionality from the Chat
                 selected in Chat history without any errors.
Pre-condition  : User has valid DocuChat access.
                 Application should have Prompts created (specific to Chat type selected
                 and support long queries of 3000 words) in Prompt Library and can be
                 selected in Chat module under Saved Prompts section.
Feature        : Chat
Environment    : QA-CRT
"""
from pathlib import Path
import sys

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
    _ensure_chat_configuration_open,
    _open_chat_workspace,
    _select_and_verify_saved_prompt,
    _select_model_and_chat_type,
    _verify_chat_edit_and_initialize_basic_chat,
    _verify_chat_history_edit_delete_controls,
    _verify_chat_response,
    _verify_chat_type_options,
    _verify_chat_ui_details,
    _verify_long_query_with_saved_prompt,
    _verify_saved_prompt_chat_initialization,
)

_TC018_NAME = (
    "TC018_Regression_DocuChat_Chat_Validate user level saved prompt with "
    "4.1 mini CRT model and Basic Chat type"
)


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    query: str,
    tc_name: str,
    model_name: str,
    tc_key: str,
) -> None:
    """Execute all 11 steps for TC018.

    Step 1  : Open browser and navigate to the DocuChat URL.
    Step 2  : Verify landing page options (Chat, File Management, Prompt Library).
    Step 3  : Verify UI details of Chat landing page.
    Step 4  : Go to Chat Configurations, select Model 4.1 mini CRT and Chat Type Basic Chat.
    Step 5  : Navigate to Saved Prompts section, select a saved prompt, verify it
              populates the 'How can I help?' text area.
    Step 6  : Click Send; verify response with copy icon and Regenerate Response button.
    Step 7  : Re-configure model + Basic Chat, select a Saved Prompt with >3000 words,
              send long query (>3000 words), verify response without latency or errors.
    Step 8  : Verify Chat history in left sidebar — Edit and Delete buttons present.
    Step 9  : Edit first chat title (225-char limit), save, verify changes reflected.
    Step 10 : Initiate a Chat using the updated (edited) chat — verify response generated.
    Step 11 : Exit application.
    """
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]

    # Mutable container so inner closures can share state across steps
    _state: dict[str, str] = {"prompt_text": ""}

    # ── Step 3 ───────────────────────────────────────────────────────────────
    async def _step_3_verify_chat_landing_ui() -> None:
        await _open_chat_workspace(page)
        await _verify_chat_ui_details(page)

    # ── Step 4 ───────────────────────────────────────────────────────────────
    async def _step_4_configure_model_and_chat_type() -> None:
        await _ensure_chat_configuration_open(page)
        await _verify_chat_type_options(page)
        await _select_model_and_chat_type(page, model_name=model_name, chat_type="Basic Chat")

    # ── Step 5 ───────────────────────────────────────────────────────────────
    async def _step_5_select_saved_prompt() -> None:
        _state["prompt_text"] = await _select_and_verify_saved_prompt(page)

    # ── Step 6 ───────────────────────────────────────────────────────────────
    async def _step_6_verify_chat_initialization() -> None:
        await _verify_saved_prompt_chat_initialization(chat_page, _state["prompt_text"])

    # ── Step 7 ───────────────────────────────────────────────────────────────
    async def _step_7_verify_long_query() -> None:
        await _verify_long_query_with_saved_prompt(page, chat_page, model_name, tc_key)

    # ── Steps 9-10 ───────────────────────────────────────────────────────────
    # _verify_chat_edit_and_initialize_basic_chat: edits the first chat title (up to 225
    # chars), saves, verifies the change, then sends a query in the updated chat to satisfy
    # Step 10 ("initiate a Chat using the updated Chat").
    async def _step_9_10_edit_and_initialize() -> None:
        await _verify_chat_edit_and_initialize_basic_chat(page, chat_page, query)

    # ── Step 11 ──────────────────────────────────────────────────────────────
    async def _step_11_exit_application() -> None:
        await page.wait_for_timeout(100)

    # ── Test execution ───────────────────────────────────────────────────────
    await _run_step(
        1,
        "Open the browser and navigate to the DocuChat URL",
        page.goto(settings["base_url"]),
        tc_name, page,
    )
    chat_page = ChatPage(page, int(settings["timeout_ms"]))

    await _run_step(
        2,
        "Verify landing page options are displayed (Chat, File Management, Prompt Library)",
        _assert_landing_page_options(page),
        tc_name, page,
    )
    await _run_step(
        3,
        "Verify UI details of Chat landing page — left sidebar with '+ New Chat' button; "
        "right panel with Chat Configuration (Select Model dropdown, Select Chat Type with "
        "values Basic Chat / Chat with Documents / Document Review / Code Assistant - Python), "
        "Saved Prompts dropdown, 'Select Ready Files to Include in Chat Context' dropdown "
        "defaulting to 'Choose Options', DocuChat warning text, Tips & Tricks button, "
        "'How can I help?' text area, and Send button (enabled only when text is entered)",
        _step_3_verify_chat_landing_ui(),
        tc_name, page,
    )
    await _run_step(
        4,
        f"Go to Chat Configurations, select Model {model_name} and Chat Type as Basic Chat",
        _step_4_configure_model_and_chat_type(),
        tc_name, page,
    )
    await _run_step(
        5,
        "Navigate to Saved Prompts section > click on the Saved Prompts dropdown > select a "
        "saved prompt — verify its details are shown in the 'How can I help?' text box",
        _step_5_select_saved_prompt(),
        tc_name, page,
    )
    await _run_step(
        6,
        "Verify Chat Initialization — 'How can I help?' text box shows saved prompt details; "
        "click Send and confirm a chat response is displayed in the conversation window with a "
        "copy icon (to copy response contents) and a Regenerate Response button",
        _step_6_verify_chat_initialization(),
        tc_name, page,
    )
    await _run_step(
        7,
        "Verify long queries — click Chat Configuration, select the specified model and Basic "
        "Chat type, select a Saved Prompt with more than 3000 words, input a long query "
        "(more than 3000 words) in the 'How can I help?' text area, click Send, and verify the "
        "response is generated without latency or errors",
        _step_7_verify_long_query(),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify Chat history details — previous chats are visible in the left sidebar with "
        "Edit (\u270f\ufe0f) and Delete (\U0001f5d1\ufe0f) buttons",
        _verify_chat_history_edit_delete_controls(page),
        tc_name, page,
    )
    await _run_step(
        9,
        "Verify Chat Edit — select a chat from Chat History, click Edit button, make changes "
        "to the Chat Title (with 225-character limit) and click Save; verify the updated title "
        "is reflected in the sidebar",
        _step_9_10_edit_and_initialize(),
        tc_name, page,
    )
    await _run_step(
        10,
        "Initiate a Chat using the updated (edited) chat — verify the response is shown as "
        "per the edited chat",
        _verify_chat_response(chat_page, query),
        tc_name, page,
    )
    await _run_step(
        11,
        "Exit the application by clicking the browser close button",
        _step_11_exit_application(),
        tc_name, page,
    )


@pytest.mark.chat
@pytest.mark.regression
async def test_tc018_regression_docuchat_chat_validate_user_level_saved_prompt_with_41mini_crt_model_and_basic_chat_type(
    docuchat_context,
):
    """TC018 — Validate user level saved prompt with 4.1 mini CRT model and Basic Chat type."""
    _td = _get_chat_inputs("tc018")
    await _run_tc_flow(
        docuchat_context,
        query=_td.query,
        tc_name=_TC018_NAME,
        model_name=_td.model_name,
        tc_key="tc018",
    )
