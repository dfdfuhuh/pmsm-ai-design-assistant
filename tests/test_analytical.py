"""Numerical and qualitative checks for the reduced-order model."""

import pytest

from pmsm_ai.analytical import AnalyticalPMSMModel
from pmsm_ai.domain import DEFAULT_DESIGN


def test_reference_design_matches_documented_result() -> None:
    prediction = AnalyticalPMSMModel().evaluate(DEFAULT_DESIGN).prediction

    assert prediction.torque_nm == pytest.approx(2.4692197246, rel=1e-8)
    assert prediction.torque_ripple_pct == pytest.approx(4.2961620469, rel=1e-8)
    assert prediction.efficiency_pct == pytest.approx(90.3348241896, rel=1e-8)


def test_torque_increases_with_current() -> None:
    model = AnalyticalPMSMModel()
    low_current = model.evaluate(DEFAULT_DESIGN.with_updates(rated_current_a=4.0))
    high_current = model.evaluate(DEFAULT_DESIGN.with_updates(rated_current_a=8.0))

    assert high_current.prediction.torque_nm > low_current.prediction.torque_nm


def test_larger_airgap_reduces_torque() -> None:
    model = AnalyticalPMSMModel()
    small_gap = model.evaluate(DEFAULT_DESIGN.with_updates(air_gap_mm=0.30))
    large_gap = model.evaluate(DEFAULT_DESIGN.with_updates(air_gap_mm=0.80))

    assert large_gap.prediction.torque_nm < small_gap.prediction.torque_nm


def test_losses_are_positive_and_efficiency_below_100() -> None:
    evaluation = AnalyticalPMSMModel().evaluate(DEFAULT_DESIGN)

    assert evaluation.copper_loss_w > 0
    assert evaluation.core_loss_w > 0
    assert evaluation.mechanical_loss_w > 0
    assert 0 < evaluation.prediction.efficiency_pct < 100
