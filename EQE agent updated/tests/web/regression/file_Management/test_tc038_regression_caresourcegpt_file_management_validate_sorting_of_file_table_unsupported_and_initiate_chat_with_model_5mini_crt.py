"""TC038 Regression - CareSourceGPT File Management: Validate sorting of file table,
unsupported/duplicate/huge file upload, cancel upload, upload progress, delete file,
download processed documents and initiate chat with model 5-mini CRT."""
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
    _verify_send_button_enables_for_valid_input,
)
from tests.web.regression.file_Management.file_management_test_helpers import (
    _navigate_to_chat_section,
    _navigate_to_file_management,
    _verify_file_management_ui,
    _upload_files_bulk_via_file_page,
    _verify_sort_default,
    _verify_sort_column,
    _verify_sort_after_navigation,
    _try_unsupported_file_upload,
    _upload_huge_file,
    _upload_duplicate_file,
    _verify_cancel_upload,
    _verify_upload_progress,
    _upload_multiple_valid_documents,
    _verify_delete_single_file,
    _verify_delete_multiple_files,
    _verify_download_single_file,
    _verify_download_multiple_files,
    _open_choose_options_dropdown,
    _select_huge_and_duplicate_files,
    _select_model_and_chat_type_with_retry,
    _verify_chat_response_direct,
    _verify_long_query_direct,
    _pre_test_delete_all_files,
    _post_test_delete_all_chats,
    _post_test_delete_all_files,
    _cleanup_on_failure,
)

_TC_NAME = "TC038"


async def _run_tc_flow(docuchat_context: dict) -> None:
    """Execute all 41 steps for TC038."""
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]
    _td = _get_inputs("tc038")
    file_page = FileHandlingPage(page, int(settings["timeout_ms"]))

    # Steps 1-4
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

    # Step 5 — Upload 15 files
    await _run_step(5,
                    "Upload file types (.manifest, .docx, .pdf, .sql, .xlsx, .pptx, .html, .txt, .csv, "
                    ".md, .png, .bmp, .json, .xml, .jpg) via Browse Files / Drag and Drop; verify visible",
                    _upload_files_bulk_via_file_page(page, file_page, _TC_NAME), _TC_NAME, page)

    # Steps 6-12 — Sort verification
    await _run_step(6, "Verify default sort of the Files table",
                    _verify_sort_default(page), _TC_NAME, page)
    await _run_step(7, "Verify File Name column is sorted correctly (ascending and descending)",
                    _verify_sort_column(page, "File Name"), _TC_NAME, page)
    await _run_step(8, "Verify File Status column is sorted correctly (ascending and descending)",
                    _verify_sort_column(page, "Status"), _TC_NAME, page)
    await _run_step(9, "Verify File Size column is sorted correctly (ascending and descending)",
                    _verify_sort_column(page, "File Size"), _TC_NAME, page)
    await _run_step(10, "Verify File Type column is sorted correctly (ascending and descending)",
                    _verify_sort_column(page, "File Type"), _TC_NAME, page)
    await _run_step(11, "Verify Uploaded Date column is sorted correctly (ascending and descending)",
                    _verify_sort_column(page, "Uploaded Date"), _TC_NAME, page)
    await _run_step(12, "Verify ID column is sorted correctly (ascending and descending)",
                    _verify_sort_column(page, "ID"), _TC_NAME, page)

    # Step 13 — Navigate away and back; verify default sort restored
    await _run_step(13,
                    "Verify default sort is restored after navigating to a different page and back",
                    _verify_sort_after_navigation(page), _TC_NAME, page)

    # Steps 14-15 — Unsupported file type
    await _run_step(14,
                    "Verify Unsupported File Type: select unsupported file (.exe/.zip/.epub) via Browse/Drag",
                    _try_unsupported_file_upload(page, file_page), _TC_NAME, page)
    await _run_step(15,
                    "Click Upload for unsupported file; verify system restricts upload and shows error message",
                    _try_unsupported_file_upload(page, file_page), _TC_NAME, page)

    # Step 16 — Huge file upload
    huge_file_name_holder: list = [None]

    async def _wrap_huge_upload() -> None:
        huge_file_name_holder[0] = await _upload_huge_file(page, file_page, _TC_NAME.lower())

    await _run_step(16,
                    "Verify Huge File Upload (>30 MB): upload via Browse/Drag; verify progress bar and file in list",
                    _wrap_huge_upload(), _TC_NAME, page)

    # Step 17 — Duplicate file upload
    await _run_step(17,
                    "Verify Duplicate File Upload: upload the same file again; verify duplicate handled and visible",
                    _upload_duplicate_file(page, file_page, huge_file_name_holder[0], _TC_NAME.lower()), _TC_NAME, page)

    # Steps 18-20 — Cancel upload
    await _run_step(18, "Verify Cancel Upload: select a large file via Browse File / Drag and Drop",
                    _verify_cancel_upload(page, file_page, _TC_NAME.lower()), _TC_NAME, page)
    await _run_step(19, "Click Upload to start; verify file upload process starts with progress indicator",
                    _verify_cancel_upload(page, file_page, _TC_NAME.lower()), _TC_NAME, page)
    await _run_step(20, "While uploading click Cancel; verify upload stops immediately",
                    _verify_cancel_upload(page, file_page, _TC_NAME.lower()), _TC_NAME, page)

    # Steps 21-25 — Upload progress
    await _run_step(21, "Verify File Upload Progress: select a file via Browse Files / Drag and Drop",
                    _verify_upload_progress(page, file_page, _TC_NAME.lower()), _TC_NAME, page)
    await _run_step(22, "Click Upload to start; verify upload starts with progress indicator",
                    _verify_upload_progress(page, file_page, _TC_NAME.lower()), _TC_NAME, page)
    await _run_step(23, "Observe upload progress indicator during file upload (real-time status)",
                    _verify_upload_progress(page, file_page, _TC_NAME.lower()), _TC_NAME, page)
    await _run_step(24, "Verify Refresh button; ensure file upload is successful",
                    _verify_upload_progress(page, file_page, _TC_NAME.lower()), _TC_NAME, page)
    await _run_step(25, "Verify progress reaches 100% and file appears in the file list",
                    _verify_upload_progress(page, file_page, _TC_NAME.lower()), _TC_NAME, page)

    # Step 26 — Upload multiple valid documents
    await _run_step(26,
                    "Upload multiple valid documents of different file types (PDF/PPT/Word etc.)",
                    _upload_multiple_valid_documents(page, file_page, _TC_NAME.lower()), _TC_NAME, page)

    # Steps 27-28 — Delete single file
    await _run_step(27,
                    "Select single file; verify Delete Document and Download Processed Document buttons appear",
                    _verify_delete_single_file(page, _TC_NAME), _TC_NAME, page)
    await _run_step(28,
                    "Click Delete Document; verify document deleted with confirmation message",
                    _verify_delete_single_file(page, _TC_NAME), _TC_NAME, page)

    # Steps 29-30 — Delete multiple files
    await _run_step(29,
                    "Select multiple documents; verify Delete Documents and Download Processed Documents buttons appear",
                    _verify_delete_multiple_files(page, _TC_NAME), _TC_NAME, page)
    await _run_step(30,
                    "Click Delete Documents; verify documents deleted with confirmation message",
                    _verify_delete_multiple_files(page, _TC_NAME), _TC_NAME, page)

    # Step 31 — Upload multiple valid documents again (pre-req for download steps)
    await _run_step(31,
                    "Upload multiple valid documents of different file types for download verification",
                    _upload_multiple_valid_documents(page, file_page, _TC_NAME.lower()), _TC_NAME, page)

    # Steps 32-33 — Download single file
    await _run_step(32,
                    "Select single file; verify Delete Document and Download Processed Document buttons appear",
                    _verify_download_single_file(page, _TC_NAME), _TC_NAME, page)
    await _run_step(33,
                    "Click Download Processed Document; verify .txt file downloaded",
                    _verify_download_single_file(page, _TC_NAME), _TC_NAME, page)

    # Steps 34-35 — Download multiple files
    await _run_step(34,
                    "Select multiple files; verify Download Processed Documents button appears",
                    _verify_download_multiple_files(page, _TC_NAME), _TC_NAME, page)
    await _run_step(35,
                    "Click Download Processed Documents; verify .zip file with multiple .txt files downloaded",
                    _verify_download_multiple_files(page, _TC_NAME), _TC_NAME, page)

    # Step 36 — Navigate to Chat, configure model + chat type
    async def _step_36() -> None:
        await _navigate_to_chat_section(page)
        await _open_chat_workspace(page)
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type_with_retry(page, _td.model_name, _td.chat_type, _TC_NAME)

    await _run_step(36,
                    "Navigate to Chat > Chat Configurations, select Model 5-mini CRT and Chat Type as "
                    "Chat with Documents; verify Choose Options dropdown visible",
                    _step_36(), _TC_NAME, page)

    # Step 37 — Open Choose Options dropdown
    await _run_step(37,
                    "Click Choose Options dropdown and verify uploaded files list is visible",
                    _open_choose_options_dropdown(page), _TC_NAME, page)

    # Step 38 — Select huge and duplicate files
    await _run_step(38,
                    "Select the huge file and duplicate from the dropdown; verify selected and highlighted",
                    _select_huge_and_duplicate_files(page, huge_file_name_holder[0], _TC_NAME),
                    _TC_NAME, page)

    # Steps 39-40 — Chat verification
    chat_page = ChatPage(page, int(settings["timeout_ms"]))

    async def _step_39() -> None:
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_chat_response_direct(chat_page, _td.query)

    await _run_step(39,
                    "Verify Chat Initialization: send query for selected documents; verify response",
                    _step_39(), _TC_NAME, page)
    await _run_step(40,
                    "Verify Long query (>3000 words) for selected documents; verify response without errors",
                    _verify_long_query_direct(chat_page, _td.long_query), _TC_NAME, page)
    await _run_step(41, "Delete the chat session created during the test before closing the application",
                    _post_test_delete_all_chats(page), _TC_NAME, page)
    await _run_step(42, "Delete all uploaded documents from File Management before closing the application",
                    _post_test_delete_all_files(page), _TC_NAME, page)
    await _run_step(43, "Exit the application", page.wait_for_timeout(100), _TC_NAME, page)


@pytest.mark.file
@pytest.mark.regression
async def test_tc038_regression_caresourcegpt_file_management_validate_sorting_of_file_table_unsupported_and_initiate_chat_with_model_5mini_crt(
    docuchat_context,
):
    """TC038 - Validate sorting, unsupported/duplicate/huge file upload, delete, download, chat with 5-mini CRT."""
    try:
        await _run_tc_flow(docuchat_context)
    finally:
        await _cleanup_on_failure(docuchat_context["page"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv"]))
