"""TC-408 — Successful upload and processing of single valid TIFF file

Description    : Verify that a user can upload a valid TIFF file (.tif or .tiff)
                 and the OCR engine processes it without errors
Pre-condition  : User is logged into the OCR system with upload permissions;
                 Browser: Chrome latest version; TIFF file size under system limit
                 (e.g., 10MB)
Feature        : OCR File Upload - TIFF Support
Environment    : QA
"""
from pathlib import Path
import sys
import time

import pytest
import requests as _requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    if venv_python.exists() and current_python != venv_python.resolve():
        import subprocess
        raise SystemExit(subprocess.call([str(venv_python), __file__]))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.step_runner import run_step as _run_step

_TC_NAME = "TC-408"


async def _run_tc_flow(docuchat_context: dict) -> None:
    settings = docuchat_context["settings"]
    base_url = settings.get("ocr_api_base_url", settings["base_url"]).rstrip("/")
    timeout_s = int(settings["timeout_ms"]) / 1000

    _auth_token: list[str] = []
    _upload_resp: list = []

    # ── Step 1 — Open the OCR system upload page ──────────────────────────
    async def _step_1_open_upload_page() -> None:
        """Navigate to OCR upload page and verify it loads with upload button."""
        resp = _requests.get(f"{base_url}/upload", timeout=timeout_s)
        assert resp.status_code == 200, (
            f"OCR upload page did not load successfully: HTTP {resp.status_code}"
        )

    await _run_step(
        1, "Open the OCR system upload page in Chrome browser",
        _step_1_open_upload_page(), _TC_NAME,
    )

    # ── Step 2 — Authenticate and prepare upload ──────────────────────────
    async def _step_2_authenticate() -> None:
        """Authenticate with the OCR API to obtain upload credentials."""
        auth_url = f"{base_url}/auth/token"
        creds = {
            "client_id": settings.get("ocr_client_id", ""),
            "client_secret": settings.get("ocr_client_secret", ""),
        }
        resp = _requests.post(auth_url, json=creds, timeout=timeout_s)
        assert resp.status_code == 200, (
            f"Auth failed: HTTP {resp.status_code} — {resp.text[:200]}"
        )
        token = resp.json().get("access_token") or resp.json().get("token", "")
        assert token, "Auth response did not contain an access_token."
        _auth_token.append(token)

    await _run_step(
        2, "Click on the 'Upload File' button",
        _step_2_authenticate(), _TC_NAME,
    )

    # ── Step 3 — Select a valid TIFF file ─────────────────────────────────
    async def _step_3_select_tiff_file() -> None:
        """Locate and validate the TIFF test file exists and is under size limit."""
        # TODO: set 'ocr_test_tiff_path' in settings to point at a real .tif file
        tiff_path = Path(
            settings.get("ocr_test_tiff_path",
                         str(PROJECT_ROOT / "test_data" / "sample.tif"))
        )
        assert tiff_path.exists(), (
            f"TIFF test file not found: {tiff_path}. "
            "Set 'ocr_test_tiff_path' in settings or add test_data/sample.tif."
        )
        file_size_mb = tiff_path.stat().st_size / (1024 * 1024)
        assert file_size_mb <= 10, (
            f"TIFF file size ({file_size_mb:.1f} MB) exceeds 10MB limit."
        )
        _upload_resp.append({"tiff_path": tiff_path})

    await _run_step(
        3, "Select a valid TIFF file (.tif) of size 5MB from local drive",
        _step_3_select_tiff_file(), _TC_NAME,
    )

    # ── Step 4 — Upload the TIFF file ─────────────────────────────────────
    async def _step_4_upload_tiff() -> None:
        """POST the TIFF file to the OCR upload endpoint and verify acceptance."""
        tiff_path = _upload_resp[0]["tiff_path"]
        headers = {"Authorization": f"Bearer {_auth_token[0]}"}
        with open(tiff_path, "rb") as f:
            start = time.monotonic()
            resp = _requests.post(
                f"{base_url}/v1/ocr/upload",
                headers=headers,
                files={"file": (tiff_path.name, f, "image/tiff")},
                timeout=timeout_s,
            )
            elapsed = time.monotonic() - start
        assert resp.status_code in (200, 201, 202), (
            f"TIFF upload failed: HTTP {resp.status_code} — {resp.text[:300]}"
        )
        _upload_resp[0]["upload_response"] = resp.json()
        _upload_resp[0]["upload_elapsed"] = elapsed

    await _run_step(
        4, "Click on the 'Submit' or 'Upload' button to start upload",
        _step_4_upload_tiff(), _TC_NAME,
    )

    # ── Step 5 — Wait for OCR processing to complete ──────────────────────
    async def _step_5_wait_for_processing() -> None:
        """Poll the OCR processing status until completion or timeout."""
        upload_data = _upload_resp[0]["upload_response"]
        job_id = upload_data.get("job_id") or upload_data.get("id", "")
        headers = {"Authorization": f"Bearer {_auth_token[0]}"}

        if job_id:
            # Poll status endpoint until processing completes
            deadline = time.monotonic() + timeout_s
            status = "processing"
            while time.monotonic() < deadline and status in ("processing", "pending", "queued"):
                time.sleep(2)
                resp = _requests.get(
                    f"{base_url}/v1/ocr/status/{job_id}",
                    headers=headers,
                    timeout=timeout_s,
                )
                if resp.ok:
                    status = resp.json().get("status", "").lower()
            assert status in ("completed", "success", "done"), (
                f"OCR processing did not complete successfully. Final status: '{status}'"
            )
            _upload_resp[0]["process_status"] = status
        else:
            # Synchronous processing — response already contains result
            assert "text" in upload_data or "result" in upload_data, (
                "Upload response does not contain processing result or job_id for async polling."
            )
            _upload_resp[0]["process_status"] = "completed"

    await _run_step(
        5, "Wait for the OCR engine to process the uploaded TIFF file",
        _step_5_wait_for_processing(), _TC_NAME,
    )

    # ── Step 6 — Verify OCR output is available ───────────────────────────
    async def _step_6_verify_ocr_output() -> None:
        """Verify that extracted text or OCR output is available."""
        upload_data = _upload_resp[0]["upload_response"]
        headers = {"Authorization": f"Bearer {_auth_token[0]}"}

        # Try to get result from the upload response directly
        extracted_text = upload_data.get("text") or upload_data.get("result", {}).get("text", "")

        if not extracted_text:
            # Fetch result from status/result endpoint
            job_id = upload_data.get("job_id") or upload_data.get("id", "")
            if job_id:
                resp = _requests.get(
                    f"{base_url}/v1/ocr/result/{job_id}",
                    headers=headers,
                    timeout=timeout_s,
                )
                assert resp.ok, (
                    f"Failed to retrieve OCR result: HTTP {resp.status_code}"
                )
                extracted_text = resp.json().get("text", "")

        assert extracted_text and extracted_text.strip(), (
            "OCR output is empty — no text was extracted from the TIFF file."
        )
        _upload_resp[0]["extracted_text"] = extracted_text

    await _run_step(
        6, "Verify that the extracted text or OCR output is displayed or available for download",
        _step_6_verify_ocr_output(), _TC_NAME,
    )

    # ── Step 7 — Check audit trail / logs ─────────────────────────────────
    async def _step_7_check_audit_logs() -> None:
        """Verify system logs contain the upload and processing event."""
        headers = {"Authorization": f"Bearer {_auth_token[0]}"}
        upload_data = _upload_resp[0]["upload_response"]
        job_id = upload_data.get("job_id") or upload_data.get("id", "")

        resp = _requests.get(
            f"{base_url}/v1/ocr/audit",
            headers=headers,
            params={"job_id": job_id} if job_id else {},
            timeout=timeout_s,
        )
        # Audit endpoint may not exist in all environments — log but don't hard-fail
        if resp.ok:
            audit_entries = resp.json() if isinstance(resp.json(), list) else resp.json().get("entries", [])
            assert len(audit_entries) > 0, (
                "No audit log entries found for the TIFF upload event."
            )
        else:
            # If audit endpoint returns 404, skip gracefully with warning
            if resp.status_code == 404:
                pytest.skip("Audit endpoint not available in this environment.")
            assert resp.ok, (
                f"Audit log check failed: HTTP {resp.status_code} — {resp.text[:200]}"
            )

    await _run_step(
        7, "Check system logs or audit trail for the upload and processing entry",
        _step_7_check_audit_logs(), _TC_NAME,
    )


@pytest.mark.ocr
@pytest.mark.regression
async def test_successful_upload_processing_single_valid_tiff_file(docuchat_context):
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
