"""Reduced-order analytical model for a surface-mounted PMSM."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pmsm_ai.domain import (
    SPM_TOPOLOGIES,
    PerformancePrediction,
    PMSMDesign,
    TopologySpec,
    get_topology,
)

RELATIVE_PERMEABILITY = 1.05
MAGNETIC_SATURATION_FACTOR = 1.15
LAMINATION_STACKING_FACTOR = 0.95
LAMINATION_DENSITY_KG_M3 = 7600.0
SLOT_OPENING_REFERENCE_MM = 1.2
ROTOR_YOKE_REFERENCE_MM = 10.0


@dataclass(frozen=True, slots=True)
class AnalyticalEvaluation:
    """Performance and intermediate quantities from the teaching model."""

    prediction: PerformancePrediction
    airgap_flux_density_t: float
    pm_flux_linkage_wb: float
    electrical_frequency_hz: float
    mechanical_angular_speed_rad_s: float
    rotor_diameter_mm: float
    rotor_mass_kg: float
    required_voltage_v: float
    maximum_phase_voltage_v: float
    voltage_utilization_pct: float
    shaft_power_w: float
    copper_loss_w: float
    core_loss_w: float
    mechanical_loss_w: float


class AnalyticalPMSMModel:
    """Physics-inspired reduced-order model, not a finite-element substitute."""

    def evaluate(self, design: PMSMDesign) -> AnalyticalEvaluation:
        """Evaluate one validated design at its steady-state operating point."""

        design.validate()
        topology = get_topology(design.topology)
        airgap_flux_density = self._airgap_flux_density(design)
        pm_flux_linkage = self._pm_flux_linkage(design, topology, airgap_flux_density)
        torque = (
            1.5
            * topology.pole_pairs
            * pm_flux_linkage
            * design.rated_current_a
            * math.cos(math.radians(design.current_angle_deg))
        )
        electrical_frequency = topology.pole_pairs * design.speed_rpm / 60.0
        angular_speed = 2.0 * math.pi * design.speed_rpm / 60.0
        current_angle = math.radians(design.current_angle_deg)
        current_d = -design.rated_current_a * math.sin(current_angle)
        current_q = design.rated_current_a * math.cos(current_angle)
        inductance_h = design.phase_inductance_mh * 1e-3
        flux_speed = electrical_frequency * 2.0 * math.pi
        voltage_d = (
            design.phase_resistance_ohm * current_d - flux_speed * inductance_h * current_q
        )
        voltage_q = (
            design.phase_resistance_ohm * current_q
            + flux_speed * (pm_flux_linkage + inductance_h * current_d)
        )
        required_voltage = math.hypot(voltage_d, voltage_q)
        maximum_phase_voltage = design.dc_bus_voltage_v / math.sqrt(3.0)
        voltage_utilization = 100.0 * required_voltage / maximum_phase_voltage
        shaft_power = torque * angular_speed
        copper_loss = 3.0 * design.rated_current_a**2 * design.phase_resistance_ohm
        core_loss = self._core_loss(design, airgap_flux_density, electrical_frequency)
        rotor_diameter = design.stator_inner_diameter_mm - 2.0 * design.air_gap_mm
        rotor_mass = self._rotor_mass(design, rotor_diameter)
        mechanical_loss = (5e-7 + 2e-9 * rotor_mass) * design.speed_rpm**2
        total_loss = copper_loss + core_loss + mechanical_loss
        efficiency = 100.0 * shaft_power / (shaft_power + total_loss)
        ripple = self._torque_ripple(design, topology.ripple_factor, airgap_flux_density)

        return AnalyticalEvaluation(
            prediction=PerformancePrediction(
                torque_nm=torque,
                torque_ripple_pct=ripple,
                efficiency_pct=efficiency,
            ),
            airgap_flux_density_t=airgap_flux_density,
            pm_flux_linkage_wb=pm_flux_linkage,
            electrical_frequency_hz=electrical_frequency,
            mechanical_angular_speed_rad_s=angular_speed,
            rotor_diameter_mm=rotor_diameter,
            rotor_mass_kg=rotor_mass,
            required_voltage_v=required_voltage,
            maximum_phase_voltage_v=maximum_phase_voltage,
            voltage_utilization_pct=voltage_utilization,
            shaft_power_w=shaft_power,
            copper_loss_w=copper_loss,
            core_loss_w=core_loss,
            mechanical_loss_w=mechanical_loss,
        )

    def feature_dict(self, design: PMSMDesign) -> dict[str, float]:
        """Build raw and physically derived features in deterministic order."""

        evaluation = self.evaluate(design)
        features: dict[str, float] = design.to_dict()
        features.update(
            {
                f"topology_{topology.key}": float(design.topology == topology.key)
                for topology in SPM_TOPOLOGIES
            }
        )
        features.update(
            {
                "airgap_flux_density_t": evaluation.airgap_flux_density_t,
                "pm_flux_linkage_wb": evaluation.pm_flux_linkage_wb,
                "electrical_frequency_hz": evaluation.electrical_frequency_hz,
                "mechanical_angular_speed_rad_s": evaluation.mechanical_angular_speed_rad_s,
                "rotor_diameter_mm": evaluation.rotor_diameter_mm,
                "rotor_mass_kg": evaluation.rotor_mass_kg,
                "voltage_utilization_pct": evaluation.voltage_utilization_pct,
            }
        )
        return features

    @staticmethod
    def _airgap_flux_density(design: PMSMDesign) -> float:
        carter_factor = 1.0 + 0.18 * design.slot_opening_mm / (
            design.slot_opening_mm + design.air_gap_mm
        )
        leakage_factor = 1.0 - 0.03 * max(
            0.0,
            ROTOR_YOKE_REFERENCE_MM - design.rotor_yoke_thickness_mm,
        ) / ROTOR_YOKE_REFERENCE_MM
        denominator = (
            design.magnet_thickness_mm
            + RELATIVE_PERMEABILITY
            * design.air_gap_mm
            * carter_factor
            * MAGNETIC_SATURATION_FACTOR
        )
        return (
            design.magnet_remanence_t
            * design.magnet_thickness_mm
            * leakage_factor
            / denominator
        )

    @staticmethod
    def _pm_flux_linkage(
        design: PMSMDesign,
        topology: TopologySpec,
        airgap_flux_density: float,
    ) -> float:
        inner_radius_m = design.stator_inner_diameter_mm * 1e-3 / 2.0
        pole_area_m2 = (
            math.pi
            * inner_radius_m
            / topology.pole_pairs
            * design.stack_length_mm
            * 1e-3
        )
        return (
            topology.winding_factor
            * design.turns_per_phase
            * airgap_flux_density
            * pole_area_m2
            * LAMINATION_STACKING_FACTOR
        )

    @staticmethod
    def _core_loss(
        design: PMSMDesign,
        airgap_flux_density: float,
        electrical_frequency: float,
    ) -> float:
        outer_radius_m = design.stator_outer_diameter_mm * 1e-3 / 2.0
        inner_radius_m = design.stator_inner_diameter_mm * 1e-3 / 2.0
        lamination_mass = (
            math.pi
            * (outer_radius_m**2 - inner_radius_m**2)
            * design.stack_length_mm
            * 1e-3
            * LAMINATION_STACKING_FACTOR
            * LAMINATION_DENSITY_KG_M3
        )
        specific_loss = (
            0.022 * electrical_frequency * airgap_flux_density**2
            + 5e-5 * electrical_frequency**2 * airgap_flux_density**2
        )
        return lamination_mass * specific_loss

    @staticmethod
    def _torque_ripple(
        design: PMSMDesign,
        ripple_factor: float,
        airgap_flux_density: float,
    ) -> float:
        ripple = (
            2.0
            + 1.4 * 3.0 / design.magnet_thickness_mm
            + 0.6 * 0.5 / design.air_gap_mm
            + 0.02 * design.current_angle_deg
            + 0.2 * airgap_flux_density
        )
        mechanical_modifier = 1.0 + 0.15 * (
            design.slot_opening_mm - SLOT_OPENING_REFERENCE_MM
        ) / SLOT_OPENING_REFERENCE_MM + 0.04 * (
            ROTOR_YOKE_REFERENCE_MM - design.rotor_yoke_thickness_mm
        ) / 5.0
        return max(ripple * ripple_factor * mechanical_modifier, 0.0)

    @staticmethod
    def _rotor_mass(design: PMSMDesign, rotor_diameter_mm: float) -> float:
        rotor_radius_m = rotor_diameter_mm * 1e-3 / 2.0
        shaft_radius_m = design.shaft_diameter_mm * 1e-3 / 2.0
        volume = (
            math.pi
            * (rotor_radius_m**2 - shaft_radius_m**2)
            * design.stack_length_mm
            * 1e-3
            * LAMINATION_STACKING_FACTOR
        )
        return volume * LAMINATION_DENSITY_KG_M3


DERIVED_FEATURE_NAMES: tuple[str, ...] = (
    "airgap_flux_density_t",
    "pm_flux_linkage_wb",
    "electrical_frequency_hz",
    "mechanical_angular_speed_rad_s",
    "rotor_diameter_mm",
    "rotor_mass_kg",
    "voltage_utilization_pct",
)
