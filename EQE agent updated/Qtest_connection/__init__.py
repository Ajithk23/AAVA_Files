# qTest integration package for DocuChat automation framework.
# Exposes submit_playwright_failure and related helpers from Defect.py.

from .Defect import (
    submit_defect,
    submit_playwright_failure,
    submit_defect_from_dict,
    build_defect_payload,
    build_playwright_defect_properties,
    extract_defect_url,
    PlaywrightTestResult,
)

__all__ = [
    "submit_defect",
    "submit_playwright_failure",
    "submit_defect_from_dict",
    "build_defect_payload",
    "build_playwright_defect_properties",
    "extract_defect_url",
    "PlaywrightTestResult",
]
