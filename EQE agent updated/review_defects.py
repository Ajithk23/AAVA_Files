"""
review_defects.py
─────────────────────────────────────────────────────────────────────────────
Interactive tool to review pending test failures and decide whether to log
them as defects in qTest.

Usage
─────
    python review_defects.py

For each pending failure you will be shown:
  - Test name, error message, screenshot path, timestamp
  - A prompt: [A]pprove / [R]eject / [S]kip

  Approve  → defect is submitted to qTest immediately, entry marked 'approved'
  Reject   → entry marked 'rejected' (will not be shown again)
  Skip     → entry stays 'pending' (shown again next time you run this script)

No time limit — take as long as you need.
"""

from __future__ import annotations

import base64
import json
import logging
import sys
from pathlib import Path

# ── Project root on sys.path ──────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_QTEST_DIR = _PROJECT_ROOT / "Qtest_connection"
if str(_QTEST_DIR) not in sys.path:
    sys.path.insert(0, str(_QTEST_DIR))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── qTest import ──────────────────────────────────────────────────────────────
try:
    from Defect import (  # type: ignore[import]
        submit_playwright_failure,
        extract_defect_url,
        QTEST_HOST,
        QTEST_TOKEN,
        QTEST_PROJECT_ID,
    )
    _QTEST_AVAILABLE = True
except ImportError as _ie:
    _QTEST_AVAILABLE = False
    logger.warning("qTest integration unavailable — could not import Defect.py: %s", _ie)

# ── Config ────────────────────────────────────────────────────────────────────
_PENDING_FILE = _PROJECT_ROOT / "reports" / "pending_defects.json"
_DIVIDER = "=" * 72


def _load_pending() -> list[dict]:
    if not _PENDING_FILE.exists():
        return []
    try:
        return json.loads(_PENDING_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Could not read pending_defects.json: %s", exc)
        return []


def _save_pending(entries: list[dict]) -> None:
    _PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PENDING_FILE.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _submit_to_qtest(entry: dict) -> tuple[bool, str]:
    """Submit a pending entry to qTest. Returns (success, message)."""
    if not _QTEST_AVAILABLE:
        return False, "qTest integration not available (Defect.py import failed)"

    try:
        attachments: list[dict] = []
        screenshot_path = entry.get("screenshot_path", "")
        if screenshot_path:
            _sp = Path(screenshot_path)
            if _sp.exists() and _sp.stat().st_size > 0:
                img_b64 = base64.b64encode(_sp.read_bytes()).decode("ascii")
                attachments.append({
                    "name": _sp.name,
                    "content_type": "image/png",
                    "data": img_b64,
                })

        result = submit_playwright_failure(
            {
                "title": entry["test_nodeid"],
                "error_message": entry["error_message"],
                "file": entry.get("test_file", ""),
                "browser": entry.get("browser", "chromium"),
                "status": "failed",
                "duration_ms": entry.get("duration_ms", 0),
                "retry": 0,
                "stack_trace": entry.get("stack_trace", ""),
            },
            host=QTEST_HOST,
            token=QTEST_TOKEN,
            project_id=QTEST_PROJECT_ID,
            attachments=attachments if attachments else None,
        )

        defect_id  = result.get("id", "")
        defect_pid = result.get("pid", "")
        defect_url = extract_defect_url(result)
        msg = f"Defect created → ID: {defect_id} | PID: {defect_pid} | URL: {defect_url}"
        entry["qtest_defect_id"]  = str(defect_id)
        entry["qtest_defect_pid"] = str(defect_pid)
        entry["qtest_defect_url"] = str(defect_url)
        return True, msg

    except Exception as exc:
        return False, f"Submission failed: {exc}"


def _prompt_user(prompt: str) -> str:
    """Read user input with no timeout."""
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        sys.exit(0)


def main() -> None:
    all_entries = _load_pending()
    pending = [e for e in all_entries if e.get("status") == "pending"]

    if not pending:
        print("\nNo pending defects to review.")
        _done = [e for e in all_entries if e["status"] != "pending"]
        if _done:
            approved = sum(1 for e in _done if e["status"] == "approved")
            rejected = sum(1 for e in _done if e["status"] == "rejected")
            print(f"History: {approved} approved, {rejected} rejected.\n")
        return

    print(f"\n{_DIVIDER}")
    print(f"  qTest Defect Review — {len(pending)} pending failure(s)")
    print(_DIVIDER)
    print("  Commands:  [A] Approve & log to qTest   [R] Reject   [S] Skip\n")

    approved_count = 0
    rejected_count = 0

    for idx, entry in enumerate(pending, start=1):
        print(f"\n{'─' * 72}")
        print(f"  [{idx}/{len(pending)}]  {entry['test_nodeid']}")
        print(f"  Saved at   : {entry.get('saved_at', 'unknown')}")
        print(f"  Browser    : {entry.get('browser', 'unknown')}")
        print(f"  Duration   : {entry.get('duration_ms', 0)} ms")
        print(f"  Error      : {entry['error_message'][:300]}")
        ss = entry.get("screenshot_path", "")
        if ss:
            print(f"  Screenshot : {ss}")
        print()

        while True:
            choice = _prompt_user("  Action [A/R/S]: ")
            if choice in ("a", "approve"):
                print("  --> Submitting to qTest...")
                ok, msg = _submit_to_qtest(entry)
                if ok:
                    entry["status"] = "approved"
                    approved_count += 1
                    print(f"  ✓ {msg}")
                    if entry.get("qtest_defect_url"):
                        print(f"  Direct qTest URL: {entry['qtest_defect_url']}")
                else:
                    print(f"  ✗ {msg}")
                    retry = _prompt_user("  Retry? [y/n]: ")
                    if retry in ("y", "yes"):
                        continue
                    # Keep as pending if submission failed and user doesn't retry
                break
            elif choice in ("r", "reject"):
                entry["status"] = "rejected"
                rejected_count += 1
                print("  --> Rejected. Will not appear again.")
                break
            elif choice in ("s", "skip"):
                print("  --> Skipped. Will appear again next time.")
                break
            else:
                print("  Invalid input. Enter A, R, or S.")

        # Save after every decision so progress is not lost
        _save_pending(all_entries)

    print(f"\n{_DIVIDER}")
    print(f"  Review complete — Approved: {approved_count} | Rejected: {rejected_count} | Remaining pending: {sum(1 for e in all_entries if e['status'] == 'pending')}")
    print(f"{_DIVIDER}\n")


if __name__ == "__main__":
    main()
