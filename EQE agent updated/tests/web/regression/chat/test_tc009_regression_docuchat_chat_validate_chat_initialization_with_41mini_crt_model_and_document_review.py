"""TC009 Regression — DocuChat Chat: Validate Chat Initialization with 4.1-mini CRT model and Document Review.

Test Case Name : TC009_Regression_DocuChat_Chat_Validate Chat Initialization with 4.1-mini CRT model and Document Review
Description    : Verify DocuChat initializes Chat successfully and user can start interaction,
                 prevents empty query submission, handles very long queries gracefully without any
                 error, handles chat Edit/Delete functionality from the Chat selected in Chat history
                 without any errors.
Pre-condition  : User has valid DocuChat access.
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
    _verify_document_review_response,
    _verify_long_query_response,
    _verify_chat_history_edit_delete_controls,
    _verify_chat_edit_save,
    _verify_chat_edit_character_limit,
    _verify_chat_edit_cancel,
    _verify_chat_delete_cancel,
    _verify_chat_delete_confirm,
)


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    query: str,
    tc_name: str,
    model_name: str,
) -> None:
    """Execute all 14 steps for TC009 (Document Review, 4.1-mini CRT model).

    Note: Unlike TC007/TC008, this TC does not require pre-uploaded files
    (no file selection step in Step 4 per test case specification).
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
        await _select_model_and_chat_type(page, model_name=model_name, chat_type="Document Review")

    # ── Step 6 helpers ───────────────────────────────────────────────────────
    async def _step_6_initialize_chat() -> None:
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_document_review_response(chat_page, query)

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
        f"Go to Chat Configuration, select Model {model_name} and Chat Type as Document Review",
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
        "Verify Document Review chat initialization with garbled/special-character query — response displayed with copy and regenerate options",
        _step_6_initialize_chat(),
        tc_name, page,
    )
    await _run_step(
        7,
        "Verify long query behavior (>3000 words with grammatical/semantical errors) — response without errors",
        _verify_long_query_response(chat_page, tc_key="tc009"),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify chat history details — Edit and Delete buttons present in left sidebar",
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
        "Verify chat Delete — click Cancel in Confirm Chat Thread Delete dialog, chat is NOT deleted",
        _verify_chat_delete_cancel(page),
        tc_name, page,
    )
    await _run_step(
        13,
        "Verify chat Delete — click Delete in Confirm Chat Thread Delete dialog, chat is deleted successfully",
        _verify_chat_delete_confirm(page),
        tc_name, page,
    )
    await _run_step(
        14,
        "Exit the application by closing the browser",
        _step_14_exit_application(),
        tc_name, page,
    )


@pytest.mark.chat
@pytest.mark.regression
async def test_tc009_regression_docuchat_chat_validate_chat_initialization_with_41mini_crt_model_and_document_review(
    docuchat_context,
):
    """TC009 — Validate Chat Initialization with 4.1-mini CRT model and Document Review."""
    _td = _get_chat_inputs("tc009")
    await _run_tc_flow(
        docuchat_context,
        query=_td.query,
        tc_name="TC009",
        model_name=_td.model_name,
    )
