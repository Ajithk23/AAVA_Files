from __future__ import annotations

import base64
import os

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type
from utils.db_client import PostgresClient, PostgresConfig


TEST_CASE_NAME = "Document_OCR_TC002_API_Enterprise_POST_ProcessDocumentsOCR"
TEST_CASE_DESCRIPTION = (
    "Processes a document using specified OCR engines. "
    "Accepts a base64-encoded file, file type, and list of OCR engines. "
    "Returns a tracking identifier for asynchronous processing."
)
ENDPOINT = "/enterprise/ocr/v1/jobs/"
ENGINES_ENDPOINT = "/enterprise/ocr/v1/engines/"

SAMPLE_FILE_CONTENT = base64.b64encode(b"Hello World").decode("utf-8")
SAMPLE_FILE_TYPE = "txt"

DB_QUERY = (
    "SELECT id, status, file_type, ocr_engines "
    "FROM enterprise_ocr_response WHERE id = %s"
)


def _get_csrf_token(api_client: ApiClient) -> str:
    """Obtain CSRF token by making a GET request to seed the csrftoken cookie."""
    api_client.get(ENDPOINT, expected_status=None)
    csrf_token = api_client.session.cookies.get("csrftoken", "")
    return csrf_token


def _get_db_client() -> PostgresClient:
    """Build a PostgresClient from INT_PG* environment variables."""
    config = PostgresConfig(
        host=os.environ["INT_PGHOST"],
        port=int(os.environ["INT_PGPORT"]),
        database=os.environ["INT_PGDATABASE"],
        user=os.environ["INT_PGUSER"],
        password=os.environ["INT_PGPASSWORD"],
        sslmode=os.environ.get("INT_PGSSLMODE", "require"),
    )
    return PostgresClient(config)


@pytest.mark.api
@pytest.mark.api_integration
def test_process_documents_with_ocr_success(api_client: ApiClient) -> None:
    """Verify POST /enterprise/ocr/v1/jobs/ returns 202 Accepted for each available OCR engine."""
    # Fetch available engines dynamically from the GET endpoint
    engines_response = api_client.get(ENGINES_ENDPOINT, expected_status=200)
    engines_data = engines_response.json()
    engines = engines_data.get("engines", [])
    assert engines, "No OCR engines returned from GET /enterprise/ocr/v1/engines/"

    csrf_token = _get_csrf_token(api_client)
    db = _get_db_client()

    for engine_entry in engines:
        engine_name, engine_key = engine_entry[0], engine_entry[1]

        # Submit document for OCR processing with this engine
        payload = {
            "file_content": SAMPLE_FILE_CONTENT,
            "file_type": SAMPLE_FILE_TYPE,
            "ocr_engine": engine_key,
        }

        response = api_client.post(
            ENDPOINT,
            json=payload,
            headers={"X-CSRFTOKEN": csrf_token},
            expected_status=202,
        )

        assert response.status_code == 202, (
            f"Expected 202 for engine {engine_name} ({engine_key}), got {response.status_code}"
        )
        assert_json_content_type(response)

        response_body = response.json()
        assert response_body is not None, (
            f"Response body should not be empty for engine {engine_name} ({engine_key})"
        )

        # Verify the record exists in DB using doc_id from response
        doc_id = response_body.get("doc_id")
        assert doc_id is not None, (
            f"Response should contain doc_id for engine {engine_name} ({engine_key})"
        )

        db_record = db.fetch_one(DB_QUERY, (doc_id,))
        assert db_record is not None, (
            f"OCR record with doc_id={doc_id} should exist in DB for engine {engine_name} ({engine_key})"
        )
        assert db_record["id"] is not None, (
            f"Record should have an id for engine {engine_name} ({engine_key})"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=int", "-vv", "-s"]))
