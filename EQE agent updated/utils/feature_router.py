from __future__ import annotations

from pathlib import Path


FEATURE_PATH_MAP = {
    "chat": Path("tests/web/chat"),
    "file": Path("tests/web/file_Management"),
    "file_handling": Path("tests/web/file_Management"),
    "file_management": Path("tests/web/file_Management"),
    "prompt": Path("tests/web/prompt_library"),
    "prompt_library": Path("tests/web/prompt_library"),
}


def detect_feature(scenario_text: str) -> str | None:
    text = scenario_text.lower()
    if "chat" in text or "message" in text:
        return "chat"
    if "file" in text or "upload" in text or "download" in text:
        return "file"
    if "prompt" in text or "template" in text:
        return "prompt"
    return None


def get_test_folder_by_feature(feature: str) -> Path:
    feature_key = feature.strip().lower().replace("-", "_").replace(" ", "_")
    if feature_key not in FEATURE_PATH_MAP:
        raise ValueError("Unsupported feature. Use one of: chat, file/file_handling/file_management, prompt/prompt_library")
    return FEATURE_PATH_MAP[feature_key]
