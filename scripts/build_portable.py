"""Build a self-contained Windows onedir package and portable ZIP."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from pmsm_ai.paths import DEFAULT_METRICS_PATH, DEFAULT_MODEL_PATH, PROJECT_ROOT

APP_NAME = "PMSM-AI-Design-Assistant"
PORTABLE_ZIP = PROJECT_ROOT.parent / f"{APP_NAME}-portable.zip"
CONDA_RUNTIME_DLLS = (
    "ffi-8.dll",
    "libbz2.dll",
    "libcrypto-3-x64.dll",
    "libexpat.dll",
    "liblzma.dll",
    "libssl-3-x64.dll",
    "sqlite3.dll",
    "zlib.dll",
    "zlib1.dll",
)


def main() -> int:
    if os.name != "nt":
        raise RuntimeError("便携包必须在 Windows 上构建")
    if not DEFAULT_MODEL_PATH.is_file():
        raise FileNotFoundError(f"缺少已训练模型：{DEFAULT_MODEL_PATH}")

    build_dir = PROJECT_ROOT / "build" / "portable"
    dist_dir = PROJECT_ROOT / "dist"
    target_dir = dist_dir / APP_NAME
    for path in (build_dir, target_dir):
        if path.exists():
            shutil.rmtree(path)
    build_dir.mkdir(parents=True, exist_ok=True)

    runtime_arguments: list[str] = []
    conda_library_bin = Path(sys.prefix) / "Library" / "bin"
    for filename in CONDA_RUNTIME_DLLS:
        dll = conda_library_bin / filename
        if dll.is_file():
            runtime_arguments.extend(["--add-binary", f"{dll}{os.pathsep}."])

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        *runtime_arguments,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--paths",
        str(PROJECT_ROOT / "src"),
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(build_dir),
        "--add-data",
        f"{PROJECT_ROOT / 'data'}{os.pathsep}data",
        "--hidden-import",
        "matplotlib.backends.backend_qtagg",
        "--exclude-module",
        "pyaedt",
        "--exclude-module",
        "ansys",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "pytest_qt",
        "--exclude-module",
        "ruff",
        str(PROJECT_ROOT / "src" / "pmsm_ai" / "__main__.py"),
    ]
    _run(command)

    executable = target_dir / f"{APP_NAME}.exe"
    if not executable.is_file():
        raise RuntimeError(f"未生成可执行文件：{executable}")
    artifacts = target_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEFAULT_MODEL_PATH, artifacts / DEFAULT_MODEL_PATH.name)
    if DEFAULT_METRICS_PATH.is_file():
        shutil.copy2(DEFAULT_METRICS_PATH, artifacts / DEFAULT_METRICS_PATH.name)
    shutil.copy2(
        PROJECT_ROOT / "packaging" / "PORTABLE_README.txt",
        target_dir / "使用说明.txt",
    )
    _write_checksums(target_dir)
    _smoke_test(executable, target_dir)
    _write_zip(target_dir)
    print(f"便携目录：{target_dir}")
    print(f"压缩包：{PORTABLE_ZIP}")
    print(f"压缩包大小：{PORTABLE_ZIP.stat().st_size / (1024**2):.1f} MB")
    return 0


def _run(command: list[str]) -> None:
    print("执行：", " ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _smoke_test(executable: Path, working_directory: Path) -> None:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PATH"] = (
        str(Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32")
    )
    result = subprocess.run(
        [str(executable), "--smoke-test"],
        cwd=working_directory,
        env=environment,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"便携程序启动测试失败：退出码 {result.returncode}")
    print("便携程序无界面启动测试通过")


def _write_checksums(directory: Path) -> None:
    lines = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(directory).as_posix()}")
    (directory / "SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_zip(target_dir: Path) -> None:
    if PORTABLE_ZIP.exists():
        PORTABLE_ZIP.unlink()
    with zipfile.ZipFile(
        PORTABLE_ZIP,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in sorted(target_dir.rglob("*")):
            archive.write(path, path.relative_to(target_dir.parent))


if __name__ == "__main__":
    raise SystemExit(main())
