"""TC036 Regression - CareSourceGPT File Management: Validate Chat Initialization with 5 CRT
model for multi file selection and cross document summary."""
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
from pages.file_handling_page import FileHandlingPage
from utils.step_runner import run_step as _run_step
from utils.test_data_loader import get_file_management_tc_inputs as _get_inputs
from tests.web.regression.chat.chat_test_helpers import (
    _assert_landing_page_options,
    _open_chat_workspace,
    _ensure_chat_configuration_open,
    _select_model_and_chat_type,
    _verify_send_button_enables_for_valid_input,
)
from tests.web.regression.file_Management.file_management_test_helpers import (
    _navigate_to_chat_section,
    _navigate_to_file_management,
    _verify_file_management_ui,
    _upload_files_bulk_via_file_page,
    _open_choose_options_dropdown,
    _select_multiple_ready_files,
    _verify_chat_response_direct,
    _verify_long_query_direct,
    _pre_test_delete_all_files,
    _post_test_delete_all_chats,
    _post_test_delete_all_files,
    _cleanup_on_failure,
)

_TC_NAME = "TC036"


async def _run_tc_flow(docuchat_context: dict) -> None:
    """Execute all 11 steps for TC036."""
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]
    _td = _get_inputs("tc036")
    file_page = FileHandlingPage(page, int(settings["timeout_ms"]))

    async def _step_6() -> None:
        await _navigate_to_chat_section(page)
        await _open_chat_workspace(page)
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(page, model_name=_td.model_name, chat_type=_td.chat_type)

    async def _step_9() -> None:
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_chat_response_direct(chat_page, _td.query)

    await _run_step(1, "Open the browser and navigate to DocuChat URL",
                    page.goto(settings["base_url"]), _TC_NAME, page)
    await _run_step(2, "Verify landing page options (Chat, File Management, Prompt Library)",
                    _assert_landing_page_options(page), _TC_NAME, page)
    await _run_step(3, "Select File Management in left sidebar and navigate to File Management module",
                    _navigate_to_file_management(page), _TC_NAME, page)
    await _run_step(4, "Verify the UI details of File Management landing page",
                    _verify_file_management_ui(page), _TC_NAME, page)

    # Pre-test cleanup — delete all existing files
    await _pre_test_delete_all_files(page)
    await _run_step(3, "Re-navigate to File Management after pre-test cleanup",
                    _navigate_to_file_management(page), _TC_NAME, page)

    await _run_step(5,
                    "Upload file types (.manifest, .docx, .pdf, .sql, .xlsx, .pptx, .html, .txt, .csv, "
                    ".md, .png, .bmp, .json, .xml, .jpg) via Browse Files / Drag and Drop; verify visible",
                    _upload_files_bulk_via_file_page(page, file_page, _TC_NAME), _TC_NAME, page)
    await _run_step(6,
                    "Navigate to Chat > Chat Configurations, select Model 5 CRT and Chat Type as "
                    "Chat with Documents; verify Choose Options dropdown visible",
                    _step_6(), _TC_NAME, page)
    await _run_step(7, "Click Choose Options dropdown and verify uploaded files list is visible",
                    _open_choose_options_dropdown(page), _TC_NAME, page)
    await _run_step(8, "Select 2 or 3 files from the dropdown and verify they are selected and highlighted",
                    _select_multiple_ready_files(page, count=2), _TC_NAME, page)

    chat_page = ChatPage(page, int(settings["timeout_ms"]))
    await _run_step(9, "Verify Chat Initialization: send cross-document summary query; verify response",
                    _step_9(), _TC_NAME, page)
    await _run_step(10, "Verify Long query (>3000 words): verify cross-document summary without errors",
                    _verify_long_query_direct(chat_page, _td.long_query), _TC_NAME, page)
    await _run_step(11, "Delete the chat session created during the test before closing the application",
                    _post_test_delete_all_chats(page), _TC_NAME, page)
    await _run_step(12, "Delete all uploaded documents from File Management before closing the application",
                    _post_test_delete_all_files(page), _TC_NAME, page)
    await _run_step(13, "Exit the application", page.wait_for_timeout(100), _TC_NAME, page)


@pytest.mark.file
@pytest.mark.regression
async def test_tc036_regression_caresourcegpt_file_management_validate_chat_initialization_with_5_crt_model_for_multi_file_selection_used_by_the_client_and_look_for_cross_document_summary(
    docuchat_context,
):
    """TC036 - Validate Chat Initialization with 5 CRT model for multi file selection."""
    try:
        await _run_tc_flow(docuchat_context)
    finally:
        await _cleanup_on_failure(docuchat_context["page"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv"]))