# IGEL Profile Compare & Migration Tool

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()

A standalone Windows desktop application for comparing and migrating configuration settings between IGEL Profile Export (.ipm) files.

![Application Screenshot](docs/screenshot.png)

## Features

### Core Functionality
- **Profile Loading & Validation**: Load and validate .ipm files with comprehensive error handling
- **Side-by-Side Comparison**: Visual comparison of configuration keys and values
- **Smart Filtering**: Real-time search and filter by key name, value, or difference type
- **Configuration Migration**: Transfer settings between profiles with preview and backup

### Advanced Features
- **Color-Coded Diff View**: Easily identify added, removed, and changed settings
- **Backup & Recovery**: Automatic backup creation before any modifications
- **Detailed Logging**: Comprehensive logging for troubleshooting
- **Keyboard Navigation**: Full keyboard support for power users

## Installation

### Option 1: Download Pre-built Executable (Recommended)

1. Download the latest release from the [Releases](https://github.com/Malli88/igel-profile-compare/releases) page
2. Run `IGEL-Profile-Compare.exe` - no installation required!

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/Malli88/igel-profile-compare.git
cd igel-profile-compare

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

## Usage

### Loading Profiles

1. Click **"Browse..."** in the Left Profile panel to select your first .ipm file
2. Click **"Browse..."** in the Right Profile panel to select your second .ipm file
3. Click **"Compare Profiles"** to analyze the differences

### Understanding the Comparison View

| Color | Meaning |
|-------|--------|
| 🔴 Light Red | Key exists only in Left profile |
| 🟢 Light Green | Key exists only in Right profile |
| 🟡 Light Yellow | Key exists in both but values differ |
| ⚪ White | Key exists in both with identical values |
| 🟣 Light Purple | Key exists in both but types differ |

### Filtering Results

- **Search Box**: Type to filter by key name or value
- **Show Checkboxes**: Toggle visibility of different categories
- Filters are combinable and case-insensitive

### Migrating Settings

1. Select the keys you want to migrate (click rows, use Ctrl+Click for multiple)
2. Choose migration direction: **Left → Right** or **Right → Left**
3. Click **"Preview Migration"** to review changes
4. Click **"Migrate Selected"** to apply changes
5. Choose output file location
6. A backup is automatically created before modification

## Technical Details

### IPM File Format

- **File Extension**: `.ipm`
- **Format**: ZIP archive containing JSON configuration files
- **Structure**: Hierarchical directory structure with one or more JSON files

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk**: 100 MB free space
- **Display**: 1280x720 minimum resolution

### Architecture

```
src/
├── core/
│   ├── ipm_handler.py    # IPM file loading, parsing, saving
│   ├── comparator.py     # Profile comparison engine
│   └── migrator.py       # Migration planning and execution
├── gui/
│   └── main_window.py    # PyQt6 user interface
├── utils/
│   └── logger.py         # Logging system
└── main.py               # Application entry point
```

## Building from Source

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Build Steps

```bash
# Install build dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Build executable
python build.py
```

The executable will be created in the `dist/` directory.

### Build with Obfuscation

```bash
# Install PyArmor
pip install pyarmor

# Build with protection
python build.py --protected
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ipm_handler.py -v
```

### Code Structure

- **src/core/**: Core business logic (no GUI dependencies)
- **src/gui/**: PyQt6 user interface components
- **src/utils/**: Utility modules (logging, helpers)
- **tests/**: Automated test suite

## Configuration

### Log Files

Logs are stored in:
- **Windows**: `%LOCALAPPDATA%\IGELProfileCompare\logs\`
- **Linux**: `~/.local/share/IGELProfileCompare/logs/`

### Backup Files

Backups are created in the same directory as the target file with the naming pattern:
```
original_filename.YYYYMMDD_HHMMSS.backup.ipm
```

## Troubleshooting

### Common Issues

**"File is not a valid archive"**
- Ensure the file is a valid .ipm export from IGEL UMS
- Check if the file is corrupted or incomplete

**"Invalid JSON in file"**
- The .ipm file contains malformed JSON
- Try re-exporting the profile from IGEL UMS

**Application crashes on startup**
- Check the log files for error details
- Ensure all dependencies are installed correctly

### Getting Help

1. Check the [Issues](https://github.com/Malli88/igel-profile-compare/issues) page
2. Review log files for error details
3. Open a new issue with:
   - Steps to reproduce
   - Log file contents
   - System information

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'')
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- IGEL Technology for the excellent thin client platform
- The IGEL Community for inspiration and feedback
- PyQt6 for the cross-platform GUI framework

## Author

**Stephan Mallmann**
- GitHub: [@Malli88](https://github.com/Malli88)
- Company: IGEL Technology

---

*This tool is not officially affiliated with or endorsed by IGEL Technology GmbH.*
