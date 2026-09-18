from __future__ import annotations

from typing import Any, Dict, List, Tuple

from locators.chat_locators import CHAT_LOCATORS
from locators.file_handling_locators import FILE_HANDLING_LOCATORS
from locators.prompt_library_locators import PROMPT_LIBRARY_LOCATORS


PRIORITY_ORDER = ["data-testid", "role", "text", "css", "relative", "xpath"]


def _priority_index(strategy: str) -> int:
    try:
        return PRIORITY_ORDER.index(strategy)
    except ValueError:
        return len(PRIORITY_ORDER) + 1


def _audit_single_map(name: str, locator_map: Dict[str, List[Dict[str, str]]]) -> Tuple[List[str], List[str], set[Tuple[str, str]]]:
    errors: List[str] = []
    warnings: List[str] = []
    signatures: set[Tuple[str, str]] = set()

    for key, candidates in locator_map.items():
        seen_local: set[Tuple[str, str]] = set()
        previous_priority = -1

        for candidate in candidates:
            strategy = candidate.get("strategy", "")
            value = candidate.get("value", "")
            signature = (strategy, value)

            if not strategy or not value:
                errors.append(f"{name}.{key} has invalid candidate: {candidate}")
                continue

            if signature in seen_local:
                errors.append(f"Duplicate locator candidate in {name}.{key}: {strategy} => {value}")
            seen_local.add(signature)
            signatures.add(signature)

            current_priority = _priority_index(strategy)
            if current_priority < previous_priority:
                warnings.append(
                    f"Priority order drift in {name}.{key}: '{strategy}' appears after a lower-priority strategy"
                )
            previous_priority = current_priority

    return errors, warnings, signatures


def audit_locator_maps() -> Dict[str, Any]:
    maps = {
        "chat": CHAT_LOCATORS,
        "file_handling": FILE_HANDLING_LOCATORS,
        "prompt_library": PROMPT_LIBRARY_LOCATORS,
    }

    errors: List[str] = []
    warnings: List[str] = []
    global_usage: Dict[Tuple[str, str], List[str]] = {}

    for map_name, locator_map in maps.items():
        map_errors, map_warnings, signatures = _audit_single_map(map_name, locator_map)
        errors.extend(map_errors)
        warnings.extend(map_warnings)
        for signature in signatures:
            global_usage.setdefault(signature, []).append(map_name)

    for (strategy, value), usage in global_usage.items():
        unique_usage = sorted(set(usage))
        if len(unique_usage) > 1:
            warnings.append(
                f"Shared locator candidate across features ({', '.join(unique_usage)}): {strategy} => {value}"
            )

    return {"errors": errors, "warnings": warnings}


def main() -> None:
    result = audit_locator_maps()
    if result["errors"]:
        print("Locator guard: FAILED")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("Locator guard: PASSED")
    if result["warnings"]:
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
