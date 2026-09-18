from __future__ import annotations

from collections.abc import Mapping

from .auth import build_authorization_header
from .config import ApiSettings


def build_default_headers(
    settings: ApiSettings,
    overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Application": settings.application,
        "Cs-Client-Principal": settings.cs_client_principal,
    }
    headers.update(build_authorization_header(settings.authorization))

    if overrides:
        headers.update({key: value for key, value in overrides.items() if value is not None})

    return headers