"""Random-forest accuracy, persistence and service behavior."""

from pathlib import Path

import pandas as pd
import pytest

from pmsm_ai.dataset import OUTPUT_COLUMNS
from pmsm_ai.domain import DEFAULT_DESIGN
from pmsm_ai.paths import DEFAULT_DATASET_PATH
from pmsm_ai.surrogate import ModelBundle, RandomForestSurrogate


def test_full_model_meets_acceptance_metrics() -> None:
    frame = pd.read_csv(DEFAULT_DATASET_PATH)
    bundle = RandomForestSurrogate().train(frame)

    for target in OUTPUT_COLUMNS:
        metric = bundle.test_metric(target)
        observed_range = frame[target].max() - frame[target].min()
        assert metric.r2 >= 0.95
        assert metric.mae <= 0.02 * observed_range


def test_model_bundle_round_trip(tmp_path: Path, tiny_bundle) -> None:
    model_path = tmp_path / "model.joblib"
    tiny_bundle.save(model_path)
    loaded = ModelBundle.load(model_path)

    assert loaded.feature_names == tiny_bundle.feature_names
    assert loaded.training_metadata["rows"] == 400
    assert set(loaded.topology_metrics) == {
        "spm_4p6s",
        "spm_6p9s",
        "spm_8p12s",
        "spm_8p18s",
        "spm_10p12s",
    }


def test_corrupt_model_file_is_rejected(tmp_path: Path) -> None:
    model_path = tmp_path / "corrupt.joblib"
    model_path.write_bytes(b"not a joblib model")

    with pytest.raises(KeyError):
        ModelBundle.load(model_path)


def test_prediction_service_returns_baseline_and_trend(tiny_service) -> None:
    report = tiny_service.predict(DEFAULT_DESIGN)
    series = tiny_service.scan(DEFAULT_DESIGN, "air_gap_mm", "torque_nm")

    assert report.surrogate.torque_nm > 0
    assert report.analytical.torque_nm > 0
    assert series.parameter == "air_gap_mm"
    assert len(series.x_values) == 50
    assert len(series.analytical_y_values) == 50
    assert any(value is not None for value in series.y_values)
    assert any(value is not None for value in series.analytical_y_values)


def test_scan_preserves_invalid_geometries_as_chart_gaps(tiny_service) -> None:
    series = tiny_service.scan(
        DEFAULT_DESIGN,
        "stator_outer_diameter_mm",
        "torque_nm",
        points=16,
    )

    assert len(series.x_values) == 16
    assert series.design_valid[0] is False
    assert series.y_values[0] is None
    assert series.analytical_y_values[0] is None
    assert any(series.design_valid)


def test_formula_scan_respects_target_dependencies(tiny_service) -> None:
    speed_series = tiny_service.scan(
        DEFAULT_DESIGN, "speed_rpm", "torque_nm", points=9
    )
    voltage_series = tiny_service.scan(
        DEFAULT_DESIGN, "dc_bus_voltage_v", "torque_nm", points=9
    )
    resistance_series = tiny_service.scan(
        DEFAULT_DESIGN, "phase_resistance_ohm", "torque_nm", points=9
    )
    shaft_series = tiny_service.scan(
        DEFAULT_DESIGN, "shaft_diameter_mm", "torque_nm", points=9
    )

    for series in (speed_series, voltage_series, resistance_series, shaft_series):
        values = [value for value in series.analytical_values if value is not None]
        assert max(values) - min(values) < 1e-9


def test_prediction_service_rejects_unknown_scan_parameter(tiny_service) -> None:
    with pytest.raises(ValueError, match="不支持扫描参数"):
        tiny_service.scan(DEFAULT_DESIGN, "unknown", "torque_nm")
