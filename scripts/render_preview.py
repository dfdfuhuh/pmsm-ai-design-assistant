"""Render the launch page to a PNG without opening a visible window."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pmsm_ai.app import create_application  # noqa: E402
from pmsm_ai.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    output_directory = Path(__file__).resolve().parents[1] / "docs" / "images"
    output_directory.mkdir(parents=True, exist_ok=True)
    design_output = output_directory / "launch-page.png"
    advanced_output = output_directory / "advanced-parameters.png"
    model_output = output_directory / "model-evaluation.png"

    application = create_application([])
    window = MainWindow()
    window.show()
    application.processEvents()
    if window.prediction_service is not None:
        window.predict_current_design()
        application.processEvents()

    if not window.grab().save(str(design_output), "PNG"):
        print(f"无法保存预览：{design_output}")
        return 1

    window.input_tabs.setCurrentIndex(1)
    application.processEvents()
    if not window.grab().save(str(advanced_output), "PNG"):
        print(f"无法保存预览：{advanced_output}")
        return 1

    window.tabs.setCurrentIndex(1)
    application.processEvents()
    if not window.grab().save(str(model_output), "PNG"):
        print(f"无法保存预览：{model_output}")
        return 1

    window.close()
    print(f"设计页预览已保存：{design_output}")
    print(f"高级参数页预览已保存：{advanced_output}")
    print(f"模型评估页预览已保存：{model_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
