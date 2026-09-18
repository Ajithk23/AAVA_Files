from __future__ import annotations

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type


TEST_CASE_NAME = "Document_OCR_TC001_API_Enterprise_GET_AvailableOCREngines"
TEST_CASE_DESCRIPTION = (
    "Returns the available OCR engine options for document processing. "
    "Only engines supported by the platform are listed."
)
ENDPOINT = "/enterprise/ocr/v1/engines/"


@pytest.mark.api
@pytest.mark.api_integration
def test_get_ocr_engines_success(api_client: ApiClient) -> None:
    """Verify GET /enterprise/ocr/v1/engines/ returns 200 OK with available OCR engines."""
    response = api_client.get(ENDPOINT, expected_status=200)

    assert response.status_code == 200
    assert_json_content_type(response)

    payload = response.json()
    assert payload is not None, "Response body should not be empty"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=int", "-vv", "-s"]))
