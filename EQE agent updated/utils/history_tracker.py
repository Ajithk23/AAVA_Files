from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


HISTORY_DIR = Path(__file__).resolve().parents[1] / "reports" / "history"
HISTORY_FILE = HISTORY_DIR / "run_history.json"
TC_HISTORY_FILE = HISTORY_DIR / "tc_run_history.json"


def _read_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _read_tc_history() -> List[Dict[str, Any]]:
    if not TC_HISTORY_FILE.exists():
        return []
    try:
        with TC_HISTORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append_run_history(passed: int, failed: int, duration_sec: float) -> Dict[str, Any]:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history = _read_history()
    run_count = len(history) + 1

    entry = {
        "run_count": run_count,
        "passed": passed,
        "failed": failed,
        "duration_sec": round(duration_sec, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    history.append(entry)

    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)

    return entry


def append_tc_run_history(
    run_id: str,
    tc_results: Dict[str, str],
    env: str = "unknown",
    run_timestamp: str = "",
) -> None:
    """Persist per-TC results for every run into tc_run_history.json.

    Each entry represents one TC execution:
    {
        "run_id": "RUN_20260416_125637",
        "run_timestamp": "2026-04-16 12:56:37",
        "env": "QA",
        "tc_number": "001",
        "tc_name": "TC001",
        "status": "PASS"
    }
    tc_results: dict of {tc_number_zfilled: "PASS"|"FAIL"}
    """
    if not tc_results:
        return

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history = _read_tc_history()

    if not run_timestamp:
        run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for tc_num, status in tc_results.items():
        history.append(
            {
                "run_id": run_id,
                "run_timestamp": run_timestamp,
                "env": env.upper(),
                "tc_number": tc_num,
                "tc_name": f"TC{tc_num}",
                "status": status,
            }
        )

    with TC_HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)


def read_run_history() -> List[Dict[str, Any]]:
    return _read_history()


def read_tc_run_history() -> List[Dict[str, Any]]:
    return _read_tc_history()


def get_basic_history_summary() -> Dict[str, Any]:
    history = _read_history()
    if not history:
        return {
            "total_runs": 0,
            "total_passed": 0,
            "total_failed": 0,
            "avg_duration_sec": 0.0,
            "last_run": None,
        }

    total_runs = len(history)
    total_passed = sum(int(item.get("passed", 0)) for item in history)
    total_failed = sum(int(item.get("failed", 0)) for item in history)
    avg_duration = sum(float(item.get("duration_sec", 0.0)) for item in history) / total_runs

    return {
        "total_runs": total_runs,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "avg_duration_sec": round(avg_duration, 2),
        "last_run": history[-1],
    }
