# IGEL Profile Compare & Migrate Tool

A Windows desktop application for comparing and migrating settings between IGEL IPM profile exports.

## Features

- **Load & Compare**: Open two `.ipm` files side-by-side
- **Visual Diff**: See differences highlighted by category:
  - Different values (yellow)
  - Only in source profile (green)
  - Only in target profile (blue)
- **Filter**: Search settings by name
- **Selective Migration**: Check settings to migrate from source to target
- **Export**: Save new IPM file with migrated settings

## Installation

### Option 1: Run from Source
```bash
pip install -r requirements.txt
python run.py
```

### Option 2: Build Windows Executable
```bash
# On Windows:
build_windows.bat

# Or manually:
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "IGEL-Profile-Compare" src/main.py
```

The executable will be in `dist/IGEL-Profile-Compare.exe`

## Usage

1. Click **"Load IPM File..."** on both panels to load source and target profiles
2. Click **"Compare Profiles"** to see differences
3. Use the filter box to search for specific settings
4. Check the settings you want to migrate from source to target
5. Click **"Migrate Selected to Target →"** and save the new IPM file

## Requirements

- Python 3.10+
- PyQt6
- See `requirements.txt` for full list

## IPM File Format

This tool works with IGEL UMS profile exports (`.ipm` files), which are ZIP archives containing:
- `PROFILES/*.json` - Profile configuration with settings
- `APPS/` - Application metadata

## License

MIT License
