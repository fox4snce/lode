# Release Process for Lode

This document outlines the complete process for creating and distributing a new release of Lode.

## Overview

The release process involves:
1. Setting the version number
2. Building the Windows executable
3. Creating distribution files (zip, checksum, README)
4. Creating a GitHub release

---

## Step 1: Set the Version Number

The version is defined in a single source of truth:

**File:** `lode_version.py`

**Location:** Project root

Edit the `__version__` variable:

```python
__version__ = "1.0.0"  # Update this value
```

**Version Numbering Guidelines:**
- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Examples: `1.0.0`, `1.0.1`, `1.1.0`, `2.0.0`
- The version will appear in:
  - Build output directory: `dist/lode-<version>/`
  - Executable metadata
  - GitHub release tag

**Verify the version:**
```powershell
python -c "import lode_version; print(lode_version.__version__)"
```

---

## Step 2: Build the Distribution

### Prerequisites

1. Ensure you're on the `main` branch and have a clean working directory:
   ```powershell
   git status
   git checkout main
   ```

2. Install/update dependencies:
   ```powershell
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

### Build the Executable

Run the build script:

```powershell
python tools/build_windows_exe.py
```

This will:
- Create versioned output directories: `dist/lode-<version>/` and `build/lode-<version>/`
- Build the Windows executable using PyInstaller
- Include all templates, static files, and icons
- Output to: `dist/lode-<version>/Lode/Lode.exe`

**Note:** Both `dist/` and `build/` are gitignored, so artifacts won't be committed.

### Verify the Build

Check that the executable was created:

```powershell
cd dist/lode-<version>/Lode
dir Lode.exe
```

Test the executable by running it once to ensure it launches correctly.

---

## Step 3: Create Distribution Files

### 3.1 Create the ZIP Archive

Navigate to the dist directory and create a ZIP file:

```powershell
cd dist/lode-<version>
Compress-Archive -Path Lode -DestinationPath Lode-<version>-win64.zip
```

**Example:**
```powershell
Compress-Archive -Path Lode -DestinationPath Lode-1.0.0-win64.zip
```

### 3.2 Generate SHA256 Checksum

Create a checksum file for verification:

```powershell
$hash = (Get-FileHash -Path Lode-<version>-win64.zip -Algorithm SHA256).Hash
"$hash  Lode-<version>-win64.zip" | Out-File -FilePath Lode-<version>-win64.zip.sha256 -Encoding utf8
```

**Example:**
```powershell
$hash = (Get-FileHash -Path Lode-1.0.0-win64.zip -Algorithm SHA256).Hash
"$hash  Lode-1.0.0-win64.zip" | Out-File -FilePath Lode-1.0.0-win64.zip.sha256 -Encoding utf8
```

**Verify the checksum file:**
```powershell
Get-Content Lode-<version>-win64.zip.sha256
```

### 3.3 Create User-Facing README

A user-facing README should already exist. If not, or if it needs updating, create/edit `README.txt` in the `dist/lode-<version>/` directory.

The README should include:
- Installation instructions
- First run guide
- Checksum verification instructions
- Data storage locations
- System requirements
- Features list
- Support information

**Note:** The README is created manually for each release. Copy the template from a previous release or create it from scratch using the format in `dist/lode-1.0.0/README.txt`.

---

## Step 4: Commit Version Changes

Before creating the GitHub release, commit the version change:

```powershell
git add lode_version.py
git commit -m "Bump version to <version>"
git push origin main
```

---

## Step 5: Create GitHub Release

### 5.1 Create Git Tag

First, create a git tag for the release:

```powershell
git tag -a v<version> -m "Release v<version>"
git push origin v<version>
```

**Example:**
```powershell
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 5.2 Create GitHub Release

1. **Go to GitHub:**
   - Navigate to: https://github.com/fox4snce/lode/releases
   - Click "Draft a new release"

2. **Select Tag:**
   - Choose the tag you just created (e.g., `v1.0.0`)
   - If creating a new release (not a tag), select "Choose a tag" and type the version (e.g., `v1.0.0`)

3. **Release Title:**
   - Use format: `v<version>` (e.g., `v1.0.0`)

4. **Release Notes:**
   - Describe what's new, changed, or fixed in this release
   - Use Markdown formatting
   - Example format:
     ```markdown
     ## Lode v1.0.0
     
     First stable release of Lode!
     
     ### Features
     - Import conversations from OpenAI and Claude
     - Full-text search
     - Analytics dashboard
     - Export to Markdown, CSV, JSON
     
     ### Installation
     Download `Lode-1.0.0-win64.zip`, extract, and run `Lode.exe`
     
     See README.txt for installation and verification instructions.
     ```

5. **Attach Files:**
   - Click "Attach binaries" or drag and drop
   - Upload these files from `dist/lode-<version>/`:
     - `Lode-<version>-win64.zip` (the main distribution)
     - `Lode-<version>-win64.zip.sha256` (checksum file)
     - `README.txt` (user-facing documentation)
   
   **Note:** GitHub releases have file size limits. If your zip is very large, consider using GitHub's release upload API or alternative distribution methods.

6. **Publish:**
   - Check "Set as the latest release" if this is the newest version
   - Click "Publish release"

### 5.3 Verify Release

After publishing:
1. Visit the releases page to confirm it's live
2. Test downloading the zip file
3. Verify the checksum file is accessible
4. Check that README.txt is attached

---

## Complete Checklist

Before publishing a release, verify:

- [ ] Version number updated in `lode_version.py`
- [ ] Version change committed and pushed to `main`
- [ ] Build completed successfully (`dist/lode-<version>/Lode/Lode.exe` exists)
- [ ] Executable tested (launches and works correctly)
- [ ] ZIP file created (`Lode-<version>-win64.zip`)
- [ ] Checksum file generated (`Lode-<version>-win64.zip.sha256`)
- [ ] README.txt created/updated and in distribution directory
- [ ] Git tag created and pushed (`v<version>`)
- [ ] GitHub release created with all files attached
- [ ] Release notes written and published

---

## File Locations Summary

During the release process, files are created in:

```
dist/lode-<version>/
├── Lode/                    # PyInstaller output directory
│   ├── Lode.exe            # Main executable
│   └── _internal/          # Dependencies
├── Lode-<version>-win64.zip      # Distribution archive
├── Lode-<version>-win64.zip.sha256  # Checksum file
└── README.txt              # User documentation
```

**All of these are gitignored** (via `dist/` in `.gitignore`), so they won't be committed to the repository.

---

## Troubleshooting

### Build Fails

- Ensure all dependencies are installed: `pip install -r requirements-dev.txt`
- Check PyInstaller version compatibility
- Review build logs in `build/lode-<version>/` for errors

### ZIP File Too Large

- GitHub releases have a 2GB file size limit per file
- If exceeded, consider:
  - Using `--onefile` mode (smaller but slower startup)
  - Uploading to alternative file hosting
  - Splitting into multiple parts

### Checksum Verification Fails

- Ensure the checksum file uses UTF-8 encoding
- Verify the format: `HASH  filename.zip` (two spaces between hash and filename)
- Re-generate the checksum if needed

### GitHub Release Upload Fails

- Check file size limits
- Ensure you have write permissions to the repository
- Try uploading files one at a time
- Use GitHub CLI (`gh release create`) as an alternative

---

## Alternative: Using GitHub CLI

If you prefer command-line tools, you can use GitHub CLI:

```powershell
# Install GitHub CLI first: https://cli.github.com/

# Create release with files
gh release create v<version> `
  --title "v<version>" `
  --notes "Release notes here" `
  dist/lode-<version>/Lode-<version>-win64.zip `
  dist/lode-<version>/Lode-<version>-win64.zip.sha256 `
  dist/lode-<version>/README.txt
```

Example:
```powershell
gh release create v1.0.0 `
  --title "v1.0.0" `
  --notes "First stable release" `
  dist/lode-1.0.0/Lode-1.0.0-win64.zip `
  dist/lode-1.0.0/Lode-1.0.0-win64.zip.sha256 `
  dist/lode-1.0.0/README.txt
```

---

## Quick Reference Commands

```powershell
# 1. Update version
# Edit lode_version.py

# 2. Build
python tools/build_windows_exe.py

# 3. Create distribution files
cd dist/lode-<version>
Compress-Archive -Path Lode -DestinationPath Lode-<version>-win64.zip
$hash = (Get-FileHash -Path Lode-<version>-win64.zip -Algorithm SHA256).Hash
"$hash  Lode-<version>-win64.zip" | Out-File -FilePath Lode-<version>-win64.zip.sha256 -Encoding utf8
# (Create/update README.txt manually)

# 4. Commit and tag
git add lode_version.py
git commit -m "Bump version to <version>"
git push origin main
git tag -a v<version> -m "Release v<version>"
git push origin v<version>

# 5. Create GitHub release (via web UI or GitHub CLI)
```
