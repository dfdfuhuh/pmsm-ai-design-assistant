"""Generate the committed PMSM synthetic dataset and metadata."""

from __future__ import annotations

import hashlib
import json

from pmsm_ai.dataset import (
    DEFAULT_SAMPLE_COUNT_PER_TOPOLOGY,
    PMSMDesignDatasetGenerator,
    dataset_metadata,
)
from pmsm_ai.paths import DEFAULT_DATASET_METADATA_PATH, DEFAULT_DATASET_PATH


def main() -> int:
    frame = PMSMDesignDatasetGenerator().generate(DEFAULT_SAMPLE_COUNT_PER_TOPOLOGY)
    DEFAULT_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        DEFAULT_DATASET_PATH,
        index=False,
        float_format="%.10g",
        lineterminator="\n",
    )

    metadata = dataset_metadata(DEFAULT_SAMPLE_COUNT_PER_TOPOLOGY)
    metadata["dataset_sha256"] = hashlib.sha256(DEFAULT_DATASET_PATH.read_bytes()).hexdigest()
    DEFAULT_DATASET_METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"数据集已生成：{DEFAULT_DATASET_PATH}（{len(frame)} 行）")
    print(f"元数据已生成：{DEFAULT_DATASET_METADATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
