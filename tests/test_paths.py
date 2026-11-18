"""Tests for frozen and source runtime path selection."""

from pathlib import Path

from pmsm_ai import paths


def test_source_paths_use_project_root() -> None:
    app_root, resource_root = paths.runtime_roots(
        frozen=False,
        executable=Path(r"C:\ignored\python.exe"),
        bundled_root=Path(r"C:\ignored"),
        project_root=paths.PROJECT_ROOT,
    )

    assert app_root == paths.PROJECT_ROOT
    assert resource_root == paths.PROJECT_ROOT


def test_frozen_layout_uses_executable_for_writable_model(tmp_path: Path) -> None:
    executable = tmp_path / "portable" / "PMSM-AI-Design-Assistant.exe"
    resource_root = tmp_path / "_internal"
    app_root, bundled_root = paths.runtime_roots(
        frozen=True,
        executable=executable,
        bundled_root=resource_root,
        project_root=paths.PROJECT_ROOT,
    )

    assert app_root == executable.parent
    assert bundled_root == resource_root
