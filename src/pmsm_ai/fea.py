"""Offline Maxwell reference-library plans and FEA calibration utilities."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from pmsm_ai.analytical import AnalyticalPMSMModel
from pmsm_ai.dataset import OUTPUT_COLUMNS, RAW_COLUMNS, PMSMDesignDatasetGenerator
from pmsm_ai.domain import SPM_TOPOLOGIES, PMSMDesign

FEA_LIBRARY_VERSION = 1
DEFAULT_FEA_SAMPLES_PER_TOPOLOGY = 20
DEFAULT_FEA_CALIBRATION_PER_TOPOLOGY = 15
FEA_SPLITS = ("calibration", "holdout")
FEA_MIN_RADIAL_BUILD_MM = {
    "spm_4p6s": 28.0,
    "spm_6p9s": 24.0,
    "spm_8p12s": 22.0,
    "spm_8p18s": 22.0,
    "spm_10p12s": 22.0,
}
FEA_COLUMNS = (
    "sample_id",
    "topology",
    "split",
) + RAW_COLUMNS + OUTPUT_COLUMNS + (
    "core_loss_w",
    "stranded_loss_w",
    "mechanical_loss_w",
    "solver_seconds",
)


@dataclass(frozen=True, slots=True)
class FEAPlanSample:
    """One fixed design point in the one-time Maxwell sampling plan."""

    sample_id: str
    topology: str
    split: str
    design: PMSMDesign


@dataclass(frozen=True, slots=True)
class FEASampleRecord:
    """One successful FEA sample and the design that produced it."""

    sample_id: str
    topology: str
    split: str
    design: PMSMDesign
    torque_nm: float
    torque_ripple_pct: float
    efficiency_pct: float
    core_loss_w: float
    stranded_loss_w: float
    mechanical_loss_w: float
    solver_seconds: float

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self.design)
        row.update(
            {
                "sample_id": self.sample_id,
                "topology": self.topology,
                "split": self.split,
                "torque_nm": self.torque_nm,
                "torque_ripple_pct": self.torque_ripple_pct,
                "efficiency_pct": self.efficiency_pct,
                "core_loss_w": self.core_loss_w,
                "stranded_loss_w": self.stranded_loss_w,
                "mechanical_loss_w": self.mechanical_loss_w,
                "solver_seconds": self.solver_seconds,
            }
        )
        return {column: row[column] for column in FEA_COLUMNS}


@dataclass(frozen=True, slots=True)
class TargetCalibration:
    """Standardized ridge correction for one topology and target."""

    target: str
    feature_names: tuple[str, ...]
    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float

    def predict(self, features: np.ndarray) -> np.ndarray:
        mean = np.asarray(self.feature_mean, dtype=float)
        scale = np.asarray(self.feature_scale, dtype=float)
        standardized = (features - mean) / scale
        return standardized @ np.asarray(self.coefficients, dtype=float) + self.intercept


@dataclass(frozen=True, slots=True)
class CalibrationBundle:
    """Topology-specific corrections fitted only on calibration samples."""

    version: int
    library_sha256: str
    models: dict[str, dict[str, TargetCalibration]]
    metrics: dict[str, Any]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_calibration_to_dict(self), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> CalibrationBundle:
        payload = json.loads(path.read_text(encoding="utf-8"))
        models: dict[str, dict[str, TargetCalibration]] = {}
        for topology, targets in payload["models"].items():
            models[topology] = {
                target: TargetCalibration(
                    target=target,
                    feature_names=tuple(values["feature_names"]),
                    feature_mean=tuple(values["feature_mean"]),
                    feature_scale=tuple(values["feature_scale"]),
                    coefficients=tuple(values["coefficients"]),
                    intercept=float(values["intercept"]),
                )
                for target, values in targets.items()
            }
        return cls(
            version=int(payload["version"]),
            library_sha256=str(payload["library_sha256"]),
            models=models,
            metrics=payload["metrics"],
        )


def build_fea_plan(
    samples_per_topology: int = DEFAULT_FEA_SAMPLES_PER_TOPOLOGY,
    calibration_per_topology: int = DEFAULT_FEA_CALIBRATION_PER_TOPOLOGY,
    seed: int = 2026,
) -> list[FEAPlanSample]:
    """Create a deterministic, topology-balanced LHS plan."""

    if not 1 < calibration_per_topology < samples_per_topology:
        raise ValueError("校准样本数必须大于1且小于每拓扑样本总数")

    frame = PMSMDesignDatasetGenerator(seed=seed).generate(samples_per_topology * 10)
    rng = np.random.default_rng(seed)
    plan: list[FEAPlanSample] = []
    for topology in SPM_TOPOLOGIES:
        subset = frame[frame["topology"] == topology.key]
        radial_build = (
            subset["stator_outer_diameter_mm"] - subset["stator_inner_diameter_mm"]
        ) / 2.0
        subset = subset[radial_build >= FEA_MIN_RADIAL_BUILD_MM[topology.key]]
        subset = subset.head(samples_per_topology).reset_index(drop=True)
        if len(subset) != samples_per_topology:
            raise RuntimeError(f"{topology.label} 的样本数量不正确")
        permutation = rng.permutation(samples_per_topology)
        holdout_indices = set(
            permutation[: samples_per_topology - calibration_per_topology]
        )
        for index in range(samples_per_topology):
            row = subset.iloc[index]
            values = {
                name: int(row[name])
                if name in {"turns_per_phase", "dc_bus_voltage_v"}
                else float(row[name])
                for name in RAW_COLUMNS
            }
            plan.append(
                FEAPlanSample(
                    sample_id=f"{topology.key}-{index + 1:03d}",
                    topology=topology.key,
                    split="holdout" if index in holdout_indices else "calibration",
                    design=PMSMDesign(topology=topology.key, **values),
                )
            )
    return plan


def write_fea_plan(plan: list[FEAPlanSample], path: Path) -> None:
    """Write a reviewable CSV plan without running Maxwell."""

    rows: list[dict[str, Any]] = []
    for item in plan:
        row = asdict(item.design)
        row.update(
            {
                "sample_id": item.sample_id,
                "topology": item.topology,
                "split": item.split,
            }
        )
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, lineterminator="\n")


def read_fea_library(path: Path) -> pd.DataFrame:
    """Load and validate the committed FEA reference library."""

    frame = pd.read_csv(path)
    missing = set(FEA_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"FEA 样本库缺少列：{', '.join(sorted(missing))}")
    grouped = frame.groupby(["topology", "split"]).size()
    for topology in SPM_TOPOLOGIES:
        for split in FEA_SPLITS:
            if grouped.get((topology.key, split), 0) == 0:
                raise ValueError(f"{topology.label} 缺少 {split} 样本")
    return frame


def calibrate_from_library(
    frame: pd.DataFrame,
    source_sha256: str,
) -> CalibrationBundle:
    """Fit topology-specific corrections without using holdout samples."""

    model = AnalyticalPMSMModel()
    models: dict[str, dict[str, TargetCalibration]] = {}
    metrics: dict[str, Any] = {}
    for topology in SPM_TOPOLOGIES:
        topology_frame = frame[frame["topology"] == topology.key]
        calibration_frame = topology_frame[topology_frame["split"] == "calibration"]
        holdout_frame = topology_frame[topology_frame["split"] == "holdout"]
        if len(calibration_frame) < 5 or len(holdout_frame) < 2:
            raise ValueError(f"{topology.label} 的校准或保留样本数量不足")

        analytic = [
            model.evaluate(_design_from_row(row)).prediction
            for row in calibration_frame.itertuples(index=False)
        ]
        holdout_analytic = [
            model.evaluate(_design_from_row(row)).prediction
            for row in holdout_frame.itertuples(index=False)
        ]
        calibration_features = _correction_features(calibration_frame)
        holdout_features = _correction_features(holdout_frame)
        topology_models: dict[str, TargetCalibration] = {}
        topology_metrics: dict[str, Any] = {}

        target_specs = {
            "torque_nm": (
                np.asarray([item.torque_nm for item in analytic]),
                calibration_frame["torque_nm"].to_numpy(dtype=float),
                np.asarray([item.torque_nm for item in holdout_analytic]),
                holdout_frame["torque_nm"].to_numpy(dtype=float),
                "ratio",
            ),
            "torque_ripple_pct": (
                np.asarray([item.torque_ripple_pct for item in analytic]),
                calibration_frame["torque_ripple_pct"].to_numpy(dtype=float),
                np.asarray([item.torque_ripple_pct for item in holdout_analytic]),
                holdout_frame["torque_ripple_pct"].to_numpy(dtype=float),
                "ratio",
            ),
            "efficiency_pct": (
                np.asarray([item.efficiency_pct for item in analytic]),
                calibration_frame["efficiency_pct"].to_numpy(dtype=float),
                np.asarray([item.efficiency_pct for item in holdout_analytic]),
                holdout_frame["efficiency_pct"].to_numpy(dtype=float),
                "delta",
            ),
        }
        for target, values in target_specs.items():
            base, observed, holdout_base, holdout_observed, kind = values
            residual = (
                observed / np.maximum(np.abs(base), 1e-9)
                if kind == "ratio"
                else observed - base
            )
            scaler = StandardScaler()
            scaled = scaler.fit_transform(calibration_features)
            ridge = RidgeCV(alphas=(0.01, 0.1, 1.0, 10.0))
            ridge.fit(scaled, residual)
            correction_model = TargetCalibration(
                target=target,
                feature_names=_correction_feature_names(),
                feature_mean=tuple(float(value) for value in scaler.mean_),
                feature_scale=tuple(float(value) for value in scaler.scale_),
                coefficients=tuple(float(value) for value in ridge.coef_),
                intercept=float(ridge.intercept_),
            )
            topology_models[target] = correction_model
            holdout_correction = correction_model.predict(holdout_features)
            predicted = (
                holdout_base * np.maximum(holdout_correction, 0.05)
                if kind == "ratio"
                else holdout_base + holdout_correction
            )
            topology_metrics[target] = {
                "r2": float(r2_score(holdout_observed, predicted)),
                "mae": float(mean_absolute_error(holdout_observed, predicted)),
                "rmse": float(
                    mean_squared_error(holdout_observed, predicted) ** 0.5
                ),
                "mape_pct": float(
                    np.mean(
                        np.abs(
                            (predicted - holdout_observed)
                            / np.maximum(np.abs(holdout_observed), 1e-9)
                        )
                    )
                    * 100
                ),
                "holdout_count": len(holdout_frame),
            }
        models[topology.key] = topology_models
        metrics[topology.key] = topology_metrics

    return CalibrationBundle(
        version=FEA_LIBRARY_VERSION,
        library_sha256=source_sha256,
        models=models,
        metrics=metrics,
    )


def apply_calibration(frame: pd.DataFrame, bundle: CalibrationBundle) -> pd.DataFrame:
    """Return dense synthetic data after topology-specific correction."""

    result = frame.copy()
    features = _correction_features(result)
    for topology in SPM_TOPOLOGIES:
        mask = result["topology"] == topology.key
        if not mask.any():
            continue
        topology_features = features[mask.to_numpy()]
        for target, kind in (
            ("torque_nm", "ratio"),
            ("torque_ripple_pct", "ratio"),
            ("efficiency_pct", "delta"),
        ):
            correction = bundle.models[topology.key][target].predict(topology_features)
            base = result.loc[mask, target].to_numpy(dtype=float)
            result.loc[mask, target] = (
                base * np.maximum(correction, 0.05)
                if kind == "ratio"
                else base + correction
            )
    return result


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def library_manifest(frame: pd.DataFrame, source_path: Path) -> dict[str, Any]:
    return {
        "version": FEA_LIBRARY_VERSION,
        "source": "Ansys Maxwell 2D transient",
        "library_sha256": file_sha256(source_path),
        "sample_count": len(frame),
        "samples_per_topology": {
            topology.key: int((frame["topology"] == topology.key).sum())
            for topology in SPM_TOPOLOGIES
        },
        "splits": {
            topology.key: {
                split: int(
                    (
                        (frame["topology"] == topology.key)
                        & (frame["split"] == split)
                    ).sum()
                )
                for split in FEA_SPLITS
            }
            for topology in SPM_TOPOLOGIES
        },
        "columns": list(FEA_COLUMNS),
    }


def _design_from_row(row: Any) -> PMSMDesign:
    values = {
        name: int(getattr(row, name))
        if name in {"turns_per_phase", "dc_bus_voltage_v"}
        else float(getattr(row, name))
        for name in RAW_COLUMNS
    }
    return PMSMDesign(topology=str(row.topology), **values)


def _correction_feature_names() -> tuple[str, ...]:
    return (
        "current_fraction",
        "airgap_flux_density_t",
        "slot_magnet_ratio",
        "speed_fraction",
        "voltage_utilization_fraction",
    )


def _correction_features(frame: pd.DataFrame) -> np.ndarray:
    analytical = AnalyticalPMSMModel()
    rows: list[list[float]] = []
    for row in frame.itertuples(index=False):
        evaluation = analytical.evaluate(_design_from_row(row))
        rows.append(
            [
                float(row.rated_current_a) / 10.0,
                evaluation.airgap_flux_density_t,
                float(row.slot_opening_mm) / max(float(row.magnet_thickness_mm), 1e-6),
                float(row.speed_rpm) / 4000.0,
                evaluation.voltage_utilization_pct / 100.0,
            ]
        )
    return np.asarray(rows, dtype=float)


def _calibration_to_dict(bundle: CalibrationBundle) -> dict[str, Any]:
    return {
        "version": bundle.version,
        "library_sha256": bundle.library_sha256,
        "models": {
            topology: {
                target: asdict(model) for target, model in targets.items()
            }
            for topology, targets in bundle.models.items()
        },
        "metrics": bundle.metrics,
    }
