from __future__ import annotations

import runpy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_DASHBOARD = PROJECT_ROOT / "dashboard.py"


def main() -> None:
    runpy.run_path(str(ROOT_DASHBOARD), run_name="__main__")


if __name__ == "__main__":
    main()
