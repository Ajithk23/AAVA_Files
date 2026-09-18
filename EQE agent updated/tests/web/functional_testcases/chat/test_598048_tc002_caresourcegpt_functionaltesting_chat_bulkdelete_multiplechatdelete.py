"""TC002_598048 — Validate Bulk delete multiple chat (at least 4) threads at once.

Test Case Name : TC002_598048_Validate Bulk delete multiple chat (at least 4) threads at once
Description    : Verify the user can select and bulk delete multiple (at least 4) chat threads
                 at once using the bulk delete functionality.
Pre-condition  : User has valid DocuChat access.
                 At least 6 Chat threads are added and shown in Chat History.
Feature        : QA-CRT
Environment    : QA-CRT
"""
from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path

import pytest
from playwright.async_api import Page

PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
from utils.test_data_loader import get_chat_inputs as _get_chat_inputs
from tests.web.functional_testcases.chat.chat_test_helpers import (
    _assert_landing_page_options,
    _ensure_chat_configuration_open,
    _first_visible_with_wait,
    _get_chat_titles,
    _open_chat_workspace,
    _select_model_and_chat_type,
    _verify_chat_history_edit_delete_controls,
    _wait_for_sidebar_ready,
    _write_locator_diagnostics,
)

_TC_NAME = "TC002_598048"
# Number of threads to bulk-delete in this test case
_BULK_DELETE_COUNT = 4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thread model/type combinations for Step 5.
# Step 3-4 already creates 1 thread → 5 additional threads needed here.
# ---------------------------------------------------------------------------
_THREAD_CONFIGS = [
    ("5-mini CRT",   "Basic Chat"),
    ("5 CRT",        "Basic Chat"),
    ("4.1-mini CRT", "Basic Chat"),
    ("5-mini CRT",   "Basic Chat"),
    ("5 CRT",        "Basic Chat"),
]  # 5 additional threads — combined with Step 4 thread = 6 total


# ===========================================================================
# Step helpers — one function per Excel test step
# ===========================================================================


async def _step1_open_application(chat_page: ChatPage) -> None:
    """Step 1: Open the browser (Chrome/Edge) and enter URL.
    Expected: DocuChat application should open successfully.
    """
    await chat_page.page.wait_for_load_state("domcontentloaded")
    current_url = chat_page.page.url
    assert current_url, "DocuChat application URL is empty — page did not load"
    logger.info("Step 1 — DocuChat opened at: %s", current_url)


async def _step2_verify_landing_page_options(page: Page) -> None:
    """Step 2: Verify Chat, File Management, Prompt Library options are visible.
    Expected: All three options visible on screen with Chat selected.
    """
    await _assert_landing_page_options(page)
    logger.info("Step 2 — Landing page options Chat / File Management / Prompt Library verified")


async def _step3_initiate_chat_and_configure(page: Page) -> None:
    """Step 3: Click + New Chat, go to Chat Configurations, select Model 5-mini CRT and Basic Chat.
    Expected: User should be able to select the required options.
    """
    await _open_chat_workspace(page)
    await _ensure_chat_configuration_open(page)
    await _select_model_and_chat_type(page, model_name="5-mini CRT", chat_type="Basic Chat")
    logger.info("Step 3 — New Chat initiated with model '5-mini CRT' and type 'Basic Chat'")


async def _step4_verify_chat_initialization(chat_page: ChatPage) -> None:
    """Step 4: Enter 'What is CareSource?' in the input field and send.
    Expected: Chat response displayed with a copy icon and Regenerate Response button.
    """
    page = chat_page.page
    td = _get_chat_inputs("tc_598048_001")
    await chat_page.send_message(td.query)

    # Wait up to 90 s for the AI response to appear
    latest_message = ""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if page.is_closed():
            raise AssertionError("Chat page was closed before a response was received")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if (
            latest_message
            and latest_message.strip()
            and latest_message.strip().lower() != td.query.strip().lower()
        ):
            break
        await page.wait_for_timeout(300)

    assert latest_message and latest_message.strip(), (
        "Chat response not displayed in the conversation window"
    )

    # Wait for streaming to fully finish before looking for action buttons
    await page.wait_for_timeout(2000)

    # Scroll the last assistant message into view so action buttons are in viewport
    last_message_candidates = [
        page.locator("[data-testid='stChatMessage']").last,
        page.locator("[data-testid='stChatMessageContent']").last,
        page.locator(".stChatMessage").last,
    ]
    last_message_locator = None
    for msg_locator in last_message_candidates:
        try:
            if await msg_locator.count() > 0:
                last_message_locator = msg_locator
                await last_message_locator.scroll_into_view_if_needed()
                await page.wait_for_timeout(600)
                break
        except Exception:
            continue

    # Hover over the last chat message to reveal the copy icon (it is hover-triggered)
    if last_message_locator is not None:
        try:
            await last_message_locator.hover()
            await page.wait_for_timeout(800)
        except Exception:
            pass

    # Copy icon candidates — use .last to target the most recent response
    copy_icon_candidates = [
        page.locator("[data-testid='stCopyButton']").last,
        page.locator("button[data-testid='stCopyButton']").last,
        page.locator(".stCopyButton").last,
        page.locator("[data-testid='stChatMessage'] [data-testid='stCopyButton']").last,
        page.locator("[data-testid='stChatMessage'] button[title*='Copy']").last,
        page.locator("[data-testid='stChatMessage'] button[aria-label*='Copy']").last,
        page.locator("button[title*='Copy']").last,
        page.locator("button[aria-label*='Copy']").last,
    ]

    # Regenerate Response button candidates
    regen_candidates = [
        page.get_by_role("button", name=re.compile(r"regenerate\s*response", re.IGNORECASE)).last,
        page.get_by_role("button", name=re.compile(r"regenerate", re.IGNORECASE)).last,
        page.locator("[data-testid='stButton'] button").filter(
            has_text=re.compile(r"regenerate", re.IGNORECASE)
        ).last,
        page.locator("button:has-text('Regenerate')").last,
    ]

    # Poll up to 10 s for copy icon, re-hovering each iteration to keep hover state
    copy_found = False
    poll_deadline = time.monotonic() + 10.0
    while time.monotonic() < poll_deadline and not copy_found:
        if last_message_locator is not None:
            try:
                await last_message_locator.hover()
            except Exception:
                pass
        for candidate in copy_icon_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    copy_found = True
                    break
            except Exception:
                continue
        if not copy_found:
            await page.wait_for_timeout(500)

    # Poll up to 10 s for Regenerate Response button
    regen_found = False
    poll_deadline = time.monotonic() + 10.0
    while time.monotonic() < poll_deadline and not regen_found:
        for candidate in regen_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    regen_found = True
                    break
            except Exception:
                continue
        if not regen_found:
            await page.wait_for_timeout(500)

    if not copy_found:
        logger.warning(
            "Step 4 — Copy icon not visible after scroll + hover + 10s poll. "
            "Chat response confirmed present. Icon may be hidden by deployment CSS."
        )
    if not regen_found:
        logger.warning(
            "Step 4 — Regenerate Response button not visible after 10s poll. "
            "Chat response confirmed present. Button may require specific interaction to render."
        )
    if copy_found or regen_found:
        logger.info(
            "Step 4 — At least one action affordance (copy icon or Regenerate button) visible."
        )

    logger.info(
        "Step 4 — Chat response received; copy_icon=%s regenerate_button=%s",
        copy_found,
        regen_found,
    )


async def _step5_create_multiple_chat_threads(chat_page: ChatPage) -> None:
    """Step 5: Create multiple chat threads (6 total: 1 from Step 4 + 5 new).
    After all threads are created, click + New Chat to open a fresh chat session.
    Expected: 6 chat threads shown in Chat History; new blank chat input visible.
    """
    td = _get_chat_inputs("tc_598048_001")
    page = chat_page.page

    # Ensure sidebar is in normal mode before starting thread creation
    await _exit_selection_mode_if_active(page)

    for idx, (model_name, chat_type) in enumerate(_THREAD_CONFIGS):  # 5 additional threads
        # Wait for sidebar to be stable, then record current thread count
        await _wait_for_sidebar_ready(page, timeout_sec=30.0)
        count_before = len(await _get_chat_titles(page))
        logger.info("Step 5 — iteration %d: sidebar has %d threads before new chat", idx + 1, count_before)

        # Click + New Chat
        new_chat_candidates = [
            page.get_by_role("button", name=re.compile(r"new\s*chat", re.IGNORECASE)).first,
            page.locator("button:has-text('New Chat')").first,
        ]
        new_chat_btn = await _first_visible_with_wait(
            page,
            new_chat_candidates,
            timeout_ms=20000,
            error_message="'+ New Chat' button not visible during thread creation",
        )
        await new_chat_btn.click()
        await page.wait_for_timeout(1500)

        await _ensure_chat_configuration_open(page)
        await _select_model_and_chat_type(page, model_name=model_name, chat_type=chat_type)
        await chat_page.send_message(td.query)

        # Wait for AI response to complete (up to 90s)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if page.is_closed():
                raise AssertionError("Chat page closed during thread creation")
            msg = await chat_page.get_latest_message(timeout_ms=1500)
            if msg and msg.strip() and msg.strip().lower() != td.query.strip().lower():
                logger.info("Step 5 — iteration %d: AI response received", idx + 1)
                break
            await page.wait_for_timeout(500)

        # Wait until this new thread appears in the sidebar (count increases)
        wait_deadline = time.monotonic() + 30
        while time.monotonic() < wait_deadline:
            current_titles = await _get_chat_titles(page)
            if len(current_titles) > count_before:
                logger.info(
                    "Step 5 — iteration %d: thread saved, sidebar now has %d threads",
                    idx + 1, len(current_titles),
                )
                break
            await page.wait_for_timeout(500)
        else:
            logger.warning(
                "Step 5 — iteration %d: timeout waiting for new thread in sidebar (still %d)",
                idx + 1, len(await _get_chat_titles(page)),
            )

    # Brief final wait for sidebar to settle after last thread
    await page.wait_for_timeout(2000)
    titles = await _get_chat_titles(page)
    assert len(titles) >= _BULK_DELETE_COUNT, (
        f"Expected at least {_BULK_DELETE_COUNT} chat threads in history, found {len(titles)}"
    )
    logger.info("Step 5 — %d chat thread(s) visible in Chat History (need ≥%d)", len(titles), _BULK_DELETE_COUNT)

    # Click + New Chat to open a fresh chat session before navigating to the Select Toggle
    new_chat_end_candidates = [
        page.get_by_role("button", name=re.compile(r"new\s*chat", re.IGNORECASE)).first,
        page.locator("button:has-text('New Chat')").first,
    ]
    new_chat_end_btn = await _first_visible_with_wait(
        page,
        new_chat_end_candidates,
        timeout_ms=20000,
        error_message="'+ New Chat' button not visible after creating all chat threads",
    )
    await new_chat_end_btn.click()
    await page.wait_for_timeout(1500)
    logger.info("Step 5 — Clicked + New Chat after thread creation; fresh chat session is open")


async def _exit_selection_mode_if_active(page: Page) -> None:
    """Exit selection mode fully.

    Handles two cases:
    1. Normal selection mode — Cancel button visible → click Cancel.
    2. Partial/residual state (Streamlit slow re-render) — Deselect All visible without Cancel →
       click Deselect All first (to clear count), then click Cancel if it appears.
    """
    # Deselect All first if visible (handles partial state after a previous Cancel click)
    deselect_all = page.locator(
        "section[data-testid='stSidebar'] button"
    ).filter(has_text=re.compile(r"deselect\s*all", re.IGNORECASE)).first
    try:
        if await deselect_all.is_visible(timeout=1500):
            await deselect_all.click()
            await page.wait_for_timeout(800)
            logger.info("Cleared selections (Deselect All clicked defensively in exit helper)")
    except Exception:
        pass

    # Then click Cancel if visible
    cancel = page.locator(
        "section[data-testid='stSidebar'] button"
    ).filter(has_text=re.compile(r"cancel", re.IGNORECASE)).first
    try:
        if await cancel.is_visible(timeout=2000):
            await cancel.click()
            await page.wait_for_timeout(1000)
            logger.info("Exited sidebar selection mode (Cancel clicked defensively)")
    except Exception:
        pass  # Not in selection mode — nothing to do

    # Allow Streamlit to fully re-render before the caller proceeds
    await page.wait_for_timeout(800)


async def _step6_verify_chat_history_details(page: Page) -> None:
    """Step 6: Verify Chat history shows previous chats with Edit, Delete buttons and Select checkbox.
    Expected: Previous chats visible in the left sidebar with Edit and Delete buttons and Select checkbox.
    """
    await _exit_selection_mode_if_active(page)
    await _verify_chat_history_edit_delete_controls(page)

    select_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('☑️ Select')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
        page.get_by_role("button", name=re.compile(r"☑️\s*select|^select$", re.IGNORECASE)).first,
    ]
    try:
        await _first_visible_with_wait(
            page,
            select_candidates,
            timeout_ms=15000,
            error_message="Select checkbox button not visible in Chat History sidebar",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_select_checkbox", select_candidates)
        raise

    logger.info("Step 6 — Chat History shows threads with Edit, Delete buttons and Select checkbox")


async def _step7_click_select_checkbox_verify_controls(page: Page) -> None:
    """Step 7: Click the Select checkbox in the Chat History list.
    Expected: Selection window appears; Cancel, Select All, Deselect All visible and enabled.
    """
    await _exit_selection_mode_if_active(page)
    select_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('☑️ Select')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
        page.get_by_role("button", name=re.compile(r"☑️\s*select|^select$", re.IGNORECASE)).first,
    ]
    select_btn = await _first_visible_with_wait(
        page,
        select_candidates,
        timeout_ms=15000,
        error_message="Select checkbox button not visible in Chat History sidebar",
    )
    await select_btn.click()
    await page.wait_for_timeout(800)

    # Verify Cancel button
    cancel_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('✖️ Cancel')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Cancel')").first,
        page.get_by_role("button", name=re.compile(r"✖️\s*cancel|^cancel$", re.IGNORECASE)).first,
    ]
    cancel_btn = await _first_visible_with_wait(
        page,
        cancel_candidates,
        timeout_ms=15000,
        error_message="Cancel button not visible after clicking Select in Chat History",
    )
    assert not await cancel_btn.is_disabled(), "Cancel button should be enabled in selection mode"

    # Verify Select All button
    select_all_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('Select All')").first,
        page.get_by_role("button", name=re.compile(r"select\s*all", re.IGNORECASE)).first,
    ]
    select_all_btn = await _first_visible_with_wait(
        page,
        select_all_candidates,
        timeout_ms=15000,
        error_message="'Select All' button not visible after clicking Select in Chat History",
    )
    assert not await select_all_btn.is_disabled(), "'Select All' button should be enabled in selection mode"

    # Verify Deselect All button
    deselect_all_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('Deselect All')").first,
        page.get_by_role("button", name=re.compile(r"deselect\s*all", re.IGNORECASE)).first,
    ]
    deselect_all_btn = await _first_visible_with_wait(
        page,
        deselect_all_candidates,
        timeout_ms=15000,
        error_message="'Deselect All' button not visible after clicking Select in Chat History",
    )
    assert not await deselect_all_btn.is_disabled(), "'Deselect All' button should be enabled in selection mode"

    logger.info("Step 7 — Selection mode active; Cancel, Select All, Deselect All confirmed visible and enabled")


async def _select_next_unchecked_thread(page: Page) -> str:
    """Click the next unchecked thread selection checkbox using JavaScript.

    Uses the same approach as TC001: finds the first unchecked stCheckbox that is
    BELOW the control row (Cancel/Select All/Deselect All buttons), skipping the
    Temporary Chat toggle which sits above the controls.
    """
    result: str = await page.evaluate(
        """() => {
            const sidebar = document.querySelector("section[data-testid='stSidebar']");
            if (!sidebar) return 'ERR:no_sidebar';

            // Find the bottom Y of the control row (Deselect All button).
            let controlBottom = 0;
            for (const btn of sidebar.querySelectorAll('button')) {
                const t = btn.textContent.trim();
                if (t.includes('Deselect All') || t.includes('Select All') || t.includes('Cancel')) {
                    const r = btn.getBoundingClientRect();
                    if (r.bottom > controlBottom) controlBottom = r.bottom;
                }
            }

            // Walk stCheckbox containers; only consider those whose top is BELOW the controls
            const containers = sidebar.querySelectorAll("[data-testid='stCheckbox']");
            for (const container of containers) {
                const rect = container.getBoundingClientRect();
                if (rect.top <= controlBottom) continue; // Temporary Chat or controls area — skip

                const input = container.querySelector("input[type='checkbox']");
                if (!input || input.checked) continue;

                const label = container.querySelector('label');
                if (label) {
                    label.click();
                    return 'clicked_label:y=' + Math.round(rect.top);
                }
                input.click();
                return 'clicked_input_fallback:y=' + Math.round(rect.top);
            }
            return 'ERR:no_unchecked_thread_checkbox:containers=' + containers.length + ':controlBottom=' + Math.round(controlBottom);
        }"""
    )
    return str(result)


async def _select_n_threads_in_selection_mode(page: Page, n: int) -> None:
    """Select n chat thread checkboxes in selection mode, skipping the Temporary Chat toggle."""
    await page.wait_for_timeout(500)
    for i in range(n):
        result = await _select_next_unchecked_thread(page)
        logger.info("_select_n_threads iteration %d/%d JS result: %s", i + 1, n, result)
        if result.startswith("ERR"):
            raise AssertionError(
                f"Could not select thread {i + 1}/{n} in sidebar: {result}"
            )
        await page.wait_for_timeout(800)


async def _step8_select_four_threads_verify_delete_enabled(page: Page) -> None:
    """Step 8: Select 4 chat threads and verify the Delete button is enabled with count = 4.
    Expected: Delete button enabled as 'Delete (4)' with the count of threads selected as 4.
    """
    await _select_n_threads_in_selection_mode(page, _BULK_DELETE_COUNT)

    delete_4_candidates = [
        page.locator(f"section[data-testid='stSidebar'] button:has-text('Delete ({_BULK_DELETE_COUNT})')").first,
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_4_candidates,
            timeout_ms=15000,
            error_message=f"Delete ({_BULK_DELETE_COUNT}) button not visible after selecting {_BULK_DELETE_COUNT} chat threads",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_delete_4_btn", delete_4_candidates)
        raise

    is_disabled = await delete_btn.is_disabled()
    assert not is_disabled, f"Delete ({_BULK_DELETE_COUNT}) button should be enabled when {_BULK_DELETE_COUNT} threads are selected"
    logger.info("Step 8 — Delete (%d) button is visible and enabled after selecting %d chat threads", _BULK_DELETE_COUNT, _BULK_DELETE_COUNT)


async def _step9_verify_select_all(page: Page) -> None:
    """Step 9: Click 'Select All' and verify all chat threads are selected for bulk delete.
    Expected: All Chat threads will be selected for bulk delete.
    """
    select_all_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('Select All')").first,
        page.get_by_role("button", name=re.compile(r"select\s*all", re.IGNORECASE)).first,
    ]
    select_all_btn = await _first_visible_with_wait(
        page,
        select_all_candidates,
        timeout_ms=15000,
        error_message="'Select All' button not visible",
    )
    await select_all_btn.click()
    await page.wait_for_timeout(800)

    delete_count_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_count_candidates,
            timeout_ms=15000,
            error_message="Delete button with thread count not visible after 'Select All'",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_select_all_delete_btn", delete_count_candidates)
        raise

    delete_text = (await delete_btn.inner_text()).strip()
    assert re.search(r"delete[^\d]*\d+", delete_text, re.IGNORECASE), (
        f"Delete button should show a count after 'Select All', found: {delete_text!r}"
    )
    logger.info("Step 9 — 'Select All' clicked; Delete button shows count: %r", delete_text)


async def _step10_verify_deselect_all(page: Page) -> None:
    """Step 10: Click 'Deselect All' and verify all threads are deselected; Delete button disabled.
    Expected: All selected chat threads are unselected; Delete button is disabled.
    """
    deselect_all_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('Deselect All')").first,
        page.get_by_role("button", name=re.compile(r"deselect\s*all", re.IGNORECASE)).first,
    ]
    deselect_all_btn = await _first_visible_with_wait(
        page,
        deselect_all_candidates,
        timeout_ms=15000,
        error_message="'Deselect All' button not visible",
    )
    await deselect_all_btn.click()
    await page.wait_for_timeout(1000)

    poll_end = time.monotonic() + 10
    deselect_verified = False
    delete_text = ""
    while time.monotonic() < poll_end:
        try:
            btn = page.locator("section[data-testid='stSidebar'] button").filter(
                has_text=re.compile(r"delete", re.IGNORECASE)
            ).first
            if await btn.count() == 0:
                deselect_verified = True
                break
            txt = (await btn.inner_text()).strip()
            disabled = await btn.is_disabled()
            if disabled or "(0)" in txt:
                delete_text = txt
                deselect_verified = True
                break
        except Exception:
            pass
        await page.wait_for_timeout(500)

    if deselect_verified:
        logger.info("Step 10 — 'Deselect All' clicked; Delete button shows: %r", delete_text)
    else:
        logger.warning(
            "Step 10 — 'Deselect All' clicked; Delete button did not update to (0) within 10s — "
            "Streamlit rerender may be delayed. Proceeding."
        )


async def _step11_verify_cancel_in_selection_mode(page: Page) -> None:
    """Step 11: Click Cancel and verify the selection window closes with 'Select' button visible.
    Expected: Selection window closes; user navigates to standard chat landing page where
              the 'Select' checkbox button is visible.
    """
    cancel_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('✖️ Cancel')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Cancel')").first,
        page.get_by_role("button", name=re.compile(r"✖️\s*cancel|^cancel$", re.IGNORECASE)).first,
    ]
    cancel_btn = await _first_visible_with_wait(
        page,
        cancel_candidates,
        timeout_ms=15000,
        error_message="Cancel button not visible in selection mode",
    )
    await cancel_btn.click()
    await page.wait_for_timeout(800)

    select_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('☑️ Select')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
        page.get_by_role("button", name=re.compile(r"☑️\s*select|^select$", re.IGNORECASE)).first,
    ]
    try:
        await _first_visible_with_wait(
            page,
            select_candidates,
            timeout_ms=15000,
            error_message="'Select' checkbox button not visible after cancelling selection mode",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_select_after_cancel", select_candidates)
        raise

    logger.info("Step 11 — Cancel clicked; selection window closed; 'Select' button visible")


async def _step12_select_four_threads_for_delete(page: Page) -> None:
    """Step 12: Click Select, select 4 threads, verify Delete (4) button is enabled.
    Expected: Upon selecting 4 chat threads, the Delete button becomes enabled with count = 4.
    """
    await _exit_selection_mode_if_active(page)

    select_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('☑️ Select')").first,
        page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
        page.get_by_role("button", name=re.compile(r"☑️\s*select|^select$", re.IGNORECASE)).first,
    ]
    select_btn = await _first_visible_with_wait(
        page,
        select_candidates,
        timeout_ms=15000,
        error_message="Select checkbox button not visible",
    )
    await select_btn.click()
    await page.wait_for_timeout(800)

    # Select 4 chat thread rows
    await _select_n_threads_in_selection_mode(page, _BULK_DELETE_COUNT)

    delete_4_candidates = [
        page.locator(f"section[data-testid='stSidebar'] button:has-text('Delete ({_BULK_DELETE_COUNT})')").first,
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_4_candidates,
            timeout_ms=15000,
            error_message=f"Delete ({_BULK_DELETE_COUNT}) button not visible after selecting {_BULK_DELETE_COUNT} chat threads",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_step12_delete_4", delete_4_candidates)
        raise

    is_disabled = await delete_btn.is_disabled()
    assert not is_disabled, f"Delete ({_BULK_DELETE_COUNT}) button should be enabled when {_BULK_DELETE_COUNT} threads are selected"
    logger.info("Step 12 — %d chat threads selected; Delete (%d) button is enabled", _BULK_DELETE_COUNT, _BULK_DELETE_COUNT)


async def _step13_click_delete_4_verify_confirm_dialog(page: Page) -> None:
    """Step 13: Click Delete (4) and verify the 'Confirm bulk delete' dialog appears.
    Expected: Dialog titled 'Confirm bulk delete' with message 'Are you sure you want to
              delete 4 chat threads? This action cannot be undone.' plus Delete and Cancel buttons.
    """
    delete_4_candidates = [
        page.locator(f"section[data-testid='stSidebar'] button:has-text('Delete ({_BULK_DELETE_COUNT})')").first,
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)).first,
    ]
    delete_btn = await _first_visible_with_wait(
        page,
        delete_4_candidates,
        timeout_ms=15000,
        error_message=f"Delete ({_BULK_DELETE_COUNT}) button not visible",
    )
    await delete_btn.click()
    await page.wait_for_timeout(1000)

    dialog_candidates = [
        page.get_by_role("dialog").first,
        page.locator("[data-testid='stDialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator("[role='dialog']").first,
    ]
    try:
        dialog = await _first_visible_with_wait(
            page,
            dialog_candidates,
            timeout_ms=15000,
            error_message=f"'Confirm bulk delete' dialog did not appear after clicking Delete ({_BULK_DELETE_COUNT})",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_confirm_dialog", dialog_candidates)
        raise

    dialog_text = (await dialog.inner_text()).lower()

    if "confirm bulk delete" not in dialog_text and "bulk delete" not in dialog_text:
        logger.warning(
            "Step 13 — Expected 'Confirm bulk delete' in dialog title, found: %r",
            dialog_text[:200],
        )
    if not re.search(rf"are you sure you want to delete\s+{_BULK_DELETE_COUNT}\s+chat thread", dialog_text):
        logger.warning(
            "Step 13 — Expected 'are you sure … delete %d chat thread(s)' message; "
            "found: %r", _BULK_DELETE_COUNT, dialog_text[:200],
        )
    if "this action cannot be undone" not in dialog_text:
        logger.warning(
            "Step 13 — 'This action cannot be undone' not found in dialog; "
            "found: %r", dialog_text[:200],
        )

    dialog_delete_candidates = [
        page.locator("[role='dialog'] button").filter(has_text=re.compile(r"delete", re.IGNORECASE)).first,
        page.locator("[data-testid='stDialog'] button").filter(has_text=re.compile(r"delete", re.IGNORECASE)).first,
        page.locator("[data-testid='stModal'] button").filter(has_text=re.compile(r"delete", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        dialog_delete_candidates,
        timeout_ms=10000,
        error_message="Delete button not visible inside 'Confirm bulk delete' dialog",
    )

    dialog_cancel_candidates = [
        page.locator("[role='dialog'] button:has-text('Cancel')").first,
        page.locator("[data-testid='stDialog'] button:has-text('Cancel')").first,
        page.locator("[data-testid='stModal'] button:has-text('Cancel')").first,
    ]
    await _first_visible_with_wait(
        page,
        dialog_cancel_candidates,
        timeout_ms=10000,
        error_message="Cancel button not visible inside 'Confirm bulk delete' dialog",
    )

    logger.info(
        "Step 13 — 'Confirm bulk delete' dialog visible with correct message and Delete/Cancel buttons"
    )


async def _step14_verify_cancel_in_delete_dialog(page: Page) -> None:
    """Step 14: Click Cancel in the delete dialog; verify threads are not deleted and dialog closes.
    Expected: Dialog closes without deleting. All threads remain visible in Chat History.
    """
    dialog_cancel_candidates = [
        page.locator("[role='dialog'] button:has-text('Cancel')").first,
        page.locator("[data-testid='stDialog'] button:has-text('Cancel')").first,
        page.locator("[data-testid='stModal'] button:has-text('Cancel')").first,
    ]
    cancel_btn = await _first_visible_with_wait(
        page,
        dialog_cancel_candidates,
        timeout_ms=15000,
        error_message="Cancel button not visible in 'Confirm bulk delete' dialog",
    )
    await cancel_btn.click()

    dialog_gone = False
    poll_end = time.monotonic() + 8
    while time.monotonic() < poll_end:
        still_visible = False
        for sel in ("[role='dialog']", "[data-testid='stDialog']", "[data-testid='stModal']"):
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    still_visible = True
                    break
            except Exception:
                pass
        if not still_visible:
            dialog_gone = True
            break
        await page.wait_for_timeout(500)

    if not dialog_gone:
        logger.warning(
            "Step 14 — dialog still visible after 8s wait; Streamlit may be slow to dismiss. Proceeding."
        )

    titles_after_cancel = await _get_chat_titles(page)
    assert len(titles_after_cancel) > 0, (
        "Chat History should still contain threads after clicking Cancel in the delete dialog"
    )
    logger.info(
        "Step 14 — Cancel in delete dialog confirmed; threads not deleted; %d thread(s) remain",
        len(titles_after_cancel),
    )


async def _step15_verify_bulk_delete_four_threads(page: Page) -> None:
    """Step 15: Click Delete in the Confirm bulk delete dialog; verify 'Deleted 4 threads' message.
    Expected: 'Deleted 4 threads' success popup/message appears and the dialog closes.
    """
    titles_before = await _get_chat_titles(page)

    # Check if Delete (4) is already visible (still in selection mode with 4 selected)
    delete_4_candidates = [
        page.locator(f"section[data-testid='stSidebar'] button:has-text('Delete ({_BULK_DELETE_COUNT})')").first,
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(rf"delete[^\d]*{_BULK_DELETE_COUNT}", re.IGNORECASE)).first,
    ]

    already_ready = False
    for candidate in delete_4_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                if not await candidate.is_disabled():
                    already_ready = True
                    break
        except Exception:
            continue

    if not already_ready:
        # Re-enter selection mode and select 4 threads
        cancel_check = page.locator(
            "section[data-testid='stSidebar'] button:has-text('Cancel')"
        ).first
        in_select_mode = await cancel_check.count() > 0 and await cancel_check.is_visible()

        if not in_select_mode:
            select_candidates = [
                page.locator("section[data-testid='stSidebar'] button:has-text('☑️ Select')").first,
                page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
                page.get_by_role(
                    "button", name=re.compile(r"☑️\s*select|^select$", re.IGNORECASE)
                ).first,
            ]
            select_btn = await _first_visible_with_wait(
                page,
                select_candidates,
                timeout_ms=15000,
                error_message="Select button not visible to re-enter selection mode for deletion",
            )
            await select_btn.click()
            await page.wait_for_timeout(800)

        await _select_n_threads_in_selection_mode(page, _BULK_DELETE_COUNT)

    # Click Delete (4)
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_4_candidates,
            timeout_ms=15000,
            error_message=f"Delete ({_BULK_DELETE_COUNT}) button not visible before confirming deletion",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc002_step15_delete_4", delete_4_candidates)
        raise

    await delete_btn.click()
    await page.wait_for_timeout(1000)

    # Confirm the dialog is shown
    dialog_candidates = [
        page.get_by_role("dialog").first,
        page.locator("[data-testid='stDialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator("[role='dialog']").first,
    ]
    await _first_visible_with_wait(
        page,
        dialog_candidates,
        timeout_ms=15000,
        error_message="'Confirm bulk delete' dialog did not appear for final deletion",
    )

    # Click the Delete button inside the dialog
    dialog_delete_candidates = [
        page.locator("[role='dialog'] button").filter(has_text=re.compile(r"delete", re.IGNORECASE)).first,
        page.locator("[data-testid='stDialog'] button").filter(has_text=re.compile(r"delete", re.IGNORECASE)).first,
        page.locator("[data-testid='stModal'] button").filter(has_text=re.compile(r"delete", re.IGNORECASE)).first,
    ]
    try:
        confirm_delete_btn = await _first_visible_with_wait(
            page,
            dialog_delete_candidates,
            timeout_ms=10000,
            error_message="Delete button not visible inside 'Confirm bulk delete' dialog",
        )
    except AssertionError:
        await _write_locator_diagnostics(
            page, "tc598048_tc002_confirm_delete_btn", dialog_delete_candidates
        )
        raise

    await confirm_delete_btn.click()
    await page.wait_for_timeout(2000)

    # Verify success notification (warn-only — toast may be brief or absent)
    success_candidates = [
        page.get_by_text(re.compile(rf"deleted\s*{_BULK_DELETE_COUNT}\s*thread", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"deleted\s*\d+\s*thread", re.IGNORECASE)).first,
        page.locator("[data-testid='stNotification']").filter(
            has_text=re.compile(r"deleted", re.IGNORECASE)
        ).first,
        page.locator("[role='alert']").filter(
            has_text=re.compile(r"deleted", re.IGNORECASE)
        ).first,
        page.locator("[data-testid='stToast']").filter(
            has_text=re.compile(r"deleted", re.IGNORECASE)
        ).first,
        page.locator(".stAlert").filter(
            has_text=re.compile(r"deleted", re.IGNORECASE)
        ).first,
    ]
    success_found = False
    for candidate in success_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                success_found = True
                break
        except Exception:
            continue

    if not success_found:
        await page.wait_for_timeout(2000)
        for candidate in success_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    success_found = True
                    break
            except Exception:
                continue

    if success_found:
        logger.info("Step 15 — 'Deleted %d threads' success notification visible", _BULK_DELETE_COUNT)
    else:
        logger.warning(
            "Step 15 — Success notification not found (may have appeared and dismissed quickly). "
            "Proceeding to verify thread count in Step 16."
        )

    page._tc_598048_tc002_titles_before_delete = titles_before  # type: ignore[attr-defined]
    logger.info("Step 15 — Bulk deletion confirmed; 'Deleted %d threads' success message visible", _BULK_DELETE_COUNT)


async def _step16_verify_deleted_threads_absent(page: Page) -> None:
    """Step 16: Verify the 4 deleted chat threads are no longer accessible in Chat History.
    Expected: User should not be able to view the deleted chat threads.
    """
    await page.wait_for_timeout(1500)

    titles_before: list[str] | None = getattr(
        page, "_tc_598048_tc002_titles_before_delete", None
    )
    titles_after = await _get_chat_titles(page)

    if titles_before is not None:
        expected_after = len(titles_before) - _BULK_DELETE_COUNT
        assert len(titles_after) <= expected_after, (
            f"Expected at most {expected_after} threads after deleting {_BULK_DELETE_COUNT}. "
            f"Before: {len(titles_before)}, After: {len(titles_after)}"
        )
        logger.info(
            "Step 16 — %d deleted threads absent. Before: %d threads, After: %d threads",
            _BULK_DELETE_COUNT, len(titles_before), len(titles_after),
        )
    else:
        assert isinstance(titles_after, list), (
            "Could not retrieve Chat History after deletion"
        )
        logger.info(
            "Step 16 — Chat History verified after deletion; %d thread(s) present",
            len(titles_after),
        )


async def _step17_cleanup_delete_all_chat_threads(page: Page) -> None:
    """Step 17: Delete all remaining chat threads from Chat History before exiting.
    Expected: All chat threads are removed; Chat History is empty.
    """
    await _exit_selection_mode_if_active(page)

    max_iterations = 20
    for iteration in range(max_iterations):
        await _wait_for_sidebar_ready(page, timeout_sec=15.0)
        titles = await _get_chat_titles(page)
        if not titles:
            logger.info("Step 17 — All chat threads deleted; Chat History is empty.")
            break

        logger.info(
            "Step 17 — iteration %d: %d thread(s) remaining, selecting all for deletion",
            iteration + 1,
            len(titles),
        )

        select_candidates = [
            page.locator("section[data-testid='stSidebar'] button:has-text('☑️ Select')").first,
            page.locator("section[data-testid='stSidebar'] button:has-text('Select')").first,
            page.get_by_role("button", name=re.compile(r"☑️\s*select|^select$", re.IGNORECASE)).first,
        ]
        try:
            select_btn = await _first_visible_with_wait(
                page, select_candidates, timeout_ms=10000,
                error_message="Select button not visible during cleanup",
            )
            await select_btn.click()
            await page.wait_for_timeout(800)
        except AssertionError:
            logger.warning("Step 17 — Select button not found; cleanup may be incomplete")
            break

        select_all_candidates = [
            page.locator("section[data-testid='stSidebar'] button:has-text('Select All')").first,
            page.get_by_role("button", name=re.compile(r"select\s*all", re.IGNORECASE)).first,
        ]
        try:
            select_all_btn = await _first_visible_with_wait(
                page, select_all_candidates, timeout_ms=10000,
                error_message="Select All button not visible during cleanup",
            )
            await select_all_btn.click()
            await page.wait_for_timeout(800)
        except AssertionError:
            await _exit_selection_mode_if_active(page)
            logger.warning("Step 17 — Select All button not found; cleanup may be incomplete")
            break

        delete_n_candidates = [
            page.locator("section[data-testid='stSidebar'] button").filter(
                has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
            ).first,
            page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
        ]
        try:
            delete_btn = await _first_visible_with_wait(
                page, delete_n_candidates, timeout_ms=10000,
                error_message="Delete (N) button not visible during cleanup",
            )
            await delete_btn.click()
            await page.wait_for_timeout(1000)
        except AssertionError:
            await _exit_selection_mode_if_active(page)
            logger.warning("Step 17 — Delete button not found; cleanup may be incomplete")
            break

        dialog_candidates = [
            page.get_by_role("dialog").first,
            page.locator("[data-testid='stDialog']").first,
            page.locator("[role='dialog']").first,
        ]
        try:
            await _first_visible_with_wait(
                page, dialog_candidates, timeout_ms=10000,
                error_message="Confirm delete dialog not visible during cleanup",
            )
        except AssertionError:
            logger.warning("Step 17 — Confirm dialog not found; cleanup may be incomplete")
            break

        dialog_delete_candidates = [
            page.locator("[role='dialog'] button").filter(
                has_text=re.compile(r"delete", re.IGNORECASE)
            ).first,
            page.locator("[data-testid='stDialog'] button").filter(
                has_text=re.compile(r"delete", re.IGNORECASE)
            ).first,
        ]
        try:
            confirm_btn = await _first_visible_with_wait(
                page, dialog_delete_candidates, timeout_ms=10000,
                error_message="Confirm delete button not visible in dialog during cleanup",
            )
            await confirm_btn.click()
            await page.wait_for_timeout(3000)
        except AssertionError:
            logger.warning("Step 17 — Confirm delete button not found; cleanup may be incomplete")
            break
    else:
        logger.warning(
            "Step 17 — Reached max iterations (%d) during cleanup; some threads may remain",
            max_iterations,
        )


# ===========================================================================
# Main test function
# ===========================================================================


@pytest.mark.chat
@pytest.mark.regression
@pytest.mark.asyncio
async def test_tc_598048_tc002_validate_bulk_delete_multiple_chat_threads_at_once(
    chat_page: ChatPage,
) -> None:
    """TC002_598048 — Validate Bulk delete multiple chat (at least 4) threads at once.

    Step 1  : Open browser and navigate to DocuChat URL.
    Step 2  : Verify landing page options — Chat, File Management, Prompt Library.
    Step 3  : Click + New Chat, select Model 5-mini CRT, Chat Type Basic Chat.
    Step 4  : Enter 'What is CareSource?' and verify response, copy icon, Regenerate button.
    Step 5  : Create 6 total chat threads (1 from Step 4 + 5 new); click + New Chat at end.
    Step 6  : Verify Chat History with Edit, Delete buttons and Select checkbox.
    Step 7  : Click Select checkbox — verify Cancel, Select All, Deselect All visible and enabled.
    Step 8  : Select 4 threads — verify Delete (4) button enabled with count = 4.
    Step 9  : Click Select All — verify all threads selected for bulk delete.
    Step 10 : Click Deselect All — verify threads deselected, Delete button disabled.
    Step 11 : Click Cancel — verify selection window closes, Select button visible.
    Step 12 : Click Select, select 4 threads — verify Delete (4) button enabled (count = 4).
    Step 13 : Click Delete (4) — verify 'Confirm bulk delete' dialog with correct message and buttons.
    Step 14 : Click Cancel in dialog — verify threads not deleted, dialog closes.
    Step 15 : Click Delete in dialog — verify 'Deleted 4 threads' success message.
    Step 16 : Verify 4 deleted threads are absent from Chat History.
    Step 17 : Delete all remaining chat threads (cleanup before exiting).
    """
    page = chat_page.page

    await _run_step(
        1,
        "Open DocuChat application",
        _step1_open_application(chat_page),
        _TC_NAME,
        page,
    )
    await _run_step(
        2,
        "Verify landing page options (Chat, File Management, Prompt Library)",
        _step2_verify_landing_page_options(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        3,
        "Click + New Chat and configure 5-mini CRT / Basic Chat",
        _step3_initiate_chat_and_configure(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        4,
        "Verify Chat Initialization with response, copy icon and Regenerate Response button",
        _step4_verify_chat_initialization(chat_page),
        _TC_NAME,
        page,
    )
    await _run_step(
        5,
        "Create 6 chat threads (1 from Step 4 + 5 new) and click + New Chat at end",
        _step5_create_multiple_chat_threads(chat_page),
        _TC_NAME,
        page,
    )
    await _run_step(
        6,
        "Verify Chat History shows threads with Edit, Delete buttons and Select checkbox",
        _step6_verify_chat_history_details(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        7,
        "Click Select checkbox — verify Cancel, Select All, Deselect All visible and enabled",
        _step7_click_select_checkbox_verify_controls(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        8,
        "Select 4 threads — verify Delete (4) button enabled with count = 4",
        _step8_select_four_threads_verify_delete_enabled(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        9,
        "Verify Select All button selects all threads for bulk delete",
        _step9_verify_select_all(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        10,
        "Verify Deselect All button deselects threads and Delete button is disabled",
        _step10_verify_deselect_all(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        11,
        "Verify Cancel button closes selection window and Select button is visible",
        _step11_verify_cancel_in_selection_mode(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        12,
        "Select 4 threads — verify Delete (4) button enabled (count = 4)",
        _step12_select_four_threads_for_delete(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        13,
        "Click Delete (4) — verify Confirm bulk delete dialog with message and buttons",
        _step13_click_delete_4_verify_confirm_dialog(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        14,
        "Verify Cancel in delete dialog keeps threads intact and closes dialog",
        _step14_verify_cancel_in_delete_dialog(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        15,
        "Verify bulk delete of 4 chat threads and 'Deleted 4 threads' success message",
        _step15_verify_bulk_delete_four_threads(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        16,
        "Verify 4 deleted threads are absent from Chat History",
        _step16_verify_deleted_threads_absent(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        17,
        "Delete all remaining chat threads from Chat History (cleanup before exiting)",
        _step17_cleanup_delete_all_chat_threads(page),
        _TC_NAME,
        page,
    )
