"""Validated design parameters for the fixed 8-pole/12-slot SPM topology."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Display and validation metadata for one model input."""

    name: str
    label: str
    unit: str
    minimum: float
    maximum: float
    decimals: int = 2
    is_integer: bool = False

    @property
    def step(self) -> float:
        return 1.0 if self.is_integer else 10 ** (-self.decimals)


PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec("stator_outer_diameter_mm", "定子外径", "mm", 80.0, 120.0, 1),
    ParameterSpec("stator_inner_diameter_mm", "定子内径", "mm", 45.0, 75.0, 1),
    ParameterSpec("stack_length_mm", "铁芯轴向长度", "mm", 25.0, 55.0, 1),
    ParameterSpec("air_gap_mm", "气隙长度", "mm", 0.30, 0.80, 2),
    ParameterSpec("magnet_thickness_mm", "永磁体厚度", "mm", 2.0, 6.0, 2),
    ParameterSpec("turns_per_phase", "每相串联匝数", "匝", 40, 120, 0, True),
    ParameterSpec("rated_current_a", "额定相电流 RMS", "A", 2.0, 10.0, 1),
    ParameterSpec("current_angle_deg", "电流超前角", "°", 0.0, 30.0, 1),
    ParameterSpec("speed_rpm", "转速", "rpm", 1000.0, 4000.0, 0, True),
    ParameterSpec("magnet_remanence_t", "永磁体剩磁", "T", 0.95, 1.25, 2),
    ParameterSpec("phase_resistance_ohm", "相电阻", "Ω", 0.20, 1.20, 2),
)

PARAMETER_SPEC_BY_NAME = {spec.name: spec for spec in PARAMETER_SPECS}
RAW_FEATURE_NAMES: tuple[str, ...] = tuple(spec.name for spec in PARAMETER_SPECS)


@dataclass(frozen=True, slots=True)
class PMSMDesign:
    """Input design and operating point for one SPM motor."""

    stator_outer_diameter_mm: float
    stator_inner_diameter_mm: float
    stack_length_mm: float
    air_gap_mm: float
    magnet_thickness_mm: float
    turns_per_phase: int
    rated_current_a: float
    current_angle_deg: float
    speed_rpm: float
    magnet_remanence_t: float
    phase_resistance_ohm: float

    def validate(self) -> None:
        """Raise ``ValueError`` when a parameter is outside the model domain."""

        values = self.to_dict()
        errors: list[str] = []
        for spec in PARAMETER_SPECS:
            value = values[spec.name]
            if not spec.minimum <= value <= spec.maximum:
                errors.append(
                    f"{spec.label}应在 {spec.minimum:g}–{spec.maximum:g} {spec.unit} 内"
                )

        diameter_difference = self.stator_outer_diameter_mm - self.stator_inner_diameter_mm
        if diameter_difference < 30.0:
            errors.append("定子外径与内径之差不得小于 30 mm")
        if not isinstance(self.turns_per_phase, int):
            errors.append("每相串联匝数必须为整数")

        if errors:
            raise ValueError("；".join(errors))

    def to_dict(self) -> dict[str, float | int]:
        """Return raw model inputs in the canonical feature order."""

        values = asdict(self)
        return {name: values[name] for name in RAW_FEATURE_NAMES}

    def with_updates(self, **changes: Any) -> PMSMDesign:
        """Return a validated copy with selected fields replaced."""

        updated = replace(self, **changes)
        updated.validate()
        return updated


DEFAULT_DESIGN = PMSMDesign(
    stator_outer_diameter_mm=110.0,
    stator_inner_diameter_mm=65.0,
    stack_length_mm=40.0,
    air_gap_mm=0.50,
    magnet_thickness_mm=3.50,
    turns_per_phase=80,
    rated_current_a=6.0,
    current_angle_deg=15.0,
    speed_rpm=3000,
    magnet_remanence_t=1.15,
    phase_resistance_ohm=0.60,
)


@dataclass(frozen=True, slots=True)
class PerformancePrediction:
    """Predicted or analytically evaluated steady-state performance."""

    torque_nm: float
    torque_ripple_pct: float
    efficiency_pct: float


def design_field_names() -> tuple[str, ...]:
    """Return dataclass field names without depending on instance creation."""

    return tuple(field.name for field in fields(PMSMDesign))
