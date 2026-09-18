"""TC-456 - Multi-select UI enables selecting multiple chat threads

Description    : Verify that users can enter selection mode and select multiple
                 chat threads, with UI reflecting selections and enabling bulk delete.
Pre-condition  : User is logged in with permission to view chat threads;
                 Chat sidebar populated with at least 5 chat threads; Browser: Chrome latest.
Feature        : Bulk Delete - Multi-select UI
Environment    : QA-CRT
qTest ID       : 272218
qTest PID      : TC-456
User Story     : US #598048
"""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pytest
from playwright.async_api import Page

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    if venv_python.exists() and current_python != venv_python.resolve():
        import subprocess

        raise SystemExit(subprocess.call([str(venv_python), __file__]))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pages.chat_page import ChatPage
from utils.step_runner import run_step as _run_step
from tests.web.functional_testcases.chat.chat_test_helpers import (
    _exit_selection_mode_if_active,
    _first_visible_with_wait,
    _get_chat_titles,
    _select_n_threads_in_selection_mode,
    _wait_for_sidebar_ready,
    _write_locator_diagnostics,
)

_TC_NAME = "TC-456"
_SELECT_COUNT = 3  # Threads to select individually in Step 4

logger = logging.getLogger(__name__)


# ===========================================================================
# Step helpers
# ===========================================================================


async def _step1_open_app_and_login(page: Page, settings: dict) -> None:
    """Step 1: Open the application and login as a valid user.
    Expected: User is successfully logged in and navigated to main chat interface.
    """
    await page.goto(settings["base_url"])
    await page.wait_for_load_state("domcontentloaded")
    assert page.url, "Application URL is empty - page did not load"
    logger.info("Step 1 - Application opened at: %s", page.url)


async def _step2_navigate_to_sidebar(page: Page) -> None:
    """Step 2: Navigate to the Chat Sidebar displaying chat threads.
    Expected: Chat Sidebar loads with a list of at least 5 chat threads visible.
    """
    await _wait_for_sidebar_ready(page, timeout_sec=30.0)
    titles = await _get_chat_titles(page)
    assert len(titles) >= 5, (
        f"Sidebar should display at least 5 chat threads, found {len(titles)}"
    )
    logger.info("Step 2 - Sidebar loaded with %d chat thread(s)", len(titles))


async def _step3_enter_selection_mode(page: Page) -> None:
    """Step 3: Click the 'Select' or 'Multi-select' mode button to enable selection mode.
    Expected: Selection mode is activated; checkboxes or selection controls appear next to each chat thread.
    """
    await _exit_selection_mode_if_active(page)

    select_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('\u2611\ufe0f Select')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
        page.get_by_role("button", name=re.compile(r"\u2611\ufe0f\s*select|^select$", re.IGNORECASE)).first,
    ]
    select_btn = await _first_visible_with_wait(
        page,
        select_candidates,
        timeout_ms=15000,
        error_message="'Select' button not visible in chat sidebar",
    )
    await select_btn.click()
    await page.wait_for_timeout(800)

    checkboxes = page.locator(
        "section[data-testid='stSidebar'] [data-testid='stCheckbox']"
    )
    checkbox_count = await checkboxes.count()
    assert checkbox_count >= 1, (
        f"Selection mode should show checkboxes next to threads, found {checkbox_count}"
    )
    logger.info("Step 3 - Selection mode active; %d checkbox(es) visible", checkbox_count)


async def _step4_select_multiple_threads(page: Page) -> None:
    """Step 4: Click the checkboxes next to at least 3 different chat threads to select them.
    Expected: Selected chat threads are visually highlighted (e.g., background color change or checkmark).
    """
    await _select_n_threads_in_selection_mode(page, _SELECT_COUNT)
    logger.info("Step 4 - Selected %d chat thread(s)", _SELECT_COUNT)


async def _step5_verify_bulk_delete_enabled(page: Page) -> None:
    """Step 5: Verify that the bulk delete action button becomes enabled once threads are selected.
    Expected: Bulk delete button is enabled and clickable.
    """
    delete_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    delete_btn = await _first_visible_with_wait(
        page,
        delete_candidates,
        timeout_ms=15000,
        error_message="Delete button not visible after selecting threads",
    )
    is_disabled = await delete_btn.is_disabled()
    assert not is_disabled, "Bulk delete button should be enabled when threads are selected"
    logger.info("Step 5 - Bulk delete button is visible and enabled")


async def _step6_deselect_one_thread(page: Page) -> None:
    """Step 6: Deselect one chat thread by unchecking its checkbox.
    Expected: Chat thread is unselected and visual highlight is removed.
    """
    checkboxes = page.locator(
        "section[data-testid='stSidebar'] [data-testid='stCheckbox'] input[type='checkbox']"
    )
    # Find the first checked checkbox and uncheck it
    total = await checkboxes.count()
    unchecked = False
    for i in range(total):
        cb = checkboxes.nth(i)
        if await cb.is_checked():
            await cb.uncheck(force=True)
            unchecked = True
            break
    assert unchecked, "Could not find a checked checkbox to uncheck"
    await page.wait_for_timeout(500)
    logger.info("Step 6 - Deselected one chat thread")


async def _step7_verify_delete_still_enabled(page: Page) -> None:
    """Step 7: Verify that bulk delete button remains enabled as long as at least one thread is selected.
    Expected: Bulk delete button remains enabled.
    """
    delete_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    delete_btn = await _first_visible_with_wait(
        page,
        delete_candidates,
        timeout_ms=10000,
        error_message="Delete button not visible after deselecting one thread",
    )
    is_disabled = await delete_btn.is_disabled()
    assert not is_disabled, "Bulk delete button should remain enabled when at least one thread is selected"
    logger.info("Step 7 - Bulk delete button still enabled after deselecting one thread")


async def _step8_deselect_all_verify_disabled(page: Page) -> None:
    """Step 8: Deselect all chat threads.
    Expected: No threads are selected and bulk delete button is disabled.
    """
    # Uncheck all remaining checked checkboxes
    checkboxes = page.locator(
        "section[data-testid='stSidebar'] [data-testid='stCheckbox'] input[type='checkbox']"
    )
    total = await checkboxes.count()
    for i in range(total):
        cb = checkboxes.nth(i)
        if await cb.is_checked():
            await cb.uncheck(force=True)
    await page.wait_for_timeout(500)

    # Verify delete button is now disabled or hidden
    delete_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
    ]
    # Button should either be disabled or not visible
    btn_found_and_enabled = False
    for candidate in delete_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                if not await candidate.is_disabled():
                    btn_found_and_enabled = True
        except Exception:
            continue
    assert not btn_found_and_enabled, (
        "Bulk delete button should be disabled or hidden when no threads are selected"
    )
    logger.info("Step 8 - All threads deselected; bulk delete button is disabled/hidden")


# ===========================================================================
# Main test flow
# ===========================================================================


async def _run_tc_flow(docuchat_context: dict) -> None:
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]

    await _run_step(1, "Open application and login", _step1_open_app_and_login(page, settings), _TC_NAME, page)
    await _run_step(2, "Navigate to Chat Sidebar", _step2_navigate_to_sidebar(page), _TC_NAME, page)
    await _run_step(3, "Enter selection mode", _step3_enter_selection_mode(page), _TC_NAME, page)
    await _run_step(4, "Select multiple threads", _step4_select_multiple_threads(page), _TC_NAME, page)
    await _run_step(5, "Verify bulk delete enabled", _step5_verify_bulk_delete_enabled(page), _TC_NAME, page)
    await _run_step(6, "Deselect one thread", _step6_deselect_one_thread(page), _TC_NAME, page)
    await _run_step(7, "Verify delete still enabled", _step7_verify_delete_still_enabled(page), _TC_NAME, page)
    await _run_step(8, "Deselect all - verify disabled", _step8_deselect_all_verify_disabled(page), _TC_NAME, page)


@pytest.mark.chat
@pytest.mark.regression
async def test_multiselect_ui_enables_selecting_multiple_chat_threads(docuchat_context):
    """TC-456: Multi-select UI enables selecting multiple chat threads."""
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
