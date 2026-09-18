from __future__ import annotations

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type, assert_response_keys


TEST_CASE_NAME = "TC_01_API_INT_Get_Chat_Thread"
TEST_CASE_DESCRIPTION = (
    "Retrieves chat threads. If thread_id is provided, returns a single thread with all "
    "messages, docs, model, and chat_type. Otherwise returns a paginated list of threads "
    "for the user (without message content, but with message_count)."
)
ENDPOINT = "/docu_chat/v1/chat_threads/"
EXPECTED_STATUS_CODE = 200


@pytest.mark.api
@pytest.mark.api_integration
def test_tc_01_api_int_get_chat_thread(api_client: ApiClient) -> None:
    """Retrieves chat threads. If thread_id is provided, returns a single thread with all messages, docs, model, and chat_type. Otherwise returns a paginated list of threads for the user (without message content, but with message_count)."""
    response = api_client.get(
        ENDPOINT,
        expected_status=EXPECTED_STATUS_CODE,
    )

    assert response.status_code == EXPECTED_STATUS_CODE
    assert_json_content_type(response)

    payload = api_client.response_json(response)
    assert isinstance(payload, dict)
    assert_response_keys(payload, ["count", "page", "page_size", "threads", "total_pages"])

    assert isinstance(payload["count"], int)
    assert isinstance(payload["page"], int)
    assert isinstance(payload["page_size"], int)
    assert isinstance(payload["total_pages"], int)
    assert isinstance(payload["threads"], list)

    if payload["threads"]:
        first_thread = payload["threads"][0]
        assert isinstance(first_thread, dict)
        assert_response_keys(
            first_thread,
            [
                "id",
                "title",
                "chat_type",
                "model",
                "message_count",
                "messages",
                "docs",
                "is_temporary",
                "created_at",
                "updated_at",
            ],
        )


test_tc_01_api_int_get_chat_thread.test_case_name = TEST_CASE_NAME
test_tc_01_api_int_get_chat_thread.test_case_description = TEST_CASE_DESCRIPTION