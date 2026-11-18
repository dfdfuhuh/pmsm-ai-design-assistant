"""Matplotlib canvases embedded in the Qt interface."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pmsm_ai.service import TrendSeries

_PARAMETER_LABELS = {
    "stator_outer_diameter_mm": "Stator OD (mm)",
    "stator_inner_diameter_mm": "Stator ID (mm)",
    "stack_length_mm": "Stack length (mm)",
    "air_gap_mm": "Air gap (mm)",
    "magnet_thickness_mm": "Magnet thickness (mm)",
    "turns_per_phase": "Turns / phase",
    "rated_current_a": "Phase current (A rms)",
    "current_angle_deg": "Current angle (deg)",
    "speed_rpm": "Speed (rpm)",
    "magnet_remanence_t": "Magnet remanence (T)",
    "phase_resistance_ohm": "Phase resistance (ohm)",
}

_OUTPUT_LABELS = {
    "torque_nm": ("Torque (N·m)", "#16825d"),
    "torque_ripple_pct": ("Torque ripple (%)", "#d18122"),
    "efficiency_pct": ("Efficiency (%)", "#2377a8"),
}

_FEATURE_LABELS = {
    "stator_outer_diameter_mm": "Stator OD",
    "stator_inner_diameter_mm": "Stator ID",
    "stack_length_mm": "Stack length",
    "air_gap_mm": "Air gap",
    "magnet_thickness_mm": "Magnet thickness",
    "turns_per_phase": "Turns per phase",
    "rated_current_a": "Rated current",
    "current_angle_deg": "Current angle",
    "speed_rpm": "Speed",
    "magnet_remanence_t": "Magnet remanence",
    "phase_resistance_ohm": "Phase resistance",
    "airgap_flux_density_t": "Air-gap flux density",
    "pm_flux_linkage_wb": "PM flux linkage",
    "electrical_frequency_hz": "Electrical frequency",
    "mechanical_angular_speed_rad_s": "Mechanical speed",
}


class TrendPlotCanvas(FigureCanvasQTAgg):
    """Parameter-scan chart with gaps for invalid design combinations."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6.2, 3.2), dpi=100)
        super().__init__(self.figure)
        self.setMinimumHeight(285)
        self.show_placeholder()

    def show_placeholder(self) -> None:
        self.figure.clear()
        axes = self.figure.add_subplot(111)
        axes.text(
            0.5,
            0.55,
            "Prediction trend",
            ha="center",
            va="center",
            fontsize=16,
            color="#73857e",
            transform=axes.transAxes,
        )
        axes.text(
            0.5,
            0.42,
            "Choose a parameter and run a design scan",
            ha="center",
            va="center",
            fontsize=9,
            color="#93a29c",
            transform=axes.transAxes,
        )
        axes.set_axis_off()
        self.figure.tight_layout()
        self.draw_idle()

    def plot_series(self, series: TrendSeries) -> None:
        """Render one bounded parameter scan."""

        self.figure.clear()
        axes = self.figure.add_subplot(111)
        x_values = np.asarray(series.x_values, dtype=float)
        y_values = np.asarray(
            [np.nan if value is None else value for value in series.y_values],
            dtype=float,
        )
        y_label, color = _OUTPUT_LABELS[series.output]
        axes.plot(x_values, y_values, color=color, linewidth=2.2)
        axes.scatter(x_values, y_values, color=color, s=14)
        axes.set_xlabel(_PARAMETER_LABELS[series.parameter])
        axes.set_ylabel(y_label)
        axes.grid(True, color="#dce6e1", linewidth=0.8, alpha=0.9)
        axes.spines[["top", "right"]].set_visible(False)
        self.figure.tight_layout()
        self.draw_idle()


class ImportancePlotCanvas(FigureCanvasQTAgg):
    """Horizontal feature-importance chart."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(6.2, 3.5), dpi=100)
        super().__init__(self.figure)
        self.setMinimumHeight(300)
        self.show_placeholder()

    def show_placeholder(self) -> None:
        self.figure.clear()
        axes = self.figure.add_subplot(111)
        axes.text(
            0.5,
            0.5,
            "No trained model",
            ha="center",
            va="center",
            fontsize=15,
            color="#73857e",
            transform=axes.transAxes,
        )
        axes.set_axis_off()
        self.figure.tight_layout()
        self.draw_idle()

    def plot_importance(self, importances: Mapping[str, float]) -> None:
        """Render the ten most important model features."""

        self.figure.clear()
        axes = self.figure.add_subplot(111)
        ranked = sorted(importances.items(), key=lambda item: item[1])[-10:]
        names = [_FEATURE_LABELS.get(name, name) for name, _ in ranked]
        values = [value for _, value in ranked]
        axes.barh(names, values, color="#3b9473")
        axes.set_xlabel("Mean importance")
        axes.grid(axis="x", color="#dce6e1", linewidth=0.8, alpha=0.9)
        axes.spines[["top", "right"]].set_visible(False)
        self.figure.tight_layout()
        self.draw_idle()


def valid_series_points(series: TrendSeries) -> Sequence[float]:
    """Expose finite points for a concise status label."""

    return [value for value in series.y_values if value is not None]
