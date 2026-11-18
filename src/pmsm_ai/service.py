"""Application services combining analytical and surrogate predictions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pmsm_ai.analytical import AnalyticalPMSMModel
from pmsm_ai.dataset import TRAINING_POWER_RANGE_W
from pmsm_ai.domain import (
    PARAMETER_SPEC_BY_NAME,
    PerformancePrediction,
    PMSMDesign,
)
from pmsm_ai.surrogate import ModelBundle


@dataclass(frozen=True, slots=True)
class PredictionReport:
    """One surrogate prediction with its transparent analytical baseline."""

    surrogate: PerformancePrediction
    analytical: PerformancePrediction
    analytical_power_w: float
    outside_training_power_range: bool


@dataclass(frozen=True, slots=True)
class TrendSeries:
    """One parameter-scan curve for a selected output."""

    parameter: str
    output: str
    x_values: tuple[float, ...]
    y_values: tuple[float | None, ...]


class PredictionService:
    """Keep scientific logic outside Qt widgets."""

    def __init__(
        self,
        bundle: ModelBundle,
        analytical_model: AnalyticalPMSMModel | None = None,
    ) -> None:
        self.bundle = bundle
        self.analytical_model = analytical_model or AnalyticalPMSMModel()

    def predict(self, design: PMSMDesign) -> PredictionReport:
        """Predict one design and report whether it leaves the training envelope."""

        design.validate()
        evaluation = self.analytical_model.evaluate(design)
        prediction = self.bundle.predict(design)
        low, high = TRAINING_POWER_RANGE_W
        outside = not low <= evaluation.shaft_power_w <= high
        return PredictionReport(
            surrogate=prediction,
            analytical=evaluation.prediction,
            analytical_power_w=evaluation.shaft_power_w,
            outside_training_power_range=outside,
        )

    def scan(
        self,
        design: PMSMDesign,
        parameter: str,
        output: str,
        points: int = 50,
    ) -> TrendSeries:
        """Scan one bounded input while holding all other inputs fixed."""

        if parameter not in PARAMETER_SPEC_BY_NAME:
            raise ValueError(f"不支持扫描参数：{parameter}")
        if output not in {"torque_nm", "torque_ripple_pct", "efficiency_pct"}:
            raise ValueError(f"不支持输出目标：{output}")
        if points < 2:
            raise ValueError("趋势扫描至少需要两个点")

        spec = PARAMETER_SPEC_BY_NAME[parameter]
        raw_values = np.linspace(spec.minimum, spec.maximum, points)
        if spec.is_integer:
            raw_values = np.unique(np.round(raw_values))

        x_values: list[float] = []
        y_values: list[float | None] = []
        for value in raw_values:
            update_value = int(value) if spec.is_integer else float(value)
            try:
                candidate = design.with_updates(**{parameter: update_value})
                report = self.predict(candidate)
            except ValueError:
                continue
            x_values.append(float(value))
            if report.outside_training_power_range:
                y_values.append(None)
            else:
                y_values.append(float(getattr(report.surrogate, output)))

        return TrendSeries(
            parameter=parameter,
            output=output,
            x_values=tuple(x_values),
            y_values=tuple(y_values),
        )
