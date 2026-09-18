"""Notification stubs for QA test run results.

Supported channels (enabled via config.yaml or environment variables):
  - Slack  (SLACK_WEBHOOK_URL)
  - Email  (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, NOTIFY_TO)
  - Teams  (TEAMS_WEBHOOK_URL)

Usage:
    from utils.notifications import send_run_summary
    send_run_summary(passed=10, failed=2, duration_sec=45.3, env="qa")
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

logger = logging.getLogger("notifications")


# ────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────────────────

def _post_json(url: str, payload: dict[str, Any]) -> bool:
    """HTTP POST JSON payload. Returns True on success."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib_request.urlopen(req, timeout=10) as response:
            return response.status < 400
    except (URLError, OSError) as exc:
        logger.warning("Webhook POST failed: %s", exc)
        return False


def _build_summary(passed: int, failed: int, duration_sec: float, env: str) -> str:
    total = passed + failed
    pct = round(passed / total * 100, 1) if total else 0
    status = "✅ PASSED" if failed == 0 else "❌ FAILED"
    return (
        f"DocuChat QA Run Summary — env: {env}\n"
        f"Status : {status}\n"
        f"Passed : {passed}/{total} ({pct}%)\n"
        f"Failed : {failed}\n"
        f"Duration: {duration_sec:.1f}s"
    )


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────

def notify_slack(passed: int, failed: int, duration_sec: float, env: str) -> bool:
    """Post a Slack message via Incoming Webhook (set SLACK_WEBHOOK_URL env var)."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.debug("SLACK_WEBHOOK_URL not set — skipping Slack notification.")
        return False

    text = _build_summary(passed, failed, duration_sec, env)
    payload = {"text": text, "mrkdwn": True}
    ok = _post_json(webhook_url, payload)
    if ok:
        logger.info("Slack notification sent.")
    return ok


def notify_teams(passed: int, failed: int, duration_sec: float, env: str) -> bool:
    """Post a Teams adaptive card via Incoming Webhook (set TEAMS_WEBHOOK_URL env var)."""
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.debug("TEAMS_WEBHOOK_URL not set — skipping Teams notification.")
        return False

    text = _build_summary(passed, failed, duration_sec, env)
    # Minimal MessageCard format
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0072C6" if failed == 0 else "D00000",
        "summary": "DocuChat QA Run",
        "text": text.replace("\n", "<br/>"),
    }
    ok = _post_json(webhook_url, payload)
    if ok:
        logger.info("Teams notification sent.")
    return ok


def notify_email(passed: int, failed: int, duration_sec: float, env: str) -> bool:
    """Send result email via SMTP.

    Required env vars: SMTP_HOST, SMTP_USER, SMTP_PASS, NOTIFY_TO
    Optional env vars: SMTP_PORT (default 587), SMTP_FROM
    """
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    to_addr = os.getenv("NOTIFY_TO", "").strip()
    from_addr = os.getenv("SMTP_FROM", user)
    port = int(os.getenv("SMTP_PORT", "587"))

    if not all([host, user, password, to_addr]):
        logger.debug("Email not fully configured — skipping email notification.")
        return False

    body = _build_summary(passed, failed, duration_sec, env)
    subject = f"[DocuChat QA] {'PASSED' if failed == 0 else 'FAILED'} — env={env}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        logger.info("Email notification sent to %s.", to_addr)
        return True
    except smtplib.SMTPException as exc:
        logger.warning("Email send failed: %s", exc)
        return False


def send_run_summary(passed: int, failed: int, duration_sec: float, env: str = "qa") -> None:
    """Broadcast test results to all configured notification channels."""
    notify_slack(passed, failed, duration_sec, env)
    notify_teams(passed, failed, duration_sec, env)
    notify_email(passed, failed, duration_sec, env)
