"""Utility to extract application version from a live Playwright page."""

from __future__ import annotations

import re
from typing import Optional

from playwright.async_api import Page

from utils.logger import get_logger

logger = get_logger("version_extractor")


async def extract_app_version_from_page(page: Page, timeout_ms: int = 5000) -> Optional[str]:
    """
    Extract application version from the live rendered page.
    
    Strategies (in order):
    1. Check meta tags: <meta name="app-version" content="1.2.3">
    2. Check window object: window.APP_VERSION or similar
    3. Check data attributes on footer/header: <footer data-version="...">
    4. Check footer text for version patterns
    5. Check JavaScript console logs or attributes
    
    Args:
        page: Playwright Page object
        timeout_ms: timeout for page evaluations
    
    Returns:
        Version string if found, else None
    """
    if page.is_closed():
        return None

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except Exception:
        pass

    # Strategy 1: Meta tags
    try:
        version = await page.evaluate(
            """
            () => {
                const metas = document.querySelectorAll('meta');
                for (const meta of metas) {
                    const name = (meta.getAttribute('name') || '').toLowerCase();
                    if (name.includes('version') || name.includes('app-version') || name.includes('application-version')) {
                        return meta.getAttribute('content');
                    }
                }
                return null;
            }
            """
        )
        if version:
            return str(version).strip()
    except Exception:
        pass

    # Strategy 2: Window object
    try:
        version = await page.evaluate(
            """
            () => {
                const candidates = [
                    window.APP_VERSION,
                    window.app_version,
                    window.appVersion,
                    window.__APP_VERSION__,
                    window.__VERSION__,
                    window.VERSION,
                ];
                for (const v of candidates) {
                    if (v) return String(v);
                }
                return null;
            }
            """
        )
        if version:
            return str(version).strip()
    except Exception:
        pass

    # Strategy 3: Data attributes on common elements
    try:
        version = await page.evaluate(
            """
            () => {
                const selectors = [
                    '[data-version]',
                    '[data-app-version]',
                    '[data-application-version]',
                    '[data-build-version]',
                    'footer [data-version]',
                    'footer [data-app-version]',
                    'header [data-version]',
                    'header [data-app-version]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const v = el.getAttribute('data-version') || 
                                  el.getAttribute('data-app-version') ||
                                  el.getAttribute('data-application-version') ||
                                  el.getAttribute('data-build-version');
                        if (v) return v;
                    }
                }
                return null;
            }
            """
        )
        if version:
            return str(version).strip()
    except Exception:
        pass

    # Strategy 4: Footer/header text patterns
    try:
        footer_text = await page.evaluate(
            """
            () => {
                const footer = document.querySelector('footer, [role="contentinfo"]');
                if (footer) return footer.innerText;
                return null;
            }
            """
        )
        if footer_text:
            match = re.search(r'v?(\d+\.\d+\.\d+(?:\.\d+)?(?:[-+][\w.]+)?)', str(footer_text), re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass

    # Strategy 5: Page title or document info
    try:
        page_title = await page.evaluate("() => document.title")
        if page_title:
            match = re.search(r'v?(\d+\.\d+\.\d+(?:\.\d+)?)', str(page_title))
            if match:
                return match.group(1)
    except Exception:
        pass

    return None
