from __future__ import annotations

from importlib import import_module

__all__ = [
    "load_config",
    "resolve_environment",
    "detect_feature",
    "get_test_folder_by_feature",
    "append_run_history",
    "get_basic_history_summary",
    "read_run_history",
    "find_element_with_fallback",
    "audit_locator_maps",
    "get_logger",
    "run_policy_guard",
]


_LAZY_IMPORTS = {
    "load_config": ("utils.config_loader", "load_config"),
    "resolve_environment": ("utils.config_loader", "resolve_environment"),
    "detect_feature": ("utils.feature_router", "detect_feature"),
    "get_test_folder_by_feature": ("utils.feature_router", "get_test_folder_by_feature"),
    "append_run_history": ("utils.history_tracker", "append_run_history"),
    "get_basic_history_summary": ("utils.history_tracker", "get_basic_history_summary"),
    "read_run_history": ("utils.history_tracker", "read_run_history"),
    "find_element_with_fallback": ("utils.locator_engine", "find_element_with_fallback"),
    "audit_locator_maps": ("utils.locator_guard", "audit_locator_maps"),
    "get_logger": ("utils.logger", "get_logger"),
    "run_policy_guard": ("utils.policy_guard", "run_policy_guard"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_name, symbol_name = _LAZY_IMPORTS[name]
        module = import_module(module_name)
        value = getattr(module, symbol_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'utils' has no attribute {name!r}")
