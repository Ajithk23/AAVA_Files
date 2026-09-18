from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import requests

from .exceptions import ApiResponseError


def assert_json_content_type(response: requests.Response) -> None:
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type.lower():
        raise ApiResponseError(
            f"Expected JSON response from {response.request.method} {response.url}, got {content_type!r}"
        )


def assert_response_keys(payload: dict[str, Any], required_keys: Iterable[str]) -> None:
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ApiResponseError(f"Response payload missing required keys: {', '.join(missing)}")