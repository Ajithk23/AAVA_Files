from __future__ import annotations

from api.client import ApiClient


class BaseApiService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client