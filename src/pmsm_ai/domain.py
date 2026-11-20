"""Validated design parameters for five surface-mounted PMSM topologies."""

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


@dataclass(frozen=True, slots=True)
class TopologySpec:
    """Fixed slot/pole data and analytical coefficients for one PMSM variant."""

    key: str
    label: str
    slots: int
    poles: int
    winding_factor: float
    ripple_factor: float
    description: str

    @property
    def pole_pairs(self) -> int:
        return self.poles // 2

    @property
    def short_label(self) -> str:
        return f"{self.poles}极{self.slots}槽"


SPM_TOPOLOGIES: tuple[TopologySpec, ...] = (
    TopologySpec(
        key="spm_4p6s",
        label="表贴式 4极6槽",
        slots=6,
        poles=4,
        winding_factor=0.866,
        ripple_factor=1.18,
        description="整数槽紧凑方案，适合低速大转矩场景。",
    ),
    TopologySpec(
        key="spm_6p9s",
        label="表贴式 6极9槽",
        slots=9,
        poles=6,
        winding_factor=0.866,
        ripple_factor=1.08,
        description="集中绕组方案，适合中低速伺服场景。",
    ),
    TopologySpec(
        key="spm_8p12s",
        label="表贴式 8极12槽",
        slots=12,
        poles=8,
        winding_factor=0.866,
        ripple_factor=1.00,
        description="结构清晰，适合作为教学与通用基准。",
    ),
    TopologySpec(
        key="spm_8p18s",
        label="表贴式 8极18槽",
        slots=18,
        poles=8,
        winding_factor=0.945,
        ripple_factor=0.76,
        description="分布绕组方案，侧重低转矩脉动。",
    ),
    TopologySpec(
        key="spm_10p12s",
        label="表贴式 10极12槽",
        slots=12,
        poles=10,
        winding_factor=0.933,
        ripple_factor=0.82,
        description="高绕组系数方案，侧重较低转矩脉动。",
    ),
)
TOPOLOGY_BY_KEY = {topology.key: topology for topology in SPM_TOPOLOGIES}
TOPOLOGY_FEATURE_NAMES: tuple[str, ...] = tuple(
    f"topology_{topology.key}" for topology in SPM_TOPOLOGIES
)
DEFAULT_TOPOLOGY_KEY = "spm_8p12s"


def get_topology(key: str) -> TopologySpec:
    """Return topology metadata or raise a user-facing validation error."""

    try:
        return TOPOLOGY_BY_KEY[key]
    except KeyError as exc:
        choices = "、".join(topology.label for topology in SPM_TOPOLOGIES)
        raise ValueError(f"未知电机拓扑；可选值为：{choices}") from exc


PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec("stator_outer_diameter_mm", "定子外径", "mm", 80.0, 120.0, 1),
    ParameterSpec("stator_inner_diameter_mm", "定子内径", "mm", 45.0, 75.0, 1),
    ParameterSpec("stack_length_mm", "铁芯轴向长度", "mm", 25.0, 55.0, 1),
    ParameterSpec("air_gap_mm", "气隙长度", "mm", 0.30, 0.80, 2),
    ParameterSpec("magnet_thickness_mm", "永磁体厚度", "mm", 2.0, 6.0, 2),
    ParameterSpec("slot_opening_mm", "定子槽口宽", "mm", 0.50, 3.0, 2),
    ParameterSpec("rotor_yoke_thickness_mm", "转子轭厚", "mm", 5.0, 18.0, 1),
    ParameterSpec("shaft_diameter_mm", "转轴直径", "mm", 8.0, 30.0, 1),
    ParameterSpec("turns_per_phase", "每相串联匝数", "匝", 40, 120, 0, True),
    ParameterSpec("rated_current_a", "额定相电流 RMS", "A", 2.0, 10.0, 1),
    ParameterSpec("current_angle_deg", "电流超前角", "°", 0.0, 30.0, 1),
    ParameterSpec("speed_rpm", "转速", "rpm", 1000.0, 4000.0, 0, True),
    ParameterSpec("magnet_remanence_t", "永磁体剩磁", "T", 0.95, 1.25, 2),
    ParameterSpec("phase_resistance_ohm", "相电阻", "Ω", 0.20, 1.20, 2),
    ParameterSpec("phase_inductance_mh", "相电感（Ld≈Lq）", "mH", 0.05, 5.0, 2),
    ParameterSpec("dc_bus_voltage_v", "逆变器母线电压", "V", 24, 400, 0, True),
)

PARAMETER_SPEC_BY_NAME = {spec.name: spec for spec in PARAMETER_SPECS}
RAW_FEATURE_NAMES: tuple[str, ...] = tuple(spec.name for spec in PARAMETER_SPECS)


@dataclass(frozen=True, slots=True)
class PMSMDesign:
    """Input design and operating point for one SPM motor."""

    topology: str
    stator_outer_diameter_mm: float
    stator_inner_diameter_mm: float
    stack_length_mm: float
    air_gap_mm: float
    magnet_thickness_mm: float
    slot_opening_mm: float
    rotor_yoke_thickness_mm: float
    shaft_diameter_mm: float
    turns_per_phase: int
    rated_current_a: float
    current_angle_deg: float
    speed_rpm: float
    magnet_remanence_t: float
    phase_resistance_ohm: float
    phase_inductance_mh: float
    dc_bus_voltage_v: int

    def validate(self) -> None:
        """Raise ``ValueError`` when a parameter is outside the model domain."""

        values = self.to_dict()
        errors: list[str] = []
        try:
            get_topology(self.topology)
        except ValueError as exc:
            errors.append(str(exc))
        for spec in PARAMETER_SPECS:
            value = values[spec.name]
            if not spec.minimum <= value <= spec.maximum:
                errors.append(
                    f"{spec.label}应在 {spec.minimum:g}–{spec.maximum:g} {spec.unit} 内"
                )

        diameter_difference = self.stator_outer_diameter_mm - self.stator_inner_diameter_mm
        if diameter_difference < 30.0:
            errors.append("定子外径与内径之差不得小于 30 mm")
        rotor_diameter = self.stator_inner_diameter_mm - 2.0 * self.air_gap_mm
        if self.shaft_diameter_mm + 2.0 * self.rotor_yoke_thickness_mm > rotor_diameter:
            errors.append("转轴直径与两倍转子轭厚之和必须小于转子外径")
        if not isinstance(self.turns_per_phase, int):
            errors.append("每相串联匝数必须为整数")
        if not isinstance(self.dc_bus_voltage_v, int):
            errors.append("逆变器母线电压必须为整数")

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
    topology=DEFAULT_TOPOLOGY_KEY,
    stator_outer_diameter_mm=110.0,
    stator_inner_diameter_mm=65.0,
    stack_length_mm=40.0,
    air_gap_mm=0.50,
    magnet_thickness_mm=3.50,
    slot_opening_mm=1.20,
    rotor_yoke_thickness_mm=10.0,
    shaft_diameter_mm=12.0,
    turns_per_phase=80,
    rated_current_a=6.0,
    current_angle_deg=15.0,
    speed_rpm=3000,
    magnet_remanence_t=1.15,
    phase_resistance_ohm=0.60,
    phase_inductance_mh=0.80,
    dc_bus_voltage_v=310,
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
