"""Tests for design validation and parameter contracts."""

from dataclasses import replace

import pytest

from pmsm_ai.domain import DEFAULT_DESIGN


def test_default_design_is_valid() -> None:
    DEFAULT_DESIGN.validate()


def test_invalid_geometry_is_rejected() -> None:
    invalid = replace(
        DEFAULT_DESIGN,
        stator_outer_diameter_mm=80.0,
        stator_inner_diameter_mm=55.0,
    )

    with pytest.raises(ValueError, match="不得小于 30 mm"):
        invalid.validate()


def test_out_of_range_parameter_is_rejected() -> None:
    invalid = replace(DEFAULT_DESIGN, air_gap_mm=0.95)

    with pytest.raises(ValueError, match="气隙长度"):
        invalid.validate()


def test_unknown_topology_is_rejected() -> None:
    invalid = replace(DEFAULT_DESIGN, topology="unknown")

    with pytest.raises(ValueError, match="未知电机拓扑"):
        invalid.validate()


def test_invalid_rotor_mechanical_stack_is_rejected() -> None:
    invalid = replace(
        DEFAULT_DESIGN,
        shaft_diameter_mm=30.0,
        rotor_yoke_thickness_mm=18.0,
    )

    with pytest.raises(ValueError, match="转子外径"):
        invalid.validate()


def test_updated_design_is_validated() -> None:
    updated = DEFAULT_DESIGN.with_updates(rated_current_a=8.0)

    assert updated.rated_current_a == 8.0
    assert DEFAULT_DESIGN.rated_current_a == 6.0
