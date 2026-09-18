"""
Agent/automation_fixtures.py — Self-contained fixtures for all automation types
═══════════════════════════════════════════════════════════════════════════════
Generated tests use a local conftest.py that imports from this module.
No changes to the main framework conftest.py are needed.

The agent generates a conftest.py alongside the test file that does:
    from Agent.automation_fixtures import <needed_fixtures>

This module provides:
  - db_connection / db_cursor   (pyodbc, auto-rollback)
  - api_client                  (httpx AsyncClient)
  - tidal_client                (TidalClient with trigger + wait)
  - file_paths                  (configured Path objects)
  - wait_for_file / wait_for_file_removal  (polling utilities)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Generator

import pytest
import httpx
import pyodbc

from Agent.env_config import get_api_config, get_db_config, get_file_config, get_tidal_config


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def db_connection(request) -> Generator[pyodbc.Connection, None, None]:
    """
    Auto-rollback database connection. All changes are discarded after test.

    Requires --env and --product-area pytest options (added by generated conftest).
    """
    env = request.config.getoption("--env", default="qa")
    product_area = request.config.getoption("--product-area")
    config = get_db_config(env, product_area)
    conn = pyodbc.connect(config["connection_string"], autocommit=False)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_cursor(db_connection) -> Generator[pyodbc.Cursor, None, None]:
    """Convenience cursor from the auto-rollback connection."""
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()


# ═══════════════════════════════════════════════════════════════════════════════
# API FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
async def api_client(request) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Authenticated async HTTP client for the target environment/product area.
    """
    env = request.config.getoption("--env", default="qa")
    product_area = request.config.getoption("--product-area")
    config = get_api_config(env, product_area)
    async with httpx.AsyncClient(
        base_url=config["base_url"],
        headers=config["headers"],
        timeout=httpx.Timeout(float(config.get("timeout", 30))),
        verify=config.get("ssl_verify", True),
    ) as client:
        yield client


# ═══════════════════════════════════════════════════════════════════════════════
# TIDAL FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TidalJobResult:
    """Result of a Tidal job execution."""
    job_name: str
    status: str          # "completed", "failed", "timeout"
    run_id: str | None
    duration_seconds: float
    output: str | None


class TidalClient:
    """Trigger and monitor Tidal Enterprise Scheduler jobs (API or SSH mode)."""

    def __init__(self, config: dict):
        self._config = config
        self._mode = config.get("mode", "api")

    async def trigger_job(self, job_name: str, *, parameters: dict | None = None) -> str:
        """Trigger a job, return run_id."""
        if self._mode == "api":
            return await self._trigger_api(job_name, parameters)
        return await self._trigger_ssh(job_name, parameters)

    async def wait_for_completion(
        self, job_name: str, run_id: str, *, timeout_seconds: int = 300, poll_interval: int = 10
    ) -> TidalJobResult:
        """Poll until job completes, fails, or times out."""
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed > timeout_seconds:
                return TidalJobResult(job_name=job_name, status="timeout", run_id=run_id, duration_seconds=elapsed, output=None)

            status, output = await self._check_status(run_id)
            if status in ("completed", "successful", "success"):
                return TidalJobResult(job_name=job_name, status="completed", run_id=run_id, duration_seconds=elapsed, output=output)
            elif status in ("failed", "error", "aborted"):
                return TidalJobResult(job_name=job_name, status="failed", run_id=run_id, duration_seconds=elapsed, output=output)
            await asyncio.sleep(poll_interval)

    async def _trigger_api(self, job_name: str, parameters: dict | None) -> str:
        base_url = self._config["api_base_url"]
        token = self._config.get("api_token", "")
        payload: dict[str, Any] = {"jobName": job_name}
        if parameters:
            payload["parameters"] = parameters
        async with httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            verify=self._config.get("ssl_verify", False),
        ) as client:
            resp = await client.post("/jobs/trigger", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("runId", data.get("id", "unknown"))

    async def _trigger_ssh(self, job_name: str, parameters: dict | None) -> str:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self._config["ssh_host"],
            port=self._config.get("ssh_port", 22),
            username=self._config["ssh_user"],
            key_filename=self._config.get("ssh_key_path") or None,
        )
        cmd = f"tidal trigger {job_name}"
        if parameters:
            cmd += " " + " ".join(f"--param {k}={v}" for k, v in parameters.items())
        _, stdout, _ = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()
        ssh.close()
        return output.split()[-1] if output else "unknown"

    async def _check_status(self, run_id: str) -> tuple[str, str | None]:
        if self._mode == "api":
            async with httpx.AsyncClient(
                base_url=self._config["api_base_url"],
                headers={"Authorization": f"Bearer {self._config.get('api_token', '')}"},
                verify=self._config.get("ssl_verify", False),
            ) as client:
                resp = await client.get(f"/jobs/runs/{run_id}")
                resp.raise_for_status()
                data = resp.json()
                return data.get("status", "unknown"), data.get("output")
        else:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self._config["ssh_host"], port=self._config.get("ssh_port", 22),
                username=self._config["ssh_user"], key_filename=self._config.get("ssh_key_path"),
            )
            _, stdout, _ = ssh.exec_command(f"tidal status {run_id}")
            output = stdout.read().decode().strip()
            ssh.close()
            if "completed" in output.lower() or "success" in output.lower():
                return "completed", output
            elif "failed" in output.lower() or "error" in output.lower():
                return "failed", output
            return "running", output


@pytest.fixture
def tidal_client(request) -> TidalClient:
    """TidalClient configured for the target environment."""
    env = request.config.getoption("--env", default="qa")
    config = get_tidal_config(env)
    return TidalClient(config)


# ═══════════════════════════════════════════════════════════════════════════════
# FILE FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def file_paths(request) -> dict[str, Path | None]:
    """
    Configured file directory paths for the target product area.
    """
    env = request.config.getoption("--env", default="qa")
    product_area = request.config.getoption("--product-area")
    config = get_file_config(env, product_area)
    return {
        "source_dir": Path(config["source_dir"]) if config.get("source_dir") else None,
        "output_dir": Path(config["output_dir"]) if config.get("output_dir") else None,
        "archive_dir": Path(config["archive_dir"]) if config.get("archive_dir") else None,
        "error_dir": Path(config.get("error_dir", "")) if config.get("error_dir") else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FILE UTILITY FUNCTIONS (not fixtures — import directly)
# ═══════════════════════════════════════════════════════════════════════════════

def wait_for_file(directory: Path, pattern: str, *, timeout_seconds: int = 120, poll_interval: int = 5) -> Path | None:
    """Poll directory until a file matching glob pattern appears. Returns Path or None on timeout."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        matches = list(directory.glob(pattern))
        if matches:
            return max(matches, key=lambda p: p.stat().st_mtime)
        time.sleep(poll_interval)
    return None


def wait_for_file_removal(file_path: Path, *, timeout_seconds: int = 120, poll_interval: int = 5) -> bool:
    """Poll until file is removed. Returns True if removed, False on timeout."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        if not file_path.exists():
            return True
        time.sleep(poll_interval)
    return False
