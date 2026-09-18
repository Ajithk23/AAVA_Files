from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="DocuChat test execution helper")
    parser.add_argument("--env", default="qa", choices=["dev", "qa", "uat", "int"], help="Target environment")
    parser.add_argument("--tag", default=None, help="Run marker/tag expression, e.g. smoke and chat")
    parser.add_argument("--feature", default=None, choices=["chat", "file_handling", "file_management", "prompt_library"], help="Run web feature folder")
    parser.add_argument("--test", default=None, help="Run a single test path")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    args = parser.parse_args()

    policy_command = [sys.executable, "-m", "utils.policy_guard"]
    print("Executing:", " ".join(policy_command))
    policy_result = subprocess.run(policy_command, cwd=PROJECT_ROOT, check=False)
    if policy_result.returncode != 0:
        return policy_result.returncode

    command = [sys.executable, "-m", "pytest", f"--env={args.env}"]

    if args.headed:
        command.append("--headless=false")

    if args.tag:
        command.extend(["-m", args.tag])

    if args.test:
        command.append(args.test)
    elif args.feature:
        command.append(str(PROJECT_ROOT / "tests" / "web" / args.feature))
    else:
        command.append(str(PROJECT_ROOT / "tests"))

    print("Executing:", " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
