"""Report archiver — copies the latest HTML/Allure reports into
a timestamped sub-folder under reports/archive/ so every run
has a permanent snapshot.

Usage (called automatically from conftest.py or run manually):
    python -m utils.report_archiver
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR  = PROJECT_ROOT / "reports"
ARCHIVE_DIR  = REPORTS_DIR / "archive"

HTML_REPORT    = REPORTS_DIR / "latest_report.html"
ALLURE_RESULTS = REPORTS_DIR / "allure-results"
SCREENSHOTS    = REPORTS_DIR / "screenshots"


def archive_run(tag: str | None = None) -> Path:
    """Copy latest report artefacts into a timestamped archive folder.

    Args:
        tag: Optional label appended to the folder name (e.g. 'smoke', 'qa').

    Returns:
        Path to the created archive folder.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{tag}" if tag else timestamp
    dest = ARCHIVE_DIR / folder_name
    dest.mkdir(parents=True, exist_ok=True)

    # ── HTML report ────────────────────────────────────────────────────────
    if HTML_REPORT.exists():
        shutil.copy2(HTML_REPORT, dest / "report.html")

    # ── Allure raw results (copy entire folder) ───────────────────────────
    if ALLURE_RESULTS.exists() and any(ALLURE_RESULTS.iterdir()):
        allure_dest = dest / "allure-results"
        shutil.copytree(ALLURE_RESULTS, allure_dest, dirs_exist_ok=True)

    # ── Screenshots ────────────────────────────────────────────────────────
    if SCREENSHOTS.exists() and any(SCREENSHOTS.iterdir()):
        shots_dest = dest / "screenshots"
        shutil.copytree(SCREENSHOTS, shots_dest, dirs_exist_ok=True)

    return dest


def prune_old_archives(keep_latest: int = 20) -> int:
    """Remove oldest archive folders keeping only *keep_latest* most recent.

    Returns:
        Number of folders removed.
    """
    if not ARCHIVE_DIR.exists():
        return 0

    folders = sorted(
        [p for p in ARCHIVE_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    to_remove = folders[keep_latest:]
    for folder in to_remove:
        shutil.rmtree(folder, ignore_errors=True)
    return len(to_remove)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Archive latest test reports")
    parser.add_argument("--tag",  default=None, help="Label for this archive (e.g. smoke, regression)")
    parser.add_argument("--keep", default=20,   type=int, help="Max archive folders to retain (default 20)")
    args = parser.parse_args()

    dest_path = archive_run(tag=args.tag)
    pruned    = prune_old_archives(keep_latest=args.keep)

    print(f"Archived to : {dest_path}")
    if pruned:
        print(f"Pruned      : {pruned} old archive(s)")
