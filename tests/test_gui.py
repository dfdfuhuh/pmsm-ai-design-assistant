"""Headless GUI smoke tests."""

from PyQt6.QtCore import Qt

from pmsm_ai.ui.main_window import MainWindow, SummaryCard


def test_main_window_contains_pre_research_content(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "永磁同步电机 AI 设计助手"
    assert window.check_button.text() == "检查开发环境"
    assert window.environment_output.isReadOnly()
    assert window.findChildren(SummaryCard)


def test_environment_check_button_reports_results(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(window.check_button, Qt.MouseButton.LeftButton)

    output = window.environment_output.toPlainText()
    assert "PyQt6" in output
    assert "scikit-learn" in output
    assert "结果：" in output
