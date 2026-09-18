from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set

from utils.locator_guard import audit_locator_maps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = PROJECT_ROOT / "tests"

FILE_PATTERN = re.compile(r"^test_[a-z0-9_]+\.py$")
FUNC_PATTERN = re.compile(r"^def\s+(test_[a-z0-9_]+)\s*\(")
MARKER_PATTERN = re.compile(r"^@pytest\.mark\.([a-zA-Z_][a-zA-Z0-9_]*)")

SUITE_MARKERS = {"smoke", "regression", "sanity"}
FEATURE_MARKERS = {"chat", "file", "prompt"}


class PolicyViolation(Exception):
    pass


def _extract_markers_and_tests(file_path: Path) -> List[dict]:
    lines = file_path.read_text(encoding="utf-8").splitlines()
    items: List[dict] = []
    pending_markers: List[str] = []

    for line in lines:
        stripped = line.strip()

        marker_match = MARKER_PATTERN.match(stripped)
        if marker_match:
            pending_markers.append(marker_match.group(1))
            continue

        func_match = FUNC_PATTERN.match(stripped)
        if func_match:
            items.append({"function": func_match.group(1), "markers": set(pending_markers)})
            pending_markers = []
            continue

        if stripped and not stripped.startswith("#"):
            pending_markers = []

    return items


def _validate_file_and_function_names(file_path: Path) -> List[str]:
    violations: List[str] = []
    if not FILE_PATTERN.match(file_path.name):
        violations.append(f"Invalid test file name: {file_path.as_posix()}")

    for item in _extract_markers_and_tests(file_path):
        function_name = item["function"]
        if not re.match(r"^test_[a-z0-9_]+$", function_name):
            violations.append(f"Invalid test function name: {function_name} in {file_path.as_posix()}")

    return violations


def _validate_markers(file_path: Path) -> List[str]:
    violations: List[str] = []
    tests = _extract_markers_and_tests(file_path)
    normalized_path = file_path.as_posix().lower()

    for test in tests:
        marker_names: Set[str] = set(test["markers"])
        suite_present = marker_names.intersection(SUITE_MARKERS)
        feature_present = marker_names.intersection(FEATURE_MARKERS)
        test_id = f"{file_path.as_posix()}::{test['function']}"

        if "/tests/web/" in normalized_path:
            if len(feature_present) != 1:
                violations.append(f"Web test must have exactly one feature marker (chat/file/prompt): {test_id}")
            if len(suite_present) != 1:
                violations.append(f"Web test must have exactly one suite marker (smoke/regression/sanity): {test_id}")

    return violations


def run_policy_guard() -> None:
    violations: List[str] = []

    if TESTS_ROOT.exists():
        test_files = sorted(TESTS_ROOT.rglob("test_*.py"))
    else:
        test_files = []

    for test_file in test_files:
        violations.extend(_validate_file_and_function_names(test_file))
        violations.extend(_validate_markers(test_file))

    locator_audit = audit_locator_maps()
    violations.extend(locator_audit.get("errors", []))

    warnings = locator_audit.get("warnings", [])
    if warnings:
        print("Policy guard warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if violations:
        details = "\n".join(violations)
        raise PolicyViolation(f"Policy guard failed with violations:\n{details}")


def main() -> None:
    try:
        run_policy_guard()
        print("Policy guard passed.")
    except PolicyViolation as error:
        print(str(error))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
