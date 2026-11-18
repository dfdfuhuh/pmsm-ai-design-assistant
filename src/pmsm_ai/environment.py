"""Development environment checks used by the GUI and command-line script."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EnvironmentCheck:
    """Result of one required environment check."""

    name: str
    passed: bool
    detail: str


_REQUIRED_PACKAGES = (
    "PyQt6",
    "numpy",
    "pandas",
    "scikit-learn",
    "matplotlib",
)


def _package_check(package: str) -> EnvironmentCheck:
    try:
        version = metadata.version(package)
    except metadata.PackageNotFoundError:
        return EnvironmentCheck(package, False, "未安装")
    return EnvironmentCheck(package, True, f"已安装，版本 {version}")


def _python_check() -> EnvironmentCheck:
    python_version = sys.version.split()[0]
    supported = sys.version_info[:2] == (3, 11)
    detail = f"{python_version} ({'符合' if supported else '需要 Python 3.11'})"
    return EnvironmentCheck("Python", supported, detail)


def _conda_check(environ: Mapping[str, str]) -> EnvironmentCheck:
    active_environment = environ.get("CONDA_DEFAULT_ENV", "")
    passed = active_environment == "pmsm-ai"
    detail = (
        f"当前环境：{active_environment}"
        if active_environment
        else "未检测到已激活的 Conda 环境"
    )
    return EnvironmentCheck("Conda 环境 pmsm-ai", passed, detail)


def _find_git(environ: Mapping[str, str]) -> str | None:
    git_path = shutil.which("git", path=environ.get("PATH"))
    if git_path:
        return git_path

    if os.name == "nt":
        program_files = environ.get("ProgramFiles", r"C:\Program Files")
        candidate = Path(program_files) / "Git" / "cmd" / "git.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _git_check(environ: Mapping[str, str]) -> EnvironmentCheck:
    git_path = _find_git(environ)
    if git_path:
        return EnvironmentCheck("Git", True, git_path)
    return EnvironmentCheck("Git", False, "未找到 git 命令")


def collect_environment_checks(
    environ: Mapping[str, str] | None = None,
) -> list[EnvironmentCheck]:
    """Collect all checks without raising for missing optional tooling."""

    current_environment = os.environ if environ is None else environ
    checks = [_python_check()]
    checks.extend(_package_check(package) for package in _REQUIRED_PACKAGES)
    checks.extend((_conda_check(current_environment), _git_check(current_environment)))
    return checks


def all_checks_passed(checks: list[EnvironmentCheck]) -> bool:
    """Return whether every required environment check passed."""

    return all(check.passed for check in checks)
