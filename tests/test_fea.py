"""Tests for offline FEA planning and leakage-free calibration."""

from pathlib import Path

import pandas as pd

from pmsm_ai.analytical import AnalyticalPMSMModel
from pmsm_ai.domain import DEFAULT_DESIGN, SPM_TOPOLOGIES
from pmsm_ai.fea import (
    FEA_COLUMNS,
    FEASampleRecord,
    apply_calibration,
    build_fea_plan,
    calibrate_from_library,
    write_fea_plan,
)
from pmsm_ai.maxwell_runner import _conductors_per_slot


def test_fea_plan_is_balanced_and_deterministic() -> None:
    first = build_fea_plan(samples_per_topology=20, calibration_per_topology=15)
    second = build_fea_plan(samples_per_topology=20, calibration_per_topology=15)

    assert [item.sample_id for item in first] == [item.sample_id for item in second]
    assert len(first) == 100
    for topology in SPM_TOPOLOGIES:
        subset = [item for item in first if item.topology == topology.key]
        assert len(subset) == 20
        assert sum(item.split == "calibration" for item in subset) == 15
        assert sum(item.split == "holdout" for item in subset) == 5


def test_fea_plan_writes_reviewable_csv(tmp_path: Path) -> None:
    plan = build_fea_plan(samples_per_topology=5, calibration_per_topology=3)
    output = tmp_path / "plan.csv"

    write_fea_plan(plan, output)

    frame = pd.read_csv(output)
    assert len(frame) == 5 * len(SPM_TOPOLOGIES)
    assert {"sample_id", "topology", "split"}.issubset(frame.columns)


def test_calibration_improves_synthetic_fea_fixture() -> None:
    plan = build_fea_plan(samples_per_topology=10, calibration_per_topology=7)
    analytical = AnalyticalPMSMModel()
    rows = []
    for item in plan:
        prediction = analytical.evaluate(item.design).prediction
        record = FEASampleRecord(
            sample_id=item.sample_id,
            topology=item.topology,
            split=item.split,
            design=item.design,
            torque_nm=prediction.torque_nm * 0.94,
            torque_ripple_pct=prediction.torque_ripple_pct * 1.08,
            efficiency_pct=prediction.efficiency_pct - 1.2,
            core_loss_w=10.0,
            stranded_loss_w=20.0,
            mechanical_loss_w=2.0,
            solver_seconds=1.0,
        )
        rows.append(record.to_dict())
    frame = pd.DataFrame(rows, columns=FEA_COLUMNS)

    bundle = calibrate_from_library(frame, "fixture-sha256")

    for topology in SPM_TOPOLOGIES:
        assert bundle.models[topology.key].keys() == {
            "torque_nm",
            "torque_ripple_pct",
            "efficiency_pct",
        }
        assert bundle.metrics[topology.key]["torque_nm"]["r2"] > 0.95


def test_calibration_applies_to_dense_data() -> None:
    plan = build_fea_plan(samples_per_topology=10, calibration_per_topology=7)
    analytical = AnalyticalPMSMModel()
    rows = []
    for item in plan:
        prediction = analytical.evaluate(item.design).prediction
        rows.append(
            FEASampleRecord(
                sample_id=item.sample_id,
                topology=item.topology,
                split=item.split,
                design=item.design,
                torque_nm=prediction.torque_nm * 0.9,
                torque_ripple_pct=prediction.torque_ripple_pct * 1.1,
                efficiency_pct=prediction.efficiency_pct - 1.0,
                core_loss_w=10.0,
                stranded_loss_w=20.0,
                mechanical_loss_w=2.0,
                solver_seconds=1.0,
            ).to_dict()
        )
    library = pd.DataFrame(rows, columns=FEA_COLUMNS)
    calibration = calibrate_from_library(library, "fixture")
    dense = library.drop(
        columns=[
            "sample_id",
            "split",
            "core_loss_w",
            "stranded_loss_w",
            "mechanical_loss_w",
            "solver_seconds",
        ]
    )

    corrected = apply_calibration(dense, calibration)

    assert corrected["torque_nm"].notna().all()
    assert corrected["efficiency_pct"].notna().all()


def test_conductor_mapping_respects_topology_slot_count() -> None:
    for topology in SPM_TOPOLOGIES:
        design = DEFAULT_DESIGN.with_updates(topology=topology.key)
        assert _conductors_per_slot(design) >= 2
