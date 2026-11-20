"""Matplotlib canvases embedded in the Qt interface."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pmsm_ai.service import TrendSeries

matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False

_PARAMETER_LABELS = {
    "stator_outer_diameter_mm": "定子外径 (mm)",
    "stator_inner_diameter_mm": "定子内径 (mm)",
    "stack_length_mm": "铁芯长度 (mm)",
    "air_gap_mm": "气隙长度 (mm)",
    "magnet_thickness_mm": "磁钢厚度 (mm)",
    "turns_per_phase": "每相串联匝数 (匝)",
    "rated_current_a": "额定相电流 RMS (A)",
    "current_angle_deg": "电流超前角 (°)",
    "speed_rpm": "转速 (rpm)",
    "magnet_remanence_t": "永磁体剩磁 (T)",
    "phase_resistance_ohm": "相电阻 (Ω)",
    "phase_inductance_mh": "相电感 (mH)",
    "dc_bus_voltage_v": "逆变器母线电压 (V)",
    "slot_opening_mm": "定子槽口宽 (mm)",
    "rotor_yoke_thickness_mm": "转子轭厚 (mm)",
    "shaft_diameter_mm": "转轴直径 (mm)",
}

_OUTPUT_LABELS = {
    "torque_nm": ("平均转矩 (N·m)", "#16825d"),
    "torque_ripple_pct": ("转矩脉动 (%)", "#d18122"),
    "efficiency_pct": ("效率 (%)", "#2377a8"),
}

_FEATURE_LABELS = {
    "stator_outer_diameter_mm": "定子外径",
    "stator_inner_diameter_mm": "定子内径",
    "stack_length_mm": "铁芯长度",
    "air_gap_mm": "气隙长度",
    "magnet_thickness_mm": "磁钢厚度",
    "turns_per_phase": "每相匝数",
    "rated_current_a": "额定相电流",
    "current_angle_deg": "电流超前角",
    "speed_rpm": "转速",
    "magnet_remanence_t": "永磁体剩磁",
    "phase_resistance_ohm": "相电阻",
    "phase_inductance_mh": "相电感",
    "dc_bus_voltage_v": "母线电压",
    "slot_opening_mm": "定子槽口宽",
    "rotor_yoke_thickness_mm": "转子轭厚",
    "shaft_diameter_mm": "转轴直径",
    "airgap_flux_density_t": "气隙磁密",
    "pm_flux_linkage_wb": "永磁磁链",
    "electrical_frequency_hz": "电频率",
    "mechanical_angular_speed_rad_s": "机械角速度",
    "rotor_diameter_mm": "转子直径",
    "rotor_mass_kg": "转子质量",
    "voltage_utilization_pct": "电压利用率",
    "topology_spm_4p6s": "4极6槽拓扑",
    "topology_spm_6p9s": "6极9槽拓扑",
    "topology_spm_8p12s": "8极12槽拓扑",
    "topology_spm_8p18s": "8极18槽拓扑",
    "topology_spm_10p12s": "10极12槽拓扑",
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
            "等待生成参数趋势",
            ha="center",
            va="center",
            fontsize=16,
            color="#73857e",
            transform=axes.transAxes,
        )
        axes.text(
            0.5,
            0.42,
            "选择参数和目标后，点击“更新趋势”",
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
        """Render formula and AI trends without hiding invalid ranges."""

        self.figure.clear()
        axes = self.figure.add_subplot(111)
        x_values = np.asarray(series.x_values, dtype=float)
        formula_values = np.asarray(
            [np.nan if value is None else value for value in series.analytical_values],
            dtype=float,
        )
        ai_values = np.asarray(
            [np.nan if value is None else value for value in series.y_values],
            dtype=float,
        )
        y_label, color = _OUTPUT_LABELS[series.output]
        if not np.isfinite(formula_values).any() and not np.isfinite(ai_values).any():
            axes.text(
                0.5,
                0.5,
                "当前范围内没有满足几何约束的设计点",
                ha="center",
                va="center",
                fontsize=13,
                color="#73857e",
                transform=axes.transAxes,
            )
            axes.set_axis_off()
            self.figure.tight_layout()
            self.draw_idle()
            return

        axes.plot(
            x_values,
            formula_values,
            color=color,
            linewidth=2.2,
            label="解析公式趋势",
        )
        if np.isfinite(ai_values).any():
            axes.plot(
                x_values,
                ai_values,
                color=color,
                linewidth=1.7,
                linestyle="--",
                marker="o",
                markersize=3.2,
                label="AI 代理预测（仅训练覆盖区）",
            )
        axes.set_xlabel(_PARAMETER_LABELS[series.parameter])
        axes.set_ylabel(y_label)
        axes.grid(True, color="#dce6e1", linewidth=0.8, alpha=0.9)
        axes.spines[["top", "right"]].set_visible(False)
        axes.legend(loc="best", fontsize=8, frameon=False)
        axes.text(
            0.0,
            1.02,
            "实线为公式趋势，虚线为 AI 代理；断点表示不可行或超出训练域",
            transform=axes.transAxes,
            fontsize=8,
            color="#73857e",
            va="bottom",
        )
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
            "尚无可用模型",
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
        axes.set_xlabel("平均特征重要性（越长表示影响越大）")
        axes.grid(axis="x", color="#dce6e1", linewidth=0.8, alpha=0.9)
        axes.spines[["top", "right"]].set_visible(False)
        self.figure.tight_layout()
        self.draw_idle()


def valid_series_points(series: TrendSeries) -> Sequence[float]:
    """Expose finite points for a concise status label."""

    return [value for value in series.y_values if value is not None]
