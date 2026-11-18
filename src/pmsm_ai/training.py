"""Shared model-building workflow used by CLI and the GUI."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from pmsm_ai.dataset import TRAINING_POWER_RANGE_W
from pmsm_ai.fea import CalibrationBundle, apply_calibration, file_sha256
from pmsm_ai.paths import (
    DEFAULT_DATASET_PATH,
    DEFAULT_METRICS_PATH,
    DEFAULT_MODEL_PATH,
    FEA_CALIBRATION_PATH,
    FEA_LIBRARY_PATH,
)
from pmsm_ai.surrogate import (
    DEFAULT_TRAINING_CONFIG,
    ModelBundle,
    RandomForestSurrogate,
    TrainingConfig,
)


def train_and_save(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    metrics_path: Path = DEFAULT_METRICS_PATH,
    calibration_path: Path = FEA_CALIBRATION_PATH,
    config: TrainingConfig = DEFAULT_TRAINING_CONFIG,
    progress: Callable[[int, str], None] | None = None,
) -> ModelBundle:
    """Train from the committed CSV, save the model and a JSON metrics summary."""

    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"找不到训练数据：{dataset_path}。请先运行 scripts/generate_dataset.py"
        )

    frame = pd.read_csv(dataset_path)
    data_source = "合成解析基线（未FEA校准）"
    fea_library_sha256: str | None = None
    fea_metrics: dict = {}
    if calibration_path.is_file():
        calibration = CalibrationBundle.load(calibration_path)
        if not FEA_LIBRARY_PATH.is_file():
            raise FileNotFoundError("存在 FEA 校准参数但缺少 FEA 参考库")
        if file_sha256(FEA_LIBRARY_PATH) != calibration.library_sha256:
            raise ValueError("FEA 参考库与校准参数哈希不一致，请重新校准")
        frame = apply_calibration(frame, calibration)
        data_source = "FEA Ridge校准的合成数据"
        fea_library_sha256 = calibration.library_sha256
        fea_metrics = calibration.metrics
    bundle = RandomForestSurrogate(config=config).train(
        frame,
        progress=progress,
        data_source=data_source,
        fea_library_sha256=fea_library_sha256,
        fea_metrics=fea_metrics,
    )
    bundle.save(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_payload = {
        "model_version": bundle.version,
        "feature_names": list(bundle.feature_names),
        "training_metadata": bundle.training_metadata,
        "validation_metrics": [asdict(metric) for metric in bundle.validation_metrics],
        "test_metrics": [asdict(metric) for metric in bundle.test_metrics],
        "topology_metrics": {
            topology: [asdict(metric) for metric in metrics]
            for topology, metrics in bundle.topology_metrics.items()
        },
        "feature_importances": bundle.feature_importances,
        "training_power_range_w": list(TRAINING_POWER_RANGE_W),
        "data_source": bundle.data_source,
        "fea_library_sha256": bundle.fea_library_sha256,
        "fea_holdout_metrics": bundle.fea_metrics,
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle
