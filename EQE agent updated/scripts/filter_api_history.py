from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_HISTORY_FILE = PROJECT_ROOT / "Test_Latest_Run_Details" / "API-INT_Latest_Run" / "api_execution_history.json"


def _parse_user_date(raw_value: str) -> str:
    supported_formats = ("%Y-%m-%d", "%m-%d-%Y")
    for date_format in supported_formats:
        try:
            return datetime.strptime(raw_value, date_format).date().isoformat()
        except ValueError:
            continue
    raise SystemExit(
        f"Invalid date '{raw_value}'. Use YYYY-MM-DD or MM-DD-YYYY."
    )


def _extract_entry_date(entry: dict[str, Any]) -> str:
    timestamp = str(entry.get("timestamp", ""))
    return timestamp[:10]


def _load_history() -> list[dict[str, Any]]:
    if not API_HISTORY_FILE.exists():
        raise SystemExit(f"History file not found: {API_HISTORY_FILE}")

    loaded = json.loads(API_HISTORY_FILE.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise SystemExit("History file format is invalid. Expected a JSON array.")
    return loaded


def _matches(entry: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.status and str(entry.get("result", "")).upper() != args.status.upper():
        return False

    if args.test_case and args.test_case.lower() not in str(entry.get("test_case_name", "")).lower():
        return False

    if args.date and not str(entry.get("timestamp", "")).startswith(args.date):
        return False

    entry_date = _extract_entry_date(entry)
    if args.start_date and entry_date < args.start_date:
        return False

    if args.end_date and entry_date > args.end_date:
        return False

    if args.endpoint:
        requests = entry.get("requests", [])
        if not isinstance(requests, list):
            return False
        endpoint_match = any(
            args.endpoint.lower() in str(request_item.get("url", "")).lower()
            for request_item in requests
            if isinstance(request_item, dict)
        )
        if not endpoint_match:
            return False

    return True


def _print_summary(entries: list[dict[str, Any]]) -> None:
    if not entries:
        print("No matching API history entries found.")
        return

    for index, entry in enumerate(entries, start=1):
        print(f"[{index}] {entry.get('timestamp', '')} | {entry.get('result', '')} | {entry.get('test_case_name', '')}")
        print(f"     Base URL   : {entry.get('base_url', '')}")
        print(f"     Report File: {entry.get('report_file', '')}")
        requests = entry.get("requests", [])
        if requests:
            first_request = requests[0]
            print(f"     Request    : {first_request.get('method', '')} {first_request.get('url', '')}")
            print(f"     Status Code: {first_request.get('status_code', '')}")
        print()


def _print_stats(entries: list[dict[str, Any]]) -> None:
    if not entries:
        print("No matching API history entries found.")
        return

    test_case_counter = Counter(
        str(entry.get("test_case_name", "UNKNOWN_TEST_CASE")) for entry in entries
    )
    passed_count = sum(1 for entry in entries if str(entry.get("result", "")).upper() == "PASSED")
    failed_count = sum(1 for entry in entries if str(entry.get("result", "")).upper() == "FAILED")

    print("API Execution Summary")
    if entries:
        timestamps = [str(entry.get("timestamp", "")) for entry in entries]
        print(f"Date Filter           : {min(timestamps)} -> {max(timestamps)}")
    print(f"Unique Test Cases Run : {len(test_case_counter)}")
    print(f"Passed Executions     : {passed_count}")
    print(f"Failed Executions     : {failed_count}")
    print(f"Total Executions      : {len(entries)}")
    print()
    print("Execution Count By Test Case")
    for test_case_name, count in sorted(test_case_counter.items()):
        print(f"- {test_case_name}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter API execution history by date, status, test case, or endpoint.")
    parser.add_argument("--date", help="Filter by date prefix, e.g. 2026-04-30")
    parser.add_argument("--start-date", help="Filter from this date, e.g. 2026-04-29 or 04-29-2026")
    parser.add_argument("--end-date", help="Filter through this date, e.g. 2026-04-30 or 04-30-2026")
    parser.add_argument("--status", help="Filter by result status, e.g. PASSED or FAILED")
    parser.add_argument("--test-case", help="Filter by test case name substring")
    parser.add_argument("--endpoint", help="Filter by endpoint URL substring")
    parser.add_argument("--latest", action="store_true", help="Show only the latest matching entry")
    parser.add_argument("--stats", action="store_true", help="Show execution summary counts for the filtered entries")
    parser.add_argument("--json", action="store_true", help="Print matching entries as JSON")
    args = parser.parse_args()

    if args.date:
        args.date = _parse_user_date(args.date)
    if args.start_date:
        args.start_date = _parse_user_date(args.start_date)
    if args.end_date:
        args.end_date = _parse_user_date(args.end_date)

    if args.start_date and args.end_date and args.start_date > args.end_date:
        raise SystemExit("start-date cannot be later than end-date.")

    history = _load_history()
    filtered = [entry for entry in history if _matches(entry, args)]
    filtered.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)

    if args.latest and filtered:
        filtered = filtered[:1]

    if args.json:
        print(json.dumps(filtered, indent=2, ensure_ascii=False))
        return

    if args.stats:
        _print_stats(filtered)
        return

    _print_summary(filtered)


if __name__ == "__main__":
    main()