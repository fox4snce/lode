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

    build_type = (os.getenv("LODE_BUILD_TYPE") or "core").strip().lower()
    if build_type not in ("core", "pro"):
        print(f"WARNING: Unknown LODE_BUILD_TYPE='{build_type}'. Using 'core' behavior.")
        build_type = "core"

    entry = project_root / "app" / "launcher.py"
    if not entry.exists():
        print(f"Entry script not found: {entry}")
        return 2

    icon_dir = project_root / "docs" / "images"
    icon_path = icon_dir / "lode.ico"
    if not icon_path.exists():
        print(f"WARNING: icon not found (build will continue without it): {icon_path}")

    # Pro build requires the offline embedder model to be present (bundled under vendor/).
    vendor_dir = project_root / "vendor"
    embedder_dir = vendor_dir / "embedder_bge_small_v1_5"
    embedder_model = embedder_dir / "model.onnx"
    embedder_tok = embedder_dir / "tokenizer.json"
    if build_type == "pro":
        if not embedder_model.exists() or not embedder_tok.exists():
            print("ERROR: Pro build requires the offline embedding model, but it's missing.")
            print(f"Expected: {embedder_model}")
            print(f"Expected: {embedder_tok}")
            print("Fix: run from project root:")
            print("  python tools/export_embedder_onnx.py --model bge-small")
            return 2

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

    # tiktoken encodings are registered via namespace-package plugins (tiktoken_ext.*).
    # In frozen builds, these can be missed unless we explicitly collect them.
    cmd.extend(["--collect-submodules", "tiktoken_ext"])
    cmd.extend(["--collect-data", "tiktoken"])

    # LiteLLM reads packaged JSON/tokenizer data at import time (e.g. anthropic_tokenizer.json).
    # Collecting the package data avoids runtime FileNotFoundError in frozen builds.
    cmd.extend(["--collect-submodules", "litellm"])
    cmd.extend(["--collect-data", "litellm"])

    # Bundle templates/static needed at runtime.
    cmd.extend(add_data(project_root / "templates", "templates"))
    cmd.extend(add_data(project_root / "static", "static"))
    # Optional: bundle docs/images if present (icons, screenshots, etc.).
    if icon_dir.exists():
        cmd.extend(add_data(icon_dir, "docs/images"))
    # Bundle vendor/ (offline embedding model). Optional for core; required for pro.
    if vendor_dir.exists():
        cmd.extend(add_data(vendor_dir, "vendor"))
    elif build_type == "pro":
        # Defensive: we already hard-failed above, but keep the message here too.
        print("ERROR: vendor/ directory is missing (required for pro builds).")
        return 2

    cmd.append(str(entry))

    print(f"Lode version: {__version__}")
    print(f"Build type: {build_type}")
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

