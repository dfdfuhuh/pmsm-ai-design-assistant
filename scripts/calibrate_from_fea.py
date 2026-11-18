"""Fit FEA correction models and report independent holdout metrics."""

from __future__ import annotations

import json

from pmsm_ai.fea import (
    calibrate_from_library,
    file_sha256,
    read_fea_library,
)
from pmsm_ai.paths import FEA_CALIBRATION_PATH, FEA_LIBRARY_PATH
from pmsm_ai.surrogate import TARGET_LABELS


def main() -> int:
    frame = read_fea_library(FEA_LIBRARY_PATH)
    bundle = calibrate_from_library(frame, file_sha256(FEA_LIBRARY_PATH))
    bundle.save(FEA_CALIBRATION_PATH)
    print(f"校准参数：{FEA_CALIBRATION_PATH}")
    for topology, targets in bundle.metrics.items():
        print(f"[{topology}]")
        for target, metrics in targets.items():
            print(
                f"  {TARGET_LABELS[target]}: R2={metrics['r2']:.4f}, "
                f"MAE={metrics['mae']:.4f}, MAPE={metrics['mape_pct']:.2f}%"
            )
    print(json.dumps(bundle.metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
