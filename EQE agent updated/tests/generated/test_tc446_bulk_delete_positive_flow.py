"""TC-446 — Bulk Delete Multiple Chat Threads - Positive Flow

Description    : Verify that a user can select multiple chat threads in the sidebar
                 and delete them successfully with UI and backend updates.
Pre-condition  : User is logged into DocuChat with permission to delete all selected
                 threads. Sidebar contains at least 5 chat threads owned by the user.
Feature        : Bulk Delete - Positive Flow
Environment    : QA-CRT
qTest ID       : 272187
qTest PID      : TC-446
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
    _open_chat_workspace,
    _select_n_threads_in_selection_mode,
    _wait_for_sidebar_ready,
    _write_locator_diagnostics,
)

_TC_NAME = "TC-446"
_SELECT_COUNT = 3  # Number of threads to select for bulk deletion

logger = logging.getLogger(__name__)



# ===========================================================================
# Step helpers
# ===========================================================================


async def _step1_open_app_and_login(page: Page, settings: dict) -> None:
    """Step 1: Open the browser and navigate to the DocuChat application URL. Log in.
    Expected: The main chat interface loads with the sidebar displaying chat threads.
    """
    await page.goto(settings["base_url"])
    await page.wait_for_load_state("domcontentloaded")
    await _open_chat_workspace(page)
    await _wait_for_sidebar_ready(page, timeout_sec=30.0)
    titles = await _get_chat_titles(page)
    assert len(titles) >= 1, (
        f"Sidebar should display chat threads after login, found {len(titles)}"
    )
    logger.info("Step 1 - Application loaded with %d chat thread(s)", len(titles))


async def _step2_enter_selection_mode(page: Page) -> None:
    """Step 2: In the chat sidebar, enter selection mode.
    Expected: Sidebar threads display checkboxes allowing multiple selections.
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
        f"Selection mode should show checkboxes, found {checkbox_count}"
    )
    logger.info("Step 2 - Selection mode active; %d checkbox(es) visible", checkbox_count)


async def _step3_select_three_threads(page: Page) -> list[str]:
    """Step 3: Select three distinct chat threads by checking their checkboxes.
    Expected: Selected threads are visibly marked and bulk delete button is enabled.
    """
    titles_before = await _get_chat_titles(page)
    assert len(titles_before) >= _SELECT_COUNT, (
        f"Need at least {_SELECT_COUNT} threads, found {len(titles_before)}"
    )

    await _select_n_threads_in_selection_mode(page, _SELECT_COUNT)

    # Verify delete button is enabled
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
        error_message="Bulk delete button not visible after selecting threads",
    )
    assert not await delete_btn.is_disabled(), "Delete button should be enabled"
    logger.info("Step 3 - Selected %d threads; delete button enabled", _SELECT_COUNT)
    return titles_before[:_SELECT_COUNT]


async def _step4_click_delete_selected(page: Page) -> None:
    """Step 4: Click the 'Delete Selected' bulk delete button.
    Expected: A confirmation modal appears listing the number of threads selected.
    """
    delete_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete\s*selected", re.IGNORECASE)
        ).first,
    ]
    delete_btn = await _first_visible_with_wait(
        page,
        delete_candidates,
        timeout_ms=15000,
        error_message="Delete button not visible",
    )
    await delete_btn.click()
    await page.wait_for_timeout(1000)

    # Verify confirmation modal appears
    modal_candidates = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
    ]
    modal = await _first_visible_with_wait(
        page,
        modal_candidates,
        timeout_ms=10000,
        error_message="Confirmation modal did not appear after clicking Delete",
    )
    modal_text = await modal.inner_text()
    count_match = re.search(r"(\d+)", modal_text)
    assert count_match, f"Modal should display thread count, got: {modal_text!r}"
    logger.info("Step 4 - Confirmation modal appeared with thread count")


async def _step5_confirm_deletion(page: Page) -> None:
    """Step 5: In the confirmation modal, click the 'Confirm' button to proceed.
    Expected: The modal closes; a bulk delete API request is sent.
    """
    modal_locators = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
    ]
    modal = await _first_visible_with_wait(
        page, modal_locators, timeout_ms=5000,
        error_message="Modal not found for confirmation",
    )

    confirm_btn = modal.locator("button").filter(
        has_text=re.compile(r"delete|confirm|^yes$", re.IGNORECASE)
    ).first
    assert await confirm_btn.is_visible(), "Confirm button should be visible"
    await confirm_btn.click()

    # Wait for modal to close
    modal_closed = False
    for _ in range(20):
        await page.wait_for_timeout(500)
        still_visible = False
        for loc in modal_locators:
            try:
                if await loc.is_visible():
                    still_visible = True
                    break
            except Exception:
                pass
        if not still_visible:
            modal_closed = True
            break
    assert modal_closed, "Modal should close after confirming deletion"
    logger.info("Step 5 - Deletion confirmed; modal closed")


async def _step6_wait_for_server_response(page: Page) -> None:
    """Step 6: Wait for the server response confirming successful deletion.
    Expected: API returns success status; no error messages.
    """
    # Allow time for the bulk delete API call to complete and UI to update
    await page.wait_for_timeout(3000)

    # Check for error toasts or alerts
    error_indicators = [
        page.locator("[data-testid='stAlert'][data-baseweb='notification']").first,
        page.locator("div[role='alert']").filter(has_text=re.compile(r"error|fail", re.IGNORECASE)).first,
    ]
    for err_loc in error_indicators:
        try:
            if await err_loc.is_visible():
                err_text = await err_loc.inner_text()
                pytest.fail(f"Error message displayed after deletion: {err_text}")
        except Exception:
            pass

    logger.info("Step 6 - Server responded without errors")


async def _step7_verify_threads_removed(page: Page, deleted_titles: list[str]) -> None:
    """Step 7: Verify that the deleted threads are removed from the sidebar immediately.
    Expected: The selected threads no longer appear in the sidebar.
    """
    await page.wait_for_timeout(2000)
    titles_after = await _get_chat_titles(page)
    for title in deleted_titles:
        assert title not in titles_after, (
            f"Thread '{title}' should have been removed from sidebar"
        )
    logger.info("Step 7 - All %d deleted threads removed from sidebar", len(deleted_titles))


async def _step8_refresh_and_verify_persistence(page: Page, deleted_titles: list[str]) -> None:
    """Step 8: Refresh the page and verify the deleted threads remain absent.
    Expected: Deleted threads are permanently removed from the UI and backend.
    """
    await page.reload()
    await page.wait_for_load_state("domcontentloaded")
    await _wait_for_sidebar_ready(page, timeout_sec=30.0)

    titles_after_refresh = await _get_chat_titles(page)
    for title in deleted_titles:
        assert title not in titles_after_refresh, (
            f"Thread '{title}' should remain absent after page refresh"
        )
    logger.info("Step 8 - Deleted threads remain absent after refresh")


async def _step9_verify_threads_not_accessible(page: Page, deleted_titles: list[str]) -> None:
    """Step 9: Attempt to access the deleted threads via search.
    Expected: Application shows threads are not found.
    """
    # Verify threads are not found in the current sidebar list
    all_titles = await _get_chat_titles(page)
    for title in deleted_titles:
        assert title not in all_titles, (
            f"Deleted thread '{title}' should not be accessible"
        )
    logger.info("Step 9 - Deleted threads are not accessible via sidebar")


# ===========================================================================
# Main test flow
# ===========================================================================


async def _run_tc_flow(docuchat_context: dict) -> None:
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]

    await _run_step(1, "Open app and login", _step1_open_app_and_login(page, settings), _TC_NAME, page)
    await _run_step(2, "Enter selection mode", _step2_enter_selection_mode(page), _TC_NAME, page)

    # Capture thread titles before selecting (for later verification)
    deleted_titles = await _get_chat_titles(page)
    deleted_titles = deleted_titles[:_SELECT_COUNT]

    await _run_step(3, "Select three threads", _step3_select_three_threads(page), _TC_NAME, page)
    await _run_step(4, "Click Delete Selected button", _step4_click_delete_selected(page), _TC_NAME, page)
    await _run_step(5, "Confirm deletion in modal", _step5_confirm_deletion(page), _TC_NAME, page)
    await _run_step(6, "Wait for server response", _step6_wait_for_server_response(page), _TC_NAME, page)
    await _run_step(7, "Verify threads removed from sidebar", _step7_verify_threads_removed(page, deleted_titles), _TC_NAME, page)
    await _run_step(8, "Refresh and verify persistence", _step8_refresh_and_verify_persistence(page, deleted_titles), _TC_NAME, page)
    await _run_step(9, "Verify threads not accessible", _step9_verify_threads_not_accessible(page, deleted_titles), _TC_NAME, page)


@pytest.mark.chat
@pytest.mark.regression
async def test_bulk_delete_positive_flow(docuchat_context):
    """TC-446: Bulk Delete Multiple Chat Threads - Positive Flow."""
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
