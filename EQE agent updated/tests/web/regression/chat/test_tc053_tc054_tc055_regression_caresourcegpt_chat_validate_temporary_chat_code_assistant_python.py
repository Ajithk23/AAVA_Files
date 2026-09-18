"""TC053 / TC054 / TC055 Regression — CareSourceGPT Chat:
Validate Temporary Chat Initialization with Chat Type as Code Assistant - Python.

Parametrized over three model variants:
  TC053 — 5-mini CRT model
  TC054 — 5 CRT model
  TC055 — 4.1 mini CRT model

Description    : Verify CareSourceGPT initializes Temporary Chat successfully and user
                 can start interaction, prevents empty query submission, handles very long
                 queries gracefully without any error, and stores no chat in Chat history
                 as user initializes New Chat.
Pre-condition  : User has valid CareSourceGPT access.
Feature        : Chat
Environment    : QA-CRT
Note           : All test cases are for Temporary Chat sessions — messages must NOT
                 appear in chat history.
                 Code-generation queries are used (e.g. 'Generate code for Palindrome').
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
    _verify_chat_ui_details,
    _ensure_chat_configuration_open,
    _select_model_and_chat_type,
    _verify_empty_query_behavior,
    _verify_long_query_response,
    _click_new_chat_button,
    _enable_temporary_chat,
    _verify_temporary_chat_banner,
    _verify_no_chat_history_for_temporary_chat,
    _verify_new_chat_clears_temporary_session,
    _verify_temporary_chat_response,
)

# ── Model variants ────────────────────────────────────────────────────────────
# Each param: (model_name, tc_name, tc_key)
_MODEL_VARIANTS = [
    pytest.param(
        "5-mini CRT",
        "TC053",
        "tc053",
        id="TC053",
    ),
    pytest.param(
        "5 CRT",
        "TC054",
        "tc054",
        id="TC054",
    ),
    pytest.param(
        "4.1-mini CRT",
        "TC055",
        "tc055",
        id="TC055",
    ),
]


async def _run_tc_flow(
    docuchat_context: dict[str, object],
    query: str,
    tc_name: str,
    model_name: str,
    tc_key: str,
) -> None:
    """Execute all 12 steps for Temporary Chat Initialization with Code Assistant - Python type.

    Key differences from TC010-TC012 (regular Code Assistant):
    - Steps 4-5  : Click '+ New Chat' then enable Temporary Chat checkbox.
    - Step 5 ER  : Verify banner 'This is a temporary chat session...' appears.
    - Step 6     : Select model and Code Assistant - Python type in Chat Configuration.
    - Step 7     : Verify empty query behavior — Send button remains disabled.
    - Step 8     : Submit code-generation query; verify response/code is displayed
                   with copy icon and Regenerate Response button.
    - Step 9     : Submit long code-generation query (>3000 words).
    - Step 10    : Verify NO chat history created for the temporary session.
    - Step 11    : Click '+ New Chat'; verify previous temp session not shown.
    - No Edit/Delete chat steps (not applicable to temporary chat).
    """
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]

    # ── Step 3 ───────────────────────────────────────────────────────────────
    async def _step_3_verify_chat_landing_ui() -> None:
        await _verify_chat_ui_details(page)

    # ── Step 6 ───────────────────────────────────────────────────────────────
    async def _step_6_configure_chat() -> None:
        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(
            page, model_name=model_name, chat_type="Code Assistant - Python"
        )
        # Log active values after configuration — DOM snapshot before proceeding
        active_values = await page.evaluate("""() => {
            const selects = document.querySelectorAll('[data-testid="stSelectbox"]');
            const parts = [];
            for (const s of selects) {
                const label = s.querySelector('label');
                const val = s.querySelector('input');
                if (label) parts.push(label.textContent.trim() + ': ' + (val ? val.value : 'n/a'));
            }
            return parts.join(' | ');
        }""")
        import logging
        logging.getLogger(__name__).info(
            f"[TC {tc_name} Step 6] Active config after selection: {active_values}"
        )

    # ── Step 12 ──────────────────────────────────────────────────────────────
    async def _step_12_exit_application() -> None:
        await page.wait_for_timeout(100)

    # ── Test execution ────────────────────────────────────────────────────────
    await _run_step(
        1,
        "Open browser (Chrome/Edge) and navigate to CareSourceGPT URL",
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
        "Verify UI details of Chat landing page — sidebar, New Chat, Chat Configuration, "
        "Saved Prompts, Ready Files selector, warning text, Tips & Tricks, query input, Send button",
        _step_3_verify_chat_landing_ui(),
        tc_name, page,
    )
    await _run_step(
        4,
        "Click '+ New Chat' in the left sidebar to initiate a new chat",
        _click_new_chat_button(page),
        tc_name, page,
    )
    await _run_step(
        5,
        "Select the 'Temporary Chat' checkbox and verify banner message appears: "
        "'This is a temporary chat session and messages won't appear in your chat history. "
        "Turn off Temporary Chat in the sidebar.'",
        _enable_temporary_chat(page),
        tc_name, page,
    )
    await _run_step(
        5,
        "Verify Temporary Chat banner is visible in the right panel",
        _verify_temporary_chat_banner(page),
        tc_name, page,
    )
    await _run_step(
        6,
        f"Go to Chat Configuration, select Model = {model_name} and Chat Type = Code Assistant - Python",
        _step_6_configure_chat(),
        tc_name, page,
    )
    await _run_step(
        7,
        "Verify empty query behavior — leave input empty and attempt to click Send; "
        "Send button must remain disabled and message must not be sent",
        _verify_empty_query_behavior(page),
        tc_name, page,
    )
    await _run_step(
        8,
        "Verify Chat Initialization — enter a code-generation query "
        f"(e.g. '{query}') and click Send; verify response/code is displayed "
        "without latency or errors, with copy icon and Regenerate Response button",
        _verify_temporary_chat_response(page, chat_page, query),
        tc_name, page,
    )
    await _run_step(
        9,
        "Verify long code-generation query (>3000 words) — response/code generated "
        "without latency or errors",
        _verify_long_query_response(chat_page, tc_key=tc_key),
        tc_name, page,
    )
    await _run_step(
        10,
        "Verify Chat history — no chat history must be created for this temporary session",
        _verify_no_chat_history_for_temporary_chat(page),
        tc_name, page,
    )
    await _run_step(
        11,
        "Click '+ New Chat' and verify previous temporary chat session is not shown; "
        "Chat history must have no records for the temporary chat initiated",
        _verify_new_chat_clears_temporary_session(page),
        tc_name, page,
    )
    await _run_step(
        12,
        "Exit the application by closing the browser",
        _step_12_exit_application(),
        tc_name, page,
    )


@pytest.mark.chat
@pytest.mark.regression
@pytest.mark.temporary_chat
@pytest.mark.parametrize("model_name, tc_name, tc_key", _MODEL_VARIANTS)
async def test_temporary_chat_initialization_code_assistant_python(
    docuchat_context,
    model_name: str,
    tc_name: str,
    tc_key: str,
):
    """Validate Temporary Chat Initialization with Code Assistant - Python type across all variants.

    Parametrize IDs: TC053 (5-mini CRT), TC054 (5 CRT), TC055 (4.1 mini CRT).
    To run a single variant: pytest -k TC053
    To run all:             pytest -k temporary_chat
    """
    _td = _get_chat_inputs(tc_key)
    await _run_tc_flow(
        docuchat_context,
        query=_td.query,
        tc_name=tc_name,
        model_name=model_name,
        tc_key=tc_key,
    )


if __name__ == "__main__":
    raise SystemExit(
        pytest.main([
            __file__,
            "--env=qa",
            "--headless=false",
            "-vv",
            "-s",
            "--tb=long",
        ])
    )
