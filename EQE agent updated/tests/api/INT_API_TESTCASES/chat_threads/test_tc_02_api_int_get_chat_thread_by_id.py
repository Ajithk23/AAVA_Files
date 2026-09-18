from __future__ import annotations

import pytest

from api.client import ApiClient
from api.validators import assert_json_content_type, assert_response_keys


TEST_CASE_NAME = "GET_TC02_api_int_Get chat therads_id"
TEST_CASE_DESCRIPTION = (
    "Retrieves a single chat thread by thread_id and validates that the JSON response "
    "contains the thread details, messages, docs, model, and chat_type."
)
ENDPOINT_TEMPLATE = "/docu_chat/v1/chat_threads/{thread_id}/"
EXPECTED_STATUS_CODE = 200
THREAD_ID = "d9d1fd15-3823-451a-bfb7-3afe6a14066e"


@pytest.mark.api
@pytest.mark.api_integration
def test_tc_02_api_int_get_chat_thread_by_id(api_client: ApiClient) -> None:
    """Retrieves a single chat thread by thread_id and validates that the JSON response contains the thread details, messages, docs, model, and chat_type."""
    endpoint = ENDPOINT_TEMPLATE.format(thread_id=THREAD_ID)
    response = api_client.get(
        endpoint,
        headers={"Accept": "application/json"},
        expected_status=EXPECTED_STATUS_CODE,
    )

    assert response.status_code == EXPECTED_STATUS_CODE
    assert_json_content_type(response)

    payload = api_client.response_json(response)
    assert isinstance(payload, dict)
    assert_response_keys(
        payload,
        [
            "id",
            "title",
            "message_count",
            "chat_type",
            "model",
            "messages",
            "docs",
            "is_temporary",
            "created_at",
            "updated_at",
        ],
    )

    assert payload["id"] == THREAD_ID
    assert isinstance(payload["title"], str)
    assert payload["title"]
    assert isinstance(payload["message_count"], int)
    assert payload["message_count"] == len(payload["messages"])
    assert isinstance(payload["chat_type"], dict)
    assert_response_keys(payload["chat_type"], ["id", "name"])
    assert isinstance(payload["chat_type"]["id"], int)
    assert isinstance(payload["chat_type"]["name"], str)
    assert payload["chat_type"]["name"]
    assert isinstance(payload["model"], dict)
    assert_response_keys(payload["model"], ["id", "description", "deployment_name"])
    assert isinstance(payload["model"]["id"], int)
    assert isinstance(payload["model"]["description"], str)
    assert payload["model"]["description"]
    assert isinstance(payload["model"]["deployment_name"], str)
    assert payload["model"]["deployment_name"]
    assert isinstance(payload["messages"], list)
    assert isinstance(payload["docs"], list)
    assert isinstance(payload["is_temporary"], bool)
    assert isinstance(payload["created_at"], str)
    assert isinstance(payload["updated_at"], str)

    for message in payload["messages"]:
        assert isinstance(message, dict)

    for document in payload["docs"]:
        assert isinstance(document, dict)


test_tc_02_api_int_get_chat_thread_by_id.test_case_name = TEST_CASE_NAME
test_tc_02_api_int_get_chat_thread_by_id.test_case_description = TEST_CASE_DESCRIPTION