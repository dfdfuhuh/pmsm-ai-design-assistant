"""Train the random-forest surrogate from the committed CSV."""

from __future__ import annotations

from pmsm_ai.surrogate import TARGET_LABELS
from pmsm_ai.training import train_and_save


def main() -> int:
    bundle = train_and_save(progress=lambda percent, message: print(f"{percent:3d}% {message}"))
    print("-" * 48)
    for metric in bundle.test_metrics:
        print(
            f"{TARGET_LABELS[metric.target]}："
            f"R2={metric.r2:.4f}, MAE={metric.mae:.4f}, RMSE={metric.rmse:.4f}"
        )
    for topology, metrics in bundle.topology_metrics.items():
        print(f"[{topology}]")
        for metric in metrics:
            print(
                f"  {TARGET_LABELS[metric.target]}：R2={metric.r2:.4f}, "
                f"MAE={metric.mae:.4f}"
            )
    print(f"训练样本：{bundle.training_metadata['train_rows']}")
    print(f"测试样本：{bundle.training_metadata['test_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
