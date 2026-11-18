"""Reduced-order analytical model for a surface-mounted PMSM."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pmsm_ai.domain import PerformancePrediction, PMSMDesign

SLOT_COUNT = 12
POLE_PAIRS = 4
RELATIVE_PERMEABILITY = 1.05
MAGNETIC_SATURATION_FACTOR = 1.15
LAMINATION_STACKING_FACTOR = 0.95
WINDING_FACTOR = 0.933
LAMINATION_DENSITY_KG_M3 = 7600.0


@dataclass(frozen=True, slots=True)
class AnalyticalEvaluation:
    """Performance and intermediate quantities from the teaching model."""

    prediction: PerformancePrediction
    airgap_flux_density_t: float
    pm_flux_linkage_wb: float
    electrical_frequency_hz: float
    mechanical_angular_speed_rad_s: float
    shaft_power_w: float
    copper_loss_w: float
    core_loss_w: float
    mechanical_loss_w: float


class AnalyticalPMSMModel:
    """Physics-inspired reduced-order model, not a finite-element substitute."""

    def evaluate(self, design: PMSMDesign) -> AnalyticalEvaluation:
        """Evaluate one validated design at its steady-state operating point."""

        design.validate()
        airgap_flux_density = self._airgap_flux_density(design)
        pm_flux_linkage = self._pm_flux_linkage(design, airgap_flux_density)
        torque = (
            1.5
            * POLE_PAIRS
            * pm_flux_linkage
            * design.rated_current_a
            * math.cos(math.radians(design.current_angle_deg))
        )
        electrical_frequency = POLE_PAIRS * design.speed_rpm / 60.0
        angular_speed = 2.0 * math.pi * design.speed_rpm / 60.0
        shaft_power = torque * angular_speed
        copper_loss = 3.0 * design.rated_current_a**2 * design.phase_resistance_ohm
        core_loss = self._core_loss(design, airgap_flux_density, electrical_frequency)
        mechanical_loss = 8e-7 * design.speed_rpm**2
        total_loss = copper_loss + core_loss + mechanical_loss
        efficiency = 100.0 * shaft_power / (shaft_power + total_loss)
        ripple = self._torque_ripple(design, airgap_flux_density)

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
                "airgap_flux_density_t": evaluation.airgap_flux_density_t,
                "pm_flux_linkage_wb": evaluation.pm_flux_linkage_wb,
                "electrical_frequency_hz": evaluation.electrical_frequency_hz,
                "mechanical_angular_speed_rad_s": evaluation.mechanical_angular_speed_rad_s,
            }
        )
        return features

    @staticmethod
    def _airgap_flux_density(design: PMSMDesign) -> float:
        denominator = (
            design.magnet_thickness_mm
            + RELATIVE_PERMEABILITY * design.air_gap_mm * MAGNETIC_SATURATION_FACTOR
        )
        return design.magnet_remanence_t * design.magnet_thickness_mm / denominator

    @staticmethod
    def _pm_flux_linkage(design: PMSMDesign, airgap_flux_density: float) -> float:
        inner_radius_m = design.stator_inner_diameter_mm * 1e-3 / 2.0
        pole_area_m2 = (
            math.pi
            * inner_radius_m
            / POLE_PAIRS
            * design.stack_length_mm
            * 1e-3
        )
        return (
            WINDING_FACTOR
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
    def _torque_ripple(design: PMSMDesign, airgap_flux_density: float) -> float:
        ripple = (
            2.0
            + 1.4 * 3.0 / design.magnet_thickness_mm
            + 0.6 * 0.5 / design.air_gap_mm
            + 0.02 * design.current_angle_deg
            + 0.2 * airgap_flux_density
        )
        return max(ripple, 0.0)


DERIVED_FEATURE_NAMES: tuple[str, ...] = (
    "airgap_flux_density_t",
    "pm_flux_linkage_wb",
    "electrical_frequency_hz",
    "mechanical_angular_speed_rad_s",
)
