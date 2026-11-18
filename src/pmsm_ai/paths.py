"""Stable local paths for data and generated model artifacts."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_DATASET_PATH = DATA_DIR / "pmsm_spm_8p12s_synthetic.csv"
DEFAULT_DATASET_METADATA_PATH = DATA_DIR / "pmsm_spm_8p12s_metadata.json"
DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "pmsm_rf_bundle.joblib"
DEFAULT_METRICS_PATH = ARTIFACTS_DIR / "model_metrics.json"
