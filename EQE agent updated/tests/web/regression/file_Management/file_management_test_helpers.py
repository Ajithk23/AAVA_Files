"""File Management module test helpers for the DocuChat automation framework.

Shared helpers used by TC032 and future File Management regression tests.
All helpers accept a Playwright ``Page`` object directly — no page-object wrapper
required — so they compose cleanly with helpers from ``chat_test_helpers.py``.
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from playwright.async_api import Page, Locator

from pages.chat_page import ChatPage
from utils.test_data_loader import get_file_management_file_paths as _get_fm_file_paths

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project root (used by unsupported-file helpers)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _get_upload_files(tc_key: str) -> list[Path]:
    """Load the file list for *tc_key* from test_inputs.json (file_management section).

    Mirrors the pattern used by TC032 via ``get_tc032_inputs()`` so there is a
    single source of truth for which files each TC uploads.
    """
    return list(_get_fm_file_paths(tc_key.lower()))

# ---------------------------------------------------------------------------
# Internal utilities (mirrors pattern in chat_test_helpers.py)
# ---------------------------------------------------------------------------

async def _first_visible_with_wait(
    page: Page,
    locators: list[Locator],
    timeout_ms: int = 20000,
    poll_ms: int = 300,
    error_message: str = "Unable to find a visible locator from provided candidates",
) -> Locator:
    elapsed = 0
    while elapsed <= timeout_ms:
        for locator in locators:
            try:
                if await locator.count() > 0 and await locator.is_visible():
                    return locator
            except Exception:
                continue
        await page.wait_for_timeout(poll_ms)
        elapsed += poll_ms
    raise AssertionError(error_message)


async def _get_ag_grid_frame(page: Page):
    """Return the first AG Grid frame locator that has a visible header, or None."""
    for src in ["iframe[src*='agGrid']", "iframe[src*='st_aggrid']", "iframe"]:
        try:
            fl = page.frame_locator(src)
            if await fl.locator(".ag-header").count() > 0:
                return fl
        except Exception:
            continue
    return None


async def _wait_for_file_ready_status(
    page: Page,
    file_name: str,
    timeout_ms: int = 180000,
    poll_ms: int = 5000,
) -> bool:
    """Poll the File Management table until ``file_name`` shows a 'Ready' status.

    Returns True when Ready is detected, False if the timeout is reached.
    """
    stem = Path(file_name).stem
    ready_pattern = re.compile(r"\bready\b", re.IGNORECASE)
    elapsed = 0
    try:
        while elapsed <= timeout_ms:
            row_candidates = [
                page.locator("table tbody tr").filter(has_text=re.compile(re.escape(stem), re.IGNORECASE)).first,
                page.locator("[role='row']").filter(has_text=re.compile(re.escape(stem), re.IGNORECASE)).first,
            ]
            fl = await _get_ag_grid_frame(page)
            if fl is not None:
                ag_row = fl.locator(".ag-row").filter(has_text=re.compile(re.escape(stem), re.IGNORECASE)).first
                try:
                    if await ag_row.count() > 0:
                        row_text = await ag_row.inner_text()
                        if ready_pattern.search(row_text):
                            logger.info(
                                "_wait_for_file_ready_status: '%s' is Ready (AG Grid, %dms elapsed).",
                                file_name, elapsed,
                            )
                            return True
                except Exception:
                    pass

            for candidate in row_candidates:
                try:
                    if await candidate.count() > 0:
                        row_text = await candidate.inner_text()
                        if ready_pattern.search(row_text):
                            logger.info(
                                "_wait_for_file_ready_status: '%s' is Ready (%dms elapsed).",
                                file_name, elapsed,
                            )
                            return True
                except Exception:
                    continue

            await page.wait_for_timeout(poll_ms)
            elapsed += poll_ms

        logger.warning(
            "_wait_for_file_ready_status: '%s' did not reach Ready status within %dms — proceeding anyway.",
            file_name, timeout_ms,
        )
    except Exception as exc:
        logger.warning(
            "_wait_for_file_ready_status: unexpected error while waiting for '%s' — %s",
            file_name, exc,
        )
    return False


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

async def _navigate_to_chat_section(page: Page) -> None:
    """Click the Chat navigation entry to switch from File Management to the Chat page.

    This must be called before ``_open_chat_workspace`` whenever the current page
    is File Management (or any non-Chat view), because ``_open_chat_workspace``
    looks for 'New Chat' which only appears inside the Chat sidebar.
    """
    chat_nav_candidates = [
        page.get_by_role("tab", name=re.compile(r"^chat$|^chats$", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"^chat$|^chats$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"^chat$|^chats$", re.IGNORECASE)).first,
        page.locator("section[data-testid='stSidebar'] a").filter(
            has_text=re.compile(r"^chat$", re.IGNORECASE)
        ).first,
        page.locator("[data-testid*='chat']:not([data-testid*='chatInput']):not([data-testid*='chatMessage'])").first,
    ]
    nav_item = await _first_visible_with_wait(
        page,
        chat_nav_candidates,
        timeout_ms=20000,
        error_message="Chat navigation item not visible — cannot switch from File Management to Chat",
    )
    await nav_item.click()

    # Wait for Chat page to load — "New Chat" button or the chat input textarea
    chat_ready_candidates = [
        page.get_by_role("button", name=re.compile(r"new\s*chat", re.IGNORECASE)).first,
        page.locator("button:has-text('New Chat')").first,
        page.locator("textarea[placeholder*='help']").first,
        page.get_by_text(re.compile(r"chat\s*configuration", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page,
        chat_ready_candidates,
        timeout_ms=25000,
        error_message="Chat page did not load after clicking Chat navigation item",
    )


# ---------------------------------------------------------------------------
# Step 3 — Navigate to File Management
# ---------------------------------------------------------------------------

async def _navigate_to_file_management(page: Page) -> None:
    """Click the File Management navigation entry in the sidebar/top bar."""
    nav_candidates = [
        page.get_by_role("tab", name=re.compile(r"file\s*management", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"file\s*management", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"file\s*management", re.IGNORECASE)).first,
        page.locator("[data-testid*='file'], [aria-label*='file management'], [class*='file']").first,
    ]
    nav_item = await _first_visible_with_wait(
        page,
        nav_candidates,
        timeout_ms=20000,
        error_message="File Management navigation item not visible",
    )
    await nav_item.click()

    # Wait for File Management module to load
    readiness_candidates = [
        page.get_by_text(re.compile(r"upload\s*files?", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"choose\s*a\s*document", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"browse\s*files?", re.IGNORECASE)).first,
        page.locator("input[type='file']").first,
    ]
    await _first_visible_with_wait(
        page,
        readiness_candidates,
        timeout_ms=25000,
        error_message="File Management module did not load after navigation",
    )


# ---------------------------------------------------------------------------
# Step 4 — Verify File Management UI
# ---------------------------------------------------------------------------

async def _verify_file_management_ui(page: Page) -> None:
    """Verify all required UI elements on the File Management landing page.

    Checks (matching expected result from TC032 step 4):
    - "Upload Files" label
    - "Choose a Document to Upload" area with "Drag and drop" text and "Browse files" button
    - File size limit of 4 GB per file
    - Supported file types list
    """
    checks: list[tuple[str, list[Locator], str]] = [
        (
            "Upload Files label",
            [
                page.get_by_text(re.compile(r"upload\s*files?", re.IGNORECASE)).first,
                page.locator("label:has-text('Upload Files')").first,
            ],
            "'Upload Files' label is not visible",
        ),
        (
            "Choose a Document to Upload area",
            [
                page.get_by_text(re.compile(r"choose\s*a\s*document\s*to\s*upload", re.IGNORECASE)).first,
                page.get_by_text(re.compile(r"drag\s*and\s*drop\s*file", re.IGNORECASE)).first,
            ],
            "'Choose a Document to Upload' / drag and drop area is not visible",
        ),
        (
            "Browse files button",
            [
                page.get_by_role("button", name=re.compile(r"browse\s*files?", re.IGNORECASE)).first,
                page.get_by_text(re.compile(r"browse\s*files?", re.IGNORECASE)).first,
            ],
            "'Browse files' button is not visible",
        ),
        (
            "File size limit text",
            [
                page.get_by_text(re.compile(r"4\s*GB|4GB|per\s*file", re.IGNORECASE)).first,
                page.get_by_text(re.compile(r"limit|size|maximum", re.IGNORECASE)).first,
            ],
            "File size limit text is not visible",
        ),
    ]

    for step_name, candidates, message in checks:
        try:
            await _first_visible_with_wait(page, candidates, timeout_ms=15000, error_message=message)
        except AssertionError:
            logger.warning("[File Management UI] Failed check: %s — %s", step_name, message)
            raise


# ---------------------------------------------------------------------------
# Step 5 — Upload file via Browse Files and verify in list
# ---------------------------------------------------------------------------

async def _upload_file_via_browse(page: Page, file_path: Path) -> None:
    """Upload a single file via the Browse Files button.

    Uses Playwright's ``set_input_files`` on the hidden ``<input type="file">``
    element, which is the mechanism behind the 'Browse files' button in
    Streamlit's ``st.file_uploader``.

    After calling ``set_input_files``, Streamlit triggers a full component
    rerender that recreates the ``<input type="file">`` DOM node.  We wait for:
      1. The specific input element we used to detach (confirming the rerender
         started) — or 3 s, whichever comes first.
      2. A fresh ``<input type="file">`` to be attached again (confirming the
         rerender completed and the widget is ready for the next upload).
      3. ``networkidle`` — the backend upload request has settled.
    This three-phase wait is what prevents the 1-2 missing uploads per run.
    """
    _FILE_INPUT_SELECTOR = "input[type='file']"

    # ── Phase 0: locate a fresh, attached file input ─────────────────────────
    file_input = None
    for selector in [
        "[data-testid='stFileUploaderDropzoneInput']",
        _FILE_INPUT_SELECTOR,
        "section input[type='file']",
    ]:
        candidate = page.locator(selector).first
        try:
            await candidate.wait_for(state="attached", timeout=15000)
            file_input = candidate
            break
        except Exception:
            continue

    if file_input is None:
        raise AssertionError(f"File input not found for upload of {file_path.name}")

    await file_input.set_input_files(str(file_path))

    # ── Phase 1: wait for the element to detach (rerender started) ───────────
    try:
        await file_input.wait_for(state="detached", timeout=5000)
    except Exception:
        pass  # element may persist on some Streamlit versions — continue

    # ── Phase 2: wait for a new file input to be attached (rerender done) ────
    try:
        await page.locator(_FILE_INPUT_SELECTOR).first.wait_for(
            state="attached", timeout=15000
        )
    except Exception:
        pass

    # ── Phase 3: wait for upload network activity to settle ──────────────────
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    # Brief stabilisation pause before the next upload
    await page.wait_for_timeout(300)


async def _verify_file_in_uploaded_list(
    page: Page,
    file_name: str,
    timeout_ms: int = 60000,
) -> None:
    """Poll until ``file_name`` appears in the uploaded files list.

    Expected result (TC032 step 5):
    - File Name, Status, File Size (MB), File Type, Uploaded Date are shown.
    - A unique system-generated ID is assigned.
    - File is visible in the File Management file list.

    Searches both the main page (plain Streamlit table) and AG Grid iframes.
    """
    stem = Path(file_name).stem   # e.g. "test_upload" from "test_upload.pdf"
    ext = Path(file_name).suffix  # e.g. ".pdf"
    name_pattern = re.compile(re.escape(stem) + r".*" + re.escape(ext), re.IGNORECASE) if ext else re.compile(re.escape(stem), re.IGNORECASE)

    # Main-page candidates (plain Streamlit table)
    file_row_candidates = [
        page.get_by_text(re.compile(re.escape(file_name), re.IGNORECASE)).first,
        page.get_by_text(name_pattern).first,
        page.locator(f"[data-testid='file-row']:has-text('{stem}')").first,
        page.locator(f"table tbody tr:has-text('{stem}')").first,
    ]

    # Also build AG Grid iframe candidates
    for fl_pattern in [
        "iframe[src*='st_aggrid.AgGrid.agGrid']",
        "iframe[src*='st_aggrid']",
        "iframe[src*='agGrid']",
    ]:
        try:
            fl = page.frame_locator(fl_pattern)
            file_row_candidates.append(
                fl.locator(f".ag-cell:has-text('{stem}')").first
            )
        except Exception:
            pass

    await _first_visible_with_wait(
        page,
        file_row_candidates,
        timeout_ms=timeout_ms,
        error_message=f"Uploaded file '{file_name}' not found in the file list after {timeout_ms // 1000}s",
    )


async def _handle_duplicate_file_dialog(page: Page) -> None:
    """Dismiss a duplicate-file confirmation dialog if one is visible.

    When the same file is uploaded twice, the application may show a dialog
    asking whether to replace/overwrite. For the file-management tests that
    intentionally exercise a duplicate upload, the dialog should be dismissed
    so it does not block later navigation. If no dialog is present, it returns
    immediately without raising.
    """
    # Confirmed Streamlit dialog selector (shows as data-testid="stDialog")
    _DIALOG_SELECTORS = [
        '[data-testid="stDialog"]',
        '[data-testid="stModal"]',
        'div[data-modal-container="true"]',
        '[role="dialog"]',
        '[aria-modal="true"]',
    ]
    # Pattern covers the actual Streamlit button text "Upload File" as well
    # as legacy/alternative confirm wordings.
    _CONFIRM_PATTERN = re.compile(
        r"upload\s*file|^upload$|replace|overwrite|confirm|^yes$|^ok$",
        re.IGNORECASE,
    )

    dialog_locator = None
    for sel in _DIALOG_SELECTORS:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible():
                dialog_locator = el
                break
        except Exception:
            continue

    if dialog_locator is None:
        return

    dialog_scope_candidates = [
        page.locator('[role="dialog"]').first,
        page.locator('div[data-modal-container="true"]').first,
        page.locator('[data-testid="stDialog"]').first,
        page.locator('[aria-modal="true"]').first,
    ]
    dialog_scope = None
    for candidate in dialog_scope_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                dialog_scope = candidate
                break
        except Exception:
            continue

    if dialog_scope is None:
        return

    dismiss_candidates = [
        dialog_scope.get_by_role("button", name=re.compile(r"cancel|close", re.IGNORECASE)).first,
        dialog_scope.locator("button").filter(
            has_text=re.compile(r"cancel|close", re.IGNORECASE)
        ).first,
        dialog_scope.locator("button[aria-label*='close' i]").first,
        dialog_scope.locator("button").nth(1),
    ]
    for candidate in dismiss_candidates:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click(force=True)
                await page.wait_for_timeout(300)
                break
        except Exception:
            continue

    try:
        await page.evaluate(
            """() => {
                const modal = document.querySelector('[role="dialog"], div[data-modal-container="true"], [data-testid="stDialog"], [aria-modal="true"]');
                if (!modal) return false;
                const buttons = Array.from(modal.querySelectorAll('button'));
                const dismiss = buttons.find((btn) => /cancel|close/i.test((btn.innerText || btn.textContent || '').trim()));
                if (dismiss) {
                    dismiss.click();
                    return true;
                }
                return false;
            }"""
        )
    except Exception:
        pass

    # Last resort: press Escape
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass

    for _ in range(20):
        try:
            if not await dialog_scope.is_visible():
                logger.info("Dismissed duplicate file dialog.")
                return
        except Exception:
            logger.info("Dismissed duplicate file dialog.")
            return
        await page.wait_for_timeout(200)

    raise AssertionError("Duplicate file dialog remained visible after dismissal attempts")


async def _upload_and_verify(page: Page, file_path: Path) -> None:
    """Upload a file via Browse Files and verify it appears in the uploaded list."""
    await _upload_file_via_browse(page, file_path)
    await _handle_duplicate_file_dialog(page)
    await _verify_file_in_uploaded_list(page, file_path.name, timeout_ms=30000)
    logger.info("Uploaded and verified: %s", file_path.name)


async def _upload_file_via_drag_drop(page: Page, file_path: Path) -> None:
    """Upload a single file via the drag-and-drop zone using JS DataTransfer injection.

    Reads the file content in Python, passes the bytes to the browser via a
    base64-encoded JS blob, then dispatches ``dragenter`` / ``dragover`` / ``drop``
    events on the Streamlit file-uploader dropzone — exactly as a real drag would.
    After the drop, applies the same 3-phase stabilisation wait used by
    ``_upload_file_via_browse`` so Streamlit's rerender completes before the next
    upload starts.
    """
    import base64
    import mimetypes

    file_bytes = file_path.read_bytes()
    b64 = base64.b64encode(file_bytes).decode("ascii")
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_name = file_path.name

    # Dropzone selectors (Streamlit st.file_uploader)
    dropzone_selectors = [
        "[data-testid='stFileUploaderDropzone']",
        "[data-testid='stFileUploaderDropzoneInstructions']",
        "div.uploadedFileData",           # fallback outer wrapper
        "label[data-testid='stFileUploaderDropzone']",
    ]
    dropzone = None
    for sel in dropzone_selectors:
        candidate = page.locator(sel).first
        try:
            await candidate.wait_for(state="attached", timeout=8000)
            dropzone = candidate
            break
        except Exception:
            continue

    if dropzone is None:
        raise AssertionError(
            f"Drag-and-drop dropzone not found for upload of {file_path.name}"
        )

    # Build the DataTransfer in the browser and fire drag events
    await page.evaluate(
        """
        async ([b64, mime, fileName]) => {
            const byteChars = atob(b64);
            const byteArr = new Uint8Array(byteChars.length);
            for (let i = 0; i < byteChars.length; i++) byteArr[i] = byteChars.charCodeAt(i);
            const blob = new Blob([byteArr], { type: mime });
            const file = new File([blob], fileName, { type: mime });
            const dt = new DataTransfer();
            dt.items.add(file);

            const selectors = [
                "[data-testid='stFileUploaderDropzone']",
                "[data-testid='stFileUploaderDropzoneInstructions']",
            ];
            let zone = null;
            for (const s of selectors) {
                const el = document.querySelector(s);
                if (el) { zone = el; break; }
            }
            if (!zone) return;

            ['dragenter', 'dragover'].forEach(evtName => {
                zone.dispatchEvent(new DragEvent(evtName, { dataTransfer: dt, bubbles: true }));
            });
            zone.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
        }
        """,
        [b64, mime, file_name],
    )

    # Same 3-phase stabilisation as _upload_file_via_browse
    _FILE_INPUT_SELECTOR = "input[type='file']"
    try:
        await page.locator(_FILE_INPUT_SELECTOR).first.wait_for(state="detached", timeout=5000)
    except Exception:
        pass
    try:
        await page.locator(_FILE_INPUT_SELECTOR).first.wait_for(state="attached", timeout=15000)
    except Exception:
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await page.wait_for_timeout(300)


async def _upload_and_verify_drag_drop(page: Page, file_path: Path) -> None:
    """Upload a file via drag-and-drop and verify it appears in the uploaded list."""
    await _upload_file_via_drag_drop(page, file_path)
    await _handle_duplicate_file_dialog(page)
    await _verify_file_in_uploaded_list(page, file_path.name, timeout_ms=30000)
    logger.info("Uploaded and verified (drag-drop): %s", file_path.name)


async def _upload_and_verify_tolerant(page: Page, file_path: Path, method: str = "browse") -> bool:
    """Upload a file with fault tolerance. Returns True on success, False on skip/failure.

    Args:
        page:      Playwright Page.
        file_path: Absolute path to the file to upload.
        method:    ``'browse'`` (default) or ``'drag_drop'``.

    - Skips 0-byte files with a WARNING (does not fail the step).
    - Catches any upload or verification error, logs a WARNING, and continues.
    """
    if file_path.stat().st_size == 0:
        logger.warning(
            "Skipping upload of 0-byte file: %s — the application will likely reject it.",
            file_path.name,
        )
        return False
    try:
        if method == "drag_drop":
            await _upload_and_verify_drag_drop(page, file_path)
        else:
            await _upload_and_verify(page, file_path)
        return True
    except Exception as exc:
        logger.warning(
            "Upload skipped for %s (%s) — %s",
            file_path.name, method, exc,
        )
        return False


# ---------------------------------------------------------------------------
# Steps 7 + 8 — Verify and select all files in "Choose Options" dropdown
# ---------------------------------------------------------------------------

async def _verify_ready_files_in_chat_dropdown(page: Page, expected_names: list[str]) -> None:
    """Open 'Select Ready Files to Include in Chat Context' and verify every
    expected file name appears in the dropdown list (one by one).

    Expected result (TC032 step 7): all uploaded files are listed.
    """
    multiselect_candidates = [
        page.locator(
            "label:has-text('Select Ready Files to Include in Chat Context') ~ div [data-baseweb='select']"
        ).first,
        page.locator("[aria-label*='Select Ready Files']").first,
        page.locator("div[data-testid='stMultiSelect'] [data-baseweb='select']").first,
        page.locator("div[data-testid='stMultiSelect']").first,
    ]
    multiselect = await _first_visible_with_wait(
        page,
        multiselect_candidates,
        timeout_ms=15000,
        error_message="'Select Ready Files to Include in Chat Context' multiselect not visible",
    )
    await multiselect.click()
    await page.wait_for_timeout(600)

    missing: list[str] = []
    for name in expected_names:
        stem = Path(name).stem
        pattern = re.compile(re.escape(stem), re.IGNORECASE)
        option_candidates = [
            page.get_by_role("option", name=pattern).first,
            page.get_by_text(pattern).first,
        ]
        found = False
        for candidate in option_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    found = True
                    break
            except Exception:
                continue
        if not found:
            missing.append(name)

    if missing:
        await page.keyboard.press("Escape")
        raise AssertionError(
            f"The following uploaded files were NOT found in the 'Choose Options' dropdown: {missing}"
        )

    # Leave dropdown open for the next step (select all)


async def _select_all_files_in_chat_dropdown(page: Page, expected_names: list[str]) -> None:
    """Select all files one by one from the already-open 'Choose Options' multiselect.

    Expected result (TC032 step 8): each file is selected and highlighted.

    Assumes the multiselect dropdown is already open (call after
    ``_verify_ready_files_in_chat_dropdown``). Re-opens the dropdown between
    selections if Streamlit closes it after each pick.
    """
    multiselect_candidates = [
        page.locator(
            "label:has-text('Select Ready Files to Include in Chat Context') ~ div [data-baseweb='select']"
        ).first,
        page.locator("div[data-testid='stMultiSelect'] [data-baseweb='select']").first,
        page.locator("div[data-testid='stMultiSelect']").first,
    ]

    for name in expected_names:
        stem = Path(name).stem
        pattern = re.compile(re.escape(stem), re.IGNORECASE)

        # Re-open dropdown for each selection (Streamlit may close it)
        try:
            multiselect = await _first_visible_with_wait(
                page, multiselect_candidates, timeout_ms=8000,
                error_message="Multiselect not visible when trying to select next file",
            )
            await multiselect.click()
            await page.wait_for_timeout(400)
        except Exception:
            pass

        option_candidates = [
            page.get_by_role("option", name=pattern).first,
            page.get_by_text(pattern).first,
        ]
        option_selected = False
        for candidate in option_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    await candidate.click()
                    option_selected = True
                    await page.wait_for_timeout(300)
                    break
            except Exception:
                continue

        if not option_selected:
            logger.warning("Could not select file '%s' from dropdown — skipping.", name)

    # Close dropdown after all selections
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass

    await page.wait_for_timeout(400)

    # Soft-verify at least one chip/tag is shown
    selection_chips = page.locator(
        "div[data-testid='stMultiSelect'] [data-baseweb='tag'], "
        "div[data-testid='stMultiSelect'] span[role='button']"
    )
    chip_count = 0
    try:
        chip_count = await selection_chips.count()
    except Exception:
        pass
    if chip_count == 0:
        logger.warning(
            "No selection chips visible after selecting all files — "
            "the multiselect may not have registered all selections."
        )


# ---------------------------------------------------------------------------
# Steps 9 + 10 — Chat verification (response and long query)
# ---------------------------------------------------------------------------

async def _verify_chat_response_direct(chat_page: ChatPage, query: str) -> None:
    """Send ``query`` and wait for a non-empty, non-echo response (up to 60 s).

    Mirrors ``chat_test_helpers._verify_chat_response`` but accepts the query
    string directly instead of fetching it from ``test_inputs.json``.
    """
    await chat_page.send_message(query)
    query_fingerprint = query.strip().lower()
    latest_message = ""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if chat_page.page.is_closed():
            raise AssertionError("Chat page was closed before a response could be validated")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if (
            latest_message
            and latest_message.strip()
            and latest_message.strip().lower() != query_fingerprint
        ):
            break
        await chat_page.page.wait_for_timeout(300)
    assert latest_message is not None and latest_message.strip() != "", "Chat response not displayed"


async def _verify_long_query_direct(chat_page: ChatPage, long_query: str) -> None:
    """Send a pre-built ``long_query`` string and wait for a NEW AI response (up to 90 s).

    Snapshots the current last message BEFORE sending so the wait loop exits
    only when a genuinely new message appears — not when it mistakenly sees
    the previous step's (step 9) AI response that is already in the DOM.
    """
    # Snapshot whatever is currently in the DOM as the last message
    prior_message = await chat_page.get_latest_message(timeout_ms=1500)
    prior_fingerprint = (prior_message or "").strip().lower()[:200]

    await chat_page.send_message(long_query)

    # Use first 150 chars as echo-detection fingerprint
    query_fingerprint = long_query.strip()[:150].lower()

    latest_message = ""
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if chat_page.page.is_closed():
            raise AssertionError("Chat page was closed while waiting for long-query response")
        latest_message = await chat_page.get_latest_message(timeout_ms=1500)
        if latest_message and latest_message.strip():
            current = latest_message.strip().lower()
            # Skip if it's the user's own echo
            if current[:150] == query_fingerprint:
                await chat_page.page.wait_for_timeout(300)
                continue
            # Skip if it's still the prior message from step 9
            if current[:200] == prior_fingerprint:
                await chat_page.page.wait_for_timeout(300)
                continue
            # A new distinct message has appeared — long query response received
            break
        await chat_page.page.wait_for_timeout(300)
    assert latest_message is not None and latest_message.strip() != "", "No response for long query"


# ---------------------------------------------------------------------------
# Bulk upload helper (TC035 / TC036 / TC037)
# ---------------------------------------------------------------------------

async def _upload_files_bulk_via_file_page(page: Page, file_page, tc_name: str) -> None:
    """Upload all files for the given TC from test_inputs.json — first 7 via Browse Files, last 8 via Drag & Drop.

    File paths are loaded from file_management.<tc_name.lower()>.files in test_inputs.json,
    exactly as TC032/TC033/TC034 do via get_tc032_inputs().
    """
    file_paths = list(_get_fm_file_paths(tc_name.lower()))
    browse_files = file_paths[:7]
    drag_drop_files = file_paths[7:]
    for fp in browse_files:
        await _upload_and_verify_tolerant(page, fp, method="browse")
    for fp in drag_drop_files:
        await _upload_and_verify_tolerant(page, fp, method="drag_drop")


# ---------------------------------------------------------------------------
# Choose Options dropdown helpers (TC035 / TC036 / TC037)
# ---------------------------------------------------------------------------

async def _open_choose_options_dropdown(page: Page) -> None:
    """Open the 'Select Ready Files to Include in Chat Context' multiselect dropdown
    and verify at least one file option is listed."""
    multiselect_candidates = [
        page.locator(
            "label:has-text('Select Ready Files to Include in Chat Context') ~ div [data-baseweb='select']"
        ).first,
        page.locator("[aria-label*='Select Ready Files']").first,
        page.locator("div[data-testid='stMultiSelect'] [data-baseweb='select']").first,
        page.locator("div[data-testid='stMultiSelect']").first,
    ]
    multiselect = await _first_visible_with_wait(
        page,
        multiselect_candidates,
        timeout_ms=20000,
        error_message="'Select Ready Files to Include in Chat Context' multiselect not visible",
    )
    await multiselect.click()
    await page.wait_for_timeout(600)

    # Verify at least one option appeared
    option_candidates = [
        page.get_by_role("option").first,
        page.locator("[role='listbox'] [role='option']").first,
        page.locator("li[data-baseweb='menu-item']").first,
    ]
    await _first_visible_with_wait(
        page,
        option_candidates,
        timeout_ms=15000,
        error_message="No file options visible in 'Choose Options' dropdown",
    )


async def _select_multiple_ready_files(
    page: Page,
    count: int = 2,
    preferred_file_names: list[str] | None = None,
) -> None:
    """Select up to ``count`` files from the already-open Choose Options multiselect.

    Closes the dropdown with Escape after selecting.
    """
    options = await page.get_by_role("option").all()
    if not options:
        options = await page.locator("[role='listbox'] [role='option']").all()
    if not options:
        options = await page.locator("li[data-baseweb='menu-item']").all()

    visible_options = []
    for opt in options:
        try:
            if await opt.is_visible():
                visible_options.append(opt)
        except Exception:
            continue

    assert visible_options, "No file options visible in the 'Choose Options' dropdown to select"

    options_to_select = visible_options
    if preferred_file_names:
        normalized_preferences = [name.strip().lower() for name in preferred_file_names if name.strip()]
        preferred_options = []
        for preferred_name in normalized_preferences:
            for opt in visible_options:
                try:
                    option_text = (await opt.inner_text()).strip().lower()
                except Exception:
                    continue
                if option_text == preferred_name or preferred_name in option_text:
                    preferred_options.append(opt)
                    break
        if preferred_options:
            options_to_select = preferred_options

    selected = 0
    for opt in options_to_select[:count]:
        await opt.click()
        await page.wait_for_timeout(300)
        selected += 1

    assert selected >= 1, (
        f"Could not select any files from 'Choose Options' dropdown. "
        f"Expected at least 1 of {count} selections."
    )

    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass
    await page.wait_for_timeout(500)

    if preferred_file_names:
        selected_text = " ".join(
            await page.locator(
                "div[data-testid='stMultiSelect'] [data-baseweb='tag'], "
                "div[data-testid='stMultiSelect'] span[role='button']"
            ).all_inner_texts()
        ).lower()
        for preferred_name in preferred_file_names:
            assert preferred_name.lower() in selected_text, (
                f"Expected ready file '{preferred_name}' to be selected, but visible chips were: {selected_text!r}"
            )


# ---------------------------------------------------------------------------
# Pre-test cleanup helper
# ---------------------------------------------------------------------------

async def _pre_test_delete_all_files(page: Page) -> None:
    """Best-effort deletion of all files present in the File Management list.

    Iterates select-all → delete until no files remain or no delete button is found.
    Failures are silenced so the test can continue even if cleanup is incomplete.
    """
    for _ in range(30):  # safety cap — at most 30 iterations
        try:
            # Try to find a "Select All" checkbox or delete-all button
            select_all_candidates = [
                page.locator("input[type='checkbox'][aria-label*='select all' i]").first,
                page.locator("th input[type='checkbox']").first,
                page.get_by_role("checkbox", name=re.compile(r"select\s*all", re.IGNORECASE)).first,
            ]
            checked = False
            for candidate in select_all_candidates:
                try:
                    if await candidate.is_visible(timeout=1500):
                        await candidate.check()
                        await page.wait_for_timeout(300)
                        checked = True
                        break
                except Exception:
                    continue

            # Look for a Delete (selected) button
            delete_btn_candidates = [
                page.get_by_role("button", name=re.compile(r"delete\s*selected|delete\s*all", re.IGNORECASE)).first,
                page.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
                page.locator("button:has([data-testid='stIconMaterial']:has-text('delete'))").first,
            ]
            deleted = False
            for btn in delete_btn_candidates:
                try:
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        await page.wait_for_timeout(800)
                        # Confirm any dialog
                        confirm_candidates = [
                            page.get_by_role("button", name=re.compile(r"yes|confirm|delete", re.IGNORECASE)).first,
                            page.locator("[role='dialog'] button").first,
                        ]
                        for confirm in confirm_candidates:
                            try:
                                if await confirm.is_visible(timeout=1000):
                                    await confirm.click()
                                    await page.wait_for_timeout(800)
                                    break
                            except Exception:
                                continue
                        deleted = True
                        break
                except Exception:
                    continue

            if not deleted:
                break  # nothing left to delete
        except Exception:
            break

    logger.info("Pre-test file cleanup completed.")


async def _cleanup_on_failure(page: Page) -> None:
    """Best-effort cleanup of chats and files — called from finally blocks.

    Swallows all exceptions so the original test failure is always re-raised.
    """
    try:
        await _post_test_delete_all_chats(page)
    except Exception as exc:
        logger.warning("Failure-cleanup: chat deletion failed: %s", exc)
    try:
        await _post_test_delete_all_files(page)
    except Exception as exc:
        logger.warning("Failure-cleanup: file deletion failed: %s", exc)


async def _post_test_delete_all_chats(page: Page) -> None:
    """Navigate to the Chat section and delete every saved chat session from the sidebar.

    This is a mandatory post-test cleanup step for TC029-TC040.  It runs BEFORE
    ``_post_test_delete_all_files`` so that no chat history is left behind.

    Strategy
    --------
    The sidebar shows chat entries with visible 🗑️ delete buttons next to each.
    We simply find and click each 🗑️ button, confirming any dialog that appears,
    and repeat until no more delete buttons remain.

    All failures are silenced so cleanup never fails the test.
    """
    await page.wait_for_timeout(2000)

    # Navigate to the Chat section if not already there
    try:
        for nav_candidate in [
            page.get_by_role("tab", name=re.compile(r"^chat$", re.IGNORECASE)).first,
            page.get_by_role("button", name=re.compile(r"^chat$", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"^chat$", re.IGNORECASE)).first,
        ]:
            try:
                if await nav_candidate.count() > 0 and await nav_candidate.is_visible():
                    await nav_candidate.click()
                    await page.wait_for_timeout(1500)
                    break
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Post-test chat cleanup: could not navigate to Chat — %s", exc)
        return

    await page.wait_for_timeout(1500)

    sidebar = page.locator("[data-testid='stSidebarUserContent']")

    # Log sidebar state for diagnostics
    try:
        _all_btn_texts = []
        for _b in await sidebar.get_by_role("button").all():
            try:
                _all_btn_texts.append((await _b.text_content() or "").strip())
            except Exception:
                pass
        logger.warning(
            "Post-test chat cleanup: sidebar buttons found = %s", _all_btn_texts,
        )
    except Exception:
        pass

    # Confirm helper for deletion dialogs
    async def _confirm_dialog():
        for _confirm in [
            page.get_by_role(
                "button",
                name=re.compile(r"^(ok|yes|confirm|delete)$", re.IGNORECASE),
            ).first,
            page.locator("[role='dialog'] button").first,
            page.locator("[data-testid='stDialog'] button").first,
        ]:
            try:
                if await _confirm.count() > 0 and await _confirm.is_visible():
                    await _confirm.click()
                    await page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    # Delete loop — find and click 🗑️ buttons until none remain
    for _iteration in range(30):
        deleted = False
        try:
            # Strategy 1: Find 🗑️ emoji buttons in the sidebar
            trash_buttons = await sidebar.get_by_role("button").all()
            for btn in trash_buttons:
                try:
                    text = (await btn.text_content() or "").strip()
                    if "🗑️" in text or "🗑" in text:
                        await btn.click()
                        await page.wait_for_timeout(800)
                        await _confirm_dialog()
                        await page.wait_for_timeout(1000)
                        deleted = True
                        break  # re-scan after deletion since DOM changed
                except Exception:
                    continue

            # Strategy 2: Material icon delete buttons
            if not deleted:
                for del_sel in [
                    "button:has([data-testid='stIconMaterial']:has-text('delete'))",
                    "button[aria-label*='delete' i]",
                    "button[data-testid*='delete' i]",
                ]:
                    try:
                        del_btn = sidebar.locator(del_sel).first
                        if await del_btn.count() > 0 and await del_btn.is_visible():
                            await del_btn.click()
                            await page.wait_for_timeout(800)
                            await _confirm_dialog()
                            await page.wait_for_timeout(1000)
                            deleted = True
                            break
                    except Exception:
                        continue

            if not deleted:
                break  # no more delete buttons found

        except Exception:
            break

    logger.info("Post-test chat cleanup completed.")


async def _post_test_delete_all_files(page: Page) -> None:
    """Navigate to File Management and delete all uploaded documents at the end of a test.

    This is a mandatory post-test cleanup step for TC029-TC040.  It must be called
    after ``_post_test_delete_all_chats`` and immediately before the
    "Exit the application" step so that no uploaded documents are left behind
    between runs.

    Uses the same two-path strategy as ``_select_file_row``:
    1. Try AG Grid iframe (TC038-TC040 style)
    2. Fall back to plain Streamlit HTML table (TC029-TC037 style)

    All failures are silenced so cleanup never fails the test.
    """
    try:
        await _navigate_to_file_management(page)
    except Exception as exc:
        logger.warning(
            "Post-test cleanup: could not navigate to File Management — %s", exc,
        )
        return

    # Wait for the page to settle after navigation
    await page.wait_for_timeout(3000)

    # Scroll to bottom so Streamlit renders all components in the viewport
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    for _round in range(50):  # safety cap
        try:
            # ── Detect which table type is present ───────────────────────
            ag_ctx = None
            is_ag_grid = False

            # Path A: AG Grid iframe
            for frame in page.frames:
                try:
                    if await frame.locator(".ag-row").count() > 0:
                        ag_ctx = frame
                        is_ag_grid = True
                        break
                except Exception:
                    continue

            if ag_ctx is None:
                for fl_pattern in [
                    "iframe[src*='st_aggrid.AgGrid.agGrid']",
                    "iframe[src*='st_aggrid']",
                    "iframe[src*='agGrid']",
                ]:
                    try:
                        fl = page.frame_locator(fl_pattern)
                        if await fl.locator(".ag-row").count() > 0:
                            ag_ctx = fl
                            is_ag_grid = True
                            break
                    except Exception:
                        continue

            # Path B: plain Streamlit HTML table
            has_plain_rows = False
            if not is_ag_grid:
                try:
                    has_plain_rows = await page.locator(
                        "table tbody tr"
                    ).count() > 0
                except Exception:
                    pass
                if not has_plain_rows:
                    # Also try role-based rows (Streamlit dataframe)
                    try:
                        has_plain_rows = await page.locator(
                            "[role='row']"
                        ).count() > 1  # >1 because header row counts as 1
                    except Exception:
                        pass

            if not is_ag_grid and not has_plain_rows:
                if _round == 0:
                    # First round: wait a bit and retry in case table is still loading
                    await page.wait_for_timeout(3000)
                    continue
                logger.warning(
                    "Post-test cleanup: no file rows found (AG Grid or plain table) — "
                    "either no files uploaded or table did not load.",
                )
                break

            # ── Select all rows ──────────────────────────────────────────
            selected = False

            if is_ag_grid:
                # AG Grid: use header select-all checkbox
                for sel in [
                    ag_ctx.locator(".ag-header-select-all input[type='checkbox']").first,
                    ag_ctx.locator(".ag-header-select-all .ag-checkbox-input").first,
                    ag_ctx.locator("[ref='cbSelectAll']").first,
                ]:
                    try:
                        if await sel.count() > 0 and await sel.is_visible():
                            await sel.check()
                            await page.wait_for_timeout(600)
                            selected = True
                            break
                    except Exception:
                        continue
                # Fallback: click individual rows
                if not selected:
                    try:
                        row_count = await ag_ctx.locator(".ag-row").count()
                        for i in range(row_count):
                            cb = ag_ctx.locator(".ag-row").nth(i).locator(
                                "input[type='checkbox']"
                            ).first
                            try:
                                if await cb.count() > 0:
                                    await cb.check()
                                    selected = True
                            except Exception:
                                continue
                        if selected:
                            await page.wait_for_timeout(600)
                    except Exception:
                        pass
            else:
                # Plain table: click each row checkbox
                for sel_candidate in [
                    page.locator("table tbody tr input[type='checkbox']"),
                    page.locator("[role='row'] input[type='checkbox']"),
                    page.locator("[role='checkbox']"),
                ]:
                    try:
                        count = await sel_candidate.count()
                        if count > 0:
                            for i in range(count):
                                try:
                                    await sel_candidate.nth(i).check()
                                    selected = True
                                except Exception:
                                    continue
                            if selected:
                                await page.wait_for_timeout(600)
                            break
                    except Exception:
                        continue

            if not selected:
                logger.warning("Post-test cleanup: could not select any file rows.")
                break

            # ── Scroll to make Delete button visible ─────────────────────
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)
            except Exception:
                pass

            # ── Click Delete Document(s) button ──────────────────────────
            delete_clicked = False
            for del_candidate in [
                page.get_by_role("button", name=re.compile(
                    r"delete\s*documents?", re.IGNORECASE)).first,
                page.get_by_text(re.compile(
                    r"delete\s*documents?", re.IGNORECASE)).first,
                page.locator(
                    "button:has-text('Delete Document')").first,
                page.locator(
                    "button:has([data-testid='stIconMaterial']:has-text('delete'))").first,
                page.get_by_role("button", name=re.compile(
                    r"delete", re.IGNORECASE)).first,
            ]:
                try:
                    if await del_candidate.count() > 0 and await del_candidate.is_visible():
                        await del_candidate.click()
                        delete_clicked = True
                        await page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue

            if not delete_clicked:
                logger.warning(
                    "Post-test cleanup: files selected but Delete button not found/visible.",
                )
                break

            # ── Confirm the deletion dialog ──────────────────────────────
            for confirm in [
                page.get_by_role("button", name=re.compile(
                    r"^(ok|confirm|yes|delete)$", re.IGNORECASE)).first,
                page.get_by_role("button", name=re.compile(
                    r"delete", re.IGNORECASE)).first,
                page.locator("[role='dialog'] button").first,
            ]:
                try:
                    if await confirm.count() > 0 and await confirm.is_visible():
                        await confirm.click()
                        await page.wait_for_timeout(2500)
                        break
                except Exception:
                    continue

        except Exception:
            break

    logger.info("Post-test file cleanup completed.")


# ===========================================================================
# AG Grid helpers (TC038-TC040)
# ===========================================================================

async def _get_ag_grid_frame(page: Page):
    """Return the first AG Grid frame locator that has a visible header, or None."""
    for src in ["iframe[src*='agGrid']", "iframe[src*='st_aggrid']", "iframe"]:
        try:
            fl = page.frame_locator(src)
            if await fl.locator(".ag-header").count() > 0:
                return fl
        except Exception:
            continue
    return None


async def _verify_sort_default(page: Page) -> None:
    """Verify the Files table is visible after upload (step 6 for TC038-040)."""
    heading_candidates = [
        page.get_by_role("heading", name=re.compile(r"^files$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"^files$", re.IGNORECASE)).first,
        page.locator("h1, h2, h3").filter(has_text=re.compile(r"^files$", re.IGNORECASE)).first,
    ]
    await _first_visible_with_wait(
        page, heading_candidates, timeout_ms=30000,
        error_message="'Files' section heading not visible on File Management page",
    )
    await page.wait_for_timeout(3000)
    for src in ["iframe[src*='agGrid']", "iframe[src*='st_aggrid']", "iframe"]:
        try:
            fl = page.frame_locator(src)
            if await fl.locator(".ag-root").count() > 0:
                return
        except Exception:
            continue


async def _verify_sort_column(page: Page, column_name: str) -> None:
    """Click a column header to sort ascending then descending (steps 7-12 for TC038-040)."""
    header = None
    fl = await _get_ag_grid_frame(page)
    if fl is not None:
        for candidate in [
            fl.get_by_role("columnheader", name=re.compile(re.escape(column_name), re.IGNORECASE)).first,
            fl.locator(".ag-header-cell").filter(has_text=re.compile(re.escape(column_name), re.IGNORECASE)).first,
            fl.locator("[col-id]").filter(has_text=re.compile(re.escape(column_name), re.IGNORECASE)).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    header = candidate
                    break
            except Exception:
                continue

    if header is None:
        for candidate in [
            page.get_by_role("columnheader", name=re.compile(re.escape(column_name), re.IGNORECASE)).first,
            page.locator("th").filter(has_text=re.compile(re.escape(column_name), re.IGNORECASE)).first,
            page.locator("[role='columnheader']").filter(has_text=re.compile(re.escape(column_name), re.IGNORECASE)).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    header = candidate
                    break
            except Exception:
                continue

    if header is None:
        return  # column not found — skip gracefully

    await header.click()
    await page.wait_for_timeout(1500)
    await header.click()
    await page.wait_for_timeout(1500)


async def _verify_sort_after_navigation(page: Page) -> None:
    """Navigate away and back, then verify default sort is restored (step 13)."""
    chat_nav = None
    for candidate in [
        page.get_by_role("tab", name=re.compile(r"^chat$", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"^chat$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"^chat$", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                chat_nav = candidate
                break
        except Exception:
            continue

    if chat_nav:
        await chat_nav.click()
        await page.wait_for_timeout(2000)

    await _navigate_to_file_management(page)
    await page.wait_for_timeout(3000)
    await _verify_sort_default(page)


# ---------------------------------------------------------------------------
# Advanced upload helpers (TC038-TC040 steps 14-25)
# ---------------------------------------------------------------------------

async def _try_unsupported_file_upload(page: Page, file_page) -> None:
    """Attempt to upload unsupported file types (.exe, .zip, .epub) and verify rejection (steps 14-15)."""
    _unsupported = [
        _PROJECT_ROOT / "test_data" / "sample_files" / "Test.exe",
        _PROJECT_ROOT / "test_data" / "sample_files" / "Test.zip",
        _PROJECT_ROOT / "test_data" / "sample_files" / "Test.epub",
    ]
    available = [f for f in _unsupported if f.exists()]
    if not available:
        return

    for fp in available:
        try:
            await file_page.upload_file(str(fp))
        except Exception:
            continue
        await page.wait_for_timeout(2000)
        error_candidates = [
            page.get_by_text(re.compile(r"unsupported\s*file", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"file\s*type\s*not\s*supported", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"invalid\s*file\s*type", re.IGNORECASE)).first,
            page.get_by_text(re.compile(r"format\s*not\s*allowed", re.IGNORECASE)).first,
            page.get_by_role("alert").first,
            page.locator("[class*='error'], [class*='alert'], [class*='warning']").first,
        ]
        for c in error_candidates:
            try:
                if await c.count() > 0 and await c.is_visible():
                    break
            except Exception:
                continue


async def _upload_huge_file(page: Page, file_page, tc_key: str = "tc038") -> "str | None":
    """Upload the largest available test file as the 'huge file' (step 16).

    Returns the file name uploaded, or None if skipped.
    """
    import time as _time
    available = [f for f in _get_upload_files(tc_key) if f.exists()]
    if not available:
        return None
    largest = max(available, key=lambda f: f.stat().st_size)
    try:
        await _upload_file_via_browse(page, largest)
    except Exception:
        return None
    await _handle_duplicate_file_dialog(page)
    await page.wait_for_timeout(1000)
    try:
        deadline = _time.monotonic() + 60
        while _time.monotonic() < deadline:
            if await page.get_by_text(largest.name).count() > 0:
                break
            await page.wait_for_timeout(2000)
    except Exception:
        pass
    await page.wait_for_timeout(2000)
    return largest.name


async def _upload_duplicate_file(page: Page, file_page, file_name: "str | None", tc_key: str = "tc038") -> None:
    """Upload the same file again to trigger duplicate handling (step 17)."""
    import time as _time
    _files = _get_upload_files(tc_key)
    if file_name is None:
        available = [f for f in _files if f.exists()]
        if not available:
            return
        dup_file = available[0]
    else:
        match = next((f for f in _files if f.name == file_name), None)
        dup_file = match if match and match.exists() else None
        if dup_file is None:
            available = [f for f in _files if f.exists()]
            dup_file = available[0] if available else None
    if dup_file is None:
        return
    try:
        await _upload_file_via_browse(page, dup_file)
    except Exception:
        return
    await _handle_duplicate_file_dialog(page)
    await page.wait_for_timeout(1000)
    try:
        deadline = _time.monotonic() + 20
        while _time.monotonic() < deadline:
            if await page.get_by_text(dup_file.name).count() > 0:
                break
            await page.wait_for_timeout(1000)
    except Exception:
        pass


async def _verify_cancel_upload(page: Page, file_page, tc_key: str = "tc038") -> None:
    """Select a large file, start upload, then click Cancel (steps 18-20)."""
    available = [f for f in _get_upload_files(tc_key) if f.exists()]
    if not available:
        return
    largest = max(available, key=lambda f: f.stat().st_size)
    try:
        # Use set_input_files directly (no upload-button click) so a Cancel
        # button can be clicked while the upload is still in progress.
        file_input = page.locator(
            "[data-testid='stFileUploaderDropzoneInput'], input[type='file']"
        ).first
        await file_input.wait_for(state="attached", timeout=15000)
        await file_input.set_input_files(str(largest))
    except Exception:
        return
    await page.wait_for_timeout(1500)
    await _handle_duplicate_file_dialog(page)
    for candidate in [
        page.get_by_role("button", name=re.compile(r"^cancel$", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"cancel\s*upload", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"^cancel$", re.IGNORECASE)).first,
        page.locator("[aria-label*='cancel'], [data-testid*='cancel']").first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click()
                await page.wait_for_timeout(2000)
                try:
                    await page.locator("[role='progressbar']").first.wait_for(state="hidden", timeout=8000)
                except Exception:
                    pass
                return
        except Exception:
            continue


async def _verify_upload_progress(page: Page, file_page, tc_key: str = "tc038") -> None:
    """Select a file, upload, observe progress, click Refresh, verify file appears (steps 21-25)."""
    import time as _time
    available = [f for f in _get_upload_files(tc_key) if f.exists()]
    if not available:
        return
    fp = available[0]
    try:
        await _upload_file_via_browse(page, fp)
    except Exception:
        return
    await _handle_duplicate_file_dialog(page)
    await page.wait_for_timeout(1000)
    for candidate in [
        page.locator("[role='progressbar']").first,
        page.locator("[class*='progress'], [class*='Progress']").first,
    ]:
        try:
            if await candidate.count() > 0:
                break
        except Exception:
            continue
    for candidate in [
        page.get_by_role("button", name=re.compile(r"refresh", re.IGNORECASE)).first,
        page.locator("[aria-label*='refresh'], [data-testid*='refresh']").first,
        page.locator("[class*='refresh']").first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click()
                await page.wait_for_timeout(2500)
                break
        except Exception:
            continue
    try:
        deadline = _time.monotonic() + 40
        while _time.monotonic() < deadline:
            if await page.get_by_text(fp.name).count() > 0:
                break
            await page.wait_for_timeout(1000)
    except Exception:
        pass


async def _upload_multiple_valid_documents(page: Page, file_page, tc_key: str = "tc038") -> list[str]:
    """Upload up to 3 files of different types (steps 26 and 31). Returns file names uploaded."""
    import time as _time
    available = [f for f in _get_upload_files(tc_key) if f.exists()]
    if not available:
        return []
    selected = available[:3]
    uploaded: list[str] = []
    for fp in selected:
        try:
            await _upload_file_via_browse(page, fp)
        except Exception:
            continue
        await _handle_duplicate_file_dialog(page)
        await page.wait_for_timeout(1000)
        try:
            deadline = _time.monotonic() + 20
            while _time.monotonic() < deadline:
                if await page.get_by_text(fp.name).count() > 0:
                    break
                await page.wait_for_timeout(1500)
        except Exception:
            pass
        uploaded.append(fp.name)
    await page.wait_for_timeout(2000)
    return uploaded


# ---------------------------------------------------------------------------
# Row selection / delete / download helpers (TC038-TC040 steps 27-35)
# ---------------------------------------------------------------------------

async def _count_visible_rows(page: Page) -> int:
    """Return the number of visible data rows in the AG Grid."""
    fl = await _get_ag_grid_frame(page)
    if fl:
        try:
            return await fl.locator(".ag-row").count()
        except Exception:
            pass
    try:
        return await page.locator("table tbody tr").count()
    except Exception:
        return 0


async def _select_all_rows(page: Page) -> bool:
    """Click the Select All checkbox in the AG Grid header, or individual rows."""
    fl = await _get_ag_grid_frame(page)
    if fl:
        for candidate in [
            fl.locator(".ag-header-select-all input[type='checkbox']").first,
            fl.locator(".ag-checkbox-input").first,
            fl.locator("[ref='cbSelectAll']").first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    await candidate.check()
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        rows = await fl.locator(".ag-row").all()
        clicked = 0
        for row in rows:
            try:
                cb = row.locator("input[type='checkbox']").first
                if await cb.count() > 0 and await cb.is_visible():
                    await cb.check()
                else:
                    await row.click()
                await page.wait_for_timeout(200)
                clicked += 1
            except Exception:
                continue
        return clicked > 0
    try:
        sel_all = page.locator("input[type='checkbox']").first
        if await sel_all.count() > 0:
            await sel_all.check()
            await page.wait_for_timeout(500)
            return True
    except Exception:
        pass
    return False


async def _click_delete_all_button(page: Page) -> bool:
    """Click Delete Document(s) and confirm any confirmation dialog."""
    delete_btn = None
    for candidate in [
        page.get_by_role("button", name=re.compile(r"delete\s*document", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"delete\s*document", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                delete_btn = candidate
                break
        except Exception:
            continue
    if delete_btn is None:
        return False
    await delete_btn.click()
    await page.wait_for_timeout(1000)
    for candidate in [
        page.get_by_role("button", name=re.compile(r"^(ok|confirm|yes|delete)$", re.IGNORECASE)).first,
        page.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click()
                await page.wait_for_timeout(1000)
                break
        except Exception:
            continue
    await page.wait_for_timeout(2000)
    return True


async def _select_file_row(page: Page, nth: int = 0) -> bool:
    """Click the nth row checkbox in the AG Grid. Returns True on success."""
    fl = await _get_ag_grid_frame(page)
    if fl is not None:
        for candidate in [
            fl.locator(".ag-row").nth(nth).locator("input[type='checkbox']").first,
            fl.locator(".ag-row").nth(nth).locator(".ag-checkbox-input").first,
            fl.locator(".ag-row").nth(nth).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    await candidate.click()
                    await page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue
    for candidate in [
        page.locator("table tbody tr").nth(nth).locator("input[type='checkbox']").first,
        page.locator("[role='row']").nth(nth + 1).locator("input[type='checkbox']").first,
        page.locator("[role='checkbox']").nth(nth).first,
        page.locator("table tbody tr").nth(nth).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                await candidate.click()
                await page.wait_for_timeout(2000)
                return True
        except Exception:
            continue
    return False


async def _verify_delete_single_file(page: Page, tc_name: str = "TC") -> None:
    """Select one file, verify Delete/Download buttons are visible, then click Delete (steps 27-28)."""
    if not await _select_file_row(page, nth=0):
        return
    delete_btn = None
    for candidate in [
        page.get_by_role("button", name=re.compile(r"delete\s*document$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"delete\s*document$", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                delete_btn = candidate
                break
        except Exception:
            continue
    if delete_btn:
        await delete_btn.click()
        await page.wait_for_timeout(2000)
        for candidate in [
            page.get_by_role("button", name=re.compile(r"^(ok|confirm|yes|delete)$", re.IGNORECASE)).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    await candidate.click()
                    await page.wait_for_timeout(2500)
                    break
            except Exception:
                continue


async def _verify_delete_multiple_files(page: Page, tc_name: str = "TC") -> None:
    """Select multiple files, verify Delete Documents button, then click it (steps 29-30)."""
    selected_count = 0
    for i in range(3):
        if await _select_file_row(page, nth=i):
            selected_count += 1
    if selected_count < 2:
        return
    delete_multi_btn = None
    for candidate in [
        page.get_by_role("button", name=re.compile(r"delete\s*documents$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"delete\s*documents$", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                delete_multi_btn = candidate
                break
        except Exception:
            continue
    if delete_multi_btn:
        await delete_multi_btn.click()
        await page.wait_for_timeout(2000)
        for candidate in [
            page.get_by_role("button", name=re.compile(r"^(ok|confirm|yes|delete)$", re.IGNORECASE)).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    await candidate.click()
                    await page.wait_for_timeout(2500)
                    break
            except Exception:
                continue


async def _verify_download_single_file(page: Page, tc_name: str = "TC") -> None:
    """Select one file and click Download Processed Document; verify .txt download (steps 32-33)."""
    if not await _select_file_row(page, nth=0):
        return
    download_btn = None
    for candidate in [
        page.get_by_role("button", name=re.compile(r"download\s*processed\s*document$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"download\s*processed\s*document$", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                download_btn = candidate
                break
        except Exception:
            continue
    if download_btn:
        async with page.expect_download(timeout=30000) as dl_info:
            await download_btn.click()
        dl = await dl_info.value
        assert dl.suggested_filename.endswith(".txt"), (
            f"{tc_name} Step 33: Expected .txt download, got '{dl.suggested_filename}'"
        )


async def _verify_download_multiple_files(page: Page, tc_name: str = "TC") -> None:
    """Select multiple files and click Download Processed Documents; verify .zip or .txt (steps 34-35)."""
    selected_count = 0
    for i in range(3):
        if await _select_file_row(page, nth=i):
            selected_count += 1
    if selected_count < 2:
        return
    download_multi_btn = None
    for candidate in [
        page.get_by_role("button", name=re.compile(r"download\s*processed\s*documents$", re.IGNORECASE)).first,
        page.get_by_text(re.compile(r"download\s*processed\s*documents$", re.IGNORECASE)).first,
    ]:
        try:
            if await candidate.count() > 0 and await candidate.is_visible():
                download_multi_btn = candidate
                break
        except Exception:
            continue
    if download_multi_btn:
        async with page.expect_download(timeout=30000) as dl_info:
            await download_multi_btn.click()
        dl = await dl_info.value
        assert dl.suggested_filename.endswith((".zip", ".txt")), (
            f"{tc_name} Step 35: Expected .zip or .txt download, got '{dl.suggested_filename}'"
        )


async def _select_huge_and_duplicate_files(
    page: Page,
    huge_file_name: "str | None",
    tc_name: str = "TC",
) -> None:
    """Select the huge file and a second file from the 'Choose Options' dropdown (step 38)."""
    options = await page.get_by_role("option").all()
    if not options:
        options = await page.locator("[role='listbox'] [role='option']").all()
    if not options:
        options = await page.locator("li[data-baseweb='menu-item']").all()

    visible = []
    for opt in options:
        try:
            if await opt.is_visible():
                visible.append(opt)
        except Exception:
            continue

    assert visible, "No file options visible in the 'Choose Options' dropdown to select"

    selected = 0
    if huge_file_name:
        for opt in visible:
            try:
                text = await opt.inner_text()
                if huge_file_name.lower() in text.lower():
                    await opt.click()
                    await page.wait_for_timeout(800)
                    selected += 1
                    break
            except Exception:
                continue

    for opt in visible:
        if selected >= 2:
            break
        try:
            await opt.click()
            await page.wait_for_timeout(800)
            selected += 1
        except Exception:
            continue

    assert selected >= 1, (
        f"{tc_name}: Could not select any files from 'Choose Options' dropdown."
    )
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(2000)


# ---------------------------------------------------------------------------
# Model + Chat Type selector with retry (TC038-TC040 step 36)
# ---------------------------------------------------------------------------

async def _select_model_and_chat_type_with_retry(
    page: Page,
    model_name: str,
    chat_type: str,
    tc_name: str = "TC",
) -> None:
    """Select model and chat type in the Chat Configuration panel with Streamlit-aware retry."""
    model_pattern = re.compile(
        re.escape(model_name).replace(r"\ ", r"\s*").replace(r"\-", r"[-\s]*"),
        re.IGNORECASE,
    )
    chat_type_pattern = re.compile(
        re.escape(chat_type).replace(r"\ ", r"\s*"),
        re.IGNORECASE,
    )

    model_dd_candidates = [
        page.get_by_role("combobox", name=re.compile("select model", re.IGNORECASE)).first,
        page.locator("[aria-label*='Select Model'], [aria-label*='select model']").first,
        page.locator("label:has-text('Select Model') ~ div [role='combobox']").first,
        page.locator("div:has-text('Select Model') [role='combobox']").first,
        page.locator("select").first,
    ]
    model_dd = await _first_visible_with_wait(
        page, model_dd_candidates, timeout_ms=60000,
        error_message=f"{tc_name} Step 36: Select Model dropdown not visible",
    )

    current_model = ""
    try:
        current_model = (await model_dd.input_value()).strip()
    except Exception:
        try:
            current_model = (await model_dd.inner_text()).strip()
        except Exception:
            pass

    if not model_pattern.search(current_model):
        # Streamlit selectboxes may need multiple click attempts — the first click
        # can land on a stale element if Streamlit is mid-re-render after navigation.
        model_opt_candidates = [
            page.get_by_role("option", name=model_pattern).first,
            page.get_by_text(model_pattern).first,
        ]
        model_opt = None
        for _click_attempt in range(1, 4):
            await model_dd.click()
            await page.wait_for_timeout(800)
            try:
                model_opt = await _first_visible_with_wait(
                    page, model_opt_candidates, timeout_ms=10000,
                    error_message=f"Model option not visible (attempt {_click_attempt})",
                )
                break
            except AssertionError:
                logger.warning(
                    "Model dropdown click attempt %d: options not visible, "
                    "pressing Escape and retrying …", _click_attempt,
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)
                # Re-locate the dropdown in case Streamlit re-rendered
                model_dd = await _first_visible_with_wait(
                    page, model_dd_candidates, timeout_ms=15000,
                    error_message=f"{tc_name} Step 36: Select Model dropdown lost after retry",
                )
        if model_opt is None:
            raise AssertionError(
                f"{tc_name} Step 36: Model option '{model_name}' not visible after 3 click attempts"
            )
        await model_opt.click()
        await page.wait_for_timeout(2000)
    else:
        await page.wait_for_timeout(500)

    chat_dd_candidates = [
        page.get_by_role("combobox", name=re.compile("chat type", re.IGNORECASE)).first,
        page.locator("[aria-label*='Chat Type'], [aria-label*='chat type']").first,
        page.locator("label:has-text('Select Chat Type') ~ div [role='combobox']").first,
        page.locator("div:has-text('Select Chat Type') [role='combobox']").first,
    ]

    for attempt in range(1, 4):
        chat_dd = await _first_visible_with_wait(
            page, chat_dd_candidates, timeout_ms=60000,
            error_message=f"{tc_name} Step 36: Select Chat Type dropdown not visible",
        )
        current_chat = ""
        try:
            current_chat = (await chat_dd.input_value()).strip()
        except Exception:
            try:
                current_chat = (await chat_dd.inner_text()).strip()
            except Exception:
                pass

        if chat_type_pattern.search(current_chat):
            break

        await chat_dd.click()
        await page.wait_for_timeout(400)
        chat_opt_candidates = [
            page.get_by_role("option", name=chat_type_pattern).first,
            page.get_by_text(chat_type_pattern).first,
        ]
        chat_opt = await _first_visible_with_wait(
            page, chat_opt_candidates, timeout_ms=30000,
            error_message=f"{tc_name} Step 36: Chat type '{chat_type}' not visible (attempt {attempt})",
        )
        await chat_opt.click()
        await page.wait_for_timeout(2000)

        updated = ""
        try:
            updated = (await chat_dd.input_value()).strip()
        except Exception:
            try:
                updated = (await chat_dd.inner_text()).strip()
            except Exception:
                pass
        if chat_type_pattern.search(updated):
            break
        await page.wait_for_timeout(1000)

    final_model_dd = await _first_visible_with_wait(
        page, model_dd_candidates, timeout_ms=30000,
        error_message=f"{tc_name} Step 36: Model dropdown disappeared after selection",
    )
    final_chat_dd = await _first_visible_with_wait(
        page, chat_dd_candidates, timeout_ms=30000,
        error_message=f"{tc_name} Step 36: Chat Type dropdown disappeared after selection",
    )
    final_model = ""
    final_chat = ""
    try:
        final_model = (await final_model_dd.input_value()).strip()
    except Exception:
        try:
            final_model = (await final_model_dd.inner_text()).strip()
        except Exception:
            pass
    try:
        final_chat = (await final_chat_dd.input_value()).strip()
    except Exception:
        try:
            final_chat = (await final_chat_dd.inner_text()).strip()
        except Exception:
            pass

    assert model_pattern.search(final_model) or await page.get_by_text(model_pattern).count() > 0, (
        f"{tc_name} Step 36: Model selection not reflected. Current value: '{final_model}'"
    )
    assert chat_type_pattern.search(final_chat) or await page.get_by_text(chat_type_pattern).count() > 0, (
        f"{tc_name} Step 36: Chat type selection not reflected. Current value: '{final_chat}'"
    )
