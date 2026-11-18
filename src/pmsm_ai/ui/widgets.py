"""Reusable presentation widgets for the PMSM workbench."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class MetricCard(QFrame):
    """Prediction card showing the surrogate value and analytical baseline."""

    def __init__(
        self,
        title: str,
        unit: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("metric-card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        caption = QLabel(title)
        caption.setObjectName("metric-caption")
        self.value_label = QLabel(f"— {unit}")
        self.value_label.setObjectName("metric-value")
        self.baseline_label = QLabel("等待模型预测")
        self.baseline_label.setObjectName("metric-baseline")
        self.baseline_label.setWordWrap(True)

        layout.addWidget(caption)
        layout.addWidget(self.value_label)
        layout.addWidget(self.baseline_label)

    def update_values(
        self,
        surrogate: float,
        analytical: float,
        unit: str,
    ) -> None:
        """Present surrogate and analytical values side by side."""

        self.value_label.setText(f"{surrogate:.3f} {unit}")
        self.baseline_label.setText(f"公式基准：{analytical:.3f} {unit}")

    def clear_values(self, unit: str) -> None:
        """Reset the card to its model-not-ready state."""

        self.value_label.setText(f"— {unit}")
        self.baseline_label.setText("等待模型预测")
