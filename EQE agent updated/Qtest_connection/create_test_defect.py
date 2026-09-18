"""
create_test_defect.py
─────────────────────────────────────────────────────────────────────────────
Standalone runner: simulates a DocuChat test-case failure and creates a
real Defect in qTest, then prints the direct link.

Usage
─────
    python Qtest_connection/create_test_defect.py
    python Qtest_connection/create_test_defect.py --tc tc002
    python Qtest_connection/create_test_defect.py --tc tc001 --status timedOut

Arguments
─────────
    --tc       Test-case ID to simulate (tc001 / tc002 / tc003 / tc004 / tc005).
               Default: tc001
    --status   Failure status: failed | timedOut. Default: failed
"""

from __future__ import annotations

import argparse
import sys
import urllib3
from pathlib import Path

urllib3.disable_warnings()

# ── make sure the DocuChat root is on sys.path ────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Qtest_connection.Defect import submit_playwright_failure, extract_defect_url

# ── Test-case catalogue (mirrors test_inputs.json) ────────────────────────
TC_CATALOGUE: dict[str, dict] = {
    "tc001": {
        "title": "DocuChat › Chat › TC001 › Validate chat initialization with 5-mini CRT model (Basic Chat)",
        "file":  "tests/web/chat/test_tc001_tc002_regression_docuchat_chat_validate_chat_initialization_with_5crt_model_and_basic_chat_type.py",
        "error": 'AssertionError: Expected response element to be visible after sending query "What is CareSource?" '
                 'with model "5-mini CRT" (Basic Chat). Element .stChatMessage was not found within timeout.',
        "stack": (
            "AssertionError: Expected response element visible\n"
            "  File 'tests/web/chat/test_tc001_tc002_regression…py', line 58, in test_tc001\n"
            "    assert await page.locator('.stChatMessage').is_visible()\n"
            "playwright._impl._api_types.Error: Timeout 15000ms exceeded."
        ),
    },
    "tc002": {
        "title": "DocuChat › Chat › TC002 › Validate chat initialization with 5 CRT model (Basic Chat)",
        "file":  "tests/web/chat/test_tc001_tc002_regression_docuchat_chat_validate_chat_initialization_with_5crt_model_and_basic_chat_type.py",
        "error": 'AssertionError: Chat response not received for model "5 CRT". Response area empty after 15 s.',
        "stack": (
            "AssertionError: Chat response not received\n"
            "  File 'tests/web/chat/test_tc001_tc002…py', line 92, in test_tc002\n"
            "    assert response_text, 'Response area was empty'"
        ),
    },
    "tc003": {
        "title": "DocuChat › Chat › TC003 › Validate chat initialization with 4.1-mini CRT model (Basic Chat)",
        "file":  "tests/web/chat/test_tc003_regression_docuchat_chat_validate_chat_initialization_with_41mini_crt_model_and_basic_chat_type.py",
        "error": 'AssertionError: Model selector did not show "4.1-mini CRT" as selected after click.',
        "stack": (
            "AssertionError: Model not selected\n"
            "  File 'tests/web/chat/test_tc003…py', line 44, in test_tc003\n"
            "    assert selected_model == '4.1 -mini CRT'"
        ),
    },
    "tc004": {
        "title": "DocuChat › Chat › TC004 › Validate chat initialization with 5-mini CRT model (Chat with Documents)",
        "file":  "tests/web/chat/test_tc004_regression_docuchat_chat_validate_chat_initialization_with_5mini_crt_model_and_chat_with_documents.py",
        "error": 'AssertionError: File upload area not visible in "Chat with Documents" mode.',
        "stack": (
            "AssertionError: Upload area not visible\n"
            "  File 'tests/web/chat/test_tc004…py', line 61, in test_tc004\n"
            "    assert await page.locator('[data-testid=\"stFileUploader\"]').is_visible()"
        ),
    },
    "tc005": {
        "title": "DocuChat › Chat › TC005 › Validate chat initialization with 5 CRT model (Chat with Documents)",
        "file":  "tests/web/chat/test_tc005_regression_docuchat_chat_validate_chat_initialization_with_5crt_model_and_chat_with_documents.py",
        "error": 'TimeoutError: Waiting for document summary response timed out after 15 000 ms.',
        "stack": (
            "playwright._impl._api_types.TimeoutError: Timeout 15000ms exceeded\n"
            "  File 'tests/web/chat/test_tc005…py', line 77, in test_tc005\n"
            "    await page.wait_for_selector('.stChatMessage')"
        ),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a DocuChat test failure and create a qTest defect.")
    parser.add_argument("--tc",     default="tc001", choices=list(TC_CATALOGUE), help="Test-case ID (default: tc001)")
    parser.add_argument("--status", default="failed", choices=["failed", "timedOut"], help="Failure type (default: failed)")
    args = parser.parse_args()

    tc = TC_CATALOGUE[args.tc]

    print()
    print("=" * 70)
    print(f"  Simulating FAILED test: {args.tc.upper()}")
    print(f"  Title : {tc['title']}")
    print(f"  Status: {args.status}")
    print("=" * 70)
    print()
    print("  Submitting defect to qTest …")
    print()

    try:
        result = submit_playwright_failure({
            "title":         tc["title"],
            "error_message": tc["error"],
            "file":          tc["file"],
            "browser":       "chromium",
            "status":        args.status,
            "duration_ms":   15000 if args.status == "timedOut" else 4500,
            "retry":         0,
            "stack_trace":   tc["stack"],
        })
    except Exception as exc:
        print(f"  ERROR: Could not create defect in qTest.\n  {exc}", file=sys.stderr)
        sys.exit(1)

    defect_id  = result.get("id",      "?")
    defect_pid = result.get("pid",     "?")
    defect_url = extract_defect_url(result)

    print("  ✅  Defect created successfully!")
    print()
    print(f"  PID        : {defect_pid}")
    print(f"  Defect ID  : {defect_id}")
    print(f"  qTest Link : {defect_url}")
    print(f"  Direct qTest URL : {defect_url}")
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
