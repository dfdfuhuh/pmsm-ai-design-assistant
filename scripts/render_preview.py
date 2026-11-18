"""Render the launch page to a PNG without opening a visible window."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pmsm_ai.app import create_application  # noqa: E402
from pmsm_ai.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    output = Path(__file__).resolve().parents[1] / "docs" / "images" / "launch-page.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    application = create_application([])
    window = MainWindow()
    window.show()
    application.processEvents()

    if not window.grab().save(str(output), "PNG"):
        print(f"无法保存预览：{output}")
        return 1

    window.close()
    print(f"启动页预览已保存：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
