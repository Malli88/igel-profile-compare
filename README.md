# IGEL Profile Compare & Migrate

A tool to compare and migrate settings between IGEL IPM profile files.

## Features

- 📁 Load and parse IGEL .ipm profile files
- 🔍 Compare two profiles side-by-side
- 🔄 Migrate selected settings from source to target
- 🌐 **Web GUI** - works on any platform with a browser
- 🖥️ Desktop GUI (PyQt6) - optional

## Quick Start (Web GUI - Recommended)

```bash
git clone https://github.com/Malli88/igel-profile-compare.git
cd igel-profile-compare
pip install -r requirements.txt
python run_web.py
```

Then open http://localhost:5000 in your browser.

## Usage

1. **Upload** two .ipm files (left = source, right = target)
2. **Compare** to see differences
3. **Select** settings to migrate (checkbox)
4. **Download** the migrated profile

## Screenshots

### Web Interface
- Upload profiles on left and right panels
- View differences with color coding
- Filter settings by name
- Select and migrate with one click

## Alternative: Desktop GUI

```bash
pip install -r requirements.txt
python src/main.py
```

## Building Windows Executable

```batch
build_windows.bat
```

## Project Structure

```
src/
├── core/           # Core logic
│   ├── ipm_handler.py   # IPM file parsing
│   ├── comparator.py    # Profile comparison
│   └── migrator.py      # Settings migration
├── gui/            # Desktop GUI (PyQt6)
├── web/            # Web GUI (Flask)
└── main.py         # Desktop entry point
run_web.py          # Web entry point
```

## License

MIT
