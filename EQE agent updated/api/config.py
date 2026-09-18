from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils.config_loader import load_config, resolve_environment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"


def _load_dotenv(dotenv_path: Path = DOTENV_PATH) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def _normalize_profile_name(profile: str | None) -> str:
    raw_profile = (profile or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw_profile in {"", "default", "int", "standard"}:
        return "default"
    return raw_profile


def _profile_env_names(profile: str, *names: str) -> tuple[str, ...]:
    if profile == "default":
        return names

    profile_prefix = f"{profile.upper()}_"
    profiled_names = tuple(f"{profile_prefix}{name}" for name in names)
    return profiled_names + names


@dataclass(frozen=True)
class ApiSettings:
    environment: str
    base_url: str
    application: str
    cs_client_principal: str
    profile: str = "default"
    authorization: str = ""
    timeout_ms: int = 15000
    verify_ssl: bool = False

    @classmethod
    def from_sources(cls, env: str | None = None, profile: str | None = None) -> "ApiSettings":
        _load_dotenv()
        config = load_config()
        resolved = resolve_environment(config, env)
        resolved_profile = _normalize_profile_name(profile or os.getenv("API_PROFILE"))

        base_url = _env_first(
            *_profile_env_names(resolved_profile, "API_BASE_URL", "BASE_URL"),
            default=str(resolved.get("base_url", "")),
        )
        application = _env_first(
            *_profile_env_names(resolved_profile, "API_APPLICATION", "APPLICATION"),
            default="AAPPLICATION",
        )
        cs_client_principal = _env_first(
            *_profile_env_names(
                resolved_profile,
                "API_CS_CLIENT_PRINCIPAL",
                "CS_CLIENT_PRINCIPAL",
                "CS-CLIENT-PRINCIPAL",
            ),
        )
        authorization = _env_first(
            *_profile_env_names(
                resolved_profile,
                "API_AUTHORIZATION",
                "AUTHORIZATION",
                "API_BEARER_TOKEN",
            ),
        )

        return cls(
            profile=resolved_profile,
            environment=str(resolved.get("environment", "unknown")),
            base_url=base_url.rstrip("/"),
            application=application,
            cs_client_principal=cs_client_principal,
            authorization=authorization,
            timeout_ms=int(resolved.get("timeout_ms", 15000)),
            verify_ssl=bool(resolved.get("verify_ssl", False)),
        )

    def missing_required_values(self) -> list[str]:
        missing: list[str] = []
        profile_prefix = "" if self.profile == "default" else f"{self.profile.upper()}_"
        if not self.base_url:
            missing.append(f"{profile_prefix}API_BASE_URL or {profile_prefix}BASE_URL")
        if not self.application:
            missing.append(f"{profile_prefix}API_APPLICATION or {profile_prefix}APPLICATION")
        if not self.cs_client_principal:
            missing.append(
                f"{profile_prefix}API_CS_CLIENT_PRINCIPAL or {profile_prefix}CS_CLIENT_PRINCIPAL"
            )
        return missing

    def as_safe_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "environment": self.environment,
            "base_url": self.base_url,
            "application": self.application,
            "cs_client_principal": "***" if self.cs_client_principal else "",
            "authorization": "***" if self.authorization else "",
            "timeout_ms": self.timeout_ms,
            "verify_ssl": self.verify_ssl,
        }