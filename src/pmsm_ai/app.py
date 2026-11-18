"""Application bootstrap for the PyQt6 desktop client."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from pmsm_ai.ui.main_window import MainWindow

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
QFrame#card, QFrame#environment-panel {
    background: #ffffff;
    border: 1px solid #dbe5df;
    border-radius: 14px;
}
QLabel#card-index {
    color: #208662;
    font-size: 12px;
    font-weight: 700;
}
QLabel#card-title {
    color: #173c31;
    font-size: 17px;
    font-weight: 700;
}
QLabel#card-body {
    color: #5d7069;
    font-size: 13px;
}
QLabel#section-title {
    color: #173c31;
    font-size: 18px;
    font-weight: 700;
}
QLabel#section-caption, QLabel#footer {
    color: #6d7e78;
    font-size: 12px;
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

    application = create_application(argv)
    window = MainWindow()
    window.show()
    return application.exec()
