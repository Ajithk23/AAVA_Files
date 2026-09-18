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

from utils.test_data_loader import get_chat_inputs as _get_chat_inputs
from tests.web.regression.chat.test_tc001_tc002_tc003_regression_docuchat_chat_validate_chat_initialization_basic_chat import (
    _run_tc_flow as _run_basic_chat_flow,
)
from tests.web.regression.chat.test_tc004_tc005_tc006_chat_initialization_chat_with_documents import (
    _run_tc_flow as _run_chat_documents_flow,
)

pytestmark = [
    pytest.mark.web_suite,
    pytest.mark.p1,
    pytest.mark.regression,
    pytest.mark.chat,
]

_P1_BASIC_CHAT_VARIANTS = [
    pytest.param("5-mini CRT", "TC001", "tc001", id="TC001"),
    pytest.param("5 CRT", "TC002", "tc002", id="TC002"),
    pytest.param("4.1 mini CRT", "TC003", "tc003", id="TC003"),
]

_P1_CHAT_WITH_DOCUMENTS_VARIANTS = [
    pytest.param(
        "5-mini CRT",
        "TC004",
        "tc004",
        "TC004_Regression_DocuChat_Chat_Validate Chat Initialization with 5-mini CRT model and Chat Type as Chat with Documents",
        id="TC004",
    ),
    pytest.param(
        "5 CRT",
        "TC005",
        "tc005",
        "TC005_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Chat Type as Chat with Documents",
        id="TC005",
    ),
]


@pytest.mark.parametrize("model_name, tc_name, tc_key", _P1_BASIC_CHAT_VARIANTS)
async def test_p1_basic_chat_suite(
    docuchat_context,
    model_name: str,
    tc_name: str,
    tc_key: str,
):
    _td = _get_chat_inputs(tc_key)
    await _run_basic_chat_flow(
        docuchat_context,
        query=_td.query,
        tc_name=tc_name,
        model_name=model_name,
        tc_key=tc_key,
    )


@pytest.mark.parametrize(
    "model_name, tc_name, tc_key, file_prefix",
    _P1_CHAT_WITH_DOCUMENTS_VARIANTS,
)
async def test_p1_chat_with_documents_suite(
    docuchat_context,
    model_name: str,
    tc_name: str,
    tc_key: str,
    file_prefix: str,
):
    _td = _get_chat_inputs(tc_key)
    await _run_chat_documents_flow(
        docuchat_context,
        query=_td.query,
        tc_name=tc_name,
        model_name=model_name,
        tc_key=tc_key,
        file_prefix=file_prefix,
    )


if __name__ == "__main__":
    raise SystemExit(
        pytest.main([
            __file__,
            "--env=qa",
            "--headless=false",
            "-vv",
            "-s",
        ])
    )