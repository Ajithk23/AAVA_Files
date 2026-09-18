"""
qTest MCP Server
═══════════════════════════════════════════════════════════════════════════════
A Model Context Protocol (MCP) server that exposes qTest operations as tools.
Uses the existing logic in aava_qtest_reference.py — no duplication.

Tools exposed:
  - qtest_fetch_test_cases    : Fetch TCs by module name, module ID, or TC ID
  - qtest_upload_test_cases   : Upload a list of test cases to a qTest module
  - qtest_list_modules        : List all modules (folders) in the project
  - qtest_get_test_case       : Get full details of a single test case by ID
  - qtest_link_requirement    : Link a requirement (ADO work item) to test cases
  - qtest_submit_execution    : Submit test execution results with step-level pass/fail
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# ── Re-launch inside the project venv if not already running in it ────────────
# This makes the server work with a plain `python` command on any machine.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_VENV_PYTHON = _PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"  # Windows
if not _VENV_PYTHON.exists():
    _VENV_PYTHON = _PROJECT_ROOT / ".venv" / "bin" / "python"       # macOS / Linux
if _VENV_PYTHON.exists() and Path(sys.executable).resolve() != _VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(_VENV_PYTHON), __file__] + sys.argv[1:]))

import requests  # noqa: E402 (imported after venv check)

# ── Ensure the Agent directory is importable ─────────────────────────────────
AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from mcp.server.fastmcp import FastMCP

from aava_qtest_config import (
    QTEST_HOST,
    QTEST_MODULE,
    QTEST_PROJECT_ID,
    QTEST_TOKEN,
    QTEST_WORKSPACE_ID,
)
from aava_qtest_reference import (
    _qtest_headers,
    _qtest_ssl_verify,
    _resolve_qtest_base_url,
    fetch_from_qtest,
    link_requirement_to_test_cases,
    report_execution_results,
    upload_to_qtest,
)

mcp = FastMCP("qTest Manager MCP server — fetch and upload test cases")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Resolve nested module path to module ID
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_nested_module_id(base_url: str, headers: dict, verify_ssl, module_path: str) -> str | None:
    """
    Resolve a nested folder path (e.g. "2026 Sprints/AI Platform Delivery/ADO/...")
    to a qTest module ID by traversing the tree level-by-level.

    Uses greedy prefix matching to handle folder names that contain '/' characters
    (e.g. "Release Testing - 4/2 - Functional Testing").

    The qTest GET /modules endpoint only returns top-level modules.
    To find nested sub-modules, we fetch each parent's children via
    GET /modules/{parent_id} at each depth level.

    Returns the module ID as a string, or None if not found.
    """
    remaining_path = module_path.strip()
    if not remaining_path:
        return None

    # Fetch top-level modules
    try:
        r = requests.get(f"{base_url}/modules", headers=headers, timeout=20, verify=verify_ssl)
        if not r.ok:
            return None
        modules = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    except Exception:
        return None

    current_nodes = modules

    while remaining_path:
        # Greedy match: try to match a module name from current_nodes against
        # the beginning of remaining_path. Sort by longest name first so that
        # "Release Testing - 4/2 - Functional Testing" matches before
        # "Release Testing - 4".
        matched_module = None
        sorted_nodes = sorted(current_nodes, key=lambda m: len(m.get("name") or ""), reverse=True)

        for m in sorted_nodes:
            name = (m.get("name") or "").strip()
            if not name:
                continue
            # Check if remaining_path starts with this module name (case-insensitive)
            if remaining_path.lower().startswith(name.lower()):
                # Verify it's either an exact match or followed by '/'
                after = remaining_path[len(name):]
                if after == "" or after.startswith("/"):
                    matched_module = m
                    remaining_path = after.lstrip("/").strip()
                    break

        if matched_module is None:
            return None

        # If nothing remains, this is the target module
        if not remaining_path:
            return str(matched_module["id"])

        # Get children for the next level
        children = matched_module.get("children", matched_module.get("sub_modules", []))
        if children:
            current_nodes = children
            continue

        # Children not embedded — fetch them from the API
        parent_id = matched_module["id"]
        try:
            r = requests.get(
                f"{base_url}/modules/{parent_id}",
                headers=headers,
                timeout=20,
                verify=verify_ssl,
            )
            if r.ok:
                parent_data = r.json()
                children = parent_data.get("children", parent_data.get("sub_modules", []))

            # Fallback: some qTest versions use parentId query param
            if not children:
                r2 = requests.get(
                    f"{base_url}/modules",
                    headers=headers,
                    params={"parentId": parent_id},
                    timeout=20,
                    verify=verify_ssl,
                )
                if r2.ok:
                    data = r2.json()
                    children = data if isinstance(data, list) else data.get("items", [])
        except Exception:
            return None

        if not children:
            return None

        current_nodes = children

    return None


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: qtest_fetch_test_cases
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def qtest_fetch_test_cases(
    module_name: str | None = None,
    module_id: str | None = None,
    tc_id: str | None = None,
) -> str:
    """
    Fetch test cases from qTest Manager.

    Modes (pick one):
      - tc_id: fetch a single test case by its numeric ID
      - module_name: fetch all test cases in a module (folder) by name.
                     Supports nested folder paths separated by '/'.
                     Example: "2026 Sprints/AI Platform Delivery/ADO/SubFolder"
      - module_id: fetch all test cases in a module by its numeric ID
      - None: fetch from the default module configured in aava_qtest_config.py

    Returns JSON with: success, test_cases, total_count, error
    """
    # If module_name contains '/' (nested path) and no module_id is given,
    # resolve the nested path to a module_id first.
    effective_module_name = module_name or (QTEST_MODULE if not module_id and not tc_id else None)

    if effective_module_name and "/" in effective_module_name and not module_id and not tc_id:
        verify_ssl = _qtest_ssl_verify()
        headers = _qtest_headers(QTEST_TOKEN)
        try:
            base_url = _resolve_qtest_base_url(
                QTEST_HOST, QTEST_PROJECT_ID, QTEST_WORKSPACE_ID, headers, verify_ssl
            )
            resolved_id = _resolve_nested_module_id(base_url, headers, verify_ssl, effective_module_name)
            if resolved_id:
                # Pass the resolved module_id directly — bypasses _find_module_id
                result = fetch_from_qtest(module_id=resolved_id)
                result["module_name"] = effective_module_name
                return json.dumps(result)
            else:
                return json.dumps({
                    "success": False,
                    "test_cases": [],
                    "total_count": 0,
                    "module_name": effective_module_name,
                    "module_id": None,
                    "error": f"MODULE_NOT_FOUND: Could not resolve nested path '{effective_module_name}'. "
                             "Verify each folder segment exists in qTest.",
                })
        except RuntimeError as exc:
            return json.dumps({
                "success": False, "test_cases": [], "total_count": 0,
                "module_name": effective_module_name, "module_id": None,
                "error": str(exc),
            })

    # Non-nested path or direct module_id/tc_id — use existing logic
    result = fetch_from_qtest(
        module_name=module_name,
        module_id=module_id,
        tc_id=int(tc_id) if tc_id else None,
    )
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: qtest_get_test_case
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def qtest_get_test_case(tc_id: str) -> str:
    """
    Get full details of a single qTest test case by its numeric ID.
    Returns the complete test case object including steps, properties, and metadata.
    """
    result = fetch_from_qtest(tc_id=int(tc_id))
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: qtest_upload_test_cases
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def qtest_upload_test_cases(tc_list_json: str, module_name: str | None = None, parent_module_id: str | None = None) -> str:
    """
    Upload test cases to qTest Manager.

    Parameters:
      tc_list_json: JSON string — an array of test case objects. Each object should have:
        - title (str): test case name
        - objective (str): description/objective
        - preconditions (str): precondition text
        - steps (list): array of {test_case_description, expected_result}
        - priority (str, optional): e.g. "Medium"
        - test_case_type (str, optional): for qTest field mapping
        - test_case_status (str, optional)
        - implementation (str, optional)
        - product_area (str, optional)
      module_name: target qTest module (folder) name. Supports nested paths
                   like "Parent/Child/NewModule".
                   Defaults to QTEST_MODULE from aava_qtest_config.py.
      parent_module_id: Optional parent module ID (numeric string). If provided,
                        the module will be created under this parent. Use this to
                        create test cases inside deeply nested modules.
    """
    tc_list = tc_list_json if isinstance(tc_list_json, list) else json.loads(tc_list_json)
    target_module = module_name or QTEST_MODULE
    result = upload_to_qtest(
        tc_list=tc_list,
        host=QTEST_HOST,
        token=QTEST_TOKEN,
        project_id=QTEST_PROJECT_ID,
        module_name=target_module,
        workspace_id=QTEST_WORKSPACE_ID,
        parent_module_id=parent_module_id,
    )
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: qtest_link_requirement
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def qtest_link_requirement(
    requirement_name: str,
    test_case_ids_json: str,
    external_id: str | None = None,
    description: str | None = None,
) -> str:
    """
    Link a requirement (e.g. ADO work item) to one or more test cases in qTest.

    This creates a Requirement in qTest (if it doesn't already exist) and links
    the specified test cases to it for traceability.

    Parameters:
      requirement_name: Name of the requirement (e.g. the ADO user story title).
      test_case_ids_json: JSON string — an array of qTest test case IDs (numeric strings).
                          Example: '["12345", "12346", "12347"]'
      external_id: Optional external reference ID (e.g. ADO work item ID like "632743").
                   Stored in the requirement description for traceability.
      description: Optional description for the requirement.

    Returns JSON with: success, requirement_id, requirement_name, created,
                       link_results, success_count, fail_count, error
    """
    tc_ids = test_case_ids_json if isinstance(test_case_ids_json, list) else json.loads(test_case_ids_json)
    result = link_requirement_to_test_cases(
        requirement_name=requirement_name,
        test_case_ids=tc_ids,
        external_id=external_id,
        description=description or "",
    )
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: qtest_list_modules
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def qtest_list_modules(parent_id: str | None = None, recursive: bool = False) -> str:
    """
    List modules (folders) in the qTest project.

    Parameters:
      parent_id: If provided, list only sub-modules under this parent module ID.
                 If None, lists top-level modules.
      recursive: If True, recursively fetches all nested sub-modules (may be slow
                 for deep trees). Default False — only shows the immediate level.

    Returns a JSON array of modules with id, name, path, and depth.
    """
    verify_ssl = _qtest_ssl_verify()
    headers = _qtest_headers(QTEST_TOKEN)

    try:
        base_url = _resolve_qtest_base_url(
            QTEST_HOST, QTEST_PROJECT_ID, QTEST_WORKSPACE_ID, headers, verify_ssl
        )
    except RuntimeError as exc:
        return json.dumps({"success": False, "modules": [], "error": str(exc)})

    try:
        # Fetch modules at the requested level
        if parent_id:
            resp = requests.get(
                f"{base_url}/modules/{parent_id}",
                headers=headers,
                verify=verify_ssl,
                timeout=20,
            )
            resp.raise_for_status()
            parent_data = resp.json()
            modules = parent_data.get("children", parent_data.get("sub_modules", []))
            # Fallback: try parentId query param
            if not modules:
                resp2 = requests.get(
                    f"{base_url}/modules",
                    headers=headers,
                    params={"parentId": parent_id},
                    verify=verify_ssl,
                    timeout=20,
                )
                if resp2.ok:
                    data = resp2.json()
                    modules = data if isinstance(data, list) else data.get("items", [])
        else:
            resp = requests.get(
                f"{base_url}/modules",
                headers=headers,
                verify=verify_ssl,
                timeout=20,
            )
            resp.raise_for_status()
            modules_data = resp.json()
            modules = (
                modules_data
                if isinstance(modules_data, list)
                else modules_data.get("content", modules_data.get("items", []))
            )

        def _flatten(nodes: list, depth: int = 0, path_prefix: str = "") -> list:
            flat: list = []
            for m in nodes:
                name = m.get("name", "")
                full_path = f"{path_prefix}/{name}" if path_prefix else name
                flat.append({
                    "id": m.get("id"),
                    "name": name,
                    "path": full_path,
                    "depth": depth,
                })
                if not recursive:
                    continue
                if depth >= 10:
                    continue

                # Fetch children using ?parentId= query (the only reliable method
                # for this qTest instance — the response does NOT embed children)
                module_id = m.get("id")
                children = []
                if module_id:
                    try:
                        cr = requests.get(
                            f"{base_url}/modules",
                            headers=headers,
                            params={"parentId": str(module_id)},
                            verify=verify_ssl,
                            timeout=20,
                        )
                        if cr.ok:
                            cdata = cr.json()
                            if isinstance(cdata, list):
                                children = cdata
                            else:
                                children = cdata.get("items", cdata.get("content", []))
                    except Exception:
                        pass

                if children:
                    flat.extend(_flatten(children, depth + 1, full_path))
            return flat

        flat_modules = _flatten(modules)
        return json.dumps({"success": True, "modules": flat_modules})

    except Exception as exc:
        return json.dumps({"success": False, "modules": [], "error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: qtest_submit_execution
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def qtest_submit_execution(
    test_case_id: str,
    cycle_name: str,
    step_results_json: str,
    exe_start_date: str | None = None,
    exe_end_date: str | None = None,
    note: str | None = None,
    properties_json: str | None = None,
) -> str:
    """
    Submit test execution results (with step-level pass/fail) to qTest.

    This automatically:
    1. Auto-discovers required test-run properties from existing runs in the project
       (no manual setup needed when switching projects)
    2. Approves the test case version (required by qTest)
    3. Creates a Test Suite (if it doesn't exist)
    4. Creates a Test Run linked to the test case inside the suite
    5. Fetches test_step_ids from the API (required in step logs)
    6. Submits an execution log via POST /test-runs/{id}/test-logs

    Parameters:
      test_case_id: The numeric qTest test case ID.
      cycle_name: Name of the test suite (e.g. "Sprint 42 Regression").
                  Created automatically if it does not exist.
      step_results_json: JSON string — an array of step result objects. Each object:
        - description (str): step description (for readability only)
        - expected_result (str): what was expected
        - actual_result (str): what actually happened
        - status (str): "PASS" | "FAIL" | "UNEXECUTED"
        - order (int): 1-based step order
        NOTE: ALL steps must be included. test_step_ids are fetched automatically.
      exe_start_date: Optional ISO-8601 start time (defaults to now).
      exe_end_date: Optional ISO-8601 end time (defaults to now).
      note: Optional execution note.
      properties_json: Optional JSON string — array of {"field_id": int, "field_value": str}.
                       If omitted, properties are auto-discovered from an existing
                       test run in the project — works across different projects.

    Returns JSON with: success, cycle_id, test_run_id, test_log_id,
                       overall_status, test_case_version_id, properties_source, error
    """
    # Normalize *_json params: the MCP bridge may auto-deserialize JSON strings
    # into native Python lists/dicts before they reach Pydantic validation.
    step_results = step_results_json if isinstance(step_results_json, list) else json.loads(step_results_json)
    properties = (
        properties_json if isinstance(properties_json, list)
        else json.loads(properties_json) if properties_json
        else None
    )
    result = report_execution_results(
        test_case_id=int(test_case_id),
        cycle_name=cycle_name,
        step_results=step_results,
        exe_start_date=exe_start_date,
        exe_end_date=exe_end_date,
        note=note or "",
        properties=properties,
    )
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
