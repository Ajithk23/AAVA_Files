from __future__ import annotations

import json

from utils.history_tracker import HISTORY_FILE, get_basic_history_summary, read_run_history


def main() -> None:
    summary = get_basic_history_summary()

    print("DocuChat Basic History Report")
    print("=" * 30)
    print(f"Total runs      : {summary['total_runs']}")
    print(f"Total passed    : {summary['total_passed']}")
    print(f"Total failed    : {summary['total_failed']}")
    print(f"Avg duration(s) : {summary['avg_duration_sec']}")

    if summary["last_run"]:
        print("\nLast run:")
        print(json.dumps(summary["last_run"], indent=2))
    else:
        print("\nNo run history yet.")

    print(f"\nHistory file: {HISTORY_FILE}")


if __name__ == "__main__":
    main()
