"""File Management test helpers (subset) — contains only the four helpers needed
for cross-module imports:

    _navigate_to_file_management
    _upload_and_verify_tolerant
    _cleanup_delete_uploaded_file
    _wait_for_file_ready_status
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal utilities
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


# ---------------------------------------------------------------------------
# Upload internals (required by _upload_and_verify_tolerant)
# ---------------------------------------------------------------------------

async def _upload_file_via_browse(page: Page, file_path: Path) -> None:
    """Upload a single file via the Browse Files button."""
    _FILE_INPUT_SELECTOR = "input[type='file']"

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

    try:
        await file_input.wait_for(state="detached", timeout=5000)
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


async def _verify_file_in_uploaded_list(
    page: Page,
    file_name: str,
    timeout_ms: int = 60000,
) -> None:
    """Poll until ``file_name`` appears in the uploaded files list."""
    stem = Path(file_name).stem
    ext = Path(file_name).suffix
    name_pattern = (
        re.compile(re.escape(stem) + r".*" + re.escape(ext), re.IGNORECASE)
        if ext
        else re.compile(re.escape(stem), re.IGNORECASE)
    )

    file_row_candidates = [
        page.get_by_text(re.compile(re.escape(file_name), re.IGNORECASE)).first,
        page.get_by_text(name_pattern).first,
        page.locator(f"[data-testid='file-row']:has-text('{stem}')").first,
        page.locator(f"table tbody tr:has-text('{stem}')").first,
    ]
    await _first_visible_with_wait(
        page,
        file_row_candidates,
        timeout_ms=timeout_ms,
        error_message=f"Uploaded file '{file_name}' not found in the file list after {timeout_ms // 1000}s",
    )


async def _upload_and_verify(page: Page, file_path: Path) -> None:
    """Upload a file via Browse Files and verify it appears in the uploaded list."""
    await _upload_file_via_browse(page, file_path)
    await _verify_file_in_uploaded_list(page, file_path.name, timeout_ms=90000)
    logger.info("Uploaded and verified: %s", file_path.name)


async def _upload_file_via_drag_drop(page: Page, file_path: Path) -> None:
    """Upload a single file via the drag-and-drop zone using JS DataTransfer injection."""
    import base64
    import mimetypes

    file_bytes = file_path.read_bytes()
    b64 = base64.b64encode(file_bytes).decode("ascii")
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_name = file_path.name

    dropzone_selectors = [
        "[data-testid='stFileUploaderDropzone']",
        "[data-testid='stFileUploaderDropzoneInstructions']",
        "div.uploadedFileData",
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
    await _verify_file_in_uploaded_list(page, file_path.name, timeout_ms=90000)
    logger.info("Uploaded and verified (drag-drop): %s", file_path.name)


# ---------------------------------------------------------------------------
# Public helpers
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


async def _cleanup_delete_uploaded_file(page: Page, file_name: str) -> None:
    """Cleanup helper — navigate to File Management, find the row for ``file_name``,
    select it, click 'Delete Document', and confirm the deletion dialog.

    All errors are caught and logged as warnings so the test outcome is not
    affected if cleanup fails.
    """
    try:
        await _navigate_to_file_management(page)
        await page.wait_for_timeout(2000)
    except Exception as exc:
        logger.warning(
            "_cleanup_delete_uploaded_file: could not navigate to File Management — %s", exc
        )
        return

    stem = Path(file_name).stem
    name_pattern = re.compile(re.escape(stem), re.IGNORECASE)
    row_selected = False

    fl = await _get_ag_grid_frame(page)
    if fl is not None:
        row_candidate = fl.locator(".ag-row").filter(has_text=name_pattern).first
        try:
            if await row_candidate.count() > 0 and await row_candidate.is_visible():
                cb = row_candidate.locator("input[type='checkbox']").first
                if await cb.count() > 0 and await cb.is_visible():
                    await cb.check()
                else:
                    await row_candidate.click()
                await page.wait_for_timeout(1000)
                row_selected = True
        except Exception:
            pass

    if not row_selected:
        for candidate in [
            page.locator("table tbody tr").filter(has_text=name_pattern).first,
            page.locator("[role='row']").filter(has_text=name_pattern).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    cb = candidate.locator("input[type='checkbox']").first
                    if await cb.count() > 0 and await cb.is_visible():
                        await cb.check()
                    else:
                        await candidate.click()
                    await page.wait_for_timeout(1000)
                    row_selected = True
                    break
            except Exception:
                continue

    if not row_selected:
        logger.warning(
            "_cleanup_delete_uploaded_file: row for '%s' not found in File Management — skipping.",
            file_name,
        )
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

    if delete_btn is None:
        logger.warning(
            "_cleanup_delete_uploaded_file: 'Delete Document' button not visible after selecting '%s'.",
            file_name,
        )
        return

    try:
        await delete_btn.click()
        await page.wait_for_timeout(1500)
        for candidate in [
            page.get_by_role("button", name=re.compile(r"^(ok|confirm|yes|delete)$", re.IGNORECASE)).first,
            page.get_by_role("button", name=re.compile(r"delete", re.IGNORECASE)).first,
        ]:
            try:
                if await candidate.count() > 0 and await candidate.is_visible():
                    await candidate.click()
                    await page.wait_for_timeout(2500)
                    break
            except Exception:
                continue
        logger.info("_cleanup_delete_uploaded_file: deleted '%s' from File Management.", file_name)
    except Exception as exc:
        logger.warning(
            "_cleanup_delete_uploaded_file: error during delete of '%s' — %s",
            file_name, exc,
        )
