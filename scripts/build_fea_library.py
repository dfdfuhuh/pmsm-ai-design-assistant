"""Build a resumable Maxwell 2D reference library for PMSM calibration."""

from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

from pmsm_ai.domain import SPM_TOPOLOGIES
from pmsm_ai.fea import (
    DEFAULT_FEA_CALIBRATION_PER_TOPOLOGY,
    DEFAULT_FEA_SAMPLES_PER_TOPOLOGY,
    FEA_COLUMNS,
    FEAPlanSample,
    build_fea_plan,
    library_manifest,
    write_fea_plan,
)
from pmsm_ai.maxwell_runner import find_maxwell_template, run_fea_sample
from pmsm_ai.paths import (
    FEA_LIBRARY_PATH,
    FEA_MANIFEST_PATH,
    FEA_PLAN_PATH,
    FEA_RUNS_DIR,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只生成采样计划")
    parser.add_argument("--pilot", action="store_true", help="每种拓扑只运行一个校准点")
    parser.add_argument("--limit", type=int, default=0, help="本次最多运行多少个点")
    parser.add_argument(
        "--samples-per-topology",
        type=int,
        default=DEFAULT_FEA_SAMPLES_PER_TOPOLOGY,
    )
    parser.add_argument(
        "--calibration-per-topology",
        type=int,
        default=DEFAULT_FEA_CALIBRATION_PER_TOPOLOGY,
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="官方 pmsg-1.aedt 模板路径",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_fea_plan(
        samples_per_topology=args.samples_per_topology,
        calibration_per_topology=args.calibration_per_topology,
    )
    write_fea_plan(plan, FEA_PLAN_PATH)
    print(f"采样计划：{FEA_PLAN_PATH}（{len(plan)} 点）")
    if args.dry_run:
        _print_plan_summary(plan)
        return 0

    if args.pilot:
        selected: list[FEAPlanSample] = []
        for topology in SPM_TOPOLOGIES:
            selected.append(
                next(
                    item
                    for item in plan
                    if item.topology == topology.key and item.split == "calibration"
                )
            )
        plan = selected
    if args.limit > 0:
        plan = plan[: args.limit]

    existing = _load_existing_library()
    completed = set(existing["sample_id"].astype(str)) if not existing.empty else set()
    pending = [item for item in plan if item.sample_id not in completed]
    FEA_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    failure_log = FEA_RUNS_DIR / "failures.jsonl"
    template = args.template or find_maxwell_template()
    print(f"Maxwell 模板：{template}")
    print(f"待运行：{len(pending)}，已完成：{len(completed)}")

    records = existing.to_dict(orient="records")
    failures = 0
    for position, sample in enumerate(pending, start=1):
        print(f"[{position}/{len(pending)}] {sample.sample_id} ...", flush=True)
        try:
            record = run_fea_sample(sample, FEA_RUNS_DIR, template)
        except Exception as exc:
            failures += 1
            failure = {
                "sample_id": sample.sample_id,
                "time": datetime.now().isoformat(timespec="seconds"),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            with failure_log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(failure, ensure_ascii=False) + "\n")
            print(f"  FAILED: {exc}")
            continue

        records.append(record.to_dict())
        frame = pd.DataFrame(records, columns=FEA_COLUMNS)
        _atomic_write_csv(frame, FEA_LIBRARY_PATH)
        print(
            f"  PASS: T={record.torque_nm:.3f} N·m, "
            f"ripple={record.torque_ripple_pct:.2f}%, "
            f"eta={record.efficiency_pct:.2f}%, {record.solver_seconds:.1f}s"
        )

    frame = pd.DataFrame(records, columns=FEA_COLUMNS)
    if not frame.empty:
        _atomic_write_csv(frame, FEA_LIBRARY_PATH)
        manifest = library_manifest(frame, FEA_LIBRARY_PATH)
        manifest["failures_this_run"] = failures
        FEA_MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"样本库：{FEA_LIBRARY_PATH}（{len(frame)} 行）")
        print(f"清单：{FEA_MANIFEST_PATH}")
    if failures:
        print(f"失败样本：{failures}；详情：{failure_log}")
        return 1
    return 0


def _load_existing_library() -> pd.DataFrame:
    if not FEA_LIBRARY_PATH.is_file():
        return pd.DataFrame(columns=FEA_COLUMNS)
    return pd.read_csv(FEA_LIBRARY_PATH)


def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def _print_plan_summary(plan: list[FEAPlanSample]) -> None:
    for topology in SPM_TOPOLOGIES:
        subset = [item for item in plan if item.topology == topology.key]
        calibration = sum(item.split == "calibration" for item in subset)
        holdout = sum(item.split == "holdout" for item in subset)
        print(f"{topology.label}: 校准 {calibration}，保留验证 {holdout}")


if __name__ == "__main__":
    raise SystemExit(main())
