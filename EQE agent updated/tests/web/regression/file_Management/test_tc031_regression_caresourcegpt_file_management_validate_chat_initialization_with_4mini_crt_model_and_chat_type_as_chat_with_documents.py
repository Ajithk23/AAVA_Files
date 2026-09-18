"""TC031 Regression - CareSourceGPT File Management: Validate Chat Initialization with 4 mini CRT
model and Chat Type as Chat with Documents."""
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
    _upload_and_verify,
    _upload_file_via_drag_drop,
    _handle_duplicate_file_dialog,
    _verify_file_in_uploaded_list,
    _open_choose_options_dropdown,
    _select_multiple_ready_files,
    _verify_chat_response_direct,
    _verify_long_query_direct,
    _pre_test_delete_all_files,
    _post_test_delete_all_chats,
    _post_test_delete_all_files,
    _cleanup_on_failure,
)

_TC_NAME = "TC031"
_DOCX_FILE = PROJECT_ROOT / "test_data" / "sample_files" / "test_upload.docx"


async def _run_tc_flow(docuchat_context: dict) -> None:
    """Execute all 11 steps for TC031."""
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]
    _td = _get_inputs("tc031")

    async def _step_5() -> None:
        # Upload the .docx file via Browse Files button
        await _upload_and_verify(page, _DOCX_FILE)
        # Exercise drag/drop as a best-effort duplicate-flow check without
        # reasserting the same file a second time.
        try:
            await _upload_file_via_drag_drop(page, _DOCX_FILE)
            await page.wait_for_timeout(2000)
        except Exception:
            pass
        try:
            await _handle_duplicate_file_dialog(page)
        except Exception:
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
        await page.wait_for_timeout(1000)

    async def _step_6() -> None:
        await _navigate_to_chat_section(page)
        await _open_chat_workspace(page)
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(page, model_name=_td.model_name, chat_type=_td.chat_type)

    async def _step_9() -> None:
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_chat_response_direct(chat_page, _td.query)

    await _run_step(1, "Open the browser (Chrome/Edge) and Enter URL as DocuChat application URL",
                    page.goto(settings["base_url"]), _TC_NAME, page)
    await _run_step(2, "Verify the landing page options are displayed (Chat, File Management, Prompt Library)",
                    _assert_landing_page_options(page), _TC_NAME, page)
    await _run_step(3, "Select File Management in left side bar and navigate to the File Management module",
                    _navigate_to_file_management(page), _TC_NAME, page)
    await _run_step(4, "Verify the UI details of File Management landing page",
                    _verify_file_management_ui(page), _TC_NAME, page)

    # Pre-test cleanup — delete all existing files before uploading
    await _pre_test_delete_all_files(page)
    await _run_step(3, "Re-navigate to File Management after pre-test cleanup",
                    _navigate_to_file_management(page), _TC_NAME, page)

    await _run_step(5,
                    "Upload file(type .docx) through both Browse files button and Drag and drop option "
                    "and verify whether the uploaded file is visible in uploaded files list",
                    _step_5(), _TC_NAME, page)
    await _run_step(6,
                    "Navigate to Chat > Go to Chat Configurations, Select Model 4 mini CRT and Chat Type "
                    "as Chat with Documents; verify Choose Options dropdown under "
                    "'Select Ready Files to Include in Chat Context:' is visible and accessible",
                    _step_6(), _TC_NAME, page)
    await _run_step(7,
                    "Click on 'Choose Options' dropdown under the label "
                    "'Select Ready Files to Include in Chat Context:' and verify the uploaded files list is visible",
                    _open_choose_options_dropdown(page), _TC_NAME, page)
    await _run_step(8,
                    "Select the file uploaded in previous step from the dropdown and verify it is selected and highlighted",
                    _select_multiple_ready_files(page, count=1, preferred_file_names=[_DOCX_FILE.name]), _TC_NAME, page)

    chat_page = ChatPage(page, int(settings["timeout_ms"]))
    await _run_step(9,
                    "Verify Chat Initialization: Click on Chat Configuration, select model 4 mini CRT and "
                    "Chat Type as Chat with Documents; input query specific to the uploaded file in the "
                    "'How can I help?' text area and click on Send button; verify response",
                    _step_9(), _TC_NAME, page)
    await _run_step(10,
                    "Verify Long query: input long query (with more than 3000 words) specific to the file "
                    "uploaded in the 'How can I help?' text area and click on Send button; "
                    "verify response without latency or errors",
                    _verify_long_query_direct(chat_page, _td.long_query), _TC_NAME, page)
    await _run_step(11, "Delete the chat session created during the test before closing the application",
                    _post_test_delete_all_chats(page), _TC_NAME, page)
    await _run_step(12, "Delete all uploaded documents from File Management before closing the application",
                    _post_test_delete_all_files(page), _TC_NAME, page)
    await _run_step(13, "Exit the application by clicking the browser close button",
                    page.wait_for_timeout(100), _TC_NAME, page)


@pytest.mark.file
@pytest.mark.regression
async def test_tc031_regression_caresourcegpt_file_management_validate_chat_initialization_with_4mini_crt_model_and_chat_type_as_chat_with_documents(
    docuchat_context,
):
    """TC031 - Validate Chat Initialization with 4 mini CRT model and Chat Type as Chat with Documents."""
    try:
        await _run_tc_flow(docuchat_context)
    finally:
        await _cleanup_on_failure(docuchat_context["page"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv"]))