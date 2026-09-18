from __future__ import annotations

import uuid

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type


TEST_CASE_NAME = "Document_Management_TC002_API_Functional_GET_GetCleanedDocumentTexts"
TEST_CASE_DESCRIPTION = (
    "Verify the Document Management - GET Request (Get Cleaned Document Texts) "
    "returns a successful response and validate error status codes (400, 401, 403, 404, 405)."
)
ENDPOINT = "/docu_chat/v1/get_cleaned_text/"

# Valid document ID that exists in the INT environment for the authenticated user.
VALID_DOC_ID = "f86e242b-add7-4095-85e5-af5fdb7830c2"


# ─── Happy Path ───────────────────────────────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_cleaned_texts_success(api_client: ApiClient) -> None:
    """Verify the GET /docu_chat/v1/get_cleaned_text/ endpoint returns 200 OK with a valid doc_id."""
    response = api_client.get(
        ENDPOINT,
        params={"doc_id": VALID_DOC_ID},
        expected_status=200,
    )

    assert response.status_code == 200


# ─── Verify Status Code 400 — Bad Request ────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_cleaned_texts_400_bad_request(api_client: ApiClient) -> None:
    """Verify 400 Bad Request when the query parameter key is invalid or missing."""
    # Send request with an invalid query parameter key instead of doc_id
    response = api_client.get(
        ENDPOINT,
        params={"invalid_key": "some-value"},
        expected_status=400,
    )

    assert response.status_code == 400


# ─── Verify Status Code 401 — Unauthorized ───────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_cleaned_texts_401_unauthorized(api_client: ApiClient) -> None:
    """Verify 401 Unauthorized when the Cs-Client-Principal header is removed."""
    response = api_client.get(
        ENDPOINT,
        params={"doc_id": VALID_DOC_ID},
        headers={"Cs-Client-Principal": "", "Authorization": ""},
        expected_status=401,
    )

    assert response.status_code == 401


# ─── Verify Status Code 403 — Forbidden ──────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_cleaned_texts_403_forbidden(api_client: ApiClient) -> None:
    """Verify 403 Forbidden when a user without DocuChat access calls the endpoint."""
    # Use a principal that does not have DocuChat group membership
    unauthorized_principal = (
        "eyJhdXRoX3R5cCI6Im9rdGEiLCJjbGFpbXMiOltdLCJuYW1lX3R5cCI6Im5hbWUiLCJyb2xlX3R5cCI6InJvbGUifQ=="
    )

    response = api_client.get(
        ENDPOINT,
        params={"doc_id": VALID_DOC_ID},
        headers={"Cs-Client-Principal": unauthorized_principal},
        expected_status=403,
    )

    assert response.status_code == 403


# ─── Verify Status Code 404 — Not Found ──────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_cleaned_texts_404_not_found(api_client: ApiClient) -> None:
    """Verify 404 Not Found when the doc_id does not exist in the database."""
    non_existent_doc_id = str(uuid.uuid4())

    response = api_client.get(
        ENDPOINT,
        params={"doc_id": non_existent_doc_id},
        expected_status=404,
    )

    assert response.status_code == 404


# ─── Verify Status Code 405 — Method Not Allowed ─────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_cleaned_texts_405_method_not_allowed(api_client: ApiClient) -> None:
    """Verify 405 Method Not Allowed when using POST instead of GET."""
    response = api_client.post(
        ENDPOINT,
        json={"doc_id": VALID_DOC_ID},
        expected_status=405,
    )

    assert response.status_code == 405
