"""
utils/qtest_reporter.py
────────────────────────────────────────────────────────────────
Thin integration layer between the DocuChat pytest framework and qTest Manager.

When a test fails, call ``report_test_failure()`` to automatically create
a Defect in qTest with:
  - Test name, error message, and full stack trace
  - Browser, duration, environment info
  - Screenshot as a base64 attachment (when available)

All errors from qTest are caught and logged; this module never raises
an exception that would affect the test outcome.
"""
from __future__ import annotations

import base64
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Resolve path to Qtest_connection/Defect.py ───────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_QTEST_DIR = _PROJECT_ROOT / "Qtest_connection"
if str(_QTEST_DIR) not in sys.path:
    sys.path.insert(0, str(_QTEST_DIR))

try:
    from Defect import (  # type: ignore[import]
        submit_defect,
        build_defect_payload,
        FIELD_MAP,
        QTEST_HOST,
        QTEST_TOKEN,
        QTEST_PROJECT_ID,
        PLAYWRIGHT_FAIL_SEVERITY,
        PLAYWRIGHT_TIMEOUT_SEVERITY,
    )
    _QTEST_AVAILABLE = True
except ImportError as _ie:
    _QTEST_AVAILABLE = False
    logger.warning("qTest integration disabled — could not import Defect.py: %s", _ie)


# ─────────────────────────────────────────────────────────────────────────────

def _encode_screenshot(screenshot_path: str | Path) -> dict[str, str] | None:
    """Return a qTest attachment dict with base64-encoded screenshot content."""
    try:
        path = Path(screenshot_path)
        if not path.exists() or path.stat().st_size == 0:
            return None
        raw = path.read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        return {
            "name": path.name,
            "content_type": "image/png",
            "data": encoded,
        }
    except Exception as exc:
        logger.warning("Could not encode screenshot for qTest attachment: %s", exc)
        return None


def _build_pytest_defect_properties(
    test_nodeid: str,
    error_message: str,
    stack_trace: str = "",
    browser: str = "chromium",
    status: str = "failed",
    duration_ms: float = 0.0,
    environment: str = "unknown",
) -> list[dict[str, Any]]:
    """Build qTest ``properties`` list from pytest failure metadata."""
    from datetime import datetime, timezone

    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    # Derive a human-readable short title from the nodeid
    # e.g. "tests/web/chat/test_tc001_...py::test_tc001_..." → "TC001 – test_tc001_..."
    node_parts = test_nodeid.split("::")
    func_name = node_parts[-1] if len(node_parts) > 1 else test_nodeid
    short_title = func_name.replace("_", " ").strip()

    summary = f"[DocuChat] {short_title}"[:200]  # qTest field length guard

    severity = (
        PLAYWRIGHT_TIMEOUT_SEVERITY if status == "timedOut"
        else PLAYWRIGHT_FAIL_SEVERITY
    )

    description_lines = [
        f"** Automated defect from DocuChat pytest — {ran_at} **",
        "",
        f"Test ID  : {test_nodeid}",
        f"Browser  : {browser.capitalize()}",
        f"Status   : {status}",
        f"Duration : {duration_ms:.0f} ms",
        f"Env      : {environment}",
        "",
        "--- Error ---",
        error_message or "(no error message captured)",
    ]
    if stack_trace:
        description_lines += ["", "--- Stack Trace ---", stack_trace]

    description = "\n".join(description_lines)
    env_label = f"{browser.capitalize()} / {environment}"

    raw: list[tuple[str, int, str]] = [
        ("summary",     FIELD_MAP.get("summary",     0), summary),
        ("description", FIELD_MAP.get("description", 0), description),
        ("severity",    FIELD_MAP.get("severity",    0), severity),
        ("status",      FIELD_MAP.get("status",      0), "New"),
        ("environment", FIELD_MAP.get("environment", 0), env_label),
    ]
    return [
        {"field_id": fid, "field_name": fname, "field_value": fvalue}
        for fname, fid, fvalue in raw
        if fid > 0
    ]


def report_test_failure(
    test_nodeid: str,
    error_message: str,
    stack_trace: str = "",
    browser: str = "chromium",
    status: str = "failed",
    duration_ms: float = 0.0,
    environment: str = "unknown",
    screenshot_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """
    Submit a qTest Defect for a failed pytest test.

    This function is intentionally exception-safe: it catches all errors from
    the qTest API and logs them without re-raising, so it never affects the
    pytest exit code.

    Parameters
    ----------
    test_nodeid      : pytest node id, e.g. "tests/web/chat/test_tc001.py::test_tc001"
    error_message    : Failure reason / assertion message
    stack_trace      : Full traceback string (optional)
    browser          : Browser name (default: "chromium")
    status           : "failed" | "timedOut" | "interrupted"
    duration_ms      : Test duration in milliseconds
    environment      : Environment label from config (e.g. "qa", "uat")
    screenshot_path  : Absolute path to failure screenshot (optional)

    Returns
    -------
    dict | None
        qTest Defect response dict on success, or None if submission failed.
    """
    if not _QTEST_AVAILABLE:
        logger.warning("qTest reporter not available — skipping defect submission for %s", test_nodeid)
        return None

    try:
        properties = _build_pytest_defect_properties(
            test_nodeid=test_nodeid,
            error_message=error_message,
            stack_trace=stack_trace,
            browser=browser,
            status=status,
            duration_ms=duration_ms,
            environment=environment,
        )

        attachments: list[dict[str, str]] | None = None
        if screenshot_path:
            attachment = _encode_screenshot(screenshot_path)
            if attachment:
                attachments = [attachment]

        logger.info(
            "Submitting qTest defect for failed test: %s (browser=%s, duration=%.0fms)",
            test_nodeid,
            browser,
            duration_ms,
        )
        result = submit_defect(properties, attachments)
        logger.info(
            "qTest defect created — ID=%s | PID=%s | URL=%s",
            result.get("id"),
            result.get("pid"),
            result.get("web_url"),
        )
        return result

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to submit qTest defect for %s: %s",
            test_nodeid,
            exc,
        )
        return None
