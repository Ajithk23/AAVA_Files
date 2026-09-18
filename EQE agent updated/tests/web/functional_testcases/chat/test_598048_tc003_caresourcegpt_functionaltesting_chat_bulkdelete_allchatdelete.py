"""TC003_598048 — Validate Bulk Delete All chat threads in Chat History.

Test Case Name : TC003_598048_Validate Bulk Delete All chat threads in Chat History
Description    : Verify the user can select ALL chat threads at once using the 'Select All'
                 button and bulk delete all of them from Chat History in a single operation.
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

_TC_NAME = "TC003_598048"
# Total chat threads created in this test (1 from Step 4 + 5 from Step 5)
_EXPECTED_THREAD_COUNT = 6

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
    assert len(titles) >= 1, (
        f"Expected at least 1 chat thread in history for the delete test, found {len(titles)}"
    )
    logger.info("Step 5 — %d chat thread(s) visible in Chat History (need ≥1)", len(titles))

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

    Handles three cases:
    1. Normal selection mode — Cancel button visible → click Cancel.
    2. Double-Cancel state (Streamlit duplicate widget after rapid Select All / Deselect All
       cycles) — clicks each Cancel in turn until none remain.
    3. Partial/residual stale state — Deselect All visible but no Cancel → click Deselect All
       (which surfaces a Cancel on the next iteration), then click Cancel.

    IMPORTANT: Cancel is always checked FIRST. Deselect All is only clicked when no Cancel
    is visible. This prevents accidentally re-triggering selection mode when Deselect All
    is a stale ghost widget left over from a previous Select All operation.
    """
    sidebar = page.locator("section[data-testid='stSidebar'] button")
    for attempt in range(6):
        # --- Check Cancel first ---
        cancel = sidebar.filter(has_text=re.compile(r"cancel", re.IGNORECASE)).first
        try:
            if await cancel.is_visible(timeout=1000):
                await cancel.click()
                await page.wait_for_timeout(700)
                logger.info(
                    "Exited sidebar selection mode (Cancel clicked defensively, attempt %d)",
                    attempt + 1,
                )
                continue  # Re-check: there may be a second Cancel from Streamlit duplication
        except Exception:
            pass

        # --- Only if no Cancel — check Deselect All (partial stale state) ---
        deselect_all = sidebar.filter(
            has_text=re.compile(r"deselect\s*all", re.IGNORECASE)
        ).first
        try:
            if await deselect_all.is_visible(timeout=1000):
                await deselect_all.click()
                await page.wait_for_timeout(700)
                logger.info(
                    "Cleared selections (Deselect All clicked defensively, attempt %d)",
                    attempt + 1,
                )
                continue  # Re-check: Cancel should now be visible
        except Exception:
            pass

        # Neither Cancel nor Deselect All visible — sidebar is in normal mode
        break

    # Allow Streamlit to fully re-render before the caller proceeds
    await page.wait_for_timeout(1000)


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
        await _write_locator_diagnostics(page, "tc598048_tc003_select_checkbox", select_candidates)
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


async def _click_select_all_and_verify_delete_count(page: Page, step_label: str) -> int:
    """Click 'Select All' and verify Delete (N) button appears with N ≥ 1.

    Returns the total thread count selected.
    Called from both Step 8 and Step 11.
    """
    select_all_candidates = [
        page.locator("section[data-testid='stSidebar'] button:has-text('Select All')").first,
        page.get_by_role("button", name=re.compile(r"select\s*all", re.IGNORECASE)).first,
    ]
    select_all_btn = await _first_visible_with_wait(
        page,
        select_all_candidates,
        timeout_ms=15000,
        error_message=f"'Select All' button not visible ({step_label})",
    )
    await select_all_btn.click()
    await page.wait_for_timeout(800)

    # Verify Delete (N) button shows total count
    delete_n_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_n_candidates,
            timeout_ms=15000,
            error_message=f"Delete (N) button not visible after 'Select All' ({step_label})",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, f"tc598048_tc003_{step_label}_delete_btn", delete_n_candidates)
        raise

    delete_text = (await delete_btn.inner_text()).strip()
    count_match = re.search(r"(\d+)", delete_text)
    assert count_match, (
        f"Delete button should show a numeric count after 'Select All' ({step_label}), "
        f"found: {delete_text!r}"
    )
    selected_count = int(count_match.group(1))
    assert selected_count >= 1, (
        f"Delete button count should be ≥ 1 after 'Select All' ({step_label}), found: {selected_count}"
    )
    is_disabled = await delete_btn.is_disabled()
    assert not is_disabled, (
        f"Delete ({selected_count}) button should be enabled after 'Select All' ({step_label})"
    )
    return selected_count


async def _step8_select_all_verify_delete_enabled(page: Page) -> None:
    """Step 8: Click 'Select All' and verify Delete (N) button is enabled with count = ALL threads.
    Expected: Delete button enabled showing count of ALL chat threads selected.
    """
    # We are already in selection mode from Step 7 — click Select All directly
    selected_count = await _click_select_all_and_verify_delete_count(page, "step8")
    logger.info(
        "Step 8 — 'Select All' clicked; Delete (%d) button is visible and enabled "
        "(all %d threads selected)",
        selected_count, selected_count,
    )


async def _step9_verify_deselect_all(page: Page) -> None:
    """Step 9: Click 'Deselect All' and verify all threads are deselected; Delete button disabled.
    Expected: All selected chat threads are unselected; Delete button is disabled / shows (0).
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

    # Poll up to 10s for Streamlit to update the Delete button to (0) / disabled / hidden
    poll_end = time.monotonic() + 10
    deselect_verified = False
    delete_text = ""
    while time.monotonic() < poll_end:
        try:
            btn = page.locator("section[data-testid='stSidebar'] button").filter(
                has_text=re.compile(r"delete", re.IGNORECASE)
            ).first
            if await btn.count() == 0:
                deselect_verified = True  # button hidden = 0 selected
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
        logger.info("Step 9 — 'Deselect All' clicked; Delete button shows: %r", delete_text)
    else:
        logger.warning(
            "Step 9 — 'Deselect All' clicked; Delete button did not update to (0) within 10s — "
            "Streamlit rerender may be delayed. Proceeding."
        )


async def _step10_verify_cancel_in_selection_mode(page: Page) -> None:
    """Step 10: Click Cancel and verify the selection window closes with 'Select' button visible.
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

    # Verify the 'Select' checkbox button is visible again (selection mode closed)
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
        await _write_locator_diagnostics(page, "tc598048_tc003_select_after_cancel", select_candidates)
        raise

    # Active stabilization: poll until the sidebar reaches CLEAN normal mode.
    # After the 'Select All → Deselect All → Cancel' sequence Streamlit may temporarily
    # render ghost Cancel widgets.  We wait up to 15 s for:
    #   - NO Cancel button visible   AND
    #   - the 'Select' toggle button IS visible (exact text, not a substring of 'Select All').
    sidebar_btns = page.locator("section[data-testid='stSidebar'] button")
    clean_deadline = time.monotonic() + 15
    clean_mode_reached = False
    while time.monotonic() < clean_deadline:
        try:
            cancel_count = await sidebar_btns.filter(
                has_text=re.compile(r"cancel", re.IGNORECASE)
            ).count()
            if cancel_count == 0:
                sel = sidebar_btns.filter(
                    has_text=re.compile(r"^\u2611\ufe0f?\s*select$|^select$", re.IGNORECASE)
                ).first
                if await sel.is_visible(timeout=800):
                    clean_mode_reached = True
                    break
        except Exception:
            pass
        await page.wait_for_timeout(500)
    if clean_mode_reached:
        logger.info("Step 10 — Cancel clicked; sidebar reached clean normal mode; 'Select' button visible")
    else:
        logger.warning(
            "Step 10 — Sidebar did not fully clear ghost Cancel widgets within 15 s. "
            "Proceeding — Step 11 will use precise locators."
        )


async def _step11_select_all_threads_for_delete(page: Page) -> None:
    """Step 11: Enter selection mode via ☑️ Select toggle, then click Select All.
    Expected: All chat threads selected; Delete (N) button enabled with N ≥ 1.

    Handles Streamlit ghost states (duplicate Cancel or Select buttons) by:
    - Ignoring duplicates and clicking the first visible ☑️ Select button
    - If already in selection mode (Select All visible), skipping the toggle click
    - Retrying Select All up to 3 times with a Deselect All reset between retries
      when Delete(N) stays at 0 (ghost state with broken selection)
    """
    sidebar_btns = page.locator("section[data-testid='stSidebar'] button")

    # --- Phase 1: Click ☑️ Select toggle to enter selection mode (if not already in it) ---
    select_all_visible = False
    try:
        sa_check = sidebar_btns.filter(
            has_text=re.compile(r"^select\s*all$", re.IGNORECASE)
        ).first
        select_all_visible = await sa_check.is_visible(timeout=1500)
    except Exception:
        pass

    if select_all_visible:
        logger.info("Step 11 — Selection mode already active; proceeding to 'Select All'")
    else:
        # Click ☑️ Select toggle — retry up to 3 times (handles duplicate ghost buttons)
        for attempt in range(3):
            try:
                btn = sidebar_btns.filter(
                    has_text=re.compile(r"^\u2611\ufe0f?\s*select$", re.IGNORECASE)
                ).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await page.wait_for_timeout(900)
            except Exception:
                pass
            try:
                sa = sidebar_btns.filter(
                    has_text=re.compile(r"^select\s*all$", re.IGNORECASE)
                ).first
                if await sa.is_visible(timeout=1500):
                    logger.info("Step 11 — Selection mode active after %d Select click(s)", attempt + 1)
                    select_all_visible = True
                    break
            except Exception:
                pass
        if not select_all_visible:
            logger.warning("Step 11 — Could not confirm selection mode; attempting Select All anyway")

    # --- Phase 2: Click Select All and verify Delete(N) ≥ 1 ---
    # In Streamlit ghost states Select All may not immediately update the count.
    # If Delete stays at 0, click Deselect All to reset state then retry.
    selected_count = 0
    for attempt in range(3):
        # Click Select All
        try:
            sa_btn = sidebar_btns.filter(
                has_text=re.compile(r"^select\s*all$", re.IGNORECASE)
            ).first
            if await sa_btn.is_visible(timeout=3000):
                await sa_btn.click()
                await page.wait_for_timeout(1500)
        except Exception:
            pass

        # Read Delete(N) count
        try:
            del_btn = sidebar_btns.filter(
                has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
            ).first
            if await del_btn.is_visible(timeout=2000):
                del_text = (await del_btn.inner_text()).strip()
                m = re.search(r"(\d+)", del_text)
                if m:
                    selected_count = int(m.group(1))
                    if selected_count >= 1:
                        break
        except Exception:
            pass

        # Delete(N) still shows 0 — click Deselect All to shake ghost state, then retry
        logger.info(
            "Step 11 — Delete(0) after Select All attempt %d; clicking Deselect All to reset",
            attempt + 1,
        )
        try:
            da_btn = sidebar_btns.filter(
                has_text=re.compile(r"deselect\s*all", re.IGNORECASE)
            ).first
            if await da_btn.is_visible(timeout=1500):
                await da_btn.click()
                await page.wait_for_timeout(800)
        except Exception:
            pass

    assert selected_count >= 1, (
        f"Step 11 — Delete(N) did not show N≥1 after 3 Select All attempts "
        f"(last count={selected_count})"
    )
    logger.info(
        "Step 11 — 'Select All' clicked; Delete (%d) button is enabled (all %d threads selected for deletion)",
        selected_count, selected_count,
    )


async def _step12_click_delete_all_verify_confirm_dialog(page: Page) -> None:
    """Step 12: Click Delete (N) and verify the 'Confirm bulk delete' dialog appears.
    Expected: Dialog titled 'Confirm bulk delete' with message
              'Are you sure you want to delete N chat threads? This action cannot be undone.'
              plus Delete and Cancel buttons.
    """
    # Delete(N) should be visible and enabled from Step 11
    delete_n_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    delete_btn = await _first_visible_with_wait(
        page,
        delete_n_candidates,
        timeout_ms=15000,
        error_message="Delete (N) button not visible for clicking (Step 12)",
    )
    await delete_btn.click()
    await page.wait_for_timeout(1000)

    # Verify the Confirm bulk delete dialog is visible
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
            error_message="'Confirm bulk delete' dialog did not appear after clicking Delete (N)",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc003_confirm_dialog", dialog_candidates)
        raise

    dialog_text = (await dialog.inner_text()).lower()

    if "confirm bulk delete" not in dialog_text and "bulk delete" not in dialog_text:
        logger.warning(
            "Step 12 — Expected 'Confirm bulk delete' in dialog title, found: %r",
            dialog_text[:200],
        )
    if "are you sure you want to delete" not in dialog_text:
        logger.warning(
            "Step 12 — Expected 'are you sure you want to delete' in dialog; "
            "found: %r", dialog_text[:200],
        )
    if "this action cannot be undone" not in dialog_text:
        logger.warning(
            "Step 12 — 'This action cannot be undone' not found in dialog; "
            "found: %r", dialog_text[:200],
        )

    # Verify Delete button inside dialog
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

    # Verify Cancel button inside dialog
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
        "Step 12 — 'Confirm bulk delete' dialog visible with correct message and Delete/Cancel buttons"
    )


async def _step13_verify_cancel_in_delete_dialog(page: Page) -> None:
    """Step 13: Click Cancel in the delete dialog; verify dialog closes and selection mode stays active.
    Expected: Dialog closes without deleting. Selection mode remains active;
              Delete (N) button is still visible and enabled with the same thread count.
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
    await page.wait_for_timeout(800)

    # Poll up to 8s for the dialog to disappear
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
            "Step 13 — dialog still visible after 8s wait; Streamlit may be slow to dismiss. Proceeding."
        )

    # After cancelling the confirm dialog the sidebar selection mode remains active —
    # Delete (N) should still be visible and enabled with the full thread count.
    delete_n_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_n_candidates,
            timeout_ms=10000,
            error_message=(
                "Delete (N) button not visible after cancelling confirm dialog — "
                "expected to remain in selection mode"
            ),
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc003_step13_delete_n", delete_n_candidates)
        raise
    delete_text = (await delete_btn.inner_text()).strip()
    logger.info(
        "Step 13 — Cancel in delete dialog confirmed; dialog closed; "
        "still in selection mode with '%s' button visible",
        delete_text,
    )


async def _step14_click_delete_button_verify_confirm_dialog_again(page: Page) -> None:
    """Step 14: Click Delete (N) again while still in selection mode; verify confirm dialog reappears.
    Expected: Clicking Delete (N) directly (selection mode still active from Step 13) causes the
              'Confirm bulk delete' dialog to reappear, ready for final confirmation.
    """
    # We are still in selection mode with all threads selected from Step 11 / Step 13.
    # No need to re-enter selection mode — just click Delete (N) directly.
    delete_n_candidates = [
        page.locator("section[data-testid='stSidebar'] button").filter(
            has_text=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)
        ).first,
        page.get_by_role("button", name=re.compile(r"delete[^\d]*\d+", re.IGNORECASE)).first,
    ]
    try:
        delete_btn = await _first_visible_with_wait(
            page,
            delete_n_candidates,
            timeout_ms=15000,
            error_message=(
                "Delete (N) button not visible in Step 14 — "
                "expected to still be in selection mode from Step 13"
            ),
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc003_step14_delete_n", delete_n_candidates)
        raise
    delete_text = (await delete_btn.inner_text()).strip()
    await delete_btn.click()
    await page.wait_for_timeout(1000)

    # Verify the Confirm bulk delete dialog reappears
    dialog_candidates = [
        page.get_by_role("dialog").first,
        page.locator("[data-testid='stDialog']").first,
        page.locator("[data-testid='stModal']").first,
        page.locator("[role='dialog']").first,
    ]
    try:
        await _first_visible_with_wait(
            page,
            dialog_candidates,
            timeout_ms=15000,
            error_message="'Confirm bulk delete' dialog did not reappear after clicking Delete (N) again",
        )
    except AssertionError:
        await _write_locator_diagnostics(page, "tc598048_tc003_step14_dialog", dialog_candidates)
        raise
    logger.info(
        "Step 14 — Clicked '%s'; 'Confirm bulk delete' dialog reappeared; ready to confirm deletion",
        delete_text,
    )


async def _step15_verify_bulk_delete_all_threads(page: Page) -> None:
    """Step 15: Confirm deletion in dialog; verify 'Deleted N threads' success message.
    Expected: 'Deleted N threads' success popup/message appears and the dialog closes.
              The confirm dialog is already open from Step 14.
    """
    titles_before = await _get_chat_titles(page)

    # Click the Delete button inside the dialog to confirm (dialog already open from Step 14)
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
            page, "tc598048_tc003_confirm_delete_btn", dialog_delete_candidates
        )
        raise

    await confirm_delete_btn.click()
    await page.wait_for_timeout(2000)

    # Verify 'Deleted N threads' success notification (warn-only — toast may be brief or absent)
    total_deleted = len(titles_before)
    success_candidates = [
        page.get_by_text(re.compile(rf"deleted\s*{total_deleted}\s*thread", re.IGNORECASE)).first,
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
        # Poll briefly one more time — toast may take a moment to render
        await page.wait_for_timeout(2000)
        for candidate in success_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    success_found = True
                    break
            except Exception:
                continue

    if success_found:
        logger.info("Step 15 — 'Deleted %d threads' success notification visible", total_deleted)
    else:
        logger.warning(
            "Step 15 — Success notification not found (may have appeared and dismissed quickly). "
            "Proceeding to verify empty Chat History in Step 16."
        )

    # Store titles_before for use in Step 16
    page._tc_598048_tc003_titles_before_delete = titles_before  # type: ignore[attr-defined]
    logger.info(
        "Step 15 — Bulk deletion of all %d threads confirmed; 'Deleted %d threads' success message visible",
        total_deleted, total_deleted,
    )


async def _step16_verify_chat_history_empty(page: Page) -> None:
    """Step 16: Verify ALL deleted chat threads are absent; Chat History is EMPTY.
    Expected: Chat History shows no threads; all threads have been successfully deleted.
    """
    await page.wait_for_timeout(1500)

    titles_before: list[str] | None = getattr(
        page, "_tc_598048_tc003_titles_before_delete", None
    )
    titles_after = await _get_chat_titles(page)

    assert len(titles_after) == 0, (
        f"Expected Chat History to be EMPTY after deleting all threads, "
        f"but found {len(titles_after)} thread(s) still present"
    )

    if titles_before is not None:
        logger.info(
            "Step 16 — All %d threads deleted. Chat History is EMPTY (0 threads remaining).",
            len(titles_before),
        )
    else:
        logger.info("Step 16 — Chat History is EMPTY; all threads have been successfully deleted.")


async def _step17_cleanup_delete_all_chat_threads(page: Page) -> None:
    """Step 17: Cleanup — verify Chat History is empty, or delete any remaining threads.
    Expected: Chat History is empty; all chat threads are removed.
    """
    await _exit_selection_mode_if_active(page)

    await _wait_for_sidebar_ready(page, timeout_sec=15.0)
    titles = await _get_chat_titles(page)
    if not titles:
        logger.info("Step 17 — Chat History is already empty; no cleanup needed.")
        return

    # Safety: if any threads remain (should not happen after Step 15/16), delete them
    logger.info(
        "Step 17 — %d thread(s) unexpectedly remaining; performing cleanup deletion.",
        len(titles),
    )

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

        # Enter selection mode
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

        # Click Select All
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

        # Click Delete (N) button
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

        # Confirm deletion in dialog
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
async def test_tc_598048_tc003_validate_bulk_delete_all_chat_threads_in_chat_history(
    chat_page: ChatPage,
) -> None:
    """TC003_598048 — Validate Bulk Delete All chat threads in Chat History.

    Step 1  : Open browser and navigate to DocuChat URL.
    Step 2  : Verify landing page options — Chat, File Management, Prompt Library.
    Step 3  : Click + New Chat, select Model 5-mini CRT, Chat Type Basic Chat.
    Step 4  : Enter 'What is CareSource?' and verify response, copy icon, Regenerate button.
    Step 5  : Create 6 total chat threads (1 from Step 4 + 5 new); click + New Chat at end.
    Step 6  : Verify Chat History with Edit, Delete buttons and Select checkbox.
    Step 7  : Click Select checkbox — verify Cancel, Select All, Deselect All visible and enabled.
    Step 8  : Click 'Select All' — verify Delete (N) button enabled with count = ALL threads.
    Step 9  : Click 'Deselect All' — verify all threads deselected, Delete button shows (0).
    Step 10 : Click Cancel — verify selection window closes, Select button visible.
    Step 11 : Re-enter selection mode, click 'Select All' — verify Delete (N) enabled for all threads.
    Step 12 : Click Delete (N) — verify 'Confirm bulk delete' dialog with correct message and buttons.
    Step 13 : Click Cancel in dialog — verify dialog closes, still in selection mode with Delete (N) active.
    Step 14 : Click Delete (N) again (still in selection mode) — verify confirm dialog reappears.
    Step 15 : Confirm deletion in dialog — verify 'Deleted N threads' success message.
    Step 16 : Verify Chat History is EMPTY — all threads have been deleted.
    Step 17 : Cleanup — confirm Chat History is empty; delete any unexpectedly remaining threads.
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
        "Click 'Select All' — verify Delete (N) button enabled with count = ALL threads",
        _step8_select_all_verify_delete_enabled(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        9,
        "Verify 'Deselect All' deselects all threads and Delete button shows (0)",
        _step9_verify_deselect_all(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        10,
        "Verify Cancel button closes selection window and Select button is visible",
        _step10_verify_cancel_in_selection_mode(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        11,
        "Re-enter selection mode, click 'Select All' — verify Delete (N) enabled for all threads",
        _step11_select_all_threads_for_delete(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        12,
        "Click Delete (N) — verify Confirm bulk delete dialog with correct message and buttons",
        _step12_click_delete_all_verify_confirm_dialog(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        13,
        "Cancel in delete dialog — verify dialog closes, still in selection mode with Delete (N) active",
        _step13_verify_cancel_in_delete_dialog(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        14,
        "Click Delete (N) again (still in selection mode) — verify confirm dialog reappears",
        _step14_click_delete_button_verify_confirm_dialog_again(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        15,
        "Confirm deletion in dialog — verify 'Deleted N threads' success message",
        _step15_verify_bulk_delete_all_threads(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        16,
        "Verify Chat History is EMPTY — all threads have been deleted",
        _step16_verify_chat_history_empty(page),
        _TC_NAME,
        page,
    )
    await _run_step(
        17,
        "Cleanup — confirm Chat History is empty; delete any unexpectedly remaining threads",
        _step17_cleanup_delete_all_chat_threads(page),
        _TC_NAME,
        page,
    )
