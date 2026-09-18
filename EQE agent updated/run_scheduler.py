from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import schedule
from croniter import croniter
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent


def _run_policy_guard() -> bool:
    policy_command = [sys.executable, "-m", "utils.policy_guard"]
    print("Running policy guard...")
    result = subprocess.run(policy_command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        print("Policy guard failed. Pytest will not run.")
        return False
    return True


def run_pytest(env: str, marker: str | None = None) -> int:
    if not _run_policy_guard():
        return 1
    command = [sys.executable, "-m", "pytest", f"--env={env}"]
    if marker:
        command.extend(["-m", marker])
    command.append("tests")
    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return result.returncode


def run_with_cron(cron_expr: str, env: str, marker: str | None = None) -> None:
    next_run = croniter(cron_expr, datetime.now()).get_next(datetime)
    print(f"Next cron execution at: {next_run}")
    while True:
        now = datetime.now()
        if now >= next_run:
            run_pytest(env, marker)
            next_run = croniter(cron_expr, datetime.now()).get_next(datetime)
            print(f"Next cron execution at: {next_run}")
        time.sleep(30)


def main() -> int:
    parser = argparse.ArgumentParser(description="DocuChat local scheduler")
    parser.add_argument("--env", default="qa", choices=["dev", "qa", "uat"])
    parser.add_argument("--marker", default=None, help="Optional pytest marker expression")
    parser.add_argument("--mode", default="daily", choices=["once", "daily", "cron"])
    parser.add_argument("--time", default="02:00", help="Daily run time HH:MM")
    parser.add_argument("--cron", default="0 2 * * *", help="Cron expression for --mode cron")
    args = parser.parse_args()

    if args.mode == "once":
        return run_pytest(args.env, args.marker)

    if args.mode == "cron":
        run_with_cron(args.cron, args.env, args.marker)
        return 0

    schedule.every().day.at(args.time).do(run_pytest, env=args.env, marker=args.marker)
    print(f"Scheduler started. Daily at {args.time}. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(20)


if __name__ == "__main__":
    raise SystemExit(main())
