"""Test data loader — loads test_data/test_inputs.json once and provides
typed accessors so every test reads from the same source of truth.

Usage example:
    from utils.test_data_loader import get_chat_inputs

    data = get_chat_inputs("tc003")
    # data.model_name  -> "4.1-mini CRT"
    # data.chat_type   -> "Basic Chat"
    # data.query       -> "What is CareSource?"
    # data.long_query  -> "CareSource policy validation " * 320
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_TEST_DATA_FILE = Path(__file__).resolve().parents[1] / "test_data" / "test_inputs.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    """Load and cache the JSON file once per process."""
    with open(_TEST_DATA_FILE, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatInputs:
    model_name: str
    chat_type: str
    query: str
    long_query: str
    empty_query: str


def get_chat_inputs(tc_key: str) -> ChatInputs:
    """Return chat test inputs for a given TC key (e.g. 'tc003').

    Args:
        tc_key: One of 'tc001', 'tc002', 'tc003', 'tc004', 'tc005', 'tc_598048_001', etc.

    Raises:
        KeyError: If tc_key is not found in test_inputs.json under chat or chat_int.
    """
    all_data = _load()
    data = all_data["chat"]
    key = tc_key.lower()
    if key in data:
        tc_data = data[key]
    else:
        tc_data = all_data["chat_int"][key]
    phrase = data["long_query_phrase"]
    repeat = int(data["long_query_repeat"])
    return ChatInputs(
        model_name=tc_data["model_name"],
        chat_type=tc_data["chat_type"],
        query=tc_data["query"],
        long_query=phrase * repeat,
        empty_query=data["empty_query"],
    )


# ---------------------------------------------------------------------------
# File Handling
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileHandlingInputs:
    valid_file: str
    policy_file: str
    invalid_extension: str
    large_file_mb: int


def get_file_handling_inputs() -> FileHandlingInputs:
    data = _load()["file_management"]
    return FileHandlingInputs(
        valid_file=data["valid_file"],
        policy_file=data["policy_file"],
        invalid_extension=data["invalid_extension"],
        large_file_mb=int(data["large_file_mb"]),
    )


# ---------------------------------------------------------------------------
# Prompt Library
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptLibraryInputs:
    valid_search: str
    no_match_search: str
    empty_search: str


def get_prompt_library_inputs() -> PromptLibraryInputs:
    data = _load()["prompt_library"]["search_terms"]
    return PromptLibraryInputs(
        valid_search=data["valid"],
        no_match_search=data["no_match"],
        empty_search=data["empty"],
    )


@dataclass(frozen=True)
class PromptLibraryCaseInputs:
    model_name: str
    base_title: str
    base_prompt: str
    edited_title: str
    edited_prompt: str
    display_order: int


def get_prompt_library_case_inputs(tc_key: str) -> PromptLibraryCaseInputs:
    """Return prompt library case inputs for a given TC key (e.g. 'tc041').

    Args:
        tc_key: One of 'tc041', 'tc042', 'tc043'.

    Raises:
        KeyError: If tc_key is not found in test_inputs.json under prompt_library.cases.
    """
    data = _load()["prompt_library"]["cases"][tc_key.lower()]
    return PromptLibraryCaseInputs(
        model_name=data["model_name"],
        base_title=data["base_title"],
        base_prompt=data["base_prompt"],
        edited_title=data["edited_title"],
        edited_prompt=data["edited_prompt"],
        display_order=int(data["display_order"]),
    )


# ---------------------------------------------------------------------------
# TC032 — File Management + Chat with Documents (all 15 supported file types)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TC032Inputs:
    model_name: str
    chat_type: str
    query: str
    long_query: str
    file_paths: tuple


def get_tc032_inputs() -> TC032Inputs:
    """Return TC032 inputs including absolute paths to the 15 test data files.

    Args:
        None

    Returns:
        TC032Inputs: model_name, chat_type, query, long_query, and a tuple of
        absolute Path objects for the 15 supported file types.
    """
    raw = _load()
    tc_data = raw["file_management"]["tc032"]
    chat_data = raw["chat"]
    phrase = chat_data["long_query_phrase"]
    repeat = int(chat_data["long_query_repeat"])
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in tc_data["files"])
    return TC032Inputs(
        model_name=tc_data["model_name"],
        chat_type=tc_data["chat_type"],
        query=tc_data["query"],
        long_query=phrase * repeat,
        file_paths=file_paths,
    )


# ---------------------------------------------------------------------------
# TC033 — File Management + Chat with Documents (5 CRT model, all 15 file types)
# ---------------------------------------------------------------------------

# TC033Inputs is identical in shape to TC032Inputs — reuse the same dataclass.
TC033Inputs = TC032Inputs


def get_tc033_inputs() -> TC033Inputs:
    """Return TC033 inputs (5 CRT model) including absolute paths to the 15 test data files."""
    raw = _load()
    tc_data = raw["file_management"]["tc033"]
    chat_data = raw["chat"]
    phrase = chat_data["long_query_phrase"]
    repeat = int(chat_data["long_query_repeat"])
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in tc_data["files"])
    return TC033Inputs(
        model_name=tc_data["model_name"],
        chat_type=tc_data["chat_type"],
        query=tc_data["query"],
        long_query=phrase * repeat,
        file_paths=file_paths,
    )


# ---------------------------------------------------------------------------
# TC034 — File Management + Chat with Documents (4.1-mini CRT model, all 15 file types)
# ---------------------------------------------------------------------------

# TC034Inputs is identical in shape to TC032Inputs — reuse the same dataclass.
TC034Inputs = TC032Inputs


def get_tc034_inputs() -> TC034Inputs:
    """Return TC034 inputs (4.1-mini CRT model) including absolute paths to the 15 test data files."""
    raw = _load()
    tc_data = raw["file_management"]["tc034"]
    chat_data = raw["chat"]
    phrase = chat_data["long_query_phrase"]
    repeat = int(chat_data["long_query_repeat"])
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in tc_data["files"])
    return TC034Inputs(
        model_name=tc_data["model_name"],
        chat_type=tc_data["chat_type"],
        query=tc_data["query"],
        long_query=phrase * repeat,
        file_paths=file_paths,
    )


# ---------------------------------------------------------------------------
# File Management — Chat inputs (tc035, tc036, tc037 — no file_paths list)
# ---------------------------------------------------------------------------

def get_file_management_inputs(tc_key: str) -> ChatInputs:
    """Return chat inputs for a file management TC key (e.g. 'tc035').

    Reads model_name, chat_type, and query from the file_management section.
    long_query is built from chat.long_query_phrase * long_query_repeat.

    Args:
        tc_key: Any key under file_management (e.g. 'tc035', 'tc036', 'tc037').

    Raises:
        KeyError: If tc_key is not found in test_inputs.json under file_management.
    """
    raw = _load()
    tc_data = raw["file_management"][tc_key.lower()]
    chat_data = raw["chat"]
    phrase = chat_data["long_query_phrase"]
    repeat = int(chat_data["long_query_repeat"])
    return ChatInputs(
        model_name=tc_data["model_name"],
        chat_type=tc_data["chat_type"],
        query=tc_data["query"],
        long_query=phrase * repeat,
        empty_query=chat_data["empty_query"],
    )


# Alias imported by TC035/TC036/TC037 test files
get_file_management_tc_inputs = get_file_management_inputs


def get_file_management_file_paths(tc_key: str) -> tuple:
    """Return a tuple of absolute Path objects for the files listed under file_management.<tc_key>.

    Args:
        tc_key: Any key under file_management that has a 'files' list (e.g. 'tc035').

    Raises:
        KeyError: If tc_key is not found or has no 'files' entry.
    """
    raw = _load()
    tc_data = raw["file_management"][tc_key.lower()]
    test_data_root = _TEST_DATA_FILE.parent
    return tuple(test_data_root / rel for rel in tc_data["files"])


# ---------------------------------------------------------------------------
# Chat INT (Integration environment)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatIntTC01Inputs:
    model_name: str
    chat_type: str
    query: str
    prompt_title: str
    prompt_description: str
    prompt_display_order: str


def get_chat_int_tc01_inputs() -> ChatIntTC01Inputs:
    """Return TC-INT-01 inputs from the chat_int section of test_inputs.json."""
    data = _load()["chat_int"]["tc_int_01"]
    return ChatIntTC01Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        prompt_title=data["prompt_title"],
        prompt_description=data["prompt_description"],
        prompt_display_order=data["prompt_display_order"],
    )


# TC-INT-02 — adds file_paths on top of TC-INT-01 shape
@dataclass(frozen=True)
class ChatIntTC02Inputs:
    model_name: str
    chat_type: str
    query: str
    prompt_title: str
    prompt_description: str
    prompt_display_order: str
    file_paths: tuple


def get_chat_int_tc02_inputs() -> ChatIntTC02Inputs:
    """Return TC-INT-02 inputs from the chat_int section of test_inputs.json."""
    data = _load()["chat_int"]["tc_int_02"]
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in data["files"])
    return ChatIntTC02Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        prompt_title=data["prompt_title"],
        prompt_description=data["prompt_description"],
        prompt_display_order=data["prompt_display_order"],
        file_paths=file_paths,
    )


# TC-INT-03 has the same shape as TC-INT-01 (no files)
ChatIntTC03Inputs = ChatIntTC01Inputs


def get_chat_int_tc03_inputs() -> ChatIntTC03Inputs:
    """Return TC-INT-03 inputs from the chat_int section of test_inputs.json."""
    data = _load()["chat_int"]["tc_int_03"]
    return ChatIntTC03Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        prompt_title=data["prompt_title"],
        prompt_description=data["prompt_description"],
        prompt_display_order=data["prompt_display_order"],
    )


# TC-INT-04 — same shape as TC-INT-01 (no files)
ChatIntTC04Inputs = ChatIntTC01Inputs


def get_chat_int_tc04_inputs() -> ChatIntTC04Inputs:
    """Return TC-INT-04 inputs from the chat_int section of test_inputs.json."""
    data = _load()["chat_int"]["tc_int_04"]
    return ChatIntTC04Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        prompt_title=data["prompt_title"],
        prompt_description=data["prompt_description"],
        prompt_display_order=data["prompt_display_order"],
    )


# ---------------------------------------------------------------------------
# TC-INT-05 through TC-INT-08 — Direct Input (long_query, no saved prompt fields)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatIntDirectInputs:
    model_name: str
    chat_type: str
    long_query: str


ChatIntTC05Inputs = ChatIntDirectInputs
ChatIntTC07Inputs = ChatIntDirectInputs
ChatIntTC08Inputs = ChatIntDirectInputs


def _get_chat_int_direct_inputs(tc_key: str) -> ChatIntDirectInputs:
    data = _load()["chat_int"][tc_key]
    return ChatIntDirectInputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        long_query=data["long_query"],
    )


def get_chat_int_tc05_inputs() -> ChatIntTC05Inputs:
    """Return TC-INT-05 inputs."""
    return _get_chat_int_direct_inputs("tc_int_05")


@dataclass(frozen=True)
class ChatIntTC06Inputs:
    model_name: str
    chat_type: str
    long_query: str
    file_paths: tuple


def get_chat_int_tc06_inputs() -> ChatIntTC06Inputs:
    """Return TC-INT-06 inputs."""
    data = _load()["chat_int"]["tc_int_06"]
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in data["files"])
    return ChatIntTC06Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        long_query=data["long_query"],
        file_paths=file_paths,
    )


def get_chat_int_tc07_inputs() -> ChatIntTC07Inputs:
    """Return TC-INT-07 inputs."""
    return _get_chat_int_direct_inputs("tc_int_07")


def get_chat_int_tc08_inputs() -> ChatIntTC08Inputs:
    """Return TC-INT-08 inputs."""
    return _get_chat_int_direct_inputs("tc_int_08")


# ---------------------------------------------------------------------------
# TC-INT-09, TC-INT-10 — Saved Prompts, Regular Query (same shape as TC-INT-01)
# ---------------------------------------------------------------------------

ChatIntTC09Inputs = ChatIntTC01Inputs

@dataclass(frozen=True)
class ChatIntTC10Inputs:
    model_name: str
    chat_type: str
    query: str
    prompt_title: str
    prompt_description: str
    prompt_display_order: str
    file_paths: tuple


def get_chat_int_tc09_inputs() -> ChatIntTC09Inputs:
    """Return TC-INT-09 inputs."""
    data = _load()["chat_int"]["tc_int_09"]
    return ChatIntTC09Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        prompt_title=data["prompt_title"],
        prompt_description=data["prompt_description"],
        prompt_display_order=data["prompt_display_order"],
    )


def get_chat_int_tc10_inputs() -> ChatIntTC10Inputs:
    """Return TC-INT-10 inputs."""
    data = _load()["chat_int"]["tc_int_10"]
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in data["files"])
    return ChatIntTC10Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        prompt_title=data["prompt_title"],
        prompt_description=data["prompt_description"],
        prompt_display_order=data["prompt_display_order"],
        file_paths=file_paths,
    )


# ---------------------------------------------------------------------------
# TC-INT-11, TC-INT-12 — Direct Input, Regular Query (query only, no prompt fields)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatIntDirectQueryInputs:
    model_name: str
    chat_type: str
    query: str


ChatIntTC11Inputs = ChatIntDirectQueryInputs


@dataclass(frozen=True)
class ChatIntTC12Inputs:
    model_name: str
    chat_type: str
    query: str
    file_paths: tuple


def get_chat_int_tc11_inputs() -> ChatIntTC11Inputs:
    """Return TC-INT-11 inputs."""
    data = _load()["chat_int"]["tc_int_11"]
    return ChatIntTC11Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
    )


def get_chat_int_tc12_inputs() -> ChatIntTC12Inputs:
    """Return TC-INT-12 inputs."""
    data = _load()["chat_int"]["tc_int_12"]
    test_data_root = _TEST_DATA_FILE.parent
    file_paths = tuple(test_data_root / rel for rel in data["files"])
    return ChatIntTC12Inputs(
        model_name=data["model_name"],
        chat_type=data["chat_type"],
        query=data["query"],
        file_paths=file_paths,
    )

