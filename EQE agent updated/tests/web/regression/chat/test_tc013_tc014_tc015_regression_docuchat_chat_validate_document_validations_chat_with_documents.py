"""TC013 / TC014 / TC015 Regression — DocuChat Chat: Validate Document validations with Chat Type as Chat with Documents.

Parametrized over three model variants:
  TC013 — 5.1 mini CRT model
  TC014 — 5 CRT model
  TC015 — 4.1 mini CRT model

Description    : Verify DocuChat initializes Chat successfully and validates details from Documents
                 (from the frequently used list .docx, .pdf, .sql, .xlsx, .pptx, .html, .txt,
                 .csv, .md, .png, .bmp, .json, .xml, .jpg, .manifest) uploaded and selected in
                 Chat module.
Pre-condition  : User has valid DocuChat access.
                 Frequently used file types are uploaded on File Management module from the
                 frequently used list (.docx, .pdf, .sql, .xlsx, .pptx, .html, .txt, .csv, .md,
                 .png, .bmp, .json, .xml, .jpg, .manifest) and are selectable in Chat module.
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
    FREQUENTLY_USED_FILE_TYPES,
    _assert_landing_page_options,
    _ensure_chat_configuration_open,
    _open_chat_workspace,
    _select_file_for_chat_context_by_extension,
    _select_model_and_chat_type,
    _verify_all_document_types_iteration,
    _log_document_validation_summary,
    _verify_chat_edit_and_initialize_with_document,
    _verify_chat_history_edit_delete_controls,
    _verify_chat_response,
    _verify_chat_type_options,
    _verify_chat_ui_details,
    _verify_long_query_response,
    _verify_send_button_enables_for_valid_input,
)

# ── Model variants ────────────────────────────────────────────────────────────
# Each param: (model_name, tc_name, tc_key)
# To add a new model variant: add one pytest.param line below — no other changes needed.
_MODEL_VARIANTS = [
    pytest.param(
        "5.1 mini CRT",
        "TC013",
        "tc013",
        id="TC013",
    ),
    pytest.param(
        "5 CRT",
        "TC014",
        "tc014",
        id="TC014",
    ),
    pytest.param(
        "4.1 mini CRT",
        "TC015",
        "tc015",
        id="TC015",
    ),
]

# First document type used in Steps 4-6; all 15 types iterated in Step 7
_FIRST_DOC_TYPE = ".docx"


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    query: str,
    tc_name: str,
    model_name: str,
    tc_key: str,
) -> None:
    """Execute all 10 steps for Document Validations — Chat with Documents (TC013 / TC014 / TC015).

    The only difference between variants is the model name selected in Step 4.
    Steps 4-6 operate on the first document type (.docx).
    Step 7 repeats the configure → select-file → simple-query → long-query cycle
    for the remaining 14 frequently used file types.
    Step 9 edits the chat title (up to 225 chars) and verifies a document response.
    """
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]

    # ── Step 3 ───────────────────────────────────────────────────────────────
    async def _step_3_verify_chat_landing_ui() -> None:
        await _open_chat_workspace(page)
        await _verify_chat_ui_details(page)

    # ── Step 4 ───────────────────────────────────────────────────────────────
    async def _step_4_configure_chat() -> None:
        await _ensure_chat_configuration_open(page)
        await _verify_chat_type_options(page)
        await _select_model_and_chat_type(
            page, model_name=model_name, chat_type="Chat with Documents"
        )
        # Select the first document type (.docx) from 'Select Ready Files to Include in Chat Context'
        await _select_file_for_chat_context_by_extension(page, _FIRST_DOC_TYPE)

    # ── Step 5 ───────────────────────────────────────────────────────────────
    async def _step_5_verify_chat_initialization() -> None:
        # Confirm Send button activates when text is entered, then send query
        await _verify_send_button_enables_for_valid_input(page)
        await _verify_chat_response(chat_page, query)

    # ── Step 7 ───────────────────────────────────────────────────────────────
    async def _step_7_validate_all_document_types() -> None:
        # Iterate the remaining 14 file types (first type .docx covered in Steps 4-6)
        remaining_types = [ext for ext in FREQUENTLY_USED_FILE_TYPES if ext != _FIRST_DOC_TYPE]
        iteration_results = await _verify_all_document_types_iteration(
            page, chat_page, model_name, query, tc_key, remaining_types
        )
        # Print a summary banner so every run shows validated vs skipped formats
        _log_document_validation_summary(
            tc_name=tc_name,
            first_ext=_FIRST_DOC_TYPE,
            first_result="PASSED",
            iteration_results=iteration_results,
        )

    # ── Step 9 ───────────────────────────────────────────────────────────────
    async def _step_9_chat_edit_and_initialize() -> None:
        await _verify_chat_edit_and_initialize_with_document(page, chat_page, query)

    # ── Step 10 ──────────────────────────────────────────────────────────────
    async def _step_10_exit_application() -> None:
        await page.wait_for_timeout(100)

    # ── Test execution ────────────────────────────────────────────────────────
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
        "Verify UI details of Chat landing page — sidebar, configuration panel, prompts, "
        "ready files dropdown, warning, Tips & Tricks, input, Send button",
        _step_3_verify_chat_landing_ui(),
        tc_name, page,
    )
    await _run_step(
        4,
        f"Go to Chat Configurations, select Model {model_name} and Chat Type as "
        f"Chat with Documents, select a {_FIRST_DOC_TYPE} document from the ready files dropdown",
        _step_4_configure_chat(),
        tc_name, page,
    )
    await _run_step(
        5,
        "Verify Chat Initialization — enter a document-specific query and confirm a "
        "response is generated without latency or errors",
        _step_5_verify_chat_initialization(),
        tc_name, page,
    )
    await _run_step(
        6,
        "Verify long query (>3000 words) specific to the uploaded document — "
        "response generated without latency or errors",
        _verify_long_query_response(chat_page, tc_key=tc_key),
        tc_name, page,
    )
    await _run_step(
        7,
        "Repeat Steps 4-6 for all remaining 14 frequently used document types "
        "(.pdf .sql .xlsx .pptx .html .txt .csv .md .png .bmp .json .xml .jpg .manifest) — "
        "validate simple and long query responses for each",
        _step_7_validate_all_document_types(),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify Chat history details — previous chats visible in sidebar with Edit and Delete buttons",
        _verify_chat_history_edit_delete_controls(page),
        tc_name, page,
    )
    await _run_step(
        9,
        "Verify Chat Edit with 225 character title limit and initialize Chat with Documents "
        "for a .docx chat — edit title, save, and confirm document-specific response is generated",
        _step_9_chat_edit_and_initialize(),
        tc_name, page,
    )
    await _run_step(
        10,
        "Exit the application by closing the browser",
        _step_10_exit_application(),
        tc_name, page,
    )


@pytest.mark.chat
@pytest.mark.regression
@pytest.mark.parametrize("model_name, tc_name, tc_key", _MODEL_VARIANTS)
async def test_document_validations_chat_with_documents(
    docuchat_context,
    model_name: str,
    tc_name: str,
    tc_key: str,
):
    """Validate Document Validations — Chat with Documents across all model variants.

    Parametrize IDs: TC013 (5.1 mini CRT), TC014 (5 CRT), TC015 (4.1 mini CRT).
    To run a single variant: pytest -k TC013
    To add a new model: add one pytest.param entry to _MODEL_VARIANTS above.
    """
    _td = _get_chat_inputs(tc_key)
    await _run_tc_flow(
        docuchat_context,
        query=_td.query,
        tc_name=tc_name,
        model_name=model_name,
        tc_key=tc_key,
    )
