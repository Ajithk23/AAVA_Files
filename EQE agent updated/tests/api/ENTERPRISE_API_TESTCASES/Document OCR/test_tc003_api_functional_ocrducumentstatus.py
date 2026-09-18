from __future__ import annotations

import base64
import os

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type
from utils.db_client import PostgresClient, PostgresConfig


TEST_CASE_NAME = "Document_OCR_TC003_API_Enterprise_GET_OCRDocumentState"
TEST_CASE_DESCRIPTION = (
    "Returns the current processing status and, when completed, "
    "the OCR output for a previously-submitted document. "
    "Creates a document via POST (TC002 flow), then uses the returned doc_id."
)
POST_ENDPOINT = "/enterprise/ocr/v1/jobs/"
ENGINES_ENDPOINT = "/enterprise/ocr/v1/engines/"
GET_ENDPOINT_TEMPLATE = "/enterprise/ocr/v1/jobs/{doc_id}/"

SAMPLE_FILE_CONTENT = base64.b64encode(b"Hello World").decode("utf-8")
SAMPLE_FILE_TYPE = "txt"
SAMPLE_OCR_ENGINE = "PARSE_TEXT"

DB_QUERY = (
    "SELECT id, status, file_type, ocr_engines, output, error_message "
    "FROM enterprise_ocr_response WHERE id = %s"
)


def _get_csrf_token(api_client: ApiClient) -> str:
    """Obtain CSRF token by making a GET request to seed the csrftoken cookie."""
    api_client.get(POST_ENDPOINT, expected_status=None)
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


def _create_ocr_job(api_client: ApiClient, ocr_engine: str) -> str:
    """Submit a document for OCR processing and return the doc_id from the response."""
    csrf_token = _get_csrf_token(api_client)

    payload = {
        "file_content": SAMPLE_FILE_CONTENT,
        "file_type": SAMPLE_FILE_TYPE,
        "ocr_engine": ocr_engine,
    }

    response = api_client.post(
        POST_ENDPOINT,
        json=payload,
        headers={"X-CSRFTOKEN": csrf_token},
        expected_status=202,
    )

    assert response.status_code == 202
    response_body = response.json()
    assert response_body is not None, "POST response body should not be empty"

    # Extract doc_id from the response
    doc_id = response_body.get("doc_id") or response_body.get("id") or response_body.get("job_id")
    assert doc_id is not None, f"Response must contain a doc_id. Got: {response_body}"
    return str(doc_id)


@pytest.mark.api
@pytest.mark.api_integration
def test_get_ocr_document_status_success(api_client: ApiClient) -> None:
    """Create an OCR job via POST, then GET its status and validate against DB."""
    # Step 0: Fetch available engines and select one
    engines_response = api_client.get(ENGINES_ENDPOINT, expected_status=200)
    engines_data = engines_response.json()
    available_engines = [entry[1] for entry in engines_data.get("engines", [])]
    assert available_engines, "No OCR engines available from GET /enterprise/ocr/v1/engines/"

    ocr_engine = SAMPLE_OCR_ENGINE if SAMPLE_OCR_ENGINE in available_engines else available_engines[0]

    # Step 1: Create OCR job and obtain doc_id
    doc_id = _create_ocr_job(api_client, ocr_engine)

    # Step 2: GET the document status using doc_id
    endpoint = GET_ENDPOINT_TEMPLATE.format(doc_id=doc_id)
    response = api_client.get(endpoint, expected_status=200)

    assert response.status_code == 200
    assert_json_content_type(response)

    api_payload = response.json()
    assert api_payload is not None, "Response body should not be empty"

    # Step 3: Validate response against DB record
    db = _get_db_client()
    db_record = db.fetch_one(DB_QUERY, (doc_id,))

    assert db_record is not None, f"DB record not found for doc_id: {doc_id}"
    assert str(db_record["id"]) == doc_id, "DB id should match the doc_id from API"
    assert db_record["file_type"] is not None, "DB file_type should not be null"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=int", "-vv", "-s"]))
