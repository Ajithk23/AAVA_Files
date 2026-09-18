"""TC-422 — Verify bulk delete confirmation modal behavior

Description    : Ensure that when bulk delete is triggered, a confirmation modal appears
                 listing the number of selected threads and requires explicit confirmation.
Pre-condition  : User logged in with delete permissions; multiple chat threads selected.
Feature        : Bulk Delete - Confirmation Modal
Environment    : QA-CRT
qTest ID       : 270026
qTest PID      : TC-422
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

_TC_NAME = "TC-422"
_SELECT_COUNT = 3  # Number of threads to individually select

logger = logging.getLogger(__name__)


# ===========================================================================
# Step helpers
# ===========================================================================


async def _step1_select_multiple_threads(page: Page, settings: dict) -> None:
    """Step 1: Select multiple chat threads using checkboxes in the sidebar.
    Expected: Selected threads are visually marked.
    """
    await page.goto(settings["base_url"])
    await page.wait_for_load_state("domcontentloaded")
    await _open_chat_workspace(page)
    await _wait_for_sidebar_ready(page, timeout_sec=30.0)

    titles_before = await _get_chat_titles(page)
    assert len(titles_before) >= _SELECT_COUNT, (
        f"Need at least {_SELECT_COUNT} threads in sidebar, found {len(titles_before)}"
    )

    await _exit_selection_mode_if_active(page)

    # Enter selection mode
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

    # Select N threads
    await _select_n_threads_in_selection_mode(page, _SELECT_COUNT)
    logger.info("Step 1 - Selected %d chat thread(s)", _SELECT_COUNT)


async def _step2_click_bulk_delete_button(page: Page) -> None:
    """Step 2: Click the 'Bulk Delete' button.
    Expected: A confirmation modal appears.
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
        error_message="Delete button not visible after selecting threads",
    )
    await delete_btn.click()
    await page.wait_for_timeout(1000)

    # Verify confirmation modal appears
    modal_candidates = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
        page.locator("div").filter(has_text=re.compile(r"confirm|are you sure", re.IGNORECASE)).first,
    ]
    modal = await _first_visible_with_wait(
        page,
        modal_candidates,
        timeout_ms=10000,
        error_message="Confirmation modal did not appear after clicking Delete",
    )
    assert modal, "Confirmation modal should be visible"
    logger.info("Step 2 - Confirmation modal appeared after clicking bulk delete")


async def _step3_verify_modal_shows_thread_count(page: Page) -> None:
    """Step 3: Verify the modal lists the exact number of selected threads.
    Expected: Modal message states the number of threads to be deleted.
    """
    modal_locators = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
    ]
    modal = await _first_visible_with_wait(
        page, modal_locators, timeout_ms=5000,
        error_message="Confirmation modal not found for count verification",
    )
    modal_text = await modal.inner_text()
    count_match = re.search(r"(\d+)", modal_text)
    assert count_match, (
        f"Modal should display the number of threads to delete, found text: {modal_text!r}"
    )
    displayed_count = int(count_match.group(1))
    assert displayed_count == _SELECT_COUNT, (
        f"Modal should indicate {_SELECT_COUNT} threads selected, found: {displayed_count}"
    )
    logger.info("Step 3 - Modal correctly shows %d thread(s) to be deleted", displayed_count)


async def _step4_verify_delete_and_cancel_buttons(page: Page) -> None:
    """Step 4: Verify presence of 'Delete' and 'Cancel' buttons in the modal.
    Expected: Both buttons are visible and clickable.
    """
    modal_locators = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
    ]
    modal = await _first_visible_with_wait(
        page, modal_locators, timeout_ms=5000,
        error_message="Modal not found for button verification",
    )

    # Verify Delete button in modal
    delete_btn = modal.locator("button").filter(
        has_text=re.compile(r"delete|confirm|^yes$", re.IGNORECASE)
    ).first
    assert await delete_btn.is_visible(), "Delete/Confirm button should be visible in modal"
    assert not await delete_btn.is_disabled(), "Delete/Confirm button should be enabled"

    # Verify Cancel button in modal
    cancel_btn = modal.locator("button").filter(
        has_text=re.compile(r"cancel|^no$|^close$", re.IGNORECASE)
    ).first
    assert await cancel_btn.is_visible(), "Cancel button should be visible in modal"
    assert not await cancel_btn.is_disabled(), "Cancel button should be enabled"

    logger.info("Step 4 - Both Delete and Cancel buttons are visible and clickable in modal")


async def _step5_click_cancel_and_verify(page: Page) -> None:
    """Step 5: Click 'Cancel' button.
    Expected: Modal closes; no threads are deleted; bulk delete button remains enabled.
    """
    modal_locators = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
    ]
    modal = await _first_visible_with_wait(
        page, modal_locators, timeout_ms=5000,
        error_message="Modal not found for cancel action",
    )

    cancel_btn = modal.locator("button").filter(
        has_text=re.compile(r"cancel|^no$|^close$", re.IGNORECASE)
    ).first
    await cancel_btn.click()

    # Poll until the modal is no longer visible (Streamlit re-render can be slow)
    modal_closed = False
    for _ in range(15):
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

    if not modal_closed:
        pytest.fail("Modal should be closed after clicking Cancel")

    # Verify threads are still present (not deleted)
    titles_after = await _get_chat_titles(page)
    assert len(titles_after) >= _SELECT_COUNT, (
        f"No threads should have been deleted after Cancel; found {len(titles_after)} threads"
    )

    # Verify bulk delete button is still enabled
    delete_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page, delete_candidates, timeout_ms=10000,
            error_message="Delete button should remain enabled after Cancel",
        )
        assert not await delete_btn.is_disabled(), "Delete button should remain enabled after Cancel"
    except AssertionError:
        await _write_locator_diagnostics(page, "tc422_step5_cancel_verify", delete_candidates)
        raise

    logger.info("Step 5 - Modal closed, no threads deleted, Delete button still enabled")


async def _step6_confirm_deletion(page: Page) -> None:
    """Step 6: Repeat steps 1-3; this time click 'Delete' button.
    Expected: Bulk delete request is initiated.
    """
    # Click delete button again to re-open confirmation modal
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
        page, delete_candidates, timeout_ms=15000,
        error_message="Delete button not visible for re-confirmation",
    )
    await delete_btn.click()
    await page.wait_for_timeout(1000)

    # Verify modal re-appeared
    modal_locators = [
        page.locator("[role='dialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator(".modal-content").first,
    ]
    modal = await _first_visible_with_wait(
        page, modal_locators, timeout_ms=10000,
        error_message="Confirmation modal did not re-appear for final deletion",
    )

    # Click the Delete/Confirm button in modal
    confirm_btn = modal.locator("button").filter(
        has_text=re.compile(r"delete|confirm|^yes$", re.IGNORECASE)
    ).first
    assert await confirm_btn.is_visible(), "Confirm/Delete button should be visible in modal"
    await confirm_btn.click()

    # Poll until the modal is no longer visible (Streamlit re-render can be slow)
    modal_still_visible = True
    for _ in range(15):
        await page.wait_for_timeout(500)
        found_visible = False
        for loc in modal_locators:
            try:
                if await loc.is_visible():
                    found_visible = True
                    break
            except Exception:
                pass
        if not found_visible:
            modal_still_visible = False
            break
    assert not modal_still_visible, "Modal should close after confirming deletion"

    logger.info("Step 6 - Bulk delete confirmed; deletion initiated successfully")


# ===========================================================================
# Main test flow
# ===========================================================================


async def _run_tc_flow(docuchat_context: dict) -> None:
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]

    await _run_step(1, "Select multiple chat threads using checkboxes", _step1_select_multiple_threads(page, settings), _TC_NAME, page)
    await _run_step(2, "Click Bulk Delete button \u2014 modal appears", _step2_click_bulk_delete_button(page), _TC_NAME, page)
    await _run_step(3, "Verify modal shows thread count", _step3_verify_modal_shows_thread_count(page), _TC_NAME, page)
    await _run_step(4, "Verify Delete and Cancel buttons in modal", _step4_verify_delete_and_cancel_buttons(page), _TC_NAME, page)
    await _run_step(5, "Click Cancel \u2014 modal closes, no deletion", _step5_click_cancel_and_verify(page), _TC_NAME, page)
    await _run_step(6, "Re-open modal and confirm deletion", _step6_confirm_deletion(page), _TC_NAME, page)


@pytest.mark.chat
@pytest.mark.regression
async def test_verify_bulk_delete_confirmation_modal(docuchat_context):
    """TC-422: Verify bulk delete confirmation modal behavior."""
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
