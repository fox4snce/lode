"""
Build a Windows executable for Lode using PyInstaller.

Outputs to dist/ and build/, which are gitignored.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onefile", action="store_true", help="Build a single-file executable.")
    parser.add_argument("--console", action="store_true", help="Keep a console window (debug builds).")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from lode_version import __version__

    if os.name != "nt":
        print("This build script is intended for Windows.")
        return 2

    entry = project_root / "app" / "launcher.py"
    if not entry.exists():
        print(f"Entry script not found: {entry}")
        return 2

    icon_path = project_root / "docs" / "images" / "lode.ico"
    if not icon_path.exists():
        print(f"WARNING: icon not found (build will continue without it): {icon_path}")

    # Versioned output directories (both are gitignored by default: dist/ and build/)
    dist_dir = project_root / "dist" / f"lode-{__version__}"
    work_dir = project_root / "build" / f"lode-{__version__}"

    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # PyInstaller --add-data uses ';' on Windows.
    def add_data(src: Path, dest: str) -> list[str]:
        return ["--add-data", f"{src}{os.pathsep}{dest}"]

    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "Lode",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
    ]

    if args.onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    if args.console:
        cmd.append("--console")
    else:
        cmd.append("--windowed")

    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    # Bundle templates/static/icons needed at runtime.
    cmd.extend(add_data(project_root / "templates", "templates"))
    cmd.extend(add_data(project_root / "static", "static"))
    cmd.extend(add_data(project_root / "docs" / "images", "docs/images"))

    cmd.append(str(entry))

    print(f"Lode version: {__version__}")
    print(f"Build output (gitignored): {dist_dir}")
    print("Running PyInstaller:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=str(project_root))
    if result.returncode != 0:
        return result.returncode

    if args.onefile:
        exe_path = dist_dir / "Lode.exe"
    else:
        exe_path = dist_dir / "Lode" / "Lode.exe"

    print(f"Build complete: {exe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

