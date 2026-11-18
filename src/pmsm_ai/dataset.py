"""Deterministic synthetic dataset generation for the teaching model."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import qmc

from pmsm_ai.analytical import AnalyticalPMSMModel
from pmsm_ai.domain import (
    DEFAULT_DESIGN,
    PARAMETER_SPECS,
    PerformancePrediction,
    PMSMDesign,
)

DATASET_VERSION = 1
DEFAULT_SAMPLE_COUNT = 8000
DEFAULT_SEED = 42
TRAINING_POWER_RANGE_W = (300.0, 3500.0)

RAW_COLUMNS = tuple(spec.name for spec in PARAMETER_SPECS)
OUTPUT_COLUMNS = ("torque_nm", "torque_ripple_pct", "efficiency_pct")
DATASET_COLUMNS = RAW_COLUMNS + OUTPUT_COLUMNS


class PMSMDesignDatasetGenerator:
    """Generate a bounded LHS dataset from the analytical teaching model."""

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        analytical_model: AnalyticalPMSMModel | None = None,
    ) -> None:
        self.seed = seed
        self.analytical_model = analytical_model or AnalyticalPMSMModel()

    def generate(self, count: int = DEFAULT_SAMPLE_COUNT) -> pd.DataFrame:
        """Return exactly ``count`` valid and reproducible design samples."""

        if count <= 0:
            raise ValueError("样本数量必须大于零")

        rows: list[dict[str, float | int]] = []
        attempt = 0
        lower = np.array([spec.minimum for spec in PARAMETER_SPECS], dtype=float)
        upper = np.array([spec.maximum for spec in PARAMETER_SPECS], dtype=float)

        while len(rows) < count:
            batch_size = max(2048, (count - len(rows)) * 2)
            sampler = qmc.LatinHypercube(d=len(PARAMETER_SPECS), seed=self.seed + attempt)
            candidates = lower + sampler.random(batch_size) * (upper - lower)
            for candidate in candidates:
                design = self._design_from_array(candidate)
                try:
                    design.validate()
                except ValueError:
                    continue

                evaluation = self.analytical_model.evaluate(design)
                low_power, high_power = TRAINING_POWER_RANGE_W
                if not low_power <= evaluation.shaft_power_w <= high_power:
                    continue

                row = asdict(design)
                row.update(asdict(evaluation.prediction))
                rows.append(row)
                if len(rows) == count:
                    break

            attempt += 1
            if attempt > 20:
                raise RuntimeError("无法在约束范围内生成足够样本")

        return pd.DataFrame(rows, columns=DATASET_COLUMNS)

    @staticmethod
    def reference_design() -> PMSMDesign:
        """Return the documented reference motor."""

        return DEFAULT_DESIGN

    @staticmethod
    def _design_from_array(values: np.ndarray) -> PMSMDesign:
        integer_index = RAW_COLUMNS.index("turns_per_phase")
        normalized = values.copy()
        normalized[integer_index] = round(normalized[integer_index])
        parameters = dict(zip(RAW_COLUMNS, normalized.tolist(), strict=True))
        parameters["turns_per_phase"] = int(parameters["turns_per_phase"])
        return PMSMDesign(**parameters)


def dataset_metadata(sample_count: int) -> dict[str, Any]:
    """Return stable metadata describing the committed dataset."""

    return {
        "schema_version": DATASET_VERSION,
        "topology": "surface-mounted PMSM, 8 poles, 12 slots",
        "seed": DEFAULT_SEED,
        "sample_count": sample_count,
        "columns": list(DATASET_COLUMNS),
        "outputs": list(OUTPUT_COLUMNS),
        "training_power_range_w": list(TRAINING_POWER_RANGE_W),
        "parameter_ranges": {
            spec.name: {
                "label": spec.label,
                "unit": spec.unit,
                "minimum": spec.minimum,
                "maximum": spec.maximum,
            }
            for spec in PARAMETER_SPECS
        },
        "analytical_constants": {
            "slots": 12,
            "pole_pairs": 4,
            "relative_permeability": 1.05,
            "magnetic_saturation_factor": 1.15,
            "lamination_stacking_factor": 0.95,
            "winding_factor": 0.933,
            "lamination_density_kg_m3": 7600.0,
        },
    }


def prediction_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Select target columns in a fixed order."""

    return frame.loc[:, list(OUTPUT_COLUMNS)]


def predictions_from_frame(frame: pd.DataFrame) -> list[PerformancePrediction]:
    """Convert target columns to public prediction objects."""

    return [
        PerformancePrediction(
            torque_nm=float(row.torque_nm),
            torque_ripple_pct=float(row.torque_ripple_pct),
            efficiency_pct=float(row.efficiency_pct),
        )
        for row in frame.itertuples(index=False)
    ]
