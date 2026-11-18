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
    SPM_TOPOLOGIES,
    PerformancePrediction,
    PMSMDesign,
)

DATASET_VERSION = 2
DEFAULT_SAMPLE_COUNT_PER_TOPOLOGY = 5000
DEFAULT_SEED = 42
TRAINING_POWER_RANGE_W = (300.0, 3500.0)

RAW_COLUMNS = tuple(spec.name for spec in PARAMETER_SPECS)
OUTPUT_COLUMNS = ("torque_nm", "torque_ripple_pct", "efficiency_pct")
DATASET_COLUMNS = ("topology",) + RAW_COLUMNS + OUTPUT_COLUMNS


class PMSMDesignDatasetGenerator:
    """Generate a bounded LHS dataset from the analytical teaching model."""

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        analytical_model: AnalyticalPMSMModel | None = None,
    ) -> None:
        self.seed = seed
        self.analytical_model = analytical_model or AnalyticalPMSMModel()

    def generate(
        self,
        count_per_topology: int = DEFAULT_SAMPLE_COUNT_PER_TOPOLOGY,
    ) -> pd.DataFrame:
        """Return an equal, reproducible number of samples for every topology."""

        if count_per_topology <= 0:
            raise ValueError("样本数量必须大于零")

        lower = np.array([spec.minimum for spec in PARAMETER_SPECS], dtype=float)
        upper = np.array([spec.maximum for spec in PARAMETER_SPECS], dtype=float)
        rows: list[dict[str, float | int | str]] = []
        for topology_index, topology in enumerate(SPM_TOPOLOGIES):
            topology_rows: list[dict[str, float | int | str]] = []
            attempt = 0
            while len(topology_rows) < count_per_topology:
                remaining = count_per_topology - len(topology_rows)
                batch_size = max(2048, remaining * 2)
                sample_seed = self.seed + topology_index * 1000 + attempt
                sampler = qmc.LatinHypercube(d=len(PARAMETER_SPECS), seed=sample_seed)
                candidates = lower + sampler.random(batch_size) * (upper - lower)
                for candidate in candidates:
                    design = self._design_from_array(candidate, topology.key)
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
                    topology_rows.append(row)
                    if len(topology_rows) == count_per_topology:
                        break

                attempt += 1
                if attempt > 20:
                    raise RuntimeError(f"无法为 {topology.label} 生成足够样本")
            rows.extend(topology_rows)

        return pd.DataFrame(rows, columns=DATASET_COLUMNS)

    @staticmethod
    def reference_design(topology: str = DEFAULT_DESIGN.topology) -> PMSMDesign:
        """Return the documented reference motor."""

        return DEFAULT_DESIGN.with_updates(topology=topology)

    @staticmethod
    def _design_from_array(values: np.ndarray, topology: str) -> PMSMDesign:
        normalized = values.copy()
        parameters = dict(zip(RAW_COLUMNS, normalized.tolist(), strict=True))
        for spec in PARAMETER_SPECS:
            if spec.is_integer:
                parameters[spec.name] = int(round(parameters[spec.name]))
        return PMSMDesign(topology=topology, **parameters)


def dataset_metadata(samples_per_topology: int) -> dict[str, Any]:
    """Return stable metadata describing the committed dataset."""

    return {
        "schema_version": DATASET_VERSION,
        "motor_type": "surface-mounted PMSM",
        "topologies": [
            {
                "key": topology.key,
                "label": topology.label,
                "slots": topology.slots,
                "poles": topology.poles,
                "winding_factor": topology.winding_factor,
                "ripple_factor": topology.ripple_factor,
            }
            for topology in SPM_TOPOLOGIES
        ],
        "seed": DEFAULT_SEED,
        "samples_per_topology": samples_per_topology,
        "sample_count": samples_per_topology * len(SPM_TOPOLOGIES),
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
