"""TC005 Regression — DocuChat Chat: Validate Chat Initialization with 5 CRT model and Chat Type as Chat with Documents.

Test Case Name : TC005_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Chat Type as Chat with Documents
Description    : Verify DocuChat initializes Chat successfully and user can start interaction,
                 prevents empty query submission, handles very long queries gracefully without any
                 error, handles chat Edit/Delete functionality from the Chat selected in Chat history
                 without any errors.
Pre-condition  : User has valid DocuChat access. Frequently used file types are uploaded on File
                 Management module and are selectable in Chat module.
Feature        : QA-CRT
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
    _open_chat_workspace,
    _verify_chat_ui_details,
    _ensure_chat_configuration_open,
    _verify_chat_type_options,
    _select_model_and_chat_type,
    _verify_empty_query_behavior,
    _verify_send_button_enables_for_valid_input,
    _verify_chat_response,
    _verify_long_query_response,
    _verify_chat_history_edit_delete_controls,
    _verify_chat_edit_save,
    _verify_chat_edit_character_limit,
    _verify_chat_edit_cancel,
    _verify_chat_delete_cancel,
    _verify_chat_delete_confirm,
    _select_file_for_chat_context,
)

# TC005 identifier prefix — used to select the matching pre-uploaded document in File Management.
# The QA environment has a file pre-uploaded whose name includes this prefix.
_TC005_FILE_PREFIX = "TC005_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Chat Type as Chat with Documents"


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    query: str,
    tc_name: str,
    model_name: str,
    file_prefix: str,
) -> None:
    """Execute all 14 steps for TC005 (Chat with Documents, 5 CRT model).

    Key differences vs Basic Chat (TC001-TC003):
    - Step 4 : After selecting model + chat type, selects a document from the
               'Select Ready Files to Include in Chat Context' multiselect.
    - Step 6 : Chat initialization query is document-specific.
    - Step 7 : Long query is document-specific (>3000 words).
    """
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]

    # ── Step 3 helpers ───────────────────────────────────────────────────────
    async def _step_3_verify_chat_landing_ui() -> None:
        await _open_chat_workspace(page)
        await _verify_chat_ui_details(page)

    # ── Step 4 helpers ───────────────────────────────────────────────────────
    async def _step_4_configure_chat() -> None:
        await _ensure_chat_configuration_open(page)
        await _verify_chat_type_options(page)
        await _select_model_and_chat_type(page, model_name=model_name, chat_type="Chat with Documents")
        # Select at least one document from "Select Ready Files to Include in Chat Context"
        await _select_file_for_chat_context(page, tc_name_prefix=file_prefix)

    # ── Step 6 helpers ───────────────────────────────────────────────────────
    async def _step_6_initialize_chat() -> None:
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_chat_response(chat_page, query)

    # ── Step 14 helpers ──────────────────────────────────────────────────────
    async def _step_14_exit_application() -> None:
        await page.wait_for_timeout(100)

    # ── Test execution ───────────────────────────────────────────────────────
    await _run_step(
        1,
        "Open browser and navigate to DocuChat URL",
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
        "Verify UI details of Chat landing page",
        _step_3_verify_chat_landing_ui(),
        tc_name, page,
    )
    await _run_step(
        4,
        f"Go to Chat Configuration, select Model {model_name}, Chat Type as Chat with Documents, and select at least one document",
        _step_4_configure_chat(),
        tc_name, page,
    )
    await _run_step(
        5,
        "Verify empty query behavior — Send button remains disabled",
        _verify_empty_query_behavior(page),
        tc_name, page,
    )
    await _run_step(
        6,
        "Verify chat initialization with valid query specific to the uploaded document",
        _step_6_initialize_chat(),
        tc_name, page,
    )
    await _run_step(
        7,
        "Verify long query behavior (>3000 words) specific to the uploaded document — response without errors",
        _verify_long_query_response(chat_page, tc_key="tc005"),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify chat history details — Edit and Delete buttons present",
        _verify_chat_history_edit_delete_controls(page),
        tc_name, page,
    )
    await _run_step(
        9,
        "Verify chat Edit — save new title (225 char limit)",
        _verify_chat_edit_save(page),
        tc_name, page,
    )
    await _run_step(
        10,
        "Verify chat Edit — >255 characters in title field shows character-limit message",
        _verify_chat_edit_character_limit(page),
        tc_name, page,
    )
    await _run_step(
        11,
        "Verify chat Edit — click Cancel, no changes persist",
        _verify_chat_edit_cancel(page),
        tc_name, page,
    )
    await _run_step(
        12,
        "Verify chat Delete — click Cancel, chat is NOT deleted",
        _verify_chat_delete_cancel(page),
        tc_name, page,
    )
    await _run_step(
        13,
        "Verify chat Delete — click Delete, chat is deleted successfully",
        _verify_chat_delete_confirm(page),
        tc_name, page,
    )
    await _run_step(
        14,
        "Exit the application",
        _step_14_exit_application(),
        tc_name, page,
    )


@pytest.mark.chat
@pytest.mark.regression
async def test_tc005_regression_docuchat_chat_validate_chat_initialization_with_5crt_model_and_chat_with_documents(
    docuchat_context,
):
    """TC005 — Validate Chat Initialization with 5 CRT model and Chat Type as Chat with Documents."""
    _td = _get_chat_inputs("tc005")
    await _run_tc_flow(
        docuchat_context,
        query=_td.query,
        tc_name="TC005",
        model_name=_td.model_name,
        file_prefix=_TC005_FILE_PREFIX,
    )
