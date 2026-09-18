from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "config.yaml"

# Environment variable map: env-var name → config key
# Any of these env vars override the YAML-derived value at runtime.
_ENV_OVERRIDES: Dict[str, str] = {
    "BASE_URL":    "base_url",
    "BROWSER":     "browser",
    "TIMEOUT_MS":  "timeout_ms",
    "HEADLESS":    "headless",
    "VERIFY_SSL":  "verify_ssl",
    "ENV":         "_env_override",   # handled separately in resolve_environment
}


def load_config(config_path: Path | None = None) -> Dict[str, Any]:
    file_path = config_path or CONFIG_PATH
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def resolve_environment(config: Dict[str, Any], env: str | None = None) -> Dict[str, Any]:
    # --env CLI flag > ENV env-var > YAML default_env
    selected_env = (
        env
        or os.getenv("ENV", "").strip()
        or config.get("default_env", "qa")
    )
    environment_map = config.get("environments", {})
    if selected_env not in environment_map:
        available = ", ".join(environment_map.keys())
        raise ValueError(f"Unsupported environment: {selected_env!r}. Available: {available}")

    env_block = environment_map[selected_env]
    merged: Dict[str, Any] = {
        "environment": selected_env,
        "base_url":   env_block.get("base_url"),
        "browser":    config.get("browser", "chromium"),
        "timeout_ms": int(config.get("timeout_ms", 15000)),
        "workers":    config.get("workers", "auto"),
        "headless":   bool(config.get("headless", True)),
        "verify_ssl": bool(config.get("verify_ssl", False)),
    }

    # Pass through per-environment auth config (storage state, etc.)
    if "auth" in env_block:
        merged["auth"] = env_block["auth"]

    # Per-environment browser channel (e.g. msedge for Windows SSO)
    if "channel" in env_block:
        merged["channel"] = env_block["channel"]

    # Apply environment-variable overrides (highest priority)
    if base_url_env := os.getenv("BASE_URL", "").strip():
        merged["base_url"] = base_url_env

    if browser_env := os.getenv("BROWSER", "").strip():
        merged["browser"] = browser_env

    if timeout_env := os.getenv("TIMEOUT_MS", "").strip():
        try:
            merged["timeout_ms"] = int(timeout_env)
        except ValueError:
            pass

    if headless_env := os.getenv("HEADLESS", "").strip():
        merged["headless"] = headless_env.lower() in {"1", "true", "yes", "y"}

    if verify_ssl_env := os.getenv("VERIFY_SSL", "").strip():
        merged["verify_ssl"] = verify_ssl_env.lower() in {"1", "true", "yes", "y"}

    return merged
