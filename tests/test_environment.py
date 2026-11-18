"""Tests for local environment reporting."""

from pmsm_ai.environment import all_checks_passed, collect_environment_checks


def test_environment_report_contains_required_checks() -> None:
    checks = collect_environment_checks()
    names = {check.name for check in checks}

    assert names == {
        "Python",
        "PyQt6",
        "numpy",
        "pandas",
        "scikit-learn",
        "matplotlib",
        "Conda 环境 pmsm-ai",
        "Git",
    }
    assert all(check.detail for check in checks)


def test_installed_project_dependencies_pass() -> None:
    checks = collect_environment_checks()
    dependency_checks = [
        check
        for check in checks
        if check.name in {"Python", "PyQt6", "numpy", "pandas", "scikit-learn", "matplotlib"}
    ]

    assert all(check.passed for check in dependency_checks)


def test_all_checks_passed_requires_every_result() -> None:
    checks = collect_environment_checks(environ={})

    assert not all_checks_passed(checks)
