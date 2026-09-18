"""
aava_qtest_reference.py
════════════════════════════════════════════════════════════════════════════════
REFERENCE FILE — AAVA Test Case Generation + qTest Upload
════════════════════════════════════════════════════════════════════════════════

PURPOSE
───────
This file is a self-contained reference for building a custom agent that:
  1. Accepts a user story (title, description, acceptance criteria)
  2. Calls the AAVA Test Case Generator agent (agent_id=48) to generate TCs
  3. Parses the structured JSON response from AAVA
  4. Uploads the generated test cases directly to qTest Manager

ENTRY POINT
───────────
    run_full_pipeline(user_story, qtest_config)

See the bottom of this file for a runnable example.

════════════════════════════════════════════════════════════════════════════════
SECTION 1 — CREDENTIALS & CONFIGURATION
════════════════════════════════════════════════════════════════════════════════

Load from environment variables (or .env file).  Never hard-code secrets.

Required env vars
─────────────────
  AAVA_API_URL        AAVA execution endpoint
                      default: https://aava-core-api-agents-svc.redtree-f4541a84.eastus.azurecontainerapps.io/agents/execute
  AAVA_BEARER_TOKEN   Bearer token for AAVA API authentication
  AAVA_USER_EMAIL     Email of the user making the request (used as audit trail)

  QTEST_HOST          qTest domain without https://   e.g. mycompany.qtestnet.com
  QTEST_TOKEN         Bearer token from qTest Manager
  QTEST_PROJECT_ID    Numeric qTest project ID         e.g. 12345
  QTEST_WORKSPACE_ID  Workspace/site ID (optional)     e.g. 21
  QTEST_MODULE        Target module (folder) name      e.g. "AI Generated Test Cases"

Optional qTest field mapping env vars (format: field_id:field_value[:field_value_name])
  QTEST_FIELD_STATUS            e.g. "601:1:New"
  QTEST_FIELD_TEST_CASE_TYPE    e.g. "602:1:Manual"
  QTEST_FIELD_TEST_TYPE         e.g. "603:2:Functional"
  QTEST_FIELD_IMPLEMENTATION    e.g. "604:1:Manual"
  QTEST_FIELD_PRODUCT_AREA      e.g. "605:3:Backend"
  QTEST_FIELD_ASSIGNED_TO       e.g. "606:42:john.doe@company.com"

SSL settings
  QTEST_CA_BUNDLE     Path to corporate CA cert bundle (if behind corporate proxy)
  QTEST_SSL_VERIFY    "true" | "false"   (default false — set true in production)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import requests
from requests.exceptions import SSLError, RequestException

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — AAVA AGENT CONFIGURATION  (loaded from aava_qtest_config.py)
# ─────────────────────────────────────────────────────────────────────────────

from aava_qtest_config import (  # noqa: E402
    AAVA_URL,
    AAVA_BEARER_TOKEN,
    AAVA_USER_EMAIL,
    AAVA_TIMEOUT_SEC,
    TC_AGENT_ID,
    TC_REALM_ID,
    TC_INPUT_KEY,
    AAVA_SKIP_AGENT_PROMPT,
    QTEST_SSL_VERIFY as _QTEST_SSL_VERIFY_DEFAULT,
    QTEST_CONFIG,
)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — BUILD THE AAVA REQUEST
# ─────────────────────────────────────────────────────────────────────────────
#
# AAVA Request Body Schema
# ────────────────────────
# {
#   "agentId":     <int>          — Agent ID (188 for TC Generator v2)
#   "userInputs":  {              — Key/value pairs the agent template expects
#     "{{Story Details_string_true}}": <JSON string>   ← stringified requirements
#   },
#   "executionId": <uuid string>  — Unique ID for this run (for tracing)
#   "user":        <email>        — Calling user's email
# }
#
# Story Details Payload (inside userInputs, JSON-stringified)
# ───────────────────────────────────────────────────────────
# {
#   "requirements": [
#     {
#       "id":                  <int>,      — ADO work item ID (optional)
#       "title":               <string>,   — User story title
#       "description":         <string>,   — Functional description
#       "acceptance_criteria": <string>    — Acceptance criteria
#     }
#   ],
#   "existing_titles": [<string>, ...]     — TC titles to skip (dedup)
# }
#
# AAVA Request Headers
# ────────────────────
# Content-Type:  application/json
# Accept:        application/json, text/plain, */*
# X-Realm-Id:    <realm_id>       — "4" for current deployment
# Authorization: Bearer <token>

def build_aava_request(
    title: str,
    description: str,
    acceptance_criteria: str,
    story_id: int | str | None = None,
    existing_titles: list[str] | None = None,
    agent_id: int | None = None,
    realm_id: str | None = None,
) -> tuple[dict, dict]:
    """
    Build the AAVA request body and headers for test case generation.

    Parameters
    ----------
    title                : User story / requirement title
    description          : User story description (functional details)
    acceptance_criteria  : Acceptance criteria text
    story_id             : Optional numeric ID of the user story (e.g. ADO work item ID)
    existing_titles      : List of already-existing TC titles to skip (dedup)
    agent_id             : AAVA agent ID to call. Defaults to TC_AGENT_ID from config.
    realm_id             : AAVA realm ID. Defaults to TC_REALM_ID from config.

    Returns
    -------
    (body, headers) — ready to pass to requests.post()
    """
    selected_agent_id = agent_id if agent_id is not None else TC_AGENT_ID
    selected_realm_id = realm_id if realm_id is not None else TC_REALM_ID

    # ── Story Details payload (sent as a JSON string inside userInputs) ────
    # This is the exact structure AAVA agent 188 expects.
    requirement: dict = {
        "title":               title,
        "description":         description or title,
        "acceptance_criteria": acceptance_criteria or "",
    }
    if story_id is not None:
        requirement["id"] = int(story_id)

    story_details = {
        "requirements":    [requirement],
        "existing_titles": existing_titles or [],
    }

    body = {
        "agentId":     selected_agent_id,
        "userInputs":  {TC_INPUT_KEY: json.dumps(story_details, indent=2)},
        "executionId": str(uuid.uuid4()),
        "user":        AAVA_USER_EMAIL,
    }

    headers = {
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "X-Realm-Id":    selected_realm_id,
        "Authorization": f"Bearer {AAVA_BEARER_TOKEN}",
    }

    return body, headers


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — CALL AAVA AGENT
# ─────────────────────────────────────────────────────────────────────────────

def call_aava_agent(
    title: str,
    description: str,
    acceptance_criteria: str,
    story_id: int | str | None = None,
    existing_titles: list[str] | None = None,
    agent_id: int | None = None,
    realm_id: str | None = None,
) -> dict[str, Any]:
    """
    Call an AAVA agent to generate test cases.

    Parameters
    ----------
    agent_id  : The AAVA agent ID to invoke. If None, uses TC_AGENT_ID from config.
    realm_id  : The AAVA realm ID. If None, uses TC_REALM_ID from config.

    Returns
    -------
    {
        "success":   bool,
        "scenarios": dict | None,   — parsed scenarios payload (see Section 5)
        "raw":       dict,          — full AAVA response (for debugging)
        "error":     str | None,
    }

    Error sentinels in "error"
    ──────────────────────────
    "QUOTA_EXCEEDED"  — HTTP 429, AAVA rate limit hit; wait and retry
    "HTTP_<status>"   — unexpected HTTP error
    "REQUEST_FAILED"  — network / timeout error
    """
    selected_agent_id = agent_id if agent_id is not None else TC_AGENT_ID
    selected_realm_id = realm_id if realm_id is not None else TC_REALM_ID

    body, headers = build_aava_request(
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        story_id=story_id,
        existing_titles=existing_titles,
        agent_id=selected_agent_id,
        realm_id=selected_realm_id,
    )

    logger.info("Calling AAVA agent %d (realm=%s) for: %s", selected_agent_id, selected_realm_id, title)

    try:
        resp = requests.post(AAVA_URL, headers=headers, json=body, timeout=AAVA_TIMEOUT_SEC)

        if resp.status_code == 429:
            return {"success": False, "scenarios": None, "raw": {}, "error": "QUOTA_EXCEEDED"}

        resp.raise_for_status()
        raw = resp.json()

        scenarios = _extract_scenarios(raw)
        return {
            "success":   True,
            "scenarios": scenarios,
            "raw":       raw,
            "error":     None,
        }

    except requests.exceptions.HTTPError as exc:
        status  = exc.response.status_code if exc.response is not None else "?"
        detail  = (exc.response.text or "")[:400] if exc.response is not None else str(exc)
        return {"success": False, "scenarios": None, "raw": {}, "error": f"HTTP_{status}: {detail}"}
    except RequestException as exc:
        return {"success": False, "scenarios": None, "raw": {}, "error": f"REQUEST_FAILED: {exc}"}
    except Exception as exc:
        return {"success": False, "scenarios": None, "raw": {}, "error": f"UNEXPECTED: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — PARSE AAVA RESPONSE
# ─────────────────────────────────────────────────────────────────────────────
#
# AAVA Response Shape (simplified)
# ─────────────────────────────────
# The AAVA API wraps the agent output in a nested structure.
# The actual test case JSON lives at one of several paths:
#
#   data.agentResponse.agent.output.scenarios          ← most common
#   data.agentResponse.agent.tasksOutputs.raw.scenarios
#   agentResponse.agent.output.scenarios               ← without data wrapper
#   output.scenarios                                   ← flat variant
#
# Scenarios Payload Schema
# ────────────────────────
# {
#   "scenarios": [
#     {
#       "scenario_id":    "SC-001",
#       "scenario_title": "Scenario description",
#       "test_cases": [
#         {
#           "testcase_id":    "TC-001",
#           "title":          "Verify that ...",
#           "preconditions":  "User is logged in. ...",
#           "test_type":      "Positive",          // Positive | Negative | Edge
#           "automation":     "Yes",               // Yes | No | Partial
#           "test_data":      "Username: user@example.com ...",
#           "steps": [
#             "Navigate to ...",
#             "Click on ...",
#             "Verify that ..."
#           ],
#           "expected_result": "The system should ..."
#         }
#       ]
#     }
#   ]
# }

def _extract_scenarios(data: dict) -> dict | None:
    """
    Walk the AAVA response tree and return the payload containing test case data.

    Supports multiple AAVA output formats:
      - Standard: dict with 'scenarios' key
      - Test cases list: dict with 'test_cases' or 'testcases' key
      - Flat list: dict with 'results', 'test_scenarios', or 'output' containing a list
      - Direct list wrapper: the response itself is a list of test case dicts

    Returns a normalised dict with a 'scenarios' key (list) for downstream processing,
    or None if no test case data can be found.
    """
    if not isinstance(data, dict):
        return None

    # ── Direct 'scenarios' key ────────────────────────────────────────────────
    if "scenarios" in data:
        return data

    # ── Nested AAVA response wrappers ─────────────────────────────────────────
    roots = [data]
    inner = data.get("data")
    if isinstance(inner, dict):
        roots.append(inner)

    for root in roots:
        agent_resp = root.get("agentResponse", {})
        agent = agent_resp.get("agent", {}) if isinstance(agent_resp, dict) else {}
        if isinstance(agent, dict):
            output = agent.get("output")
            if isinstance(output, dict):
                if "scenarios" in output:
                    return output
                # Handle alternate keys inside agent output
                normalized = _normalize_to_scenarios(output)
                if normalized:
                    return normalized
            # Path: agent.tasksOutputs.raw
            tasks = agent.get("tasksOutputs", {})
            if isinstance(tasks, dict):
                raw = tasks.get("raw")
                if isinstance(raw, dict):
                    if "scenarios" in raw:
                        return raw
                    normalized = _normalize_to_scenarios(raw)
                    if normalized:
                        return normalized

    # ── Top-level alternate keys ──────────────────────────────────────────────
    for key in ("output", "result", "response", "data"):
        candidate = data.get(key)
        if isinstance(candidate, dict):
            if "scenarios" in candidate:
                return candidate
            normalized = _normalize_to_scenarios(candidate)
            if normalized:
                return normalized
        # If the value is a list directly (e.g. {"output": [...]})
        if isinstance(candidate, list) and candidate:
            return {"scenarios": candidate}

    # ── Try normalizing the root dict itself ──────────────────────────────────
    normalized = _normalize_to_scenarios(data)
    if normalized:
        return normalized

    # ── Deep-scan fallback: recursively find any list that looks like TCs ─────
    found = _deep_scan_for_tc_list(data)
    if found:
        return found

    return None


def _deep_scan_for_tc_list(data: dict, max_depth: int = 5) -> dict | None:
    """
    Recursively scan any dict for a list of dicts that resemble test cases.

    This is the last-resort fallback when no known key names match.
    It walks the entire response tree and returns the first list whose items
    look like test cases (based on field-name heuristics).

    Parameters
    ----------
    data      : The dict to scan.
    max_depth : Maximum recursion depth to prevent infinite loops.

    Returns
    -------
    {"scenarios": [...]} if a test-case-like list is found, None otherwise.
    """
    if max_depth <= 0 or not isinstance(data, dict):
        return None

    # Signals that indicate a dict is likely a test case
    _TC_SIGNALS = {
        "title", "name", "summary", "test_scenario", "test_case_name",
        "steps", "test_steps", "tc_id", "testcase_id", "test_case_id",
        "expected_result", "preconditions", "precondition", "test_type",
    }

    for key, value in data.items():
        # Check if this value is a non-empty list of dicts
        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Heuristic: does the first item have fields that look like a test case?
            sample_keys = set(value[0].keys())
            if _TC_SIGNALS & sample_keys:
                return {"scenarios": value}

        # Recurse into nested dicts
        elif isinstance(value, dict):
            found = _deep_scan_for_tc_list(value, max_depth - 1)
            if found:
                return found

    return None


def _normalize_to_scenarios(payload: dict) -> dict | None:
    """
    Attempt to normalize a dict with non-standard keys into {'scenarios': [...]}.

    Recognises alternate keys that AAVA agents may use:
      - test_cases, testcases, testCases
      - test_scenarios, test_results
      - results, items, cases
    """
    alternate_keys = [
        "test_cases", "testcases", "testCases",
        "test_scenarios", "test_results",
        "results", "items", "cases",
    ]
    for key in alternate_keys:
        value = payload.get(key)
        if isinstance(value, list) and value:
            return {"scenarios": value}
    return None


def parse_scenarios_to_tc_list(scenarios_payload: dict) -> list[dict]:
    """
    Flatten the scenarios payload into a list of test case dicts.

    Handles ANY AAVA response format by detecting the structure of each item
    in the ``scenarios`` list and normalizing it to the standard TC dict format.

    Supported formats:
      - Flat format (agent v2): each item IS a test case (has ``tc_id`` or ``test_scenario``).
      - Nested format (agent v1): each item has a ``test_cases``/``testcases`` sub-list.
      - Generic format: each item has ``title``/``name`` and ``steps`` (arbitrary agent output).
      - Minimal format: each item has at least a title-like field — normalized with defaults.

    Each dict in the returned list always has these keys (for qTest upload compatibility):
        scenario_id, scenario_title,
        testcase_id, title, preconditions, test_type,
        automation, test_data, steps (list[dict|str]), expected_result,
        objective, priority,
        test_case_type, test_case_status, implementation, product_area

    This is the format consumed by upload_to_qtest().
    """
    tc_list: list[dict] = []

    for idx, scenario in enumerate(scenarios_payload.get("scenarios", []), start=1):
        # ── Flat format: the scenario item itself is the test case ────────────
        # Detected by the presence of "tc_id" or "test_scenario" (AAVA agent v2).
        if "tc_id" in scenario or "test_scenario" in scenario:
            tc_list.append(_normalize_tc_dict(scenario, idx))
            continue

        # ── Nested format: scenario → test_cases[] (agent v1) ────────────────
        tc_items = scenario.get("test_cases") or scenario.get("testcases") or scenario.get("testCases") or []
        if tc_items:
            sc_id    = scenario.get("scenario_id", "")
            sc_title = scenario.get("scenario_title", scenario.get("title", ""))
            for tc_idx, tc in enumerate(tc_items, start=1):
                normalized = _normalize_tc_dict(tc, tc_idx)
                normalized["scenario_id"] = sc_id or normalized["scenario_id"]
                normalized["scenario_title"] = sc_title or normalized["scenario_title"]
                tc_list.append(normalized)
            continue

        # ── Generic / unknown format: treat the item itself as a test case ───
        # Handles arbitrary AAVA agents that return test cases with non-standard keys.
        tc_list.append(_normalize_tc_dict(scenario, idx))

    return tc_list


def _normalize_tc_dict(item: dict, index: int) -> dict:
    """
    Normalize any dict representing a test case into the standard TC format
    expected by qTest upload. Handles varied key names gracefully.

    Parameters
    ----------
    item  : A dict from the AAVA response representing a single test case.
    index : Fallback numeric index for generating a TC ID if none is present.

    Returns
    -------
    A standardized TC dict with all required keys for upload_to_qtest().
    """
    # ── Resolve title (try many common key names) ─────────────────────────────
    title = (
        item.get("title")
        or item.get("test_scenario")
        or item.get("name")
        or item.get("test_case_name")
        or item.get("testcase_name")
        or item.get("scenario_title")
        or item.get("summary")
        or item.get("test_name")
        or f"Test Case {index}"
    )

    # ── Resolve TC ID ─────────────────────────────────────────────────────────
    tc_id = (
        item.get("tc_id")
        or item.get("testcase_id")
        or item.get("test_case_id")
        or item.get("id")
        or item.get("scenario_id")
        or f"TC-{index:03d}"
    )

    # ── Resolve steps (handle list of strings, list of dicts, or single string) ─
    steps_raw = (
        item.get("steps")
        or item.get("test_steps")
        or item.get("testSteps")
        or item.get("actions")
        or []
    )
    if isinstance(steps_raw, str):
        steps_raw = [steps_raw]

    # ── Resolve preconditions ─────────────────────────────────────────────────
    preconditions = (
        item.get("preconditions")
        or item.get("precondition")
        or item.get("pre_conditions")
        or item.get("prerequisites")
        or ""
    )

    # ── Resolve expected result ───────────────────────────────────────────────
    expected_result = (
        item.get("expected_result")
        or item.get("expected_results")
        or item.get("expectedResult")
        or item.get("expected_outcome")
        or item.get("expected")
        or ""
    )

    # ── Resolve test type ─────────────────────────────────────────────────────
    test_type = (
        item.get("test_type")
        or item.get("type")
        or item.get("category")
        or item.get("test_category")
        or ""
    )

    return {
        "scenario_id":      item.get("scenario_id", ""),
        "scenario_title":   item.get("scenario_title", ""),
        "testcase_id":      str(tc_id),
        "title":            title,
        "preconditions":    preconditions,
        "test_type":        test_type,
        "automation":       item.get("automation_feasible") or item.get("automation") or item.get("automatable") or "",
        "test_data":        item.get("test_data") or item.get("testData") or item.get("data") or "",
        "steps":            steps_raw,
        "expected_result":  expected_result,
        "objective":        item.get("description") or item.get("objective") or item.get("purpose") or "",
        "priority":         item.get("priority") or item.get("severity") or "Medium",
        # AAVA metadata fields — used by _build_properties_from_aava()
        "test_case_type":   item.get("test_case_type", ""),
        "test_case_status": item.get("test_case_status", ""),
        "implementation":   item.get("implementation", ""),
        "product_area":     item.get("product_area", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — QTEST CONFIGURATION & HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _qtest_ssl_verify():
    """Return SSL verify setting for qTest requests."""
    ca_bundle = os.getenv("QTEST_CA_BUNDLE", "").strip()
    if ca_bundle:
        return ca_bundle
    env_val = os.getenv("QTEST_SSL_VERIFY", "").strip()
    if env_val:
        return env_val.lower() in {"1", "true", "yes", "y", "on"}
    return _QTEST_SSL_VERIFY_DEFAULT


def _qtest_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }


def _qtest_base_url(host: str, project_id: str, workspace_id: str) -> list[str]:
    """Return candidate base URLs in priority order."""
    wid = (workspace_id or "").strip()
    candidates = [f"https://{host}/api/v3/projects/{project_id}"]
    if wid:
        candidates.append(f"https://{host}/api/v3/workspaces/{wid}/projects/{project_id}")
        candidates.append(f"https://{host}/p/{wid}/api/v3/projects/{project_id}")
    return candidates


def _resolve_qtest_base_url(host: str, project_id: str, workspace_id: str,
                             headers: dict, verify_ssl) -> str:
    """
    Try each candidate base URL and return the first that responds (non-404, non-HTML).
    Raises RuntimeError if none succeed.
    """
    for candidate in _qtest_base_url(host, project_id, workspace_id):
        try:
            r = requests.get(
                f"{candidate}/modules",
                headers=headers,
                params={"pageSize": 1},
                timeout=20,
                verify=verify_ssl,
            )
        except SSLError as exc:
            raise RuntimeError(
                "SSL handshake failed. Set QTEST_CA_BUNDLE to your CA cert path, "
                f"or QTEST_SSL_VERIFY=false for testing. Detail: {exc}"
            ) from exc
        except RequestException:
            continue

        if r.status_code == 404:
            continue
        ctype = r.headers.get("Content-Type", "").lower()
        if "text/html" in ctype or r.text.strip().lower().startswith("<html"):
            continue

        return candidate

    raise RuntimeError(
        "qTest API unreachable: all candidate base URLs returned 404 or errors. "
        f"host={host}  project_id={project_id}  workspace_id={workspace_id}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — QTEST MODULE (FOLDER) MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _find_module_id(base_url: str, headers: dict, verify_ssl, module_name: str) -> str | None:
    """
    Find a qTest module (folder) by name (case-insensitive).
    Recursively searches all nested child modules in the entire tree.
    Returns id or None.
    """
    try:
        r = requests.get(f"{base_url}/modules", headers=headers, timeout=20, verify=verify_ssl)
        if not r.ok:
            return None
        modules = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    except Exception:
        return None

    target = module_name.strip().lower()

    def _get_children(node: dict) -> list:
        """Get children using ?parentId= query (qTest does not embed children)."""
        node_id = node.get("id")
        if not node_id:
            return []
        try:
            resp = requests.get(
                f"{base_url}/modules",
                headers=headers,
                params={"parentId": str(node_id)},
                timeout=20,
                verify=verify_ssl,
            )
            if resp.ok:
                data = resp.json()
                if isinstance(data, list):
                    return data
                return data.get("items", data.get("content", []))
        except Exception:
            pass
        return []

    def _search(nodes: list) -> str | None:
        for m in nodes:
            if (m.get("name") or "").strip().lower() == target:
                return str(m["id"])
            children = _get_children(m)
            if children:
                found = _search(children)
                if found:
                    return found
        return None

    return _search(modules)


def _resolve_module_path(base_url: str, headers: dict, verify_ssl, module_path: str) -> str | None:
    """
    Resolve a nested module path (e.g. "Parent/Child/Grandchild") to a module ID.
    Traverses the tree level-by-level using greedy prefix matching.
    Returns the module ID as a string, or None if not found.
    """
    remaining_path = module_path.strip()
    if not remaining_path or "/" not in remaining_path:
        # Not a nested path — fall through to simple name search
        return _find_module_id(base_url, headers, verify_ssl, remaining_path)

    try:
        r = requests.get(f"{base_url}/modules", headers=headers, timeout=20, verify=verify_ssl)
        if not r.ok:
            return None
        modules = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    except Exception:
        return None

    current_nodes = modules

    while remaining_path:
        matched_module = None
        sorted_nodes = sorted(current_nodes, key=lambda m: len(m.get("name") or ""), reverse=True)

        for m in sorted_nodes:
            name = (m.get("name") or "").strip()
            if not name:
                continue
            if remaining_path.lower().startswith(name.lower()):
                after = remaining_path[len(name):]
                if after == "" or after.startswith("/"):
                    matched_module = m
                    remaining_path = after.lstrip("/").strip()
                    break

        if matched_module is None:
            return None

        if not remaining_path:
            return str(matched_module["id"])

        # Get children for next level using ?parentId= query
        parent_id = matched_module["id"]
        children = []
        try:
            resp = requests.get(
                f"{base_url}/modules",
                headers=headers,
                params={"parentId": str(parent_id)},
                timeout=20,
                verify=verify_ssl,
            )
            if resp.ok:
                data = resp.json()
                children = data if isinstance(data, list) else data.get("items", data.get("content", []))
        except Exception:
            return None

        if not children:
            return None
        current_nodes = children

    return None


def _find_or_create_module(
    base_url: str,
    headers: dict,
    verify_ssl,
    module_name: str,
    parent_id: str | int | None = None,
) -> str:
    """
    Find an existing qTest module (folder) by name, or create it if absent.
    Supports creating modules inside nested parents via parent_id.

    Parameters
    ----------
    base_url    : Resolved qTest project base URL
    headers     : Auth headers
    verify_ssl  : SSL verification setting
    module_name : Name of the module to find or create
    parent_id   : Optional parent module ID to create under (for nested modules).
                  If None, creates at the top level.

    Returns the module id as a string.
    Raises RuntimeError if both operations fail.
    """
    # If module_name contains '/', try resolving as a nested path first
    if "/" in module_name:
        resolved = _resolve_module_path(base_url, headers, verify_ssl, module_name)
        if resolved:
            return resolved
        # Path not fully resolved — try to create the leaf under the deepest existing parent
        parts = module_name.rsplit("/", 1)
        if len(parts) == 2:
            parent_path, leaf_name = parts
            parent_resolved = _resolve_module_path(base_url, headers, verify_ssl, parent_path)
            if parent_resolved:
                parent_id = parent_resolved
                module_name = leaf_name
            else:
                raise RuntimeError(
                    f"Cannot create module '{module_name}': parent path '{parent_path}' not found."
                )

    # Simple name search (non-nested)
    if not parent_id:
        existing = _find_module_id(base_url, headers, verify_ssl, module_name)
        if existing:
            return existing

    # Create the module (optionally under a parent)
    body: dict = {
        "name": module_name,
        "description": f"Auto-created {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    }
    if parent_id:
        body["parent_id"] = int(parent_id)

    try:
        resp = requests.post(
            f"{base_url}/modules",
            headers=headers,
            json=body,
            timeout=20,
            verify=verify_ssl,
        )
        if resp.ok:
            mid = resp.json().get("id")
            if mid:
                logger.info("Created module '%s' (id=%s, parent_id=%s)", module_name, mid, parent_id)
                return str(mid)
    except Exception as exc:
        logger.warning("Could not create module '%s': %s", module_name, exc)

    raise RuntimeError(f"Could not find or create qTest module '{module_name}'.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — QTEST FIELD PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────
#
# qTest mandatory/custom fields are passed as a "properties" array in the
# test-case body.  Each entry maps a field_id to a value.
#
# Set them via environment variables: QTEST_FIELD_<NAME>=field_id:value[:label]
# Example: QTEST_FIELD_STATUS=601:1:New
#          QTEST_FIELD_TEST_CASE_TYPE=602:1:Manual

def _build_qtest_properties(overrides: dict | None = None) -> list[dict]:
    """
    Build the 'properties' array for qTest test-case creation.

    overrides: {key: "field_id:value[:label"]} — keys match the _FIELD_KEYS below.
    Falls back to env vars if no override provided.
    """
    overrides = overrides or {}
    _FIELD_KEYS = ["STATUS", "TEST_CASE_TYPE", "TEST_TYPE", "IMPLEMENTATION",
                   "PRODUCT_AREA", "ASSIGNED_TO"]

    properties: list[dict] = []
    for key in _FIELD_KEYS:
        raw = overrides.get(key) or os.getenv(f"QTEST_FIELD_{key}", "").strip()
        if not raw:
            continue
        parts = raw.split(":", 2)
        if len(parts) < 2:
            continue
        entry: dict = {"field_id": int(parts[0].strip()), "field_value": parts[1].strip()}
        if len(parts) == 3:
            entry["field_value_name"] = parts[2].strip()
        properties.append(entry)

    return properties


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — QTEST UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
#
# qTest Test Case Body Schema
# ───────────────────────────
# POST /api/v3/projects/{project_id}/test-cases
# {
#   "name":         <string>              — test case title
#   "description":  <string>              — objective / description
#   "precondition": <string>              — preconditions block
#   "parent_id":    <int>                 — module (folder) id
#   "test_steps": [
#     {
#       "description": <string>,          — step description
#       "expected":    <string>,          — expected result (last step only)
#       "order":       <int>              — 1-based
#     }
#   ],
#   "properties": [                       — optional custom field values
#     { "field_id": <int>, "field_value": <string>, "field_value_name": <string> }
#   ]
# }

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9a — MAP AAVA METADATA TO QTEST PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────
#
# Known qTest field IDs (project 21) and their allowed values:
#   3115 = Test Case Type    → 11891 = "Manual Test case"
#   3163 = Test Type         → 9067  = "Product/Feature"
#   3165 = Implementation    → 9078  = "Global"
#   3168 = Product Area      → 9147  = "Clinical"
#   3114 = Status            → 11882 = "Ready to Test", 201 = "New"

# Mapping from AAVA field_value_name → qTest numeric value ID
_QTEST_FIELD_MAP: dict[int, dict[str, str]] = {
    3115: {  # Test Case Type
        "Manual Test case": "11891",
    },
    3163: {  # Test Type
        "Product/Feature": "9067",
        "Functional": "9067",
    },
    3165: {  # Implementation
        "Global": "9078",
    },
    3168: {  # Product Area
        "Clinical": "9147",
    },
    3114: {  # Status
        "Ready to Test": "11882",
        "New": "201",
    },
}


def _build_properties_from_aava(tc: dict) -> list[dict]:
    """
    Build qTest properties from AAVA metadata fields present in the test case dict.

    Maps these AAVA fields to qTest field IDs:
      test_case_type   → field 3115
      test_type        → field 3163
      implementation   → field 3165
      product_area     → field 3168
      test_case_status → field 3114
    """
    aava_to_field = {
        "test_case_type":   3115,
        "test_type":        3163,
        "implementation":   3165,
        "product_area":     3168,
        "test_case_status": 3114,
    }

    properties: list[dict] = []
    for aava_key, field_id in aava_to_field.items():
        value_name = (tc.get(aava_key) or "").strip()
        if not value_name:
            continue
        lookup = _QTEST_FIELD_MAP.get(field_id, {})
        field_value = lookup.get(value_name, "")
        if field_value:
            properties.append({
                "field_id":         field_id,
                "field_value":      field_value,
                "field_value_name": value_name,
            })
        else:
            # Default: for Product Area (3168), fall back to 'Clinical' since it's
            # the only allowed value in qTest project 21.
            if field_id == 3168:
                properties.append({
                    "field_id":         field_id,
                    "field_value":      "9147",
                    "field_value_name": "Clinical",
                })
                logger.info(
                    "Defaulting Product Area to 'Clinical' (unmapped value: '%s').",
                    value_name,
                )
            else:
                logger.warning(
                    "No qTest value mapping for field %d value '%s'. Skipping.",
                    field_id, value_name,
                )

    return properties


def _upload_single_tc(
    base_url: str,
    headers: dict,
    verify_ssl,
    host: str,
    project_id: str,
    tc: dict,
    module_id: str,
    qtest_properties: list[dict],
) -> dict:
    """
    Upload one test case to qTest.

    Returns
    -------
    {
        "name":      str,
        "status":    "Uploaded" | "Failed (...)",
        "qtest_id":  str | "-",
        "qtest_url": str | None,
    }
    """
    title     = tc.get("title", "Untitled")
    raw_steps = tc.get("steps", [])

    # Build steps payload — support both list[str] and list[dict] formats.
    # When steps are dicts (AAVA format), extract per-step expected_result.
    steps_payload: list[dict] = []
    for i, step in enumerate(raw_steps):
        if isinstance(step, dict):
            desc = step.get("test_case_description", step.get("description", ""))
            exp  = step.get("expected_result", step.get("expected", ""))
        else:
            desc = step
            exp  = ""
        steps_payload.append({"description": desc, "expected": exp, "order": i + 1})

    # Fallback: if steps were plain strings and a single expected_result is provided,
    # place it on the last step only (legacy behavior).
    if steps_payload and all(not s["expected"] for s in steps_payload):
        fallback_expected = tc.get("expected_result", "")
        if fallback_expected:
            steps_payload[-1]["expected"] = fallback_expected

    # Map AAVA metadata fields to qTest properties if not already provided.
    properties = list(qtest_properties) if qtest_properties else []
    if not properties:
        properties = _build_properties_from_aava(tc)

    body: dict = {
        "name":         title,
        "description":  tc.get("objective", tc.get("description", "")),
        "precondition": tc.get("preconditions", tc.get("precondition", "")),
        "test_steps":   steps_payload,
        "parent_id":    int(module_id),
    }

    if properties:
        body["properties"] = properties

    try:
        resp = requests.post(
            f"{base_url}/test-cases",
            headers=headers,
            json=body,
            timeout=20,
            verify=verify_ssl,
        )
    except SSLError as exc:
        raise RuntimeError(
            f"SSL error uploading test case '{title}'. "
            "Set QTEST_CA_BUNDLE or QTEST_SSL_VERIFY=false. "
            f"Detail: {exc}"
        ) from exc

    if resp.ok and "text/html" not in resp.headers.get("Content-Type", "").lower():
        try:
            uploaded_id = str(resp.json().get("id", ""))
        except Exception:
            uploaded_id = ""
        qtest_url = (
            f"https://{host}/p/{project_id}/portal/project#tab=testdesign&object=1&id={uploaded_id}"
            if uploaded_id else None
        )
        return {
            "name":      title,
            "status":    "Uploaded" if uploaded_id else "Failed (no id returned)",
            "qtest_id":  uploaded_id or "-",
            "qtest_url": qtest_url,
        }
    else:
        return {
            "name":      title,
            "status":    f"Failed ({resp.status_code}): {(resp.text or '')[:120]}",
            "qtest_id":  "-",
            "qtest_url": None,
        }


def upload_to_qtest(
    tc_list: list[dict],
    host: str,
    token: str,
    project_id: str,
    module_name: str,
    workspace_id: str = "",
    qtest_field_overrides: dict | None = None,
    parent_module_id: str | int | None = None,
) -> dict[str, Any]:
    """
    Upload a list of test case dicts to qTest Manager.

    Parameters
    ----------
    tc_list              : Output of parse_scenarios_to_tc_list()
    host                 : qTest domain without https://  e.g. mycompany.qtestnet.com
    token                : Bearer token from qTest Manager
    project_id           : Numeric qTest project ID as a string
    module_name          : Module (folder) name in qTest  e.g. "AI Generated Test Cases"
                           Supports nested paths like "Parent/Child/NewModule".
    workspace_id         : Optional workspace / site ID
    qtest_field_overrides: Optional dict to override custom field values
    parent_module_id     : Optional parent module ID for creating nested modules.
                           If provided, the module will be created under this parent.

    Returns
    -------
    {
        "success_count": int,
        "fail_count":    int,
        "module_id":     str | None,
        "results": [
            {
                "name":      str,
                "status":    "Uploaded" | "Failed (...)",
                "qtest_id":  str,
                "qtest_url": str | None,
            }
        ]
    }
    """
    verify_ssl = _qtest_ssl_verify()
    headers    = _qtest_headers(token)

    # ── 1. Resolve the working base URL ───────────────────────
    base_url = _resolve_qtest_base_url(host, project_id, workspace_id, headers, verify_ssl)
    logger.info("Resolved qTest base URL: %s", base_url)

    # ── 2. Find or create the target module (folder) ──────────
    module_id = _find_or_create_module(base_url, headers, verify_ssl, module_name, parent_id=parent_module_id)
    logger.info("qTest module '%s' → id=%s", module_name, module_id)

    # ── 3. Build field properties once ────────────────────────
    qtest_properties = _build_qtest_properties(qtest_field_overrides)

    # ── 4. Upload each test case ───────────────────────────────
    results: list[dict] = []
    for tc in tc_list:
        result = _upload_single_tc(
            base_url, headers, verify_ssl,
            host, project_id, tc, module_id, qtest_properties,
        )
        results.append(result)
        status_icon = "✓" if "Uploaded" in result["status"] else "✗"
        logger.info("  %s %s  →  %s", status_icon, tc.get("title", "?"), result["status"])

    success_count = sum(1 for r in results if "Uploaded" in r["status"])
    return {
        "success_count": success_count,
        "fail_count":    len(results) - success_count,
        "module_id":     module_id,
        "results":       results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — FULL PIPELINE (ENTRY POINT FOR CUSTOM AGENT)
# ─────────────────────────────────────────────────────────────────────────────

def run_full_pipeline(
    user_story: dict,
    qtest_config: dict,
    existing_titles: list[str] | None = None,
) -> dict[str, Any]:
    """
    End-to-end pipeline: user story → AAVA → parsed TCs → qTest upload.

    Parameters
    ----------
    user_story : {
        "id":                  int,   — Optional ADO work item ID
        "title":               str,   — User story title / feature name
        "description":         str,   — Functional description
        "acceptance_criteria": str,   — Acceptance criteria (optional)
    }

    qtest_config : {
        "host":         str,   — e.g. "mycompany.qtestnet.com"
        "token":        str,   — Bearer token
        "project_id":   str,   — Numeric project ID
        "workspace_id": str,   — Optional
        "module":       str,   — Target folder name in qTest
    }

    existing_titles : Previously existing TC titles to skip (deduplication)

    Returns
    -------
    {
        "status":          "success" | "partial" | "failed",
        "tc_count":        int,
        "upload_results":  list[dict] | None,
        "success_count":   int,
        "fail_count":      int,
        "module_id":       str | None,
        "aava_error":      str | None,
        "parse_error":     str | None,
    }
    """
    result: dict[str, Any] = {
        "status":         "failed",
        "tc_count":       0,
        "upload_results": None,
        "success_count":  0,
        "fail_count":     0,
        "module_id":      None,
        "aava_error":     None,
        "parse_error":    None,
    }

    # ── Step 1: Call AAVA ─────────────────────────────────────
    logger.info("Step 1: Calling AAVA Test Case Generator for '%s'", user_story.get("title"))
    aava_result = call_aava_agent(
        title=user_story.get("title", ""),
        description=user_story.get("description", ""),
        acceptance_criteria=user_story.get("acceptance_criteria", ""),
        story_id=user_story.get("id"),
        existing_titles=existing_titles,
    )

    if not aava_result["success"]:
        result["aava_error"] = aava_result["error"]
        logger.error("AAVA call failed: %s", aava_result["error"])
        return result

    scenarios_payload = aava_result["scenarios"]
    if not scenarios_payload:
        result["parse_error"] = "AAVA returned a response but no 'scenarios' key was found."
        logger.error("No scenarios found in AAVA response. Raw: %s", str(aava_result["raw"])[:300])
        return result

    # ── Step 2: Parse response into TC list ───────────────────
    logger.info("Step 2: Parsing AAVA scenarios response")
    tc_list = parse_scenarios_to_tc_list(scenarios_payload)
    result["tc_count"] = len(tc_list)

    if not tc_list:
        result["parse_error"] = "Parsed 0 test cases from the AAVA scenarios payload."
        return result

    logger.info("Parsed %d test cases", len(tc_list))

    # ── Step 3: Upload to qTest ───────────────────────────────
    logger.info("Step 3: Uploading %d test cases to qTest", len(tc_list))
    upload_result = upload_to_qtest(
        tc_list=tc_list,
        host=qtest_config["host"],
        token=qtest_config["token"],
        project_id=qtest_config["project_id"],
        module_name=qtest_config.get("module", "AI Generated Test Cases"),
        workspace_id=qtest_config.get("workspace_id", ""),
    )

    result["upload_results"] = upload_result["results"]
    result["success_count"]  = upload_result["success_count"]
    result["fail_count"]     = upload_result["fail_count"]
    result["module_id"]      = upload_result["module_id"]
    result["status"]         = (
        "success" if upload_result["fail_count"] == 0
        else "partial" if upload_result["success_count"] > 0
        else "failed"
    )

    logger.info(
        "Pipeline complete. %d/%d uploaded. Status: %s",
        result["success_count"], result["tc_count"], result["status"],
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10b — FETCH TEST CASES FROM QTEST
# ─────────────────────────────────────────────────────────────────────────────

def fetch_from_qtest(
    host: str | None = None,
    token: str | None = None,
    project_id: str | None = None,
    workspace_id: str | None = None,
    module_name: str | None = None,
    module_id: str | None = None,
    tc_id: str | int | None = None,
) -> dict[str, Any]:
    """
    Fetch test cases from qTest Manager.

    Modes
    -----
    - If `tc_id` is provided: fetch a single test case by ID.
    - If `module_name` or `module_id` is provided: fetch all TCs in that module.
    - If neither: use the default module from QTEST_CONFIG.

    Parameters
    ----------
    host         : qTest domain (defaults to QTEST_CONFIG["host"])
    token        : Bearer token (defaults to QTEST_CONFIG["token"])
    project_id   : Project ID (defaults to QTEST_CONFIG["project_id"])
    workspace_id : Workspace ID (defaults to QTEST_CONFIG["workspace_id"])
    module_name  : Module name to fetch TCs from
    module_id    : Module ID to fetch TCs from (takes priority over module_name)
    tc_id        : Specific test case ID to fetch

    Returns
    -------
    {
        "success":      bool,
        "test_cases":   list[dict],    — list of TC objects from qTest
        "total_count":  int,
        "module_name":  str | None,
        "module_id":    str | None,
        "error":        str | None,
    }
    """
    host         = host or QTEST_CONFIG["host"]
    token        = token or QTEST_CONFIG["token"]
    project_id   = project_id or QTEST_CONFIG["project_id"]
    workspace_id = workspace_id or QTEST_CONFIG.get("workspace_id", "")
    module_name  = module_name or QTEST_CONFIG.get("module", "Created via API")

    verify_ssl = _qtest_ssl_verify()
    headers    = _qtest_headers(token)

    try:
        base_url = _resolve_qtest_base_url(host, project_id, workspace_id, headers, verify_ssl)
    except RuntimeError as exc:
        return {"success": False, "test_cases": [], "total_count": 0,
                "module_name": module_name, "module_id": module_id, "error": str(exc)}

    # ── Single test case by ID ────────────────────────────────
    if tc_id:
        try:
            resp = requests.get(
                f"{base_url}/test-cases/{tc_id}",
                headers=headers,
                timeout=30,
                verify=verify_ssl,
            )
            if resp.status_code == 401:
                return {"success": False, "test_cases": [], "total_count": 0,
                        "module_name": None, "module_id": None,
                        "error": "AUTH_EXPIRED: qTest returned 401. Update token in aava_qtest_config.py."}
            if resp.status_code == 404:
                return {"success": False, "test_cases": [], "total_count": 0,
                        "module_name": None, "module_id": None,
                        "error": f"NOT_FOUND: Test case {tc_id} does not exist."}
            resp.raise_for_status()
            tc_data = resp.json()
            return {"success": True, "test_cases": [tc_data], "total_count": 1,
                    "module_name": None, "module_id": None, "error": None}
        except SSLError as exc:
            return {"success": False, "test_cases": [], "total_count": 0,
                    "module_name": None, "module_id": None,
                    "error": f"SSL_ERROR: {exc}"}
        except RequestException as exc:
            return {"success": False, "test_cases": [], "total_count": 0,
                    "module_name": None, "module_id": None,
                    "error": f"REQUEST_FAILED: {exc}"}

    # ── Resolve module ID ─────────────────────────────────────
    if not module_id:
        module_id = _find_module_id(base_url, headers, verify_ssl, module_name)
        if not module_id:
            return {"success": False, "test_cases": [], "total_count": 0,
                    "module_name": module_name, "module_id": None,
                    "error": f"MODULE_NOT_FOUND: Module '{module_name}' does not exist in project {project_id}."}

    # ── Paginated fetch of all TCs in module ──────────────────
    page = 1
    page_size = 100
    all_tcs: list[dict] = []

    try:
        while True:
            resp = requests.get(
                f"{base_url}/test-cases",
                headers=headers,
                params={"parentId": module_id, "page": page, "pageSize": page_size},
                timeout=30,
                verify=verify_ssl,
            )
            if resp.status_code == 401:
                return {"success": False, "test_cases": [], "total_count": 0,
                        "module_name": module_name, "module_id": module_id,
                        "error": "AUTH_EXPIRED: qTest returned 401. Update token in aava_qtest_config.py."}
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("items", data.get("content", []))
            if not items:
                break
            all_tcs.extend(items)
            if len(items) < page_size:
                break
            page += 1
    except SSLError as exc:
        return {"success": False, "test_cases": all_tcs, "total_count": len(all_tcs),
                "module_name": module_name, "module_id": module_id,
                "error": f"SSL_ERROR: {exc}"}
    except RequestException as exc:
        return {"success": False, "test_cases": all_tcs, "total_count": len(all_tcs),
                "module_name": module_name, "module_id": module_id,
                "error": f"REQUEST_FAILED: {exc}"}

    logger.info("Fetched %d test cases from module '%s' (id=%s)", len(all_tcs), module_name, module_id)
    return {
        "success":     True,
        "test_cases":  all_tcs,
        "total_count": len(all_tcs),
        "module_name": module_name,
        "module_id":   module_id,
        "error":       None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10c — QTEST REQUIREMENT LINKING
# ─────────────────────────────────────────────────────────────────────────────
#
# qTest Requirements → Test Case Linking
# ───────────────────────────────────────
# qTest supports linking external requirements (e.g. ADO work items) to test
# cases for traceability.  The flow is:
#   1. Find or create a Requirement in qTest (representing the ADO work item)
#   2. Link each uploaded test case to that requirement
#
# API Endpoints
# ─────────────
#   GET  /requirements                       → list requirements
#   POST /requirements                       → create a requirement
#   POST /requirements/{req_id}/link?type=test-cases  → link TCs to a requirement
#   POST /test-cases/{tc_id}/requirements    → link a requirement to a TC
#


def find_or_create_requirement(
    base_url: str,
    headers: dict,
    verify_ssl,
    requirement_name: str,
    external_id: str | int | None = None,
    description: str = "",
    parent_id: int | str | None = None,
) -> dict[str, Any]:
    """
    Search qTest for an existing requirement by name, recursively traversing
    all nested requirement modules (branches) until the entire tree is exhausted.

    If NOT found after a full recursive search, returns a result with
    ``"not_found": True`` so the caller (the agent) can notify the user and
    ask for approval before taking further action.  This function does NOT
    auto-create requirements.

    Parameters
    ----------
    base_url         : Resolved qTest project base URL
    headers          : Auth headers
    verify_ssl       : SSL verification setting
    requirement_name : Name of the requirement (e.g. ADO work item title)
    external_id      : External reference ID (e.g. ADO work item ID)
    description      : Description text
    parent_id        : Optional parent requirement/module ID

    Returns
    -------
    {"id": str, "name": str, "not_found": bool, "error": str | None}
    """
    target_lower = requirement_name.strip().lower()

    # qTest naming convention: requirements are named "WI<work_item_id>: <title>"
    # (e.g. "WI598048: CSGPT - Bulk delete multiple chat threads")
    # Build the WI-prefixed search target from the external_id
    wi_prefix_lower = f"wi{str(external_id).strip()}".lower() if external_id else None

    def _search_requirements_page(page: int = 1, page_size: int = 100) -> list[dict]:
        """Fetch a page of top-level requirements."""
        try:
            resp = requests.get(
                f"{base_url}/requirements",
                headers=headers,
                params={"pageSize": page_size, "page": page},
                timeout=30,
                verify=verify_ssl,
            )
            if resp.ok:
                data = resp.json()
                return data if isinstance(data, list) else data.get("items", data.get("content", []))
        except RequestException as exc:
            logger.warning("Failed to fetch requirements page %d: %s", page, exc)
        return []

    def _get_children(parent: dict) -> list[dict]:
        """Get child requirements for a parent node.
        
        Uses parentId query param as the primary strategy (confirmed to work
        on this qTest instance — the /requirements/{id} endpoint does NOT
        embed children in the response).
        """
        parent_id_val = parent.get("id")
        if not parent_id_val:
            return []

        # Primary strategy: GET /requirements?parentId={id}
        try:
            resp = requests.get(
                f"{base_url}/requirements",
                headers=headers,
                params={"parentId": parent_id_val, "pageSize": 100},
                timeout=20,
                verify=verify_ssl,
            )
            if resp.ok:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("items", data.get("content", []))
                if items:
                    return items
        except RequestException:
            pass

        # Fallback: check embedded children (for API versions that support it)
        children = parent.get("children", parent.get("sub_requirements", []))
        if children:
            return children

        return []

    def _recursive_search(nodes: list[dict]) -> dict | None:
        """Recursively search nodes and their children for matching requirement.
        
        Matches by:
        1. Full requirement name (exact match)
        2. WI-prefixed ID pattern — startswith "WI{id}" (e.g. "WI598048: ...")
           This is qTest's naming convention: "WI<work_item_id>: <title>"
        """
        for node in nodes:
            node_name = (node.get("name") or "").strip().lower()
            # Match by full title OR by WI{external_id} prefix pattern
            if node_name == target_lower:
                logger.info("Found requirement by title: '%s' (id=%s)", node.get("name"), node["id"])
                return {"id": str(node["id"]), "name": node.get("name", ""), "not_found": False, "error": None}
            if wi_prefix_lower and node_name.startswith(wi_prefix_lower):
                logger.info("Found requirement by WI prefix: '%s' (id=%s)", node.get("name"), node["id"])
                return {"id": str(node["id"]), "name": node.get("name", ""), "not_found": False, "error": None}

            # Recurse into children (sub-modules / nested requirements)
            children = _get_children(node)
            if children:
                result = _recursive_search(children)
                if result is not None:
                    return result
        return None

    # ── Paginate through ALL requirements (flat list) and match ───────
    # qTest returns requirements as a flat paginated list (20 per page, ignores pageSize).
    # Each item has parent_id indicating which module it belongs to.
    # We scan all pages looking for a name match or WI prefix match.
    try:
        page = 1
        max_pages = 100  # Safety limit (20 items * 100 pages = 2000 requirements max)
        while page <= max_pages:
            top_level = _search_requirements_page(page=page)
            if not top_level:
                break  # no more pages

            # Direct match on this page (no recursion needed — it's a flat list)
            for node in top_level:
                node_name = (node.get("name") or "").strip().lower()
                if node_name == target_lower:
                    logger.info("Found requirement by title on page %d: '%s' (id=%s)",
                                page, node.get("name"), node["id"])
                    return {"id": str(node["id"]), "name": node.get("name", ""),
                            "not_found": False, "error": None}
                if wi_prefix_lower and node_name.startswith(wi_prefix_lower):
                    logger.info("Found requirement by WI prefix on page %d: '%s' (id=%s)",
                                page, node.get("name"), node["id"])
                    return {"id": str(node["id"]), "name": node.get("name", ""),
                            "not_found": False, "error": None}

            # qTest returns exactly 20 per page regardless of pageSize param.
            # If we got fewer than 20, we've reached the last page.
            if len(top_level) < 20:
                break
            page += 1

    except RequestException as exc:
        logger.warning("Failed to search requirements: %s", exc)
        return {"id": None, "name": requirement_name, "not_found": False,
                "error": f"Failed to search requirements: {exc}"}

    # ── Requirement not found after scanning all pages ─────
    logger.info("Requirement '%s' (WI prefix: '%s') not found in qTest after scanning %d pages.",
                requirement_name, wi_prefix_lower or "N/A", page)
    return {"id": None, "name": requirement_name, "not_found": True, "error": None}


def link_test_cases_to_requirement(
    base_url: str,
    headers: dict,
    verify_ssl,
    requirement_id: int | str,
    test_case_ids: list[int | str],
) -> dict[str, Any]:
    """
    Link one or more test cases to a requirement in qTest.

    Parameters
    ----------
    base_url        : Resolved qTest project base URL
    headers         : Auth headers
    verify_ssl      : SSL verification setting
    requirement_id  : qTest requirement ID
    test_case_ids   : List of qTest test case IDs to link

    Returns
    -------
    {
        "success_count": int,
        "fail_count": int,
        "results": [{"tc_id": str, "status": "Linked" | "Failed (...)"}]
    }
    """
    results: list[dict] = []

    for tc_id in test_case_ids:
        try:
            # POST /requirements/{req_id}/link?type=test-cases
            # This is the correct endpoint for linking TCs to a requirement in qTest v3.
            resp = requests.post(
                f"{base_url}/requirements/{requirement_id}/link",
                headers=headers,
                params={"type": "test-cases"},
                json=[int(tc_id)],
                timeout=20,
                verify=verify_ssl,
            )
            if resp.ok:
                results.append({"tc_id": str(tc_id), "status": "Linked"})
                logger.info("Linked TC %s → Requirement %s", tc_id, requirement_id)
            else:
                results.append({"tc_id": str(tc_id),
                                "status": f"Failed ({resp.status_code}): {resp.text[:100]}"})
        except RequestException as exc:
            results.append({"tc_id": str(tc_id), "status": f"Failed: {exc}"})

    success_count = sum(1 for r in results if r["status"] == "Linked")
    return {
        "success_count": success_count,
        "fail_count": len(results) - success_count,
        "results": results,
    }


def link_requirement_to_test_cases(
    requirement_name: str,
    test_case_ids: list[int | str],
    external_id: str | int | None = None,
    description: str = "",
    host: str | None = None,
    token: str | None = None,
    project_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """
    High-level function: find/create a requirement and link test cases to it.

    Parameters
    ----------
    requirement_name : Name for the requirement (e.g. ADO user story title)
    test_case_ids    : List of qTest test case IDs to link
    external_id      : External ID (e.g. ADO work item ID) for traceability
    description      : Requirement description
    host             : qTest host (defaults to QTEST_CONFIG)
    token            : Bearer token (defaults to QTEST_CONFIG)
    project_id       : Project ID (defaults to QTEST_CONFIG)
    workspace_id     : Workspace ID (defaults to QTEST_CONFIG)

    Returns
    -------
    {
        "success":         bool,
        "requirement_id":  str | None,
        "requirement_name": str,
        "not_found":       bool,
        "link_results":    list[dict],
        "success_count":   int,
        "fail_count":      int,
        "error":           str | None,
    }
    """
    host         = host or QTEST_CONFIG["host"]
    token        = token or QTEST_CONFIG["token"]
    project_id   = project_id or QTEST_CONFIG["project_id"]
    workspace_id = workspace_id or QTEST_CONFIG.get("workspace_id", "")

    verify_ssl = _qtest_ssl_verify()
    headers    = _qtest_headers(token)

    result: dict[str, Any] = {
        "success": False, "requirement_id": None, "requirement_name": requirement_name,
        "not_found": False, "link_results": [], "success_count": 0, "fail_count": 0,
        "error": None,
    }

    # ── 1. Resolve base URL ───────────────────────────────────
    try:
        base_url = _resolve_qtest_base_url(host, project_id, workspace_id, headers, verify_ssl)
    except RuntimeError as exc:
        result["error"] = str(exc)
        return result

    # ── 2. Search for the requirement ────────────────────────
    req_info = find_or_create_requirement(
        base_url, headers, verify_ssl,
        requirement_name=requirement_name,
        external_id=external_id,
        description=description,
    )
    if req_info.get("error"):
        result["error"] = req_info["error"]
        return result

    if req_info.get("not_found"):
        result["not_found"] = True
        result["error"] = (
            f"Requirement '{requirement_name}' not found in qTest. "
            "User approval is required to proceed."
        )
        return result

    result["requirement_id"] = req_info["id"]
    result["not_found"] = False

    # ── 3. Link test cases to the requirement ─────────────────
    link_result = link_test_cases_to_requirement(
        base_url, headers, verify_ssl,
        requirement_id=req_info["id"],
        test_case_ids=test_case_ids,
    )

    result["link_results"] = link_result["results"]
    result["success_count"] = link_result["success_count"]
    result["fail_count"] = link_result["fail_count"]
    result["success"] = link_result["fail_count"] == 0

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10d — QTEST TEST EXECUTION (Suites, Runs, Execution Logs)
# ─────────────────────────────────────────────────────────────────────────────
#
# qTest Test Execution Hierarchy
# ──────────────────────────────
#   Test Suite  (container — e.g. "Sprint 42 Regression")
#     └── Test Run  (links a Test Case to the suite)
#           └── Test Log  (execution result with step-level pass/fail)
#
# API Endpoints (VALIDATED 2026-05-29)
# ─────────────────────────────────────
#   POST /test-suites                            → create a suite
#   GET  /test-suites                            → list suites
#   POST /test-runs                              → create a test run in a suite
#   GET  /test-runs?parentId=<suite_id>&parentType=test-suite
#   POST /test-runs/<run_id>/test-logs           → submit execution log (CORRECT)
#   POST /test-runs/<run_id>/auto-test-logs      → 403 "Automation not turned on" (DO NOT USE)
#   PUT  /test-cases/<id>/approve                → approve TC version (required before log)
#   GET  /test-cases/<id>/versions/<ver>/test-steps → fetch step IDs (required)
#
# test-logs Body Schema (WORKING)
# ───────────────────────────────
# {
#   "status":               {"id": 601, "name": "Passed"},   ← object, NOT string
#   "exe_start_date":       "2026-05-29T10:00:00Z",
#   "exe_end_date":         "2026-05-29T10:05:00Z",
#   "note":                 "Executed via TestGenAgent",
#   "test_case_version_id": 311405,                          ← required (approved version)
#   "test_step_logs": [
#     {
#       "test_step_id":  4089883,                            ← required (from GET test-steps)
#       "actual_result": "Page loaded successfully",
#       "status":        {"id": 601},                        ← object, NOT string
#       "order":         1
#     }
#   ],
#   "properties": [                                          ← required in body
#     {"field_id": 3128, "field_value": "11902"},            ← Execution Type = Manual
#     {"field_id": 3167, "field_value": "9117"},             ← Implementation = Regression
#     {"field_id": 3171, "field_value": "9169"},             ← Product Area = Clinical
#     {"field_id": 3276, "field_value": "10075"}             ← Testing Type = Functional Testing
#   ]
# }
#
# Step Execution Status IDs:  601=Passed, 602=Failed, 605=Unexecuted
# Overall Status IDs:         601=Passed, 602=Failed, 605=Unexecuted
#
# IMPORTANT: Properties are PROJECT-SPECIFIC. The field IDs and allowed values
# above are for project 21. Use _discover_test_run_properties() to auto-detect
# the correct values for any project.


def find_or_create_test_suite(
    base_url: str,
    headers: dict,
    verify_ssl,
    suite_name: str,
    parent_id: int | str | None = None,
    parent_type: str = "root",
    properties: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Find an existing test suite by name, or create a new one.

    Parameters
    ----------
    base_url    : Resolved qTest project base URL
    headers     : Auth headers
    verify_ssl  : SSL verification setting
    suite_name  : Name of the test suite (e.g. "Sprint 42 Regression")
    parent_id   : Optional parent suite/cycle/release ID for nesting
    parent_type : "root" | "test-suite" | "test-cycle" | "release"
    properties  : Optional list of property dicts to set on the suite.
                  If None, auto-discovers properties from existing suites
                  in the project and applies sensible defaults.

    Returns
    -------
    {"id": str, "name": str, "created": bool}
    """
    # ── Search for existing suite ─────────────────────────────
    try:
        params = {"parentId": parent_id, "parentType": parent_type} if parent_id else {}
        resp = requests.get(
            f"{base_url}/test-suites",
            headers=headers,
            params=params,
            timeout=20,
            verify=verify_ssl,
        )
        if resp.ok:
            suites = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
            for s in suites:
                if (s.get("name") or "").strip().lower() == suite_name.strip().lower():
                    logger.info("Found existing test suite '%s' (id=%s)", suite_name, s["id"])
                    return {"id": str(s["id"]), "name": s["name"], "created": False}
    except RequestException as exc:
        logger.warning("Failed to list test suites: %s", exc)

    # ── Auto-discover properties from existing suites if not provided ─────
    if properties is None:
        properties = _discover_suite_properties(base_url, headers, verify_ssl)

    # ── Create new suite ──────────────────────────────────────
    body: dict[str, Any] = {"name": suite_name}
    if parent_id:
        body["parentId"] = int(parent_id)
        body["parentType"] = parent_type
    if properties:
        body["properties"] = properties

    try:
        resp = requests.post(
            f"{base_url}/test-suites",
            headers=headers,
            json=body,
            timeout=20,
            verify=verify_ssl,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Created test suite '%s' (id=%s) with properties", suite_name, data["id"])
        return {"id": str(data["id"]), "name": data.get("name", suite_name), "created": True}
    except RequestException as exc:
        raise RuntimeError(f"Failed to create test suite '{suite_name}': {exc}") from exc


def _discover_suite_properties(
    base_url: str,
    headers: dict,
    verify_ssl,
) -> list[dict]:
    """
    Auto-discover required test suite properties by reading existing suites
    in the project and extracting their property field IDs and default values.

    Falls back to known defaults if no suites exist.

    Returns a list of property dicts ready to use in suite creation.
    """
    try:
        resp = requests.get(
            f"{base_url}/test-suites",
            headers=headers,
            params={"pageSize": 10},
            timeout=20,
            verify=verify_ssl,
        )
        if resp.ok:
            suites = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
            # Find a suite that has properties filled in (non-empty field values)
            for s in suites:
                props = s.get("properties", [])
                # Check if this suite has the key required fields populated
                filled = {p["field_id"]: p for p in props if p.get("field_value")}
                if filled:
                    # Build properties list using discovered field IDs with defaults
                    result = []
                    for p in props:
                        fid = p["field_id"]
                        fname = p.get("field_name", "")
                        fval = p.get("field_value", "")
                        # Use discovered values as defaults for required fields
                        if fval:
                            result.append({"field_id": fid, "field_value": fval})
                        elif fname in ("Description", "Target Release/Build", "Environment"):
                            # Optional fields — skip if empty
                            continue
                        else:
                            # Required but empty in this suite — try to find from other suites
                            for s2 in suites:
                                for p2 in s2.get("properties", []):
                                    if p2["field_id"] == fid and p2.get("field_value"):
                                        result.append({"field_id": fid, "field_value": p2["field_value"]})
                                        break
                                else:
                                    continue
                                break
                    if result:
                        logger.info("Auto-discovered %d suite properties from existing suites", len(result))
                        return result
    except RequestException as exc:
        logger.warning("Failed to discover suite properties: %s", exc)

    # Fallback: return empty — suite will be created without properties
    logger.warning("Could not discover suite properties — creating suite without properties")
    return []


def create_test_run(
    base_url: str,
    headers: dict,
    verify_ssl,
    test_case_id: int | str,
    suite_id: int | str,
    test_run_name: str | None = None,
) -> dict[str, Any]:
    """
    Create a test run inside a test suite, linked to a specific test case.

    Parameters
    ----------
    base_url      : Resolved qTest project base URL
    headers       : Auth headers
    verify_ssl    : SSL verification setting
    test_case_id  : qTest test case ID
    suite_id      : qTest test suite ID
    test_run_name : Optional name; defaults to "Run - TC <test_case_id>"

    Returns
    -------
    {"id": str, "name": str, "test_case_id": str}
    """
    name = test_run_name or f"Run - TC {test_case_id}"
    body = {
        "name": name,
        "test_case": {"id": int(test_case_id)},
        "parentId": int(suite_id),
        "parentType": "test-suite",
    }

    try:
        resp = requests.post(
            f"{base_url}/test-runs",
            headers=headers,
            json=body,
            timeout=20,
            verify=verify_ssl,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Created test run '%s' (id=%s) for TC %s in suite %s",
                     name, data["id"], test_case_id, suite_id)
        return {"id": str(data["id"]), "name": data.get("name", name),
                "test_case_id": str(test_case_id)}
    except RequestException as exc:
        raise RuntimeError(
            f"Failed to create test run for TC {test_case_id} in suite {suite_id}: {exc}"
        ) from exc


def _discover_test_run_properties(
    base_url: str,
    headers: dict,
    verify_ssl,
) -> list[dict]:
    """
    Auto-discover the required test-run properties for the current project.

    Strategy:
    1. Try GET /settings/test-runs/fields — if 200, extract required fields
       and their first allowed value.
    2. If 403 (no admin access), find any existing test run in the project
       that already has properties filled, and copy those field_id/field_value pairs.
    3. If no existing runs found, return empty list (caller should handle gracefully).

    Returns a list of {"field_id": int, "field_value": str} dicts.
    """
    # ── Approach 1: Try the settings API ──────────────────────
    try:
        resp = requests.get(
            f"{base_url}/settings/test-runs/fields",
            headers=headers,
            timeout=20,
            verify=verify_ssl,
        )
        if resp.status_code == 200:
            fields = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
            properties: list[dict] = []
            for field in fields:
                if not field.get("required", False):
                    continue
                field_id = field.get("id")
                # Get first allowed value
                allowed = field.get("allowed_values", [])
                if allowed and field_id:
                    first_val = allowed[0]
                    val = str(first_val.get("value", first_val.get("id", "")))
                    if val:
                        properties.append({"field_id": field_id, "field_value": val})
            if properties:
                logger.info("Discovered %d required test-run properties from settings API", len(properties))
                return properties
    except RequestException:
        pass

    # ── Approach 2: Read from an existing test run ────────────
    logger.info("Settings API unavailable (403); attempting to discover properties from existing test runs")
    try:
        # Find any test run that has properties filled
        resp = requests.get(
            f"{base_url}/test-runs",
            headers=headers,
            params={"page": 1, "pageSize": 20},
            timeout=20,
            verify=verify_ssl,
        )
        if resp.ok:
            runs_data = resp.json()
            runs = runs_data if isinstance(runs_data, list) else runs_data.get("items", runs_data.get("content", []))

            for run in runs:
                run_id = run.get("id")
                if not run_id:
                    continue
                # Fetch full test run details to get properties
                detail_resp = requests.get(
                    f"{base_url}/test-runs/{run_id}",
                    headers=headers,
                    timeout=20,
                    verify=verify_ssl,
                )
                if not detail_resp.ok:
                    continue
                run_detail = detail_resp.json()
                run_props = run_detail.get("properties", [])

                # Filter to properties that have a value set
                filled_props: list[dict] = []
                for prop in run_props:
                    field_id = prop.get("field_id")
                    field_value = prop.get("field_value")
                    if field_id and field_value and str(field_value).strip():
                        filled_props.append({
                            "field_id": field_id,
                            "field_value": str(field_value),
                        })

                if filled_props:
                    logger.info(
                        "Discovered %d properties from existing test run %s: %s",
                        len(filled_props), run_id,
                        [(p["field_id"], p["field_value"]) for p in filled_props],
                    )
                    return filled_props
    except RequestException as exc:
        logger.warning("Failed to discover properties from existing test runs: %s", exc)

    logger.warning("Could not discover test-run properties — submission may fail if fields are required")
    return []


# Module-level cache for discovered properties (avoids repeated API calls per session)
_DISCOVERED_PROPERTIES_CACHE: dict[str, list[dict]] = {}

# Known-correct execution-level properties for project 21.
# Auto-discovery picks up wrong values for Implementation (gets "Global" instead of
# "Regression") because the settings API returns the first allowed value, not the
# contextually correct one for execution logs.
_KNOWN_EXECUTION_PROPERTIES: dict[str, list[dict]] = {
    "21": [
        {"field_id": 3128, "field_value": "11902"},   # Execution Type = Manual
        {"field_id": 3167, "field_value": "9117"},    # Implementation = Regression
        {"field_id": 3171, "field_value": "9169"},    # Product Area = Clinical
        {"field_id": 3276, "field_value": "10075"},   # Testing Type = Functional Testing
    ],
}


def _get_or_discover_properties(
    base_url: str,
    headers: dict,
    verify_ssl,
    project_id: str,
) -> list[dict]:
    """
    Return cached properties for the project, or discover them on first call.
    Uses known-correct values for recognized projects (auto-discovery is unreliable
    for the Implementation field which differs between test design and execution).
    """
    if project_id not in _DISCOVERED_PROPERTIES_CACHE:
        # Use known-correct properties for recognized projects
        if project_id in _KNOWN_EXECUTION_PROPERTIES:
            _DISCOVERED_PROPERTIES_CACHE[project_id] = _KNOWN_EXECUTION_PROPERTIES[project_id]
            logger.info("Using known-correct execution properties for project %s", project_id)
        else:
            _DISCOVERED_PROPERTIES_CACHE[project_id] = _discover_test_run_properties(
                base_url, headers, verify_ssl
            )
    return _DISCOVERED_PROPERTIES_CACHE[project_id]


def submit_execution_log(
    base_url: str,
    headers: dict,
    verify_ssl,
    test_run_id: int | str,
    overall_status: str,
    test_step_logs: list[dict],
    exe_start_date: str | None = None,
    exe_end_date: str | None = None,
    note: str = "",
    test_case_version_id: int | str | None = None,
    properties: list[dict] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """
    Submit an execution log (with step-level results) to a test run.

    Uses POST /test-runs/{runId}/test-logs (NOT auto-test-logs which returns 403).

    Parameters
    ----------
    test_run_id           : qTest test run ID
    overall_status        : "PASS" | "FAIL" | "UNEXECUTED"
    test_step_logs        : List of step results, each with:
                            {
                              "test_step_id": int,        ← required (from GET test-steps)
                              "actual_result": str,
                              "status": {"id": int},      ← 601=Passed, 602=Failed, 605=Unexecuted
                              "order": int (1-based)
                            }
                            ALL steps must be included (count must match test case steps).
    exe_start_date        : ISO-8601 start time (defaults to now)
    exe_end_date          : ISO-8601 end time (defaults to now)
    note                  : Optional note/comment
    test_case_version_id  : Required — the approved version ID of the test case
    properties            : Test run field values. If None, auto-discovered from project.
    project_id            : Used for property cache key (auto-discovery)

    Returns
    -------
    {"success": bool, "test_log_id": str | None, "error": str | None}
    """
    # ── Status ID mapping ─────────────────────────────────────
    _STATUS_MAP = {
        "PASS":        {"id": 601, "name": "Passed"},
        "PASSED":      {"id": 601, "name": "Passed"},
        "FAIL":        {"id": 602, "name": "Failed"},
        "FAILED":      {"id": 602, "name": "Failed"},
        "UNEXECUTED":  {"id": 605, "name": "Unexecuted"},
    }

    now = datetime.now(tz=__import__('zoneinfo').ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Resolve overall status to object format
    overall_key = overall_status.upper().strip()
    status_obj = _STATUS_MAP.get(overall_key, {"id": 605, "name": "Unexecuted"})

    # Auto-discover properties if not provided
    effective_properties = properties
    if effective_properties is None and project_id:
        effective_properties = _get_or_discover_properties(base_url, headers, verify_ssl, project_id)

    body: dict[str, Any] = {
        "status": status_obj,
        "exe_start_date": exe_start_date or now,
        "exe_end_date": exe_end_date or now,
        "note": note or f"Executed via TestGenAgent on {now}",
        "test_step_logs": test_step_logs,
    }

    # Include properties if available
    if effective_properties:
        body["properties"] = effective_properties

    # Include test_case_version_id if provided (required for submission)
    if test_case_version_id:
        body["test_case_version_id"] = int(test_case_version_id)

    try:
        # Use test-logs endpoint (NOT auto-test-logs which returns 403)
        resp = requests.post(
            f"{base_url}/test-runs/{test_run_id}/test-logs",
            headers=headers,
            json=body,
            timeout=30,
            verify=verify_ssl,
        )
        if resp.status_code == 401:
            return {"success": False, "test_log_id": None,
                    "error": "AUTH_EXPIRED: qTest returned 401. Update token in aava_qtest_config.py."}
        if resp.status_code == 400:
            error_detail = resp.text[:500]
            return {"success": False, "test_log_id": None,
                    "error": f"BAD_REQUEST (400): {error_detail}. "
                             "Check: test case approved? All steps included? test_step_ids correct? "
                             "Required properties filled?"}
        resp.raise_for_status()
        data = resp.json()
        log_id = str(data.get("id", data.get("test_log_id", "")))
        logger.info("Submitted execution log (id=%s) for test run %s — %s",
                     log_id, test_run_id, overall_status)
        return {"success": True, "test_log_id": log_id, "error": None}
    except RequestException as exc:
        return {"success": False, "test_log_id": None, "error": f"REQUEST_FAILED: {exc}"}


def report_execution_results(
    test_case_id: int | str,
    cycle_name: str,
    step_results: list[dict],
    host: str | None = None,
    token: str | None = None,
    project_id: str | None = None,
    workspace_id: str | None = None,
    exe_start_date: str | None = None,
    exe_end_date: str | None = None,
    note: str = "",
    properties: list[dict] | None = None,
) -> dict[str, Any]:
    """
    High-level function: approve TC → discover properties → create suite →
    create run → fetch step IDs → submit log.

    Auto-discovers required test-run properties by reading an existing test run
    in the project — no manual intervention needed when switching projects.

    Parameters
    ----------
    test_case_id   : qTest test case ID
    cycle_name     : Test suite name (created if it does not exist)
    step_results   : List of step-level results:
                     [
                       {
                         "description": "Navigate to login",
                         "expected_result": "Page loads",
                         "actual_result": "Page loaded",
                         "status": "PASS",       ← string, converted to {"id": N} internally
                         "order": 1
                       },
                       ...
                     ]
                     Must include ALL steps (count must match test case steps).
    host           : qTest host (defaults to QTEST_CONFIG)
    token          : Bearer token (defaults to QTEST_CONFIG)
    project_id     : Project ID (defaults to QTEST_CONFIG)
    workspace_id   : Workspace ID (defaults to QTEST_CONFIG)
    exe_start_date : ISO-8601 start time
    exe_end_date   : ISO-8601 end time
    note           : Optional execution note
    properties     : Optional explicit properties override. If None, auto-discovered.

    Returns
    -------
    {
        "success":              bool,
        "cycle_id":             str | None,
        "cycle_created":        bool,
        "test_run_id":          str | None,
        "test_log_id":          str | None,
        "overall_status":       str,
        "test_case_version_id": str | None,
        "properties_source":    str,   ← "provided" | "discovered" | "none"
        "error":                str | None,
    }
    """
    host         = host or QTEST_CONFIG["host"]
    token        = token or QTEST_CONFIG["token"]
    project_id   = project_id or QTEST_CONFIG["project_id"]
    workspace_id = workspace_id or QTEST_CONFIG.get("workspace_id", "")

    verify_ssl = _qtest_ssl_verify()
    headers    = _qtest_headers(token)

    # Step status mapping: string → {"id": N} object
    _STEP_STATUS_MAP = {
        "PASS":       {"id": 601},
        "PASSED":     {"id": 601},
        "FAIL":       {"id": 602},
        "FAILED":     {"id": 602},
        "UNEXECUTED": {"id": 605},
    }

    result: dict[str, Any] = {
        "success": False, "cycle_id": None, "cycle_created": False,
        "test_run_id": None, "test_log_id": None, "overall_status": "UNEXECUTED",
        "test_case_version_id": None, "properties_source": "none", "error": None,
    }

    # ── 1. Resolve base URL ───────────────────────────────────
    try:
        base_url = _resolve_qtest_base_url(host, project_id, workspace_id, headers, verify_ssl)
    except RuntimeError as exc:
        result["error"] = str(exc)
        return result

    # ── 2. Auto-discover properties (if not explicitly provided) ─────
    effective_properties = properties
    if effective_properties:
        result["properties_source"] = "provided"
    else:
        effective_properties = _get_or_discover_properties(base_url, headers, verify_ssl, project_id)
        result["properties_source"] = "discovered" if effective_properties else "none"
        if not effective_properties:
            logger.warning(
                "No properties discovered for project %s. "
                "Submission may fail if required fields exist. "
                "Workaround: fill one test run manually in qTest UI, then retry.",
                project_id,
            )

    # ── 3. Approve test case version (required before log submission) ─────
    tc_version_id = None
    try:
        tc_resp = requests.get(
            f"{base_url}/test-cases/{test_case_id}",
            headers=headers, timeout=20, verify=verify_ssl,
        )
        tc_resp.raise_for_status()
        tc_data = tc_resp.json()

        # Get the test_case_version_id
        tc_version_id = tc_data.get("test_case_version_id")
        if not tc_version_id:
            versions = tc_data.get("versions", [])
            if versions:
                tc_version_id = versions[-1].get("id")

        # Approve the test case (idempotent — safe to call even if already approved)
        approve_resp = requests.put(
            f"{base_url}/test-cases/{test_case_id}/approve",
            headers=headers, timeout=20, verify=verify_ssl,
        )
        if approve_resp.status_code not in (200, 204):
            logger.warning("Could not approve TC %s: HTTP %d — %s",
                           test_case_id, approve_resp.status_code, approve_resp.text[:200])

        result["test_case_version_id"] = str(tc_version_id) if tc_version_id else None
        logger.info("TC %s approved (version_id=%s)", test_case_id, tc_version_id)
    except RequestException as exc:
        logger.warning("Failed to approve TC %s: %s — proceeding anyway", test_case_id, exc)

    # ── 4. Fetch test step IDs from the API ───────────────────
    test_step_ids: list[int] = []
    try:
        if tc_version_id:
            steps_resp = requests.get(
                f"{base_url}/test-cases/{test_case_id}/versions/{tc_version_id}/test-steps",
                headers=headers, timeout=20, verify=verify_ssl,
            )
        else:
            steps_resp = requests.get(
                f"{base_url}/test-cases/{test_case_id}/test-steps",
                headers=headers, timeout=20, verify=verify_ssl,
            )

        if steps_resp.ok:
            steps_data = steps_resp.json()
            step_list = steps_data if isinstance(steps_data, list) else steps_data.get("items", [])
            step_list.sort(key=lambda s: s.get("order", s.get("id", 0)))
            test_step_ids = [s["id"] for s in step_list]
            logger.info("Fetched %d test_step_ids for TC %s", len(test_step_ids), test_case_id)
        else:
            logger.warning("Could not fetch test steps for TC %s: HTTP %d",
                           test_case_id, steps_resp.status_code)
    except RequestException as exc:
        logger.warning("Failed to fetch test steps for TC %s: %s", test_case_id, exc)

    # ── 5. Find or create test suite ─────────────────────────
    try:
        suite_info = find_or_create_test_suite(base_url, headers, verify_ssl, cycle_name)
        result["cycle_id"] = suite_info["id"]  # kept as cycle_id for backward compat
        result["cycle_created"] = suite_info["created"]
    except RuntimeError as exc:
        result["error"] = f"SUITE_ERROR: {exc}"
        return result

    # ── 6. Create test run ────────────────────────────────────
    try:
        run_info = create_test_run(
            base_url, headers, verify_ssl,
            test_case_id=test_case_id,
            suite_id=suite_info["id"],
        )
        result["test_run_id"] = run_info["id"]
    except RuntimeError as exc:
        result["error"] = f"RUN_ERROR: {exc}"
        return result

    # ── 7. Determine overall status from step results ─────────
    statuses = [s.get("status", "UNEXECUTED").upper() for s in step_results]
    if any(s in ("FAIL", "FAILED") for s in statuses):
        overall = "FAIL"
    elif all(s in ("PASS", "PASSED") for s in statuses):
        overall = "PASS"
    else:
        overall = "UNEXECUTED"
    result["overall_status"] = overall

    # ── 8. Build proper test_step_logs with test_step_id and status objects ─
    formatted_step_logs: list[dict] = []
    for i, step in enumerate(step_results):
        step_log: dict[str, Any] = {
            "actual_result": step.get("actual_result", step.get("expected_result", "")),
            "status": _STEP_STATUS_MAP.get(step.get("status", "UNEXECUTED").upper(), {"id": 605}),
            "order": step.get("order", i + 1),
        }
        # Include test_step_id if available (required by qTest)
        if i < len(test_step_ids):
            step_log["test_step_id"] = test_step_ids[i]
        formatted_step_logs.append(step_log)

    # Validate step count matches
    if test_step_ids and len(formatted_step_logs) != len(test_step_ids):
        logger.warning(
            "Step count mismatch: %d results provided but TC has %d steps. "
            "All steps must be included.",
            len(formatted_step_logs), len(test_step_ids),
        )

    # ── 9. Submit execution log ───────────────────────────────
    log_result = submit_execution_log(
        base_url, headers, verify_ssl,
        test_run_id=run_info["id"],
        overall_status=overall,
        test_step_logs=formatted_step_logs,
        exe_start_date=exe_start_date,
        exe_end_date=exe_end_date,
        note=note,
        test_case_version_id=tc_version_id,
        properties=effective_properties,
        project_id=project_id,
    )

    result["success"] = log_result["success"]
    result["test_log_id"] = log_result["test_log_id"]
    if log_result["error"]:
        result["error"] = log_result["error"]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — QUICK REFERENCE: DATA SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
"""
USER STORY INPUT (dict)
───────────────────────
{
    "id":                  632743,
    "title":               "Allow user to reset password via email link",
    "description":         "As a registered user I want to reset my password...",
    "acceptance_criteria": "Given I am on the login page When I click Forgot Password..."
}

AAVA REQUEST (POST body)
────────────────────────
{
    "agentId": 188,
    "userInputs": {
        "{{Story Details_string_true}}": "{\"requirements\": [{\"id\": 632743, \"title\": \"...\", ...}], \"existing_titles\": []}"
    },
    "executionId": "<uuid>",
    "user": "agent@company.com"
}

AAVA RESPONSE PATH (where to find test cases)
─────────────────────────────────────────────
response.json()
  └── data
       └── agentResponse
            └── agent
                 └── output                   ← dict with "scenarios" key
                      └── scenarios: [...]

SCENARIOS PAYLOAD
─────────────────
{
    "scenarios": [
        {
            "scenario_id":    "SC-001",
            "scenario_title": "Password Reset via Email",
            "test_cases": [
                {
                    "testcase_id":    "TC-001",
                    "title":          "Verify password reset email is sent...",
                    "preconditions":  "User account exists. Email is verified.",
                    "test_type":      "Positive",
                    "automation":     "Yes",
                    "test_data":      "Email: user@example.com",
                    "steps":          ["Click Forgot Password", "Enter email", "Submit"],
                    "expected_result": "Email with reset link is sent within 60 seconds."
                }
            ]
        }
    ]
}

QTEST UPLOAD REQUEST (per test case, POST /test-cases)
──────────────────────────────────────────────────────
{
    "name":         "Verify password reset email is sent...",
    "description":  "",
    "precondition": "User account exists. Email is verified.",
    "parent_id":    <module_id>,
    "test_steps": [
        {"description": "Click Forgot Password", "expected": "",                          "order": 1},
        {"description": "Enter email",           "expected": "",                          "order": 2},
        {"description": "Submit",                "expected": "Email sent within 60s.",    "order": 3}
    ],
    "properties": [
        {"field_id": 601, "field_value": "1", "field_value_name": "New"}
    ]
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — RUNNABLE EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # ── Example user story ────────────────────────────────────
    example_story = {
        "title": "Allow user to reset password via email link",
        "description": (
            "As a registered user, I want to reset my password using a link "
            "sent to my registered email address so that I can regain access "
            "to my account if I forget my password."
        ),
        "acceptance_criteria": (
            "Given I am on the login page "
            "When I click 'Forgot Password' and enter my email "
            "Then I receive a reset link within 60 seconds. "
            "The link expires after 24 hours. "
            "Clicking the link opens a page to set a new password."
        ),
    }

    # ── qTest connection (loaded from aava_qtest_config.py) ───
    example_qtest = QTEST_CONFIG

    print("=" * 72)
    print("AAVA → qTest Pipeline")
    print("=" * 72)
    print(f"Story : {example_story['title']}")
    print(f"qTest : {example_qtest['host']}  project={example_qtest['project_id']}")
    print()

    pipeline_result = run_full_pipeline(
        user_story=example_story,
        qtest_config=example_qtest,
    )

    print()
    print("=" * 72)
    print(f"Status         : {pipeline_result['status']}")
    print(f"TCs generated  : {pipeline_result['tc_count']}")
    print(f"Uploaded       : {pipeline_result['success_count']}")
    print(f"Failed         : {pipeline_result['fail_count']}")
    if pipeline_result.get("module_id"):
        print(f"qTest Module ID: {pipeline_result['module_id']}")
    if pipeline_result.get("aava_error"):
        print(f"AAVA Error     : {pipeline_result['aava_error']}")
    if pipeline_result.get("parse_error"):
        print(f"Parse Error    : {pipeline_result['parse_error']}")
    print("=" * 72)

    if pipeline_result.get("upload_results"):
        print("\nUpload Results:")
        for r in pipeline_result["upload_results"]:
            icon = "✓" if "Uploaded" in r["status"] else "✗"
            print(f"  {icon} [{r['qtest_id']:>8}] {r['name'][:70]}")
