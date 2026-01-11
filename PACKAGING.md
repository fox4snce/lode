# Packaging Lode (Windows)

This project is packaged on Windows using **PyInstaller**.

## Goals

- Produce a distributable Windows build with an embedded **version**
- Output to a directory that is **gitignored** so binaries never get pushed

## Output Location (Gitignored)

Build artifacts go to:

- `dist/lode-<version>/...`
- `build/lode-<version>/...`

Both `dist/` and `build/` are already in `.gitignore`.

## Versioning

The version is defined in:

- `lode_version.py` (`__version__`)

The build script prints the version and places artifacts in a versioned folder.

## Build Steps

1. Install runtime dependencies:

```bash
pip install -r requirements.txt
```

2. Install packaging dependencies:

```bash
pip install -r requirements-dev.txt
```

3. Build (recommended onedir build):

```bash
python tools/build_windows_exe.py
```

Optional:

- Single-file build:

```bash
python tools/build_windows_exe.py --onefile
```

- Console build (debug):

```bash
python tools/build_windows_exe.py --console
```

## Distribution

With the default `--onedir` mode, PyInstaller creates a directory containing:

- `Lode.exe` - The main executable
- `_internal/` - Directory containing:
  - Python runtime and DLLs
  - All bundled Python packages
  - Templates, static files, and images

**You must distribute the entire `Lode/` directory**, not just the `.exe` file.

To create a distributable zip:

```bash
# After building, zip the entire Lode directory
cd dist/lode-1.0.0
Compress-Archive -Path Lode -DestinationPath Lode-1.0.0-Windows.zip
```

Users should extract the zip and run `Lode.exe` from within the `Lode/` directory.

## Notes

- The packaged app stores persistent data (DB, uploads, exports) in the per-user app data directory:
  - Windows: `%APPDATA%\\Lode\\`
  
- Alternative: Use `--onefile` to create a single executable (slower startup, larger file):
  ```bash
  python tools/build_windows_exe.py --onefile
  ```
  With `--onefile`, you only need to distribute the single `.exe` file, but startup is slower.

