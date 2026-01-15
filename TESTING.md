# Testing Documentation

## Overview

This document describes the testing strategy, test cases, and validation procedures for the IGEL Profile Compare & Migration Tool.

## Test Environment

- **Python Version**: 3.10+
- **Test Framework**: pytest
- **Coverage Tool**: pytest-cov
- **Platform**: Windows 10/11, Linux (development)

## Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run specific test module
pytest tests/test_ipm_handler.py -v

# Run specific test class
pytest tests/test_comparator.py::TestProfileComparison -v

# Run specific test
pytest tests/test_migrator.py::TestMigrationExecution::test_execute_migration -v
```

### Test Categories

```bash
# Run only unit tests
pytest tests/ -v -m "not integration"

# Run only integration tests
pytest tests/ -v -m integration
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── fixtures/                # Test data files
│   ├── sample_left.ipm      # Sample left profile
│   ├── sample_right.ipm     # Sample right profile
│   ├── sample_empty.ipm     # Empty profile for edge cases
│   └── corrupted.ipm        # Invalid file for error testing
├── test_ipm_handler.py      # IPM file handling tests
├── test_comparator.py       # Comparison logic tests
└── test_migrator.py         # Migration logic tests
```

## Test Modules

### 1. IPM Handler Tests (`test_ipm_handler.py`)

#### Test Classes

| Class | Description | Test Count |
|-------|-------------|------------|
| `TestIPMHandlerLoading` | File loading and validation | 4 |
| `TestIPMHandlerParsing` | JSON parsing and flattening | 5 |
| `TestIPMHandlerBackup` | Backup creation and restoration | 2 |
| `TestIPMHandlerSaving` | Profile saving functionality | 2 |
| `TestIPMHandlerEdgeCases` | Edge cases and error handling | 4 |

#### Key Test Cases

- **Valid Profile Loading**: Verify that valid .ipm files load correctly
- **Invalid File Handling**: Test error handling for non-existent, corrupted, and invalid files
- **JSON Parsing**: Verify correct parsing of nested JSON structures
- **Flattening**: Test conversion of hierarchical config to flat key-value pairs
- **Array Handling**: Verify arrays are correctly indexed in flattened output
- **Special Characters**: Test handling of Unicode, quotes, newlines, and paths
- **Null Values**: Verify null values are preserved correctly
- **Deep Nesting**: Test handling of deeply nested configuration structures
- **Backup/Restore**: Verify backup creation and restoration functionality

### 2. Comparator Tests (`test_comparator.py`)

#### Test Classes

| Class | Description | Test Count |
|-------|-------------|------------|
| `TestProfileComparison` | Core comparison functionality | 7 |
| `TestDiffEntry` | Diff entry representation | 5 |
| `TestFiltering` | Search and filter functionality | 8 |
| `TestTreeStructure` | Tree structure generation | 1 |

#### Key Test Cases

- **Basic Comparison**: Verify two profiles can be compared
- **Left-Only Detection**: Find keys only in left profile
- **Right-Only Detection**: Find keys only in right profile
- **Equal Detection**: Find keys with identical values
- **Different Detection**: Find keys with different values
- **Summary Statistics**: Verify comparison summary is accurate
- **Identical Profiles**: Test comparing a profile with itself
- **Search Filtering**: Test text search in keys and values
- **Case Insensitivity**: Verify filters are case-insensitive
- **Type Filtering**: Test filtering by diff type
- **Combined Filters**: Test multiple filters together

### 3. Migrator Tests (`test_migrator.py`)

#### Test Classes

| Class | Description | Test Count |
|-------|-------------|------------|
| `TestMigrationPlanning` | Migration plan creation | 6 |
| `TestMigrationAction` | Action representation | 3 |
| `TestMigrationExecution` | Migration execution | 5 |
| `TestBackupRestore` | Backup and restore | 1 |
| `TestEdgeCases` | Edge cases | 2 |

#### Key Test Cases

- **Plan Creation**: Verify migration plans are created correctly
- **Direction Handling**: Test left-to-right and right-to-left migrations
- **Mode Selection**: Test all-different vs selected-only modes
- **Empty Selection**: Handle empty key selection gracefully
- **Plan Summary**: Verify plan summary statistics
- **Execution**: Test actual migration execution
- **Backup Creation**: Verify backups are created during migration
- **File Validity**: Ensure migrated files are valid IPM archives
- **Change Application**: Verify changes are actually applied
- **Restore Functionality**: Test restoring from backup

## Test Fixtures

### Sample Profiles

#### sample_left.ipm
```json
{
  "system": {
    "hostname": "igel-left-001",
    "timezone": "Europe/Berlin",
    "language": "de_DE",
    "keyboard": {"layout": "de", "variant": "nodeadkeys"}
  },
  "network": {
    "dhcp": true,
    "dns": ["8.8.8.8", "8.8.4.4"],
    "proxy": {"enabled": false, "server": ""}
  },
  "display": {
    "resolution": "1920x1080",
    "refresh_rate": 60,
    "scaling": 1.0
  },
  "sessions": [...],
  "security": {"firewall": true, "usb_storage": false}
}
```

#### sample_right.ipm
```json
{
  "system": {
    "hostname": "igel-right-002",
    "timezone": "Europe/Berlin",
    "language": "en_US",
    "keyboard": {"layout": "us", "variant": ""},
    "ntp_server": "pool.ntp.org"
  },
  "network": {
    "dhcp": false,
    "static_ip": "192.168.1.100",
    "dns": ["1.1.1.1"],
    "proxy": {"enabled": true, "server": "proxy.example.com"}
  },
  "display": {
    "resolution": "1920x1080",
    "refresh_rate": 75,
    "scaling": 1.25
  },
  "sessions": [...],
  "audio": {"enabled": true, "volume": 80}
}
```

### Expected Differences

| Category | Keys |
|----------|------|
| Left Only | `security.firewall`, `security.usb_storage` |
| Right Only | `system.ntp_server`, `network.static_ip`, `audio.*` |
| Equal | `system.timezone`, `display.resolution` |
| Different | `system.hostname`, `system.language`, `network.dhcp`, etc. |

## Edge Cases Tested

### File Handling
- [x] Non-existent files
- [x] Corrupted/invalid archives
- [x] Empty archives
- [x] Archives with invalid JSON
- [x] Archives with multiple JSON files

### Data Types
- [x] Null values
- [x] Empty strings
- [x] Empty arrays
- [x] Empty objects
- [x] Deeply nested structures (5+ levels)
- [x] Large arrays (100+ elements)
- [x] Unicode characters
- [x] Special characters (quotes, backslashes, newlines)

### Comparison
- [x] Identical profiles
- [x] Completely different profiles
- [x] Type mismatches (string vs number)
- [x] Array length differences
- [x] Missing nested keys

### Migration
- [x] Empty migration (no changes)
- [x] Single key migration
- [x] Bulk migration
- [x] Adding new keys
- [x] Updating existing keys
- [x] Type-changing migrations

## Manual Testing Checklist

### UI Testing

- [ ] Application launches without errors
- [ ] Window resizes correctly
- [ ] All buttons are clickable and responsive
- [ ] File dialogs open correctly
- [ ] Error messages display properly
- [ ] Progress indicators work during long operations

### Functional Testing

- [ ] Load valid .ipm file (left)
- [ ] Load valid .ipm file (right)
- [ ] Compare profiles shows correct results
- [ ] Search filter works in real-time
- [ ] Category filters work correctly
- [ ] Filters can be combined
- [ ] Row selection works (single and multi)
- [ ] Migration preview shows correct changes
- [ ] Migration executes successfully
- [ ] Backup file is created
- [ ] Migrated file is valid and importable

### Error Handling

- [ ] Invalid file shows error message
- [ ] Corrupted file shows error message
- [ ] Permission denied shows error message
- [ ] Network path errors handled gracefully

## Test Results

### Latest Test Run

```
========================= test session starts ==========================
platform: Windows-10-...
python: 3.10.x
pytest: 7.x.x

tests/test_ipm_handler.py::TestIPMHandlerLoading::test_load_valid_profile PASSED
tests/test_ipm_handler.py::TestIPMHandlerLoading::test_load_nonexistent_file PASSED
tests/test_ipm_handler.py::TestIPMHandlerLoading::test_load_corrupted_file PASSED
...

========================= XX passed in X.XXs ===========================
```

### Coverage Report

| Module | Statements | Missing | Coverage |
|--------|------------|---------|----------|
| src/core/ipm_handler.py | XXX | XX | XX% |
| src/core/comparator.py | XXX | XX | XX% |
| src/core/migrator.py | XXX | XX | XX% |
| src/utils/logger.py | XXX | XX | XX% |
| **Total** | **XXX** | **XX** | **XX%** |

## Known Limitations

1. **Large Files**: Files over 100MB may cause performance issues
2. **Binary Data**: Binary data in JSON values is not fully supported
3. **Circular References**: JSON with circular references will fail
4. **File Locking**: Windows file locking may prevent operations on open files

## Assumptions

1. IPM files are valid ZIP archives
2. JSON files within IPM use UTF-8 encoding
3. Configuration keys are case-sensitive
4. Array order is significant for comparison
5. Null values are distinct from missing keys

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src
```

## Contributing Tests

When adding new features, please:

1. Add corresponding test cases
2. Ensure all existing tests pass
3. Maintain or improve code coverage
4. Document any new test fixtures
5. Update this document if needed
