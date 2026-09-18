"""
qtest_integration.py
────────────────────────────────────────────────────────────────
Bridges DocuChat pytest failures → qTest Manager defects.

Called automatically from conftest.py whenever a test fails.
Pulls credentials and field IDs from Qtest_connection/Defect.py.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Resolve Qtest_connection/ so Defect.py can be imported ───────────────────
_QTEST_DIR = Path(__file__).resolve().parents[1] / "Qtest_connection"
if str(_QTEST_DIR) not in sys.path:
    sys.path.insert(0, str(_QTEST_DIR))

try:
    from Defect import FIELD_MAP, submit_defect  # noqa: E402
    _QTEST_AVAILABLE = True
except ImportError as _import_err:
    logger.warning("qTest integration disabled — could not import Defect.py: %s", _import_err)
    _QTEST_AVAILABLE = False


def submit_pytest_failure_defect(
    node_id: str,
    error_message: str,
    stack_trace: str = "",
    screenshot_path: str = "",
    environment: str = "Chrome (Playwright)",
) -> dict[str, Any] | None:
    """
    Submit a defect to qTest Manager for a pytest test failure.

    Parameters
    ----------
    node_id        : pytest node id, e.g. ``tests/web/chat/test_tc001...::test_tc001_...``
    error_message  : short assertion / exception message
    stack_trace    : full traceback string
    screenshot_path: path to failure screenshot (included in description)
    environment    : browser / environment label

    Returns
    -------
    dict  – parsed qTest API response (``id``, ``pid``, ``web_url``, …), or None on any error.
    """
    if not _QTEST_AVAILABLE:
        logger.warning("qTest integration skipped — Defect.py not importable.")
        return None

    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # ── Build summary (≤255 chars, as qTest enforces) ────────────────────────
    test_func_name = node_id.split("::")[-1]
    summary = f"[DocuChat Auto] FAIL: {test_func_name}"[:255]

    # ── Build rich description ────────────────────────────────────────────────
    description_lines = [
        f"** Automated defect raised by DocuChat pytest suite — {ran_at} **",
        "",
        f"Test Node  : {node_id}",
        f"Status     : FAILED",
        f"Environment: {environment}",
        "",
        "--- Error ---",
        error_message[:3000],
    ]
    if stack_trace:
        description_lines += ["", "--- Stack Trace ---", stack_trace[:4000]]
    if screenshot_path:
        description_lines += ["", f"Screenshot : {screenshot_path}"]
    description = "\n".join(description_lines)

    # ── Assemble qTest properties using FIELD_MAP from Defect.py ─────────────
    raw: list[tuple[str, int, str]] = [
        ("summary",     FIELD_MAP.get("summary",     0), summary),
        ("description", FIELD_MAP.get("description", 0), description),
        ("severity",    FIELD_MAP.get("severity",    0), "High"),
        ("status",      FIELD_MAP.get("status",      0), "New"),
        ("environment", FIELD_MAP.get("environment", 0), environment),
    ]
    properties = [
        {"field_id": fid, "field_name": fname, "field_value": fvalue}
        for fname, fid, fvalue in raw
        if fid > 0
    ]

    if not properties:
        logger.error("qTest defect not submitted — FIELD_MAP has no valid field IDs.")
        return None

    # ── POST to qTest API ─────────────────────────────────────────────────────
    try:
        result = submit_defect(properties=properties)
        logger.info(
            "qTest defect created | test=%s | defect_id=%s | pid=%s | url=%s",
            node_id,
            result.get("id"),
            result.get("pid"),
            result.get("web_url", ""),
        )
        return result
    except Exception as exc:
        logger.error("Failed to submit qTest defect for %s: %s", node_id, exc)
        return None
