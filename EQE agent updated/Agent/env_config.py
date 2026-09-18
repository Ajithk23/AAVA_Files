"""
Agent/env_config.py — Self-contained environment configuration loader
═══════════════════════════════════════════════════════════════════════════════
Reads Agent/environments.yaml and provides typed config dicts.
Generated tests import from this module — no changes needed to the framework.

Usage in generated tests:
    from Agent.env_config import get_db_config, get_api_config, get_file_config, get_tidal_config
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent / "environments.yaml"
_CACHE: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    _CACHE = _resolve_env_vars(raw)
    return _CACHE


def _resolve_env_vars(obj: Any) -> Any:
    """Recursively resolve ${ENV_VAR_NAME} patterns in string values."""
    if isinstance(obj, str):
        pattern = re.compile(r"\$\{([^}]+)\}")
        return pattern.sub(lambda m: os.environ.get(m.group(1), m.group(0)), obj)
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj


def _get_section(product_area: str, env: str, section: str) -> dict[str, Any]:
    config = _load_config()
    area = config.get(product_area)
    if not area:
        raise ValueError(f"Product area '{product_area}' not found. Available: {list(config.keys())}")
    env_cfg = area.get(env)
    if not env_cfg:
        raise ValueError(f"Environment '{env}' not configured for '{product_area}'. Available: {list(area.keys())}")
    sect = env_cfg.get(section)
    if not sect:
        raise ValueError(f"Section '{section}' not in '{product_area}/{env}'. Available: {list(env_cfg.keys())}")
    return sect


def get_db_config(env: str, product_area: str) -> dict[str, Any]:
    """
    Returns:
        {"connection_string": "...", "server": "...", "database": "...", "driver": "..."}
    """
    db = _get_section(product_area, env, "db")
    parts = [f"DRIVER={db['driver']}", f"SERVER={db['server']}", f"DATABASE={db['database']}"]
    if db.get("trusted_connection", False):
        parts.append("Trusted_Connection=yes")
    else:
        if db.get("username"):
            parts.append(f"UID={db['username']}")
        if db.get("password"):
            parts.append(f"PWD={db['password']}")
    parts += ["Encrypt=yes", "TrustServerCertificate=yes"]
    return {"connection_string": ";".join(parts), "server": db["server"], "database": db["database"], "driver": db["driver"]}


def get_api_config(env: str, product_area: str) -> dict[str, Any]:
    """
    Returns:
        {"base_url": "...", "headers": {...}, "auth_type": "...", "ssl_verify": bool, "timeout": int, ...}
    """
    api = _get_section(product_area, env, "api")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    auth_type = api.get("auth_type", "bearer")
    if auth_type == "bearer" and api.get("token"):
        headers["Authorization"] = f"Bearer {api['token']}"
    elif auth_type == "api_key" and api.get("token"):
        headers["X-API-Key"] = api["token"]
    return {
        "base_url": api["base_url"], "headers": headers, "auth_type": auth_type,
        "ssl_verify": api.get("ssl_verify", True), "timeout": api.get("timeout", 30),
        "token_url": api.get("token_url"), "client_id": api.get("client_id"), "client_secret": api.get("client_secret"),
    }


def get_file_config(env: str, product_area: str) -> dict[str, Any]:
    """Returns: {"source_dir": "...", "output_dir": "...", "archive_dir": "...", "error_dir": "..."}"""
    return _get_section(product_area, env, "files")


def get_tidal_config(env: str) -> dict[str, Any]:
    """Returns full Tidal config dict for the given environment."""
    config = _load_config()
    tidal = config.get("tidal")
    if not tidal:
        raise ValueError("Tidal configuration not found in environments.yaml")
    env_cfg = tidal.get(env)
    if not env_cfg:
        raise ValueError(f"Tidal env '{env}' not configured. Available: {list(tidal.keys())}")
    return env_cfg


def reload_config() -> None:
    """Force reload (useful after editing environments.yaml)."""
    global _CACHE
    _CACHE = None
