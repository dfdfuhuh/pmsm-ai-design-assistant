"""Stable local paths for data and generated model artifacts."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATA_DIR = PROJECT_ROOT / "data"
DATA_FEA_DIR = DATA_DIR / "fea"
FEA_RUNS_DIR = ARTIFACTS_DIR / "fea_runs"
DEFAULT_DATASET_PATH = DATA_DIR / "pmsm_spm_multitopology_synthetic.csv"
DEFAULT_DATASET_METADATA_PATH = DATA_DIR / "pmsm_spm_multitopology_metadata.json"
DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "pmsm_rf_multitopology.joblib"
DEFAULT_METRICS_PATH = ARTIFACTS_DIR / "model_metrics.json"
FEA_PLAN_PATH = DATA_FEA_DIR / "pmsm_fea_plan.csv"
FEA_LIBRARY_PATH = DATA_FEA_DIR / "pmsm_fea_reference.csv"
FEA_MANIFEST_PATH = DATA_FEA_DIR / "pmsm_fea_manifest.json"
FEA_CALIBRATION_PATH = DATA_FEA_DIR / "pmsm_fea_calibration.json"
