"""TC020 Regression — DocuChat Chat: Validate user level saved prompt with 5 CRT model and Chat Type as Chat with Documents.

Test Case Name : TC020_Regression_DocuChat_Chat_Validate user level saved prompt with
                 5 CRT model and Chat Type as Chat with Documents
Description    : Verify DocuChat initializes Chat successfully using user level Saved Prompts
                 from Prompt Library and user can start interaction, handles very long queries
                 gracefully without any error, handles chat Edit functionality from the Chat
                 selected in Chat history without any errors.
Pre-condition  : User has valid DocuChat access.
                 Frequently used file types are uploaded on File Management module and are
                 selectable in Chat module.
                 Application should have Prompts created (specific to Chat type selected and
                 support long queries of 3000 words) in Prompt Library and can be selected in
                 Chat module under Saved Prompts section.
Feature        : Chat
Environment    : QA-CRT

Note on steps: TC020 source document lists Steps 2 and 3 with identical text
("Verify the landing page options are displayed"). Step 3 is treated as the
UI-details verification step (same as TC019/TC021) — 11 steps total.
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
    _select_file_for_chat_context,
    _select_model_and_chat_type,
    _verify_chat_edit_and_initialize_saved_prompt_chat_with_documents,
    _verify_chat_history_edit_delete_controls,
    _verify_chat_response,
    _verify_chat_type_options,
    _verify_chat_ui_details,
    _verify_long_query_with_saved_prompt_chat_with_documents,
    _verify_saved_prompt_chat_initialization,
)

_TC020_NAME = (
    "TC020_Regression_DocuChat_Chat_Validate user level saved prompt with "
    "5 CRT model and Chat Type as Chat with Documents"
)

_TC020_FILE_PREFIX = (
    "TC020_Regression_DocuChat_Chat_Validate user level saved prompt with "
    "5 CRT model and Chat Type as Chat with Documents"
)


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    query: str,
    tc_name: str,
    model_name: str,
    tc_key: str,
) -> None:
    """Execute all 11 steps for TC020.

    Step 1  : Open browser and navigate to the DocuChat URL.
    Step 2  : Verify landing page options (Chat, File Management, Prompt Library).
    Step 3  : Verify UI details of Chat landing page.
    Step 4  : Go to Chat Configurations, select Model 5 CRT and Chat Type as
              Chat with Documents with at least one document selected from file drop-down.
    Step 5  : Navigate to Saved Prompts section, select a saved prompt specific to
              Chat with Documents, verify it populates the 'How can I help?' text area.
    Step 6  : Click Send; verify response is generated specific to the document
              selected without latency or errors.
    Step 7  : Re-configure model + Chat with Documents, select a Saved Prompt with
              >3000 words, send long query (>3000 words), verify response without
              latency or errors.
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
        await _select_model_and_chat_type(page, model_name=model_name, chat_type="Chat with Documents")
        await _select_file_for_chat_context(page, tc_name_prefix=_TC020_FILE_PREFIX)

    # ── Step 5 ───────────────────────────────────────────────────────────────
    async def _step_5_select_saved_prompt() -> None:
        _state["prompt_text"] = await _select_and_verify_saved_prompt(page)

    # ── Step 6 ───────────────────────────────────────────────────────────────
    async def _step_6_verify_chat_initialization() -> None:
        await _verify_saved_prompt_chat_initialization(chat_page, _state["prompt_text"])

    # ── Step 7 ───────────────────────────────────────────────────────────────
    async def _step_7_verify_long_query() -> None:
        await _verify_long_query_with_saved_prompt_chat_with_documents(
            page, chat_page, model_name, tc_key, file_prefix=_TC020_FILE_PREFIX
        )

    # ── Steps 9-10 ───────────────────────────────────────────────────────────
    async def _step_9_10_edit_and_initialize() -> None:
        await _verify_chat_edit_and_initialize_saved_prompt_chat_with_documents(
            page, chat_page, query
        )

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
        f"Go to Chat Configurations, select Model {model_name} and Chat Type as Chat with "
        "Documents; select at least one document from the 'Select Ready Files to Include in "
        "Chat Context' dropdown",
        _step_4_configure_model_and_chat_type(),
        tc_name, page,
    )
    await _run_step(
        5,
        "Navigate to Saved Prompts section > click on the Saved Prompts dropdown > select a "
        "saved prompt specific to Chat with Documents — verify its details are shown in the "
        "'How can I help?' text box",
        _step_5_select_saved_prompt(),
        tc_name, page,
    )
    await _run_step(
        6,
        "Verify Chat Initialization — input the saved prompt (at user level) specific to the "
        "uploaded file in the 'How can I help?' text area and click Send; confirm a response "
        "is generated specific to the document selected without latency or errors",
        _step_6_verify_chat_initialization(),
        tc_name, page,
    )
    await _run_step(
        7,
        "Verify Long query Saved Prompt — click Chat Configuration, select the specified "
        f"model {model_name} and Chat Type > Chat with Documents, select a Saved Prompt with "
        "more than 3000 words, input query (more than 3000 words) in the 'How can I help?' "
        "text area and click Send; verify response is generated without latency or errors",
        _step_7_verify_long_query(),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify Chat history details — previous chats are visible in the left sidebar with "
        "Edit (✏️) and Delete (🗑️) buttons",
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
async def test_tc020_regression_docuchat_chat_validate_user_level_saved_prompt_with_5crt_model_and_chat_with_documents(
    docuchat_context,
):
    """TC020 — Validate user level saved prompt with 5 CRT model and Chat Type as Chat with Documents."""
    _td = _get_chat_inputs("tc020")
    await _run_tc_flow(
        docuchat_context,
        query=_td.query,
        tc_name=_TC020_NAME,
        model_name=_td.model_name,
        tc_key="tc020",
    )
