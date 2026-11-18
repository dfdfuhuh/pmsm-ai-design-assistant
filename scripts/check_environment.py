"""Command-line environment verification for the course project."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from pmsm_ai.environment import all_checks_passed, collect_environment_checks  # noqa: E402


def main() -> int:
    checks = collect_environment_checks()
    print("永磁同步电机 AI 设计助手 - 开发环境自检")
    print("-" * 54)
    for check in checks:
        marker = "PASS" if check.passed else "FAIL"
        print(f"[{marker}] {check.name}: {check.detail}")

    passed_count = sum(check.passed for check in checks)
    print("-" * 54)
    if all_checks_passed(checks):
        print(f"环境检查通过：{passed_count}/{len(checks)}")
        return 0

    print(f"环境检查未通过：{passed_count}/{len(checks)}。请按 FAIL 项修复后重试。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
