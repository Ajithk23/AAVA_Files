from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from playwright.async_api import Page

from api.client import ApiClient
from tests.web.regression.file_Management.file_management_test_helpers import (
    _navigate_to_file_management,
    _upload_and_verify,
    _wait_for_file_ready_status,
)
from utils.db_client import PostgresClient, PostgresConfig


TEST_CASE_NAME = "Document_Management_TC001_API_Functional_POST_DeleteDocuments"
TEST_CASE_DESCRIPTION = (
    "Upload a document via UI, capture doc_id from the network response or AG Grid "
    "row-id, verify DB entry (deleted=False, deleted_at=NULL), call POST "
    "/docu_chat/v1/delete_file/, then confirm the DB row is soft-deleted "
    "(deleted=True, deleted_at set)."
)
ENDPOINT = "/docu_chat/v1/delete_file/"

# Sample file uploaded via the UI during the test.
UPLOAD_FILE = Path(__file__).parents[4] / "test_data" / "sample_files" / "test_upload.txt"

# DB query used for pre- and post-delete verification.
_DB_CHECK_BY_ID = (
    "SELECT deleted, deleted_at "
    "FROM docu_chat_docs WHERE doc_id = %s"
)

# Anchored pattern — used to validate a candidate is a full UUID.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
# Search pattern — finds a UUID anywhere inside a larger string.
_UUID_SEARCH_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _get_csrf_token(api_client: ApiClient) -> str:
    """Obtain CSRF token by making a GET request to seed the csrftoken cookie."""
    api_client.get(ENDPOINT, expected_status=None)
    return api_client.session.cookies.get("csrftoken", "")


def _get_db_client(env: str) -> PostgresClient:
    """Build a PostgresClient using ``{ENV}_PG*`` environment variables.

    The prefix is derived from the ``--env`` flag at runtime:
      --env=int  →  INT_PGHOST, INT_PGPORT, INT_PGDATABASE, INT_PGUSER, INT_PGPASSWORD
      --env=crt  →  CRT_PGHOST, CRT_PGPORT, CRT_PGDATABASE, CRT_PGUSER, CRT_PGPASSWORD
    """
    prefix = env.upper()
    try:
        config = PostgresConfig(
            host=os.environ[f"{prefix}_PGHOST"],
            port=int(os.environ[f"{prefix}_PGPORT"]),
            database=os.environ[f"{prefix}_PGDATABASE"],
            user=os.environ[f"{prefix}_PGUSER"],
            password=os.environ[f"{prefix}_PGPASSWORD"],
            sslmode=os.environ.get(f"{prefix}_PGSSLMODE", "require"),
        )
    except KeyError as exc:
        raise EnvironmentError(
            f"Missing DB environment variable {exc} for --env={env}. "
            f"Set {prefix}_PGHOST, {prefix}_PGPORT, {prefix}_PGDATABASE, "
            f"{prefix}_PGUSER, and {prefix}_PGPASSWORD before running."
        ) from exc
    return PostgresClient(config)


async def _extract_doc_id_from_ag_grid(page: Page, file_stem: str) -> str | None:
    """Search the full inner HTML of the matching AG Grid row for any UUID.

    This covers hidden columns, data-* attributes, title attributes, and any
    other place AG Grid may embed the doc_id in the rendered row markup.
    """
    for iframe_sel in ["iframe[src*='agGrid']", "iframe[src*='st_aggrid']", "iframe"]:
        try:
            fl = page.frame_locator(iframe_sel)
            if await fl.locator(".ag-header").count() == 0:
                continue
            row = fl.locator(".ag-row").filter(
                has_text=re.compile(re.escape(file_stem), re.IGNORECASE)
            ).first
            if await row.count() == 0:
                continue
            html = await row.inner_html()
            uuids = _UUID_SEARCH_RE.findall(html)
            if uuids:
                return uuids[0]
        except Exception:
            continue
    return None


# ─── Happy Path ───────────────────────────────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
async def test_delete_documents_success(docuchat_context: dict, api_client: ApiClient) -> None:
    """Upload via UI → capture doc_id → pre-check DB → delete via API → post-check DB."""
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]

    # ── Step 1: Upload file via UI ────────────────────────────────────────────
    # Delete any pre-existing copy of the file to avoid duplicate-file popups on rerun.
    # Capture doc_id via three parallel strategies:
    #   A) HTTP response interception
    #   B) WebSocket frame interception (Streamlit's primary data channel)
    #   C) AG Grid row inner_html search (after Ready state)
    captured_ids: list[str] = []
    ws_doc_ids: list[str] = []

    # Strategy B: WebSocket — only consider frames that mention the uploaded filename
    # so we don't confuse session UUIDs with the doc_id.
    def _on_ws(ws) -> None:
        def _on_frame(payload) -> None:
            text = (
                payload
                if isinstance(payload, str)
                else payload.decode("utf-8", errors="replace")
            )
            if UPLOAD_FILE.stem.lower() in text.lower():
                for uid in _UUID_SEARCH_RE.findall(text):
                    ws_doc_ids.append(uid)
        ws.on("framereceived", _on_frame)

    page.on("websocket", _on_ws)

    async def _on_response(response) -> None:
        if response.status not in (200, 201):
            return
        try:
            body = await response.json()
        except Exception:
            return
        # Check top-level dict keys
        if isinstance(body, dict):
            for key in ("doc_id", "id", "document_id", "file_id", "uuid"):
                val = body.get(key)
                if isinstance(val, str) and _UUID_RE.match(val):
                    captured_ids.append(val)
                    return
            # Check one level nested (e.g. {"file": {"doc_id": "..."}})
            for nested in body.values():
                if isinstance(nested, dict):
                    for key in ("doc_id", "id", "document_id"):
                        val = nested.get(key)
                        if isinstance(val, str) and _UUID_RE.match(val):
                            captured_ids.append(val)
                            return
        # Check list of objects
        elif isinstance(body, list):
            for item in body:
                if isinstance(item, dict):
                    for key in ("doc_id", "id", "document_id"):
                        val = item.get(key)
                        if isinstance(val, str) and _UUID_RE.match(val):
                            captured_ids.append(val)
                            return

    await page.goto(str(settings["base_url"]))

    # INT uses 2-factor authentication — wait up to 3 minutes for the SSO/2FA
    # redirect to complete before attempting any app navigation.
    await page.wait_for_url(
        re.compile(r"caresource\.corp"),
        timeout=180_000,
    )

    await _navigate_to_file_management(page)

    page.on("response", _on_response)
    try:
        await _upload_and_verify(page, UPLOAD_FILE)
        await _wait_for_file_ready_status(page, UPLOAD_FILE.name)
    finally:
        page.remove_listener("response", _on_response)
        page.remove_listener("websocket", _on_ws)

    # ── Step 2: Extract doc_id from UI ───────────────────────────────────────
    # A) HTTP response
    if captured_ids:
        doc_id: str = captured_ids[0]
    # B) AG Grid row inner_html (searches all attributes, hidden cols, data-* attrs)
    elif ag_id := await _extract_doc_id_from_ag_grid(page, UPLOAD_FILE.stem):
        doc_id = ag_id
    # C) WebSocket frames that mentioned the filename
    elif ws_doc_ids:
        doc_id = ws_doc_ids[0]
    else:
        doc_id = ""

    assert doc_id, (
        f"Could not extract doc_id from UI for '{UPLOAD_FILE.name}'. "
        "HTTP responses, AG Grid row HTML, and WebSocket frames (filtered by filename) "
        "all contained no valid UUID. Inspect the browser network/WS tab to identify "
        "where the doc_id is exposed."
    )

    # ── Step 3: Pre-delete DB check ───────────────────────────────────────────
    db = _get_db_client(settings["environment"])
    pre_row = db.fetch_one(_DB_CHECK_BY_ID, (doc_id,))
    assert pre_row is not None, (
        f"No row found in docu_chat_docs for doc_id={doc_id}"
    )
    assert pre_row["deleted"] is False, (
        f"Expected deleted=False before deletion, got {pre_row['deleted']!r} for doc_id={doc_id}"
    )
    assert pre_row["deleted_at"] is None, (
        f"Expected deleted_at=NULL before deletion, got {pre_row['deleted_at']!r} for doc_id={doc_id}"
    )

    # ── Step 3: Delete via API ────────────────────────────────────────────────
    csrf_token = _get_csrf_token(api_client)
    response = api_client.post(
        ENDPOINT,
        json={"doc_ids": [doc_id]},
        headers={"X-CSRFToken": csrf_token},
        expected_status=200,
    )
    assert response.status_code == 200

    # ── Step 5: Post-delete DB check ──────────────────────────────────────────
    post_row = db.fetch_one(_DB_CHECK_BY_ID, (doc_id,))
    assert post_row is not None, (
        f"Row disappeared from docu_chat_docs for doc_id={doc_id}"
    )
    assert post_row["deleted"] is True, (
        f"Expected deleted=True after deletion, got {post_row['deleted']!r} for doc_id={doc_id}"
    )
    assert post_row["deleted_at"] is not None, (
        f"Expected deleted_at to be set after deletion, got None for doc_id={doc_id}"
    )
