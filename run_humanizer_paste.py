from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from keymimic.app import main
except ModuleNotFoundError as exc:
    if exc.name == "PySide6":
        print("Missing dependency: PySide6")
        print('Install it from this folder with: python -m pip install -e "."')
        raise SystemExit(1) from exc
    raise


if __name__ == "__main__":
    raise SystemExit(main())
