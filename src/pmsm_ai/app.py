"""Application bootstrap for the PyQt6 desktop client."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from pmsm_ai.ui.dashboard import MainWindow

_STYLE_SHEET = """
QMainWindow, QWidget#page {
    background: #f4f7f5;
    color: #18332b;
}
QFrame#hero {
    background: #144c3b;
    border-radius: 18px;
}
QLabel#eyebrow {
    color: #9bd4bf;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#title {
    color: #ffffff;
    font-size: 30px;
    font-weight: 700;
}
QLabel#subtitle {
    color: #d9eee6;
    font-size: 14px;
}
QLabel#stage {
    color: #103a2e;
    background: #b9ead5;
    border-radius: 12px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 700;
}
QLabel#disclaimer {
    color: #744d12;
    background: #fff4d6;
    border: 1px solid #efd69a;
    border-radius: 10px;
    padding: 11px 14px;
    font-size: 13px;
}
QFrame#panel, QFrame#environment-panel, QFrame#metric-card {
    background: #ffffff;
    border: 1px solid #dbe5df;
    border-radius: 14px;
}
QFrame#guide-intro {
    background: #e8f2ed;
    border: 1px solid #cfe1d8;
    border-radius: 14px;
}
QFrame#guide-card {
    background: #ffffff;
    border: 1px solid #dbe5df;
    border-radius: 12px;
}
QLabel#guide-intro-title {
    color: #173c31;
    font-size: 22px;
    font-weight: 700;
}
QLabel#guide-intro-text {
    color: #526a60;
    font-size: 13px;
}
QLabel#step-badge {
    color: #1f7c5b;
    font-size: 11px;
    font-weight: 700;
}
QLabel#guide-card-title {
    color: #183c31;
    font-size: 16px;
    font-weight: 700;
}
QLabel#guide-card-body {
    color: #61736c;
    font-size: 12px;
}
QLabel#section-title {
    color: #173c31;
    font-size: 17px;
    font-weight: 700;
}
QLabel#section-caption, QLabel#footer {
    color: #6d7e78;
    font-size: 12px;
}
QLabel#trend-status, QLabel#design-relation {
    color: #286d54;
    background: #eef8f3;
    border-radius: 7px;
    padding: 7px 9px;
    font-size: 11px;
}
QLabel#metrics-help {
    color: #526a60;
    background: #f3f8f5;
    border: 1px solid #dce8e1;
    border-radius: 8px;
    padding: 9px 11px;
    font-size: 11px;
}
QLabel#relation-text {
    color: #425a51;
    font-size: 12px;
    line-height: 1.4;
}
QLabel#field-label {
    color: #425a51;
    font-size: 12px;
}
QLabel#field-section-title {
    color: #207f5e;
    font-size: 12px;
    font-weight: 700;
}
QLabel#field-unit {
    color: #82918b;
    font-size: 11px;
}
QLabel#metric-caption {
    color: #71837c;
    font-size: 12px;
    font-weight: 700;
}
QLabel#metric-value {
    color: #173c31;
    font-size: 25px;
    font-weight: 700;
}
QLabel#metric-baseline, QLabel#prediction-message {
    color: #657870;
    font-size: 11px;
}
QLabel#prediction-message {
    background: #eaf3ee;
    border-radius: 8px;
    padding: 9px 11px;
}
QLabel#model-status {
    color: #267454;
    background: #eef8f3;
    border-radius: 7px;
    padding: 7px 9px;
    font-size: 11px;
}
QLabel#warning {
    color: #a05017;
    font-size: 11px;
}
QPushButton {
    color: #ffffff;
    background: #207f5e;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 700;
}
QPushButton:hover {
    background: #17694c;
}
QPushButton:pressed {
    background: #11563e;
}
QPushButton:disabled {
    color: #82918b;
    background: #dce5e0;
}
QTabWidget::pane {
    background: transparent;
    border: none;
}
QTabBar::tab {
    color: #60746c;
    background: #e8efeb;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 700;
}
QTabBar::tab:selected {
    color: #ffffff;
    background: #207f5e;
}
QSpinBox, QDoubleSpinBox, QComboBox {
    color: #27453a;
    background: #f8fbf9;
    border: 1px solid #d5e2db;
    border-radius: 6px;
    padding: 5px 7px;
    min-height: 20px;
}
QTabWidget#input-tabs QSpinBox, QTabWidget#input-tabs QDoubleSpinBox {
    min-height: 16px;
    padding: 2px 5px;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QTableWidget {
    color: #29453b;
    background: #ffffff;
    alternate-background-color: #f5f9f7;
    border: 1px solid #dce7e1;
    border-radius: 8px;
    gridline-color: #e7eee9;
}
QHeaderView::section {
    color: #3f5d51;
    background: #e9f2ed;
    border: none;
    padding: 7px;
    font-weight: 700;
}
QProgressBar {
    color: #173c31;
    background: #e1ebe5;
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    font-size: 10px;
}
QProgressBar::chunk {
    background: #2a936c;
    border-radius: 5px;
}
QPlainTextEdit {
    color: #29453b;
    background: #f7faf8;
    border: 1px solid #dce7e1;
    border-radius: 8px;
    padding: 8px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea#input-scroll {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background: #c8d7d0;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


def _configure_font(application: QApplication) -> None:
    """Load a CJK-capable Windows font when Qt cannot discover system fonts."""

    font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = (
        font_directory / "msyh.ttc",
        font_directory / "Deng.ttf",
        font_directory / "simhei.ttf",
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(candidate))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            application.setFont(QFont(families[0], 10))
            return

    application.setFont(QFont("Microsoft YaHei UI", 10))


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create or return the single Qt application instance."""

    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing

    application = QApplication(list(argv) if argv is not None else sys.argv)
    application.setApplicationName("PMSM AI Design Assistant")
    application.setApplicationDisplayName("永磁同步电机 AI 设计助手")
    application.setOrganizationName("Course Project")
    _configure_font(application)
    application.setStyle("Fusion")
    application.setStyleSheet(_STYLE_SHEET)
    return application


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the desktop application."""

    arguments = list(argv) if argv is not None else sys.argv
    smoke_test = "--smoke-test" in arguments
    if smoke_test:
        arguments = [argument for argument in arguments if argument != "--smoke-test"]

    application = create_application(arguments)
    window = MainWindow()
    window.show()
    if smoke_test:
        QTimer.singleShot(500, application.quit)
    exit_code = application.exec()
    if smoke_test and window.prediction_service is None:
        return 2
    return exit_code
