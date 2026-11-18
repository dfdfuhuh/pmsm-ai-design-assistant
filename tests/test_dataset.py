"""Dataset reproducibility and committed artifact validation."""

import hashlib
import json

import pandas as pd

from pmsm_ai.dataset import (
    DATASET_COLUMNS,
    TRAINING_POWER_RANGE_W,
    PMSMDesignDatasetGenerator,
)
from pmsm_ai.paths import DEFAULT_DATASET_METADATA_PATH, DEFAULT_DATASET_PATH


def test_generator_is_reproducible() -> None:
    first = PMSMDesignDatasetGenerator(seed=11).generate(180)
    second = PMSMDesignDatasetGenerator(seed=11).generate(180)

    pd.testing.assert_frame_equal(first, second)


def test_generator_respects_count_columns_and_power_envelope() -> None:
    frame = PMSMDesignDatasetGenerator().generate(220)

    assert len(frame) == 220
    assert tuple(frame.columns) == DATASET_COLUMNS
    assert not frame.isna().any().any()
    assert (frame["stator_outer_diameter_mm"] - frame["stator_inner_diameter_mm"] >= 30).all()
    assert frame["turns_per_phase"].dtype.kind in {"i", "u"}
    assert frame["torque_nm"].min() > 0
    assert frame["efficiency_pct"].between(0, 100).all()
    assert TRAINING_POWER_RANGE_W == (300.0, 3500.0)


def test_committed_dataset_matches_metadata() -> None:
    frame = pd.read_csv(DEFAULT_DATASET_PATH)
    metadata = json.loads(DEFAULT_DATASET_METADATA_PATH.read_text(encoding="utf-8"))

    assert len(frame) == 8000
    assert metadata["sample_count"] == 8000
    assert metadata["seed"] == 42
    assert hashlib.sha256(DEFAULT_DATASET_PATH.read_bytes()).hexdigest() == metadata[
        "dataset_sha256"
    ]
