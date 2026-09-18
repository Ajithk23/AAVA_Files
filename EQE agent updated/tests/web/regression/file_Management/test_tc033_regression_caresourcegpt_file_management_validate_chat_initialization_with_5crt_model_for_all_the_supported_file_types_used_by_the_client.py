"""TC033 Regression — DocuChat File Management: Validate Chat Initialization with 5 CRT model for all the supported file types used by the client.

Test Case Name : TC033_Regression_DocuChat_File Management_Validate Chat Initialization with 5 CRT model for all the supported file types used by the client
Description    : Verify CareSourceGPT initializes Chat with Documents using all the 15 frequently
                 used supported file types.
Pre-condition  : User has valid CareSourceGPT access.
                 Frequently used file types are uploaded on File Management module and are
                 selectable in Chat module.
Feature        : QA-CRT
Environment    : INT/CRT
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
from utils.test_data_loader import get_tc033_inputs as _get_tc033_inputs
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
    _upload_and_verify_tolerant,
    _verify_ready_files_in_chat_dropdown,
    _select_all_files_in_chat_dropdown,
    _verify_chat_response_direct,
    _verify_long_query_direct,
    _pre_test_delete_all_files,
    _post_test_delete_all_chats,
    _post_test_delete_all_files,
    _cleanup_on_failure,
)

# Single reliable file used for Chat Initialization (steps 7-10).
# PDF is chosen as it has real content and is universally supported.
_TC033_CHAT_FILE = "test_upload.pdf"


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    tc_name: str,
) -> None:
    """Execute all 11 steps for TC033.

    Steps:
    1.  Open browser and navigate to DocuChat URL.
    2.  Verify landing page options (Chat, File Management, Prompt Library).
    3.  Select File Management in left sidebar and navigate to File Management module.
    4.  Verify the UI details of File Management landing page.
    5.  Upload all 15 supported file types and verify each appears in the uploaded files list.
    6.  Navigate to Chat > Chat Configuration, select Model 5 CRT and Chat Type as
        Chat with Documents.
    7.  Click "Choose Options" dropdown and verify the uploaded file is visible.
    8.  Select the uploaded file from the dropdown.
    9.  Verify Chat Initialization — send a query and confirm a response is returned.
    10. Verify Long query — send a >3000-word query and confirm a response is returned.
    11. Exit the application.
    """
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]
    _td = _get_tc033_inputs()

    # ── Step 5 helper: upload all 15 files — first 7 via Browse Files, last 8 via Drag & Drop ─
    async def _step_5_upload_all_files() -> None:
        file_paths = [Path(fp) for fp in _td.file_paths]
        browse_files = file_paths[:7]     # .manifest, .docx, .pdf, .sql, .xlsx, .pptx, .html
        drag_drop_files = file_paths[7:]  # .txt, .csv, .md, .png, .bmp, .json, .xml, .jpg
        for file_path in browse_files:
            await _upload_and_verify_tolerant(page, file_path, method="browse")
        for file_path in drag_drop_files:
            await _upload_and_verify_tolerant(page, file_path, method="drag_drop")

    # ── Step 6 helper: navigate to Chat and configure model + chat type ──────
    async def _step_6_navigate_and_configure_chat() -> None:
        await _navigate_to_chat_section(page)
        await _open_chat_workspace(page)
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(
            page,
            model_name=_td.model_name,
            chat_type=_td.chat_type,
        )

    # ── Step 9 helper: verify chat initialization ────────────────────────────
    async def _step_9_verify_chat_initialization() -> None:
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_chat_response_direct(chat_page, _td.query)

    # ── Step 11 helper: exit application ────────────────────────────────────
    async def _step_11_exit_application() -> None:
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
        "Select File Management in left sidebar and navigate to File Management module",
        _navigate_to_file_management(page),
        tc_name, page,
    )
    await _run_step(
        4,
        "Verify the UI details of File Management landing page",
        _verify_file_management_ui(page),
        tc_name, page,
    )

    # Pre-test cleanup — delete all existing files from previous failed runs
    await _pre_test_delete_all_files(page)
    await _run_step(
        3,
        "Re-navigate to File Management after pre-test cleanup",
        _navigate_to_file_management(page),
        tc_name, page,
    )

    await _run_step(
        5,
        "Upload all 15 supported file types (.manifest, .docx, .pdf, .sql, .xlsx, .pptx, "
        ".html, .txt, .csv, .md, .png, .bmp, .json, .xml, .jpg) and verify each in uploaded files list",
        _step_5_upload_all_files(),
        tc_name, page,
    )
    await _run_step(
        6,
        f"Navigate to Chat > Chat Configuration, select Model {_td.model_name} "
        f"and Chat Type as {_td.chat_type}",
        _step_6_navigate_and_configure_chat(),
        tc_name, page,
    )
    await _run_step(
        7,
        f"Click 'Choose Options' dropdown and verify '{_TC033_CHAT_FILE}' is visible",
        _verify_ready_files_in_chat_dropdown(page, [_TC033_CHAT_FILE]),
        tc_name, page,
    )
    await _run_step(
        8,
        f"Select '{_TC033_CHAT_FILE}' from the 'Choose Options' dropdown",
        _select_all_files_in_chat_dropdown(page, [_TC033_CHAT_FILE]),
        tc_name, page,
    )
    await _run_step(
        9,
        "Verify Chat Initialization — input query specific to uploaded files and verify response",
        _step_9_verify_chat_initialization(),
        tc_name, page,
    )
    await _run_step(
        10,
        "Verify Long query (>3000 words) specific to uploaded files — verify response without errors",
        _verify_long_query_direct(chat_page, _td.long_query),
        tc_name, page,
    )
    await _run_step(
        11,
        "Delete the chat session created during the test before closing the application",
        _post_test_delete_all_chats(page),
        tc_name, page,
    )
    await _run_step(
        12,
        "Delete all uploaded documents from File Management before closing the application",
        _post_test_delete_all_files(page),
        tc_name, page,
    )
    await _run_step(
        13,
        "Exit the application",
        _step_11_exit_application(),
        tc_name, page,
    )


@pytest.mark.file
@pytest.mark.regression
async def test_tc033_regression_docuchat_file_management_validate_chat_initialization_with_5crt_model_for_all_the_supported_file_types_used_by_the_client(
    docuchat_context,
):
    """TC033 — Validate Chat Initialization with 5 CRT model for all the supported file types used by the client."""
    try:
        await _run_tc_flow(docuchat_context, tc_name="TC033")
    finally:
        await _cleanup_on_failure(docuchat_context["page"])


if __name__ == "__main__":
    raise SystemExit(
        pytest.main([
            __file__,
            "--env=qa",
            "--headless=false",
            "-vv",
            "-s",
            "-p",
            "no:rerunfailures",
            "-p",
            "no:xdist",
        ])
    )