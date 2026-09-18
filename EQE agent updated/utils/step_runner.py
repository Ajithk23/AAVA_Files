"""Shared step execution utilities for all web UI test files.

Usage in any test file::

    from utils.step_runner import collect_step_failure_evidence, run_step

``run_step`` wraps each test step coroutine in a try/except, logs rich
diagnostic evidence on failure, and re-raises as ``AssertionError`` with a
consistent message format.

``collect_step_failure_evidence`` can also be called directly from within a
step function whenever extra diagnostics are needed mid-step.
"""

from __future__ import annotations

import logging
import time
from typing import Awaitable

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def collect_step_failure_evidence(
    page: Page,
    step_number: int,
    step_name: str,
    tc_name: str,
) -> None:
    """Collect and log diagnostic evidence whenever a test step fails.

    Evidence collected (each item is individually guarded — one failure never
    blocks the remaining items):

    1. Sidebar button texts — exact chat-history row titles visible in DOM
    2. Modal status — whether a dialog is open and its inner text
    3. Sidebar inner HTML snippet — raw DOM for deeper inspection
    4. Page URL + title — confirms correct page context
    5. Browser console messages — collected by the ``conftest.py`` page fixture
       via ``page._diag_console_messages``
    """
    tag = f"[DIAG {tc_name} Step {step_number} '{step_name}']"
    try:
        # 1. Sidebar button texts — most valuable for chat-history failures
        try:
            sidebar_btns = await page.locator(
                "section[data-testid='stSidebar'] [data-testid='stButton'] button"
            ).all_inner_texts()
            logger.warning("%s sidebar_buttons (%d): %r", tag, len(sidebar_btns), sidebar_btns)
        except Exception as _e:
            logger.warning("%s could not read sidebar buttons: %s", tag, _e)

        # 2. Modal status
        try:
            modal_info = await page.evaluate(
                """() => {
                    const dlg = document.querySelector('[role="dialog"]');
                    if (!dlg) return null;
                    const rect = dlg.getBoundingClientRect();
                    return {
                        visible: rect.width > 0 && rect.height > 0,
                        text: dlg.innerText.slice(0, 500)
                    };
                }"""
            )
            logger.warning(
                "%s modal_status: %s", tag, modal_info if modal_info else "NO MODAL"
            )
        except Exception as _e:
            logger.warning("%s could not read modal: %s", tag, _e)

        # 3. Sidebar inner HTML snippet (first 1500 chars)
        try:
            sidebar_html = await page.locator(
                "section[data-testid='stSidebar']"
            ).inner_html()
            logger.warning("%s sidebar_html (first 1500): %s", tag, sidebar_html[:1500])
        except Exception as _e:
            logger.warning("%s could not read sidebar HTML: %s", tag, _e)

        # 4. Page URL + title
        try:
            logger.warning(
                "%s page_url=%s | page_title=%s", tag, page.url, await page.title()
            )
        except Exception as _e:
            logger.warning("%s could not read page URL/title: %s", tag, _e)

        # 5. Browser console messages stored by conftest page fixture
        console_msgs: list[str] = getattr(page, "_diag_console_messages", [])
        if console_msgs:
            logger.warning(
                "%s browser_console (%d msgs, last 30):\n%s",
                tag,
                len(console_msgs),
                "\n".join(console_msgs[-30:]),
            )
        else:
            logger.warning("%s browser_console: (no messages captured)", tag)

    except Exception as _outer:
        logger.warning("%s evidence collection itself failed: %s", tag, _outer)


async def run_step(
    step_number: int,
    step_name: str,
    step_coroutine: Awaitable[None],
    tc_name: str,
    page: Page | None = None,
) -> None:
    """Execute a test step coroutine with uniform error handling.

    On any exception:
    * Calls ``collect_step_failure_evidence`` (if ``page`` is provided) to emit
      detailed diagnostic logs before re-raising.
    * Re-raises as ``AssertionError`` with a consistent
      ``"<tc_name> | Step <N> failed (<step_name>): <cause>"`` message so all
      failures are uniformly searchable in reports.

    Args:
        step_number:    Numeric step index (1-based) for log tagging.
        step_name:      Human-readable step description for log tagging.
        step_coroutine: The awaitable produced by the step function call.
        tc_name:        Test case identifier, e.g. ``"TC001"``.
        page:           Playwright ``Page`` instance.  When supplied, diagnostic
                        evidence is collected on failure.  Pass ``None`` to skip
                        diagnostics (e.g. non-browser steps).
    """
    try:
        _start = time.perf_counter()
        await step_coroutine
        _elapsed_ms = round((time.perf_counter() - _start) * 1000, 2)
        logger.info(
            "[STEP_TIMING] %s | Step %d | %s | latency_ms=%.2f",
            tc_name, step_number, step_name, _elapsed_ms,
        )
    except Exception as exc:
        _elapsed_ms = round((time.perf_counter() - _start) * 1000, 2)
        logger.info(
            "[STEP_TIMING] %s | Step %d | %s | latency_ms=%.2f | status=FAILED",
            tc_name, step_number, step_name, _elapsed_ms,
        )
        if page is not None:
            await collect_step_failure_evidence(page, step_number, step_name, tc_name)
        raise AssertionError(
            f"{tc_name} | Step {step_number} failed ({step_name}): {exc}"
        ) from exc
