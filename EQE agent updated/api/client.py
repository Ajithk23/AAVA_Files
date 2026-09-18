from __future__ import annotations

import json
import time
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urljoin

import requests

from utils.logger import get_logger

from .auth import mask_secret
from .config import ApiSettings
from .exceptions import ApiConfigurationError, ApiRequestError, ApiResponseError
from .headers import build_default_headers


logger = get_logger("api_client")


class ApiClient:
    def __init__(
        self,
        settings: ApiSettings,
        *,
        session: requests.Session | None = None,
        retry_count: int = 2,
        retry_statuses: Iterable[int] = (429, 502, 503, 504),
        backoff_seconds: float = 0.5,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.retry_count = retry_count
        self.retry_statuses = set(retry_statuses)
        self.backoff_seconds = backoff_seconds
        self.request_history: list[dict[str, Any]] = []

    def close(self) -> None:
        self.session.close()

    def clear_history(self) -> None:
        self.request_history.clear()

    def get_history_snapshot(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self.request_history]

    def build_headers(self, overrides: Mapping[str, str] | None = None) -> dict[str, str]:
        return build_default_headers(self.settings, overrides)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        expected_status: int | Iterable[int] | None = None,
        timeout_ms: int | None = None,
    ) -> requests.Response:
        missing = self.settings.missing_required_values()
        if missing:
            raise ApiConfigurationError(
                "Missing API configuration: " + ", ".join(missing)
            )

        url = urljoin(f"{self.settings.base_url}/", path.lstrip("/"))
        request_headers = self.build_headers(headers)
        timeout_seconds = (timeout_ms or self.settings.timeout_ms) / 1000

        last_error: Exception | None = None
        response: requests.Response | None = None

        for attempt in range(self.retry_count + 1):
            try:
                logger.info(
                    "API request | method=%s | url=%s | headers=%s | params=%s | attempt=%d",
                    method.upper(),
                    url,
                    self._safe_headers_for_log(request_headers),
                    dict(params or {}),
                    attempt + 1,
                )
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    headers=request_headers,
                    json=json,
                    data=data,
                    files=files,
                    timeout=timeout_seconds,
                    verify=self.settings.verify_ssl,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.retry_count:
                    raise ApiRequestError(f"{method.upper()} {url} failed: {exc}") from exc
                time.sleep(self.backoff_seconds * (attempt + 1))
                continue

            logger.info(
                "API response | method=%s | url=%s | status=%s",
                method.upper(),
                url,
                response.status_code,
            )
            response_body = self._format_response_body(response)
            logger.info(
                "API response body | method=%s | url=%s\n%s",
                method.upper(),
                url,
                response_body,
            )
            self.request_history.append(
                {
                    "method": method.upper(),
                    "url": url,
                    "status_code": response.status_code,
                    "request_headers": self._safe_headers_for_log(request_headers),
                    "params": dict(params or {}),
                    "response_headers": dict(response.headers),
                    "response_body": response_body,
                }
            )

            if response.status_code not in self.retry_statuses or attempt >= self.retry_count:
                break

            time.sleep(self.backoff_seconds * (attempt + 1))

        if response is None:
            raise ApiRequestError(f"{method.upper()} {url} failed without a response") from last_error

        self.assert_status(response, expected_status)
        return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    @staticmethod
    def response_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise ApiResponseError(
                f"Response from {response.request.method} {response.url} is not valid JSON"
            ) from exc

    @staticmethod
    def assert_status(
        response: requests.Response,
        expected_status: int | Iterable[int] | None,
    ) -> None:
        if expected_status is None:
            return

        allowed = {expected_status} if isinstance(expected_status, int) else set(expected_status)
        if response.status_code not in allowed:
            raise ApiResponseError(
                "Unexpected status code for "
                f"{response.request.method} {response.url}: "
                f"expected {sorted(allowed)}, got {response.status_code}. "
                f"Body: {response.text[:500]}"
            )

    @staticmethod
    def _safe_headers_for_log(headers: Mapping[str, str]) -> dict[str, str]:
        safe_headers = dict(headers)
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = mask_secret(safe_headers["Authorization"])
        if "Cs-Client-Principal" in safe_headers:
            safe_headers["Cs-Client-Principal"] = mask_secret(safe_headers["Cs-Client-Principal"])
        return safe_headers

    @staticmethod
    def _format_response_body(response: requests.Response) -> str:
        try:
            return json.dumps(response.json(), indent=2, ensure_ascii=False)
        except ValueError:
            return response.text