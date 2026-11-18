"""Random-forest surrogate training, evaluation and persistence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from pmsm_ai.analytical import DERIVED_FEATURE_NAMES, AnalyticalPMSMModel
from pmsm_ai.dataset import OUTPUT_COLUMNS, RAW_COLUMNS
from pmsm_ai.domain import (
    TOPOLOGY_FEATURE_NAMES,
    PerformancePrediction,
    PMSMDesign,
)

MODEL_VERSION = 3
MODEL_FEATURE_NAMES = RAW_COLUMNS + TOPOLOGY_FEATURE_NAMES + DERIVED_FEATURE_NAMES
TARGET_LABELS = {
    "torque_nm": "转矩",
    "torque_ripple_pct": "转矩脉动",
    "efficiency_pct": "效率",
}


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Reproducible random-forest settings for the course prototype."""

    seed: int = 42
    estimators: int = 200
    max_depth: int = 18
    min_samples_leaf: int = 3
    test_fraction: float = 0.30


DEFAULT_TRAINING_CONFIG = TrainingConfig()


@dataclass(frozen=True, slots=True)
class RegressionMetric:
    """Validation or test result for one target."""

    target: str
    r2: float
    mae: float
    rmse: float


@dataclass(slots=True)
class ModelBundle:
    """Three trained target models plus their exact inference contract."""

    models: dict[str, RandomForestRegressor]
    feature_names: tuple[str, ...]
    feature_importances: dict[str, float]
    validation_metrics: tuple[RegressionMetric, ...]
    test_metrics: tuple[RegressionMetric, ...]
    topology_metrics: dict[str, tuple[RegressionMetric, ...]]
    training_metadata: dict[str, Any]
    data_source: str
    fea_library_sha256: str | None
    fea_metrics: dict[str, Any]
    version: int = MODEL_VERSION

    def predict(self, design: PMSMDesign) -> PerformancePrediction:
        """Predict all three performance targets for one design."""

        analytical = AnalyticalPMSMModel()
        features = analytical.feature_dict(design)
        vector = np.array([[features[name] for name in self.feature_names]], dtype=float)
        predictions = {
            target: float(self.models[target].predict(vector)[0]) for target in OUTPUT_COLUMNS
        }
        return PerformancePrediction(
            torque_nm=predictions["torque_nm"],
            torque_ripple_pct=predictions["torque_ripple_pct"],
            efficiency_pct=predictions["efficiency_pct"],
        )

    def save(self, path: Path) -> None:
        """Persist the complete bundle with its feature and metric contract."""

        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)

    @classmethod
    def load(cls, path: Path) -> ModelBundle:
        """Load and validate a previously trained bundle."""

        if not path.is_file():
            raise FileNotFoundError(f"模型文件不存在：{path}")
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise ValueError("模型文件类型不正确，请重新训练")
        if loaded.version != MODEL_VERSION:
            raise ValueError("模型版本已更新，请重新训练")
        if loaded.feature_names != MODEL_FEATURE_NAMES:
            raise ValueError("模型特征顺序与当前代码不一致，请重新训练")
        if set(loaded.models) != set(OUTPUT_COLUMNS):
            raise ValueError("模型文件缺少预测目标，请重新训练")
        return loaded

    def test_metric(self, target: str) -> RegressionMetric:
        """Return the final test metric for a target."""

        return next(metric for metric in self.test_metrics if metric.target == target)


class RandomForestSurrogate:
    """Train one random forest per performance target."""

    def __init__(
        self,
        config: TrainingConfig = DEFAULT_TRAINING_CONFIG,
        analytical_model: AnalyticalPMSMModel | None = None,
    ) -> None:
        self.config = config
        self.analytical_model = analytical_model or AnalyticalPMSMModel()

    def train(
        self,
        frame: pd.DataFrame,
        progress: Callable[[int, str], None] | None = None,
        data_source: str = "synthetic analytical baseline",
        fea_library_sha256: str | None = None,
        fea_metrics: dict[str, Any] | None = None,
    ) -> ModelBundle:
        """Train and evaluate a model bundle on a tabular synthetic dataset."""

        required_columns = ("topology",) + RAW_COLUMNS + OUTPUT_COLUMNS
        missing = set(required_columns) - set(frame.columns)
        if missing:
            raise ValueError(f"训练数据缺少列：{', '.join(sorted(missing))}")
        if len(frame) < 50:
            raise ValueError("训练数据至少需要 50 行")

        self._report(progress, 5, "构造物理派生特征")
        features = self._build_feature_frame(frame)
        targets = frame.loc[:, list(OUTPUT_COLUMNS)].to_numpy(dtype=float)

        train_indices, remaining_indices = train_test_split(
            np.arange(len(frame)),
            test_size=self.config.test_fraction,
            random_state=self.config.seed,
            shuffle=True,
            stratify=frame["topology"],
        )
        validation_indices, test_indices = train_test_split(
            remaining_indices,
            test_size=0.50,
            random_state=self.config.seed,
            shuffle=True,
            stratify=frame.iloc[remaining_indices]["topology"],
        )

        models: dict[str, RandomForestRegressor] = {}
        validation_metrics: list[RegressionMetric] = []
        test_metrics: list[RegressionMetric] = []
        topology_metrics: dict[str, tuple[RegressionMetric, ...]] = {}
        importances: list[np.ndarray] = []

        for position, target in enumerate(OUTPUT_COLUMNS, start=1):
            self._report(progress, 15 + position * 20, f"训练 {TARGET_LABELS[target]}模型")
            model = RandomForestRegressor(
                n_estimators=self.config.estimators,
                max_depth=self.config.max_depth,
                min_samples_leaf=self.config.min_samples_leaf,
                max_features=1.0,
                random_state=self.config.seed,
                n_jobs=-1,
            )
            model.fit(features[train_indices], targets[train_indices, position - 1])
            model.set_params(n_jobs=1)
            validation_prediction = model.predict(features[validation_indices])
            test_prediction = model.predict(features[test_indices])
            validation_metrics.append(
                self._metric(
                    target,
                    targets[validation_indices, position - 1],
                    validation_prediction,
                )
            )
            test_metrics.append(
                self._metric(target, targets[test_indices, position - 1], test_prediction)
            )
            models[target] = model
            importances.append(model.feature_importances_)

        test_frame = frame.iloc[test_indices]
        for topology in test_frame["topology"].unique():
            topology_mask = (test_frame["topology"] == topology).to_numpy()
            topology_metrics[str(topology)] = tuple(
                self._metric(
                    target,
                    targets[test_indices[topology_mask], position],
                    models[target].predict(features[test_indices[topology_mask]]),
                )
                for position, target in enumerate(OUTPUT_COLUMNS)
            )

        mean_importance = np.mean(importances, axis=0)
        importance_map = {
            name: float(value)
            for name, value in zip(MODEL_FEATURE_NAMES, mean_importance, strict=True)
        }
        self._report(progress, 95, "整理模型指标")

        bundle = ModelBundle(
            models=models,
            feature_names=MODEL_FEATURE_NAMES,
            feature_importances=importance_map,
            validation_metrics=tuple(validation_metrics),
            test_metrics=tuple(test_metrics),
            topology_metrics=topology_metrics,
            training_metadata={
                "seed": self.config.seed,
                "estimators": self.config.estimators,
                "max_depth": self.config.max_depth,
                "min_samples_leaf": self.config.min_samples_leaf,
                "rows": len(frame),
                "train_rows": len(train_indices),
                "validation_rows": len(validation_indices),
                "test_rows": len(test_indices),
                "topologies": sorted(str(value) for value in frame["topology"].unique()),
                "sklearn_version": sklearn.__version__,
            },
            data_source=data_source,
            fea_library_sha256=fea_library_sha256,
            fea_metrics=fea_metrics or {},
        )
        self._report(progress, 100, "模型训练完成")
        return bundle

    def _build_feature_frame(self, frame: pd.DataFrame) -> np.ndarray:
        rows: list[list[float]] = []
        columns = ("topology",) + RAW_COLUMNS
        for row in frame.loc[:, list(columns)].itertuples(index=False, name=None):
            topology = str(row[0])
            raw_values = dict(zip(RAW_COLUMNS, row[1:], strict=True))
            raw_values["turns_per_phase"] = int(raw_values["turns_per_phase"])
            design = PMSMDesign(topology=topology, **raw_values)
            design.validate()
            features = self.analytical_model.feature_dict(design)
            rows.append([features[name] for name in MODEL_FEATURE_NAMES])
        return np.asarray(rows, dtype=float)

    @staticmethod
    def _metric(
        target: str,
        target_values: np.ndarray,
        predictions: np.ndarray,
    ) -> RegressionMetric:
        return RegressionMetric(
            target=target,
            r2=float(r2_score(target_values, predictions)),
            mae=float(mean_absolute_error(target_values, predictions)),
            rmse=float(mean_squared_error(target_values, predictions) ** 0.5),
        )

    @staticmethod
    def _report(
        progress: Callable[[int, str], None] | None,
        percent: int,
        message: str,
    ) -> None:
        if progress is not None:
            progress(percent, message)
