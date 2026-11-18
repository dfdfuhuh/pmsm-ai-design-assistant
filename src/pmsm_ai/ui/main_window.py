"""Main window and reusable presentation widgets."""

from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pmsm_ai.environment import EnvironmentCheck, all_checks_passed, collect_environment_checks


class SummaryCard(QFrame):
    """Small informational card with a consistent visual hierarchy."""

    def __init__(
        self,
        index: str,
        title: str,
        body: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)

        index_label = QLabel(index)
        index_label.setObjectName("card-index")
        title_label = QLabel(title)
        title_label.setObjectName("card-title")
        body_label = QLabel(body)
        body_label.setObjectName("card-body")
        body_label.setWordWrap(True)

        layout.addWidget(index_label)
        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    """Pre-research launch page for the PMSM design assistant."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("永磁同步电机 AI 设计助手")
        self.setMinimumSize(900, 680)
        self.resize(1120, 780)

        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(28, 28, 28, 24)
        page_layout.setSpacing(16)

        page_layout.addWidget(self._build_hero())

        disclaimer = QLabel(
            "教学原型声明：本阶段仅验证开发链路。规划中的性能结果将来自合成数据，"
            "不能替代有限元计算、样机测试或正式工程设计结论。"
        )
        disclaimer.setObjectName("disclaimer")
        disclaimer.setWordWrap(True)
        page_layout.addWidget(disclaimer)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        cards.addWidget(
            SummaryCard(
                "01 / 当前阶段",
                "开发环境与工程骨架",
                "已完成 Python 工具链、PyQt6 启动页和自动化测试配置。",
            )
        )
        cards.addWidget(
            SummaryCard(
                "02 / 后续路线",
                "数据驱动的性能代理",
                "物理约束合成数据与随机森林将用于预测转矩、转矩脉动和效率。",
            )
        )
        cards.addWidget(
            SummaryCard(
                "03 / 下一步",
                "先验证模型边界",
                "后续再实现参数采样、解析模型、训练评估和交互式设计分析。",
            )
        )
        page_layout.addLayout(cards)
        page_layout.addWidget(self._build_environment_panel())

        footer = QLabel("Python · PyQt6 · OOP · Random Forest（后续阶段）")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        page_layout.addWidget(footer)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(page)
        self.setCentralWidget(scroll_area)

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("hero")
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(26, 22, 26, 24)
        layout.setSpacing(7)

        top_row = QHBoxLayout()
        eyebrow = QLabel("PMSM DESIGN WORKBENCH")
        eyebrow.setObjectName("eyebrow")
        stage = QLabel("预研阶段")
        stage.setObjectName("stage")
        top_row.addWidget(eyebrow)
        top_row.addStretch(1)
        top_row.addWidget(stage)

        title = QLabel("永磁同步电机 AI 设计助手")
        title.setObjectName("title")
        subtitle = QLabel("面向课程项目的电机设计参数与性能预测原型")
        subtitle.setObjectName("subtitle")

        layout.addLayout(top_row)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return hero

    def _build_environment_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("environment-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("开发环境自检")
        title.setObjectName("section-title")
        caption = QLabel("只检查本地依赖，不访问网络")
        caption.setObjectName("section-caption")
        self.check_button = QPushButton("检查开发环境")
        self.check_button.setToolTip("检查 Python、科学计算依赖、Conda 与 Git")
        self.check_button.clicked.connect(self.run_environment_check)

        title_row.addWidget(title)
        title_row.addWidget(caption)
        title_row.addStretch(1)
        title_row.addWidget(self.check_button)

        self.environment_output = QPlainTextEdit()
        self.environment_output.setReadOnly(True)
        self.environment_output.setPlaceholderText("点击“检查开发环境”查看结果。")
        self.environment_output.setMinimumHeight(165)
        self.environment_output.setMaximumHeight(205)

        layout.addLayout(title_row)
        layout.addWidget(self.environment_output)
        return panel

    def run_environment_check(self) -> list[EnvironmentCheck]:
        """Run checks and present a compact pass/fail report."""

        checks = collect_environment_checks()
        self._display_checks(checks)
        return checks

    def _display_checks(self, checks: Sequence[EnvironmentCheck]) -> None:
        lines = [
            f"{'PASS' if check.passed else 'FAIL'}  {check.name}: {check.detail}"
            for check in checks
        ]
        passed_count = sum(check.passed for check in checks)
        result = "全部通过" if all_checks_passed(list(checks)) else "存在待处理项"
        lines.extend(("", f"结果：{result}（{passed_count}/{len(checks)}）"))
        self.environment_output.setPlainText("\n".join(lines))
