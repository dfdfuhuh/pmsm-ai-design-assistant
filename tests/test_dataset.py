"""Dataset reproducibility and committed artifact validation."""

import hashlib
import json

import pandas as pd

from pmsm_ai.dataset import (
    DATASET_COLUMNS,
    TRAINING_POWER_RANGE_W,
    PMSMDesignDatasetGenerator,
)
from pmsm_ai.domain import SPM_TOPOLOGIES
from pmsm_ai.paths import DEFAULT_DATASET_METADATA_PATH, DEFAULT_DATASET_PATH


def test_generator_is_reproducible() -> None:
    first = PMSMDesignDatasetGenerator(seed=11).generate(60)
    second = PMSMDesignDatasetGenerator(seed=11).generate(60)

    pd.testing.assert_frame_equal(first, second)


def test_generator_respects_count_columns_and_power_envelope() -> None:
    frame = PMSMDesignDatasetGenerator().generate(70)

    assert len(frame) == 350
    assert tuple(frame.columns) == DATASET_COLUMNS
    assert not frame.isna().any().any()
    assert (frame["stator_outer_diameter_mm"] - frame["stator_inner_diameter_mm"] >= 30).all()
    assert frame["turns_per_phase"].dtype.kind in {"i", "u"}
    assert frame["torque_nm"].min() > 0
    assert frame["efficiency_pct"].between(0, 100).all()
    assert TRAINING_POWER_RANGE_W == (300.0, 3500.0)
    assert set(frame["topology"]) == {topology.key for topology in SPM_TOPOLOGIES}
    assert frame.groupby("topology").size().eq(70).all()
    shaft_power = frame["torque_nm"] * frame["speed_rpm"] * 2 * 3.141592653589793 / 60
    assert shaft_power.between(*TRAINING_POWER_RANGE_W).all()


def test_committed_dataset_matches_metadata() -> None:
    frame = pd.read_csv(DEFAULT_DATASET_PATH)
    metadata = json.loads(DEFAULT_DATASET_METADATA_PATH.read_text(encoding="utf-8"))

    assert len(frame) == 25000
    assert metadata["sample_count"] == 25000
    assert metadata["samples_per_topology"] == 5000
    assert len(metadata["topologies"]) == 5
    assert metadata["seed"] == 42
    assert hashlib.sha256(DEFAULT_DATASET_PATH.read_bytes()).hexdigest() == metadata[
        "dataset_sha256"
    ]
