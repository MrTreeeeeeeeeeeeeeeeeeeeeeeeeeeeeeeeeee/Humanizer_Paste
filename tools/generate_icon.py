from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    svg_path = project_root / "keymimic" / "assets" / "keymimic.svg"
    icon_path = svg_path.with_suffix(".ico")
    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    pixmap = QIcon(str(svg_path)).pixmap(QSize(256, 256))
    if pixmap.isNull() or not pixmap.save(str(icon_path), "ICO"):
        print(f"Could not generate {icon_path}", file=sys.stderr)
        return 1
    print(icon_path)
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
