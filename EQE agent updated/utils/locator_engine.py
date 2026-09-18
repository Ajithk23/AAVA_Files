from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError


HEALING_CACHE_PATH = Path(__file__).resolve().parents[1] / "locators" / "self_healing_cache.json"


def _load_healing_cache() -> Dict[str, str]:
    if not HEALING_CACHE_PATH.exists():
        return {}
    try:
        with open(HEALING_CACHE_PATH, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save_healing_cache(cache: Dict[str, str]) -> None:
    HEALING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = HEALING_CACHE_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2)
    temp_path.replace(HEALING_CACHE_PATH)


def _build_locator(page: Page, strategy: str, value: str) -> Locator:
    if strategy == "data-testid":
        return page.get_by_test_id(value)
    if strategy == "role":
        role, name = value.split("|", maxsplit=1)
        return page.get_by_role(role, name=name)
    if strategy == "text":
        return page.get_by_text(value)
    if strategy in {"css", "relative", "xpath"}:
        return page.locator(value)
    raise ValueError(f"Unsupported locator strategy: {strategy}")


async def find_element_with_fallback(
    page: Page,
    locator_key: str,
    candidates: List[Dict[str, str]],
    timeout_ms: int = 15000,
) -> Locator:
    # Per-candidate probe timeout: cap at 4s so wrong selectors fail fast.
    # The caller's overall timeout_ms still governs final wait on the winning candidate.
    probe_timeout_ms = min(4000, timeout_ms)

    cache = _load_healing_cache()
    ordered_candidates = candidates.copy()

    cached_selector = cache.get(locator_key)
    if cached_selector:
        ordered_candidates.insert(0, {"strategy": "css", "value": cached_selector, "source": "self-healed"})

    winning_candidate: Dict[str, str] | None = None
    for candidate in ordered_candidates:
        strategy = candidate["strategy"]
        value = candidate["value"]
        try:
            locator = _build_locator(page, strategy, value)
            await locator.first.wait_for(state="visible", timeout=probe_timeout_ms)
            winning_candidate = candidate
            break
        except (PlaywrightTimeoutError, ValueError):
            continue

    if winning_candidate is None:
        raise AssertionError(f"Unable to resolve locator key '{locator_key}' with fallback strategy")

    strategy = winning_candidate["strategy"]
    value = winning_candidate["value"]
    locator = _build_locator(page, strategy, value)
    if strategy in {"css", "relative", "xpath"}:
        cache[locator_key] = value
        _save_healing_cache(cache)
    return locator.first

