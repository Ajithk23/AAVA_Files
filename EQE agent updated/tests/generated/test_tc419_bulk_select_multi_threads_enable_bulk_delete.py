"""TC-419 - Bulk select multiple chat threads in sidebar and enable bulk delete action

Description    : Verify that the user can enter selection mode, select multiple chat
                 threads, and the UI marks them as selected and enables the bulk delete button.
Pre-condition  : User is logged in with valid permissions to view chat threads.
                 Chat sidebar contains at least 5 chat threads.
Feature        : Bulk Delete - Multi-select UI
Environment    : QA-CRT
qTest ID       : 270023
qTest PID      : TC-419
User Story     : US #598048
"""
from __future__ import annotations

import logging
import re
import sys
import time
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
    _assert_landing_page_options,
    _click_select_all_and_verify_delete_count,
    _exit_selection_mode_if_active,
    _first_visible_with_wait,
    _get_chat_titles,
    _open_chat_workspace,
    _select_n_threads_in_selection_mode,
    _wait_for_sidebar_ready,
    _write_locator_diagnostics,
)

_TC_NAME = "TC-419"
_SELECT_COUNT = 3  # Number of threads to individually select in Steps 4-6

logger = logging.getLogger(__name__)


# ===========================================================================
# Step helpers
# ===========================================================================


async def _step1_open_app_and_login(page: Page, settings: dict) -> None:
    """Step 1: Open the application and login as a standard user with chat delete permission.
    Expected: User is successfully logged in and navigated to the main chat interface.
    """
    await page.goto(settings["base_url"])
    await page.wait_for_load_state("domcontentloaded")
    current_url = page.url
    assert current_url, "Application URL is empty - page did not load"
    logger.info("Step 1 - Application opened at: %s", current_url)


async def _step2_verify_sidebar_threads(page: Page) -> None:
    """Step 2: Locate the chat sidebar containing chat threads.
    Expected: Sidebar loads and displays a list of chat threads.
    """
    await _wait_for_sidebar_ready(page, timeout_sec=30.0)
    titles = await _get_chat_titles(page)
    assert len(titles) >= 1, (
        f"Sidebar should display chat threads, found {len(titles)}"
    )
    logger.info("Step 2 - Sidebar loaded with %d chat thread(s)", len(titles))


async def _step3_enter_selection_mode(page: Page) -> None:
    """Step 3: Click on the 'Select' or 'Multi-select' mode button in the sidebar UI.
    Expected: Sidebar enters selection mode, checkboxes appear next to each chat thread.
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

    # Verify checkboxes appear (stCheckbox elements in sidebar)
    checkboxes = page.locator(
        "section[data-testid='stSidebar'] [data-testid='stCheckbox']"
    )
    checkbox_count = await checkboxes.count()
    assert checkbox_count >= 1, (
        f"Selection mode should show checkboxes next to threads, found {checkbox_count}"
    )
    logger.info("Step 3 - Selection mode active; %d checkbox(es) visible", checkbox_count)


async def _step4_select_multiple_threads(page: Page) -> None:
    """Step 4: Click the checkboxes next to at least 3 different chat threads.
    Expected: Selected threads are visually highlighted and checkboxes are checked.
    """
    await _select_n_threads_in_selection_mode(page, _SELECT_COUNT)
    logger.info("Step 4 - Selected %d chat thread(s)", _SELECT_COUNT)


async def _step5_verify_delete_button_enabled(page: Page) -> None:
    """Step 5: Observe the bulk action toolbar or button area.
    Expected: A 'Delete Selected' button is enabled and clickable.
    """
    delete_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_candidates,
            timeout_ms=15000,
            error_message="Delete button not visible after selecting threads",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc419_step5_delete_btn", delete_candidates)
        raise

    is_disabled = await delete_btn.is_disabled()
    assert not is_disabled, "Delete button should be enabled when threads are selected"
    logger.info("Step 5 - Delete button is visible and enabled")


async def _step6_verify_selected_count_displayed(page: Page) -> None:
    """Step 6: Verify that the number of selected threads is displayed near the bulk delete button.
    Expected: UI shows text like '3 selected' near the bulk delete button.
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
        error_message="Delete button with count not visible",
    )
    delete_text = (await delete_btn.inner_text()).strip()
    count_match = re.search(r"(\d+)", delete_text)
    assert count_match, (
        f"Delete button should display a numeric count, found: {delete_text!r}"
    )
    displayed_count = int(count_match.group(1))
    assert displayed_count == _SELECT_COUNT, (
        f"Delete button should show count={_SELECT_COUNT}, found: {displayed_count}"
    )
    logger.info("Step 6 - Delete button shows count: %d (expected %d)", displayed_count, _SELECT_COUNT)


async def _step7_select_all_verify_total_count(page: Page) -> None:
    """Step 7: Try to select all threads using a 'Select All' checkbox if available.
    Expected: All threads become selected and bulk delete button updates to reflect total count.
    """
    total_count = await _click_select_all_and_verify_delete_count(page, step_label="Step 7")
    logger.info("Step 7 - 'Select All' clicked; Delete button reflects total count: %d", total_count)


# ===========================================================================
# Main test flow
# ===========================================================================


async def _run_tc_flow(docuchat_context: dict) -> None:
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]

    await _run_step(1, "Open application and login", _step1_open_app_and_login(page, settings), _TC_NAME, page)
    await _run_step(2, "Verify sidebar displays chat threads", _step2_verify_sidebar_threads(page), _TC_NAME, page)
    await _run_step(3, "Enter selection mode", _step3_enter_selection_mode(page), _TC_NAME, page)
    await _run_step(4, "Select multiple threads", _step4_select_multiple_threads(page), _TC_NAME, page)
    await _run_step(5, "Verify Delete button enabled", _step5_verify_delete_button_enabled(page), _TC_NAME, page)
    await _run_step(6, "Verify selected count displayed", _step6_verify_selected_count_displayed(page), _TC_NAME, page)
    await _run_step(7, "Select All and verify total count", _step7_select_all_verify_total_count(page), _TC_NAME, page)


@pytest.mark.chat
@pytest.mark.regression
async def test_bulk_select_multi_threads_enable_bulk_delete(docuchat_context):
    """TC-419: Bulk select multiple chat threads in sidebar and enable bulk delete action."""
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
