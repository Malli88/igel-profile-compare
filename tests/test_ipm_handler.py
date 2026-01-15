"""Tests for IPM Handler module."""

import pytest
import json
import zipfile
import tempfile
from pathlib import Path

from src.core.ipm_handler import IPMHandler, IPMProfile, IPMValidationError


class TestIPMHandlerLoading:
    """Tests for IPM file loading functionality."""

    def test_load_valid_profile(self, ipm_handler, sample_left_ipm):
        """Test loading a valid IPM profile."""
        profile = ipm_handler.load_profile(sample_left_ipm)

        assert profile is not None
        assert profile.is_valid is True
        assert profile.file_path == sample_left_ipm
        assert len(profile.files) > 0
        assert len(profile.json_configs) > 0
        assert len(profile.flattened_config) > 0

    def test_load_nonexistent_file(self, ipm_handler):
        """Test loading a file that doesn't exist."""
        with pytest.raises(IPMValidationError) as exc_info:
            ipm_handler.load_profile("/nonexistent/path/file.ipm")

        assert "not found" in str(exc_info.value).lower()

    def test_load_corrupted_file(self, ipm_handler, corrupted_ipm):
        """Test loading a corrupted/invalid archive."""
        with pytest.raises(IPMValidationError) as exc_info:
            ipm_handler.load_profile(corrupted_ipm)

        assert "not a valid archive" in str(exc_info.value).lower()

    def test_load_empty_profile(self, ipm_handler, sample_empty_ipm):
        """Test loading an empty profile."""
        profile = ipm_handler.load_profile(sample_empty_ipm)

        assert profile is not None
        assert profile.is_valid is True
        # Empty config should still have the JSON file
        assert len(profile.json_configs) > 0


class TestIPMHandlerParsing:
    """Tests for JSON parsing and flattening."""

    def test_json_parsing(self, left_profile):
        """Test that JSON files are correctly parsed."""
        assert "config/settings.json" in left_profile.json_configs
        config = left_profile.json_configs["config/settings.json"]

        assert "system" in config
        assert "network" in config
        assert config["system"]["hostname"] == "igel-left-001"

    def test_flattening(self, left_profile):
        """Test that nested config is correctly flattened."""
        flat = left_profile.flattened_config

        # Check various flattened keys exist
        assert any("hostname" in key for key in flat.keys())
        assert any("keyboard.layout" in key for key in flat.keys())

    def test_array_flattening(self, left_profile):
        """Test that arrays are correctly flattened."""
        flat = left_profile.flattened_config

        # Check array elements are flattened with indices
        session_keys = [k for k in flat.keys() if "sessions[" in k]
        assert len(session_keys) > 0

    def test_get_all_keys(self, left_profile):
        """Test getting all configuration keys."""
        keys = left_profile.get_all_keys()

        assert isinstance(keys, list)
        assert len(keys) > 0
        assert all(isinstance(k, str) for k in keys)

    def test_get_value(self, left_profile):
        """Test getting specific values."""
        # Find a key that exists
        keys = left_profile.get_all_keys()
        if keys:
            value = left_profile.get_value(keys[0])
            assert value is not None or value == left_profile.flattened_config[keys[0]]


class TestIPMHandlerBackup:
    """Tests for backup functionality."""

    def test_create_backup(self, ipm_handler, sample_left_ipm, tmp_path):
        """Test creating a backup of an IPM file."""
        # Copy sample to temp location
        import shutil
        temp_ipm = tmp_path / "test.ipm"
        shutil.copy(sample_left_ipm, temp_ipm)

        backup_path = ipm_handler.create_backup(temp_ipm)

        assert backup_path.exists()
        assert ".backup.ipm" in backup_path.name

        # Verify backup content matches original
        with zipfile.ZipFile(temp_ipm, 'r') as orig:
            with zipfile.ZipFile(backup_path, 'r') as backup:
                assert orig.namelist() == backup.namelist()

    def test_restore_backup(self, ipm_handler, sample_left_ipm, tmp_path):
        """Test restoring from backup."""
        import shutil

        # Create original and backup
        original = tmp_path / "original.ipm"
        shutil.copy(sample_left_ipm, original)
        backup_path = ipm_handler.create_backup(original)

        # Modify original (delete it)
        original.unlink()
        assert not original.exists()

        # Restore
        ipm_handler.restore_backup(backup_path, original)

        assert original.exists()


class TestIPMHandlerSaving:
    """Tests for saving modified profiles."""

    def test_save_profile(self, ipm_handler, left_profile, tmp_path):
        """Test saving a profile to a new file."""
        output_path = tmp_path / "output.ipm"

        ipm_handler.save_profile(left_profile, output_path)

        assert output_path.exists()

        # Verify saved file is valid
        reloaded = ipm_handler.load_profile(output_path)
        assert reloaded.is_valid

    def test_save_preserves_structure(self, ipm_handler, left_profile, tmp_path):
        """Test that saving preserves archive structure."""
        output_path = tmp_path / "output.ipm"

        ipm_handler.save_profile(left_profile, output_path)

        # Compare file lists
        with zipfile.ZipFile(left_profile.file_path, 'r') as orig:
            with zipfile.ZipFile(output_path, 'r') as saved:
                assert set(orig.namelist()) == set(saved.namelist())


class TestIPMHandlerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_json_in_archive(self, ipm_handler, tmp_path):
        """Test handling of invalid JSON within archive."""
        bad_ipm = tmp_path / "bad_json.ipm"

        with zipfile.ZipFile(bad_ipm, 'w') as zf:
            zf.writestr("config.json", "{ invalid json }")

        with pytest.raises(IPMValidationError) as exc_info:
            ipm_handler.load_profile(bad_ipm)

        assert "invalid json" in str(exc_info.value).lower()

    def test_deeply_nested_config(self, ipm_handler, tmp_path):
        """Test handling of deeply nested configuration."""
        deep_config = {"level1": {"level2": {"level3": {"level4": {"level5": {"value": "deep"}}}}}}

        deep_ipm = tmp_path / "deep.ipm"
        with zipfile.ZipFile(deep_ipm, 'w') as zf:
            zf.writestr("config.json", json.dumps(deep_config))

        profile = ipm_handler.load_profile(deep_ipm)

        assert profile.is_valid
        # Check deep value is accessible
        deep_keys = [k for k in profile.flattened_config.keys() if "level5" in k]
        assert len(deep_keys) > 0

    def test_special_characters_in_values(self, ipm_handler, tmp_path):
        """Test handling of special characters in values."""
        special_config = {
            "unicode": "äöü ñ 中文 🎉",
            "quotes": 'He said "hello"',
            "newlines": "line1\nline2",
            "path": "C:\\Users\\test"
        }

        special_ipm = tmp_path / "special.ipm"
        with zipfile.ZipFile(special_ipm, 'w') as zf:
            zf.writestr("config.json", json.dumps(special_config, ensure_ascii=False))

        profile = ipm_handler.load_profile(special_ipm)

        assert profile.is_valid
        assert any("äöü" in str(v) for v in profile.flattened_config.values())

    def test_null_values(self, ipm_handler, tmp_path):
        """Test handling of null values."""
        null_config = {
            "null_value": None,
            "nested": {"also_null": None}
        }

        null_ipm = tmp_path / "null.ipm"
        with zipfile.ZipFile(null_ipm, 'w') as zf:
            zf.writestr("config.json", json.dumps(null_config))

        profile = ipm_handler.load_profile(null_ipm)

        assert profile.is_valid
        # Null values should be preserved
        null_keys = [k for k, v in profile.flattened_config.items() if v is None]
        assert len(null_keys) >= 2
