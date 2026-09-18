from __future__ import annotations

import uuid

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type


TEST_CASE_NAME = "Document_Management_TC003_API_Functional_POST_GetUserFiles"
TEST_CASE_DESCRIPTION = (
    "Verify the Document Management - POST Request (Get User Files) "
    "returns a successful response and validate error status codes (400, 401, 403, 404, 405)."
)
ENDPOINT = "/docu_chat/v1/read_files/"


def _get_csrf_token(api_client: ApiClient) -> str:
    """Obtain CSRF token by making a GET request to seed the csrftoken cookie."""
    api_client.get(ENDPOINT, expected_status=None)
    csrf_token = api_client.session.cookies.get("csrftoken", "")
    return csrf_token


# ─── Happy Path ───────────────────────────────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_user_files_success(api_client: ApiClient) -> None:
    """Verify the POST /docu_chat/v1/read_files/ endpoint returns 200 OK."""
    csrf_token = _get_csrf_token(api_client)

    response = api_client.post(
        ENDPOINT,
        json={},
        headers={"X-CSRFToken": csrf_token},
        expected_status=200,
    )

    assert response.status_code == 200


# ─── Verify Status Code 400 — Bad Request ────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_user_files_400_bad_request(api_client: ApiClient) -> None:
    """Verify 400 Bad Request when the payload has an invalid key/structure."""
    csrf_token = _get_csrf_token(api_client)
    # Send a malformed payload with an invalid key
    malformed_payload = {"invalid_key": "some-value"}

    response = api_client.post(
        ENDPOINT,
        json=malformed_payload,
        headers={"X-CSRFToken": csrf_token},
        expected_status=400,
    )

    assert response.status_code == 400


# ─── Verify Status Code 401 — Unauthorized ───────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_user_files_401_unauthorized(api_client: ApiClient) -> None:
    """Verify 401 Unauthorized when the Cs-Client-Principal header is removed."""
    response = api_client.post(
        ENDPOINT,
        json={},
        headers={"Cs-Client-Principal": "", "Authorization": ""},
        expected_status=401,
    )

    assert response.status_code == 401


# ─── Verify Status Code 403 — Forbidden ──────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_user_files_403_forbidden(api_client: ApiClient) -> None:
    """Verify 403 Forbidden when a user without DocuChat access calls the endpoint."""
    # Use a principal that does not have DocuChat group membership
    unauthorized_principal = (
        "eyJhdXRoX3R5cCI6Im9rdGEiLCJjbGFpbXMiOltdLCJuYW1lX3R5cCI6Im5hbWUiLCJyb2xlX3R5cCI6InJvbGUifQ=="
    )

    response = api_client.post(
        ENDPOINT,
        json={},
        headers={"Cs-Client-Principal": unauthorized_principal},
        expected_status=403,
    )

    assert response.status_code == 403


# ─── Verify Status Code 404 — Not Found ──────────────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_user_files_404_not_found(api_client: ApiClient) -> None:
    """Verify 404 Not Found when a record (with record id) is not present in DB."""
    csrf_token = _get_csrf_token(api_client)
    non_existent_id = str(uuid.uuid4())

    response = api_client.post(
        ENDPOINT,
        json={"record_id": non_existent_id},
        headers={"X-CSRFToken": csrf_token},
        expected_status=404,
    )

    assert response.status_code == 404


# ─── Verify Status Code 405 — Method Not Allowed ─────────────────────────────


@pytest.mark.api
@pytest.mark.api_integration
def test_get_user_files_405_method_not_allowed(api_client: ApiClient) -> None:
    """Verify 405 Method Not Allowed when using GET instead of POST."""
    response = api_client.get(
        ENDPOINT,
        expected_status=405,
    )

    assert response.status_code == 405
