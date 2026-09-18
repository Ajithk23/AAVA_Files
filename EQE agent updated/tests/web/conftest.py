from __future__ import annotations

import pytest_asyncio
from playwright.async_api import Page

from pages.chat_page import ChatPage
from pages.file_handling_page import FileHandlingPage
from pages.prompt_library_page import PromptLibraryPage


@pytest_asyncio.fixture
async def chat_page(docuchat_context: dict) -> ChatPage:
    """Ready-to-use ChatPage navigated to base URL."""
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]
    await page.goto(settings["base_url"])
    return ChatPage(page, int(settings["timeout_ms"]))


@pytest_asyncio.fixture
async def file_page(docuchat_context: dict) -> FileHandlingPage:
    """Ready-to-use FileHandlingPage navigated to base URL."""
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]
    await page.goto(settings["base_url"])
    return FileHandlingPage(page, int(settings["timeout_ms"]))


@pytest_asyncio.fixture
async def prompt_page(docuchat_context: dict) -> PromptLibraryPage:
    """Ready-to-use PromptLibraryPage navigated to base URL."""
    page: Page = docuchat_context["page"]
    settings: dict = docuchat_context["settings"]
    await page.goto(settings["base_url"])
    return PromptLibraryPage(page, int(settings["timeout_ms"]))
