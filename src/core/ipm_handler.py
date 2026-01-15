"""IPM File Handler for IGEL Profile Compare & Migration Tool.

Handles loading, parsing, validation, and saving of .ipm profile files.
IPM files are ZIP archives containing JSON configuration files.
"""

import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import os
import hashlib

from src.utils.logger import get_logger


@dataclass
class IPMFileInfo:
    """Information about a file within the IPM archive."""
    path: str
    size: int
    compressed_size: int
    is_json: bool
    content: Optional[Any] = None
    raw_content: Optional[bytes] = None
    checksum: Optional[str] = None


@dataclass
class IPMProfile:
    """Represents a loaded IPM profile."""
    file_path: Path
    files: Dict[str, IPMFileInfo] = field(default_factory=dict)
    json_configs: Dict[str, Any] = field(default_factory=dict)
    flattened_config: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = False
    error_message: Optional[str] = None
    load_timestamp: Optional[datetime] = None

    def get_all_keys(self) -> List[str]:
        """Get all configuration keys from flattened config."""
        return list(self.flattened_config.keys())

    def get_value(self, key: str) -> Optional[Any]:
        """Get value for a specific key."""
        return self.flattened_config.get(key)


class IPMValidationError(Exception):
    """Exception raised for IPM validation errors."""
    pass


class IPMHandler:
    """Handler for IPM profile files."""

    def __init__(self):
        """Initialize the IPM handler."""
        self.logger = get_logger()
        self._temp_dirs: List[Path] = []

    def load_profile(self, file_path: str | Path) -> IPMProfile:
        """Load and parse an IPM profile file.

        Args:
            file_path: Path to the .ipm file

        Returns:
            IPMProfile object with parsed data

        Raises:
            IPMValidationError: If the file is invalid
        """
        file_path = Path(file_path)
        profile = IPMProfile(file_path=file_path)

        self.logger.info(f"Loading IPM profile: {file_path}")

        try:
            # Validate file exists
            if not file_path.exists():
                raise IPMValidationError(f"File not found: {file_path}")

            # Validate file extension
            if file_path.suffix.lower() != '.ipm':
                self.logger.warning(f"File does not have .ipm extension: {file_path}")

            # Validate it's a valid ZIP archive
            if not zipfile.is_zipfile(file_path):
                raise IPMValidationError(f"File is not a valid archive: {file_path}")

            # Open and parse the archive
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Check for corruption
                bad_file = zf.testzip()
                if bad_file:
                    raise IPMValidationError(f"Corrupted file in archive: {bad_file}")

                # Process each file in the archive
                for info in zf.infolist():
                    if info.is_dir():
                        continue

                    file_info = IPMFileInfo(
                        path=info.filename,
                        size=info.file_size,
                        compressed_size=info.compress_size,
                        is_json=info.filename.lower().endswith('.json')
                    )

                    # Read file content
                    raw_content = zf.read(info.filename)
                    file_info.raw_content = raw_content
                    file_info.checksum = hashlib.md5(raw_content).hexdigest()

                    # Parse JSON files
                    if file_info.is_json:
                        try:
                            content = json.loads(raw_content.decode('utf-8'))
                            file_info.content = content
                            profile.json_configs[info.filename] = content
                            self.logger.debug(f"Parsed JSON file: {info.filename}")
                        except json.JSONDecodeError as e:
                            raise IPMValidationError(
                                f"Invalid JSON in {info.filename}: {str(e)}"
                            )
                        except UnicodeDecodeError as e:
                            raise IPMValidationError(
                                f"Encoding error in {info.filename}: {str(e)}"
                            )

                    profile.files[info.filename] = file_info

            # Flatten all JSON configurations
            profile.flattened_config = self._flatten_all_configs(profile.json_configs)

            profile.is_valid = True
            profile.load_timestamp = datetime.now()

            self.logger.info(
                f"Successfully loaded profile: {len(profile.files)} files, "
                f"{len(profile.json_configs)} JSON configs, "
                f"{len(profile.flattened_config)} configuration keys"
            )

        except IPMValidationError:
            raise
        except Exception as e:
            self.logger.exception(f"Error loading profile: {e}")
            raise IPMValidationError(f"Failed to load profile: {str(e)}")

        return profile

    def _flatten_all_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten all JSON configurations into a single dictionary.

        Keys are prefixed with the source file path for uniqueness.
        """
        flattened = {}
        for file_path, config in configs.items():
            prefix = file_path.replace('.json', '').replace('/', '.').replace('\\', '.') 
            file_flattened = self._flatten_dict(config, prefix)
            flattened.update(file_flattened)
        return flattened

    def _flatten_dict(self, d: Any, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Recursively flatten a nested dictionary.

        Args:
            d: Dictionary or value to flatten
            parent_key: Parent key prefix
            sep: Separator between key levels

        Returns:
            Flattened dictionary with dot-notation keys
        """
        items = {}

        if isinstance(d, dict):
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.update(self._flatten_dict(v, new_key, sep))
        elif isinstance(d, list):
            for i, v in enumerate(d):
                new_key = f"{parent_key}[{i}]"
                items.update(self._flatten_dict(v, new_key, sep))
        else:
            items[parent_key] = d

        return items

    def _unflatten_dict(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a flattened dictionary back to nested structure.

        Args:
            flat_dict: Flattened dictionary with dot-notation keys

        Returns:
            Nested dictionary structure
        """
        result = {}

        for flat_key, value in flat_dict.items():
            keys = self._parse_flat_key(flat_key)
            current = result

            for i, key in enumerate(keys[:-1]):
                next_key = keys[i + 1]

                if isinstance(key, int):
                    while len(current) <= key:
                        current.append(None)
                    if current[key] is None:
                        current[key] = [] if isinstance(next_key, int) else {}
                    current = current[key]
                else:
                    if key not in current:
                        current[key] = [] if isinstance(next_key, int) else {}
                    current = current[key]

            final_key = keys[-1]
            if isinstance(final_key, int):
                while len(current) <= final_key:
                    current.append(None)
                current[final_key] = value
            else:
                current[final_key] = value

        return result

    def _parse_flat_key(self, flat_key: str) -> List[str | int]:
        """Parse a flattened key into its components.

        Args:
            flat_key: Key like "config.items[0].name"

        Returns:
            List of key components, with integers for array indices
        """
        import re
        parts = []
        # Split by dots, but handle array indices
        tokens = re.split(r'\.|(?=\[)', flat_key)

        for token in tokens:
            if not token:
                continue
            # Check for array index
            match = re.match(r'\[(\d+)\]', token)
            if match:
                parts.append(int(match.group(1)))
            else:
                parts.append(token)

        return parts

    def create_backup(self, file_path: str | Path) -> Path:
        """Create a backup of an IPM file.

        Args:
            file_path: Path to the file to backup

        Returns:
            Path to the backup file
        """
        file_path = Path(file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.{timestamp}.backup.ipm')

        self.logger.info(f"Creating backup: {backup_path}")
        shutil.copy2(file_path, backup_path)

        return backup_path

    def restore_backup(self, backup_path: str | Path, target_path: str | Path) -> None:
        """Restore a backup file.

        Args:
            backup_path: Path to the backup file
            target_path: Path where to restore the file
        """
        backup_path = Path(backup_path)
        target_path = Path(target_path)

        if not backup_path.exists():
            raise IPMValidationError(f"Backup file not found: {backup_path}")

        self.logger.info(f"Restoring backup from {backup_path} to {target_path}")
        shutil.copy2(backup_path, target_path)

    def save_profile(self, profile: IPMProfile, output_path: str | Path) -> None:
        """Save a modified profile to a new IPM file.

        Preserves the original archive structure, compression, and unchanged files.

        Args:
            profile: The IPMProfile to save
            output_path: Path for the output file
        """
        output_path = Path(output_path)
        self.logger.info(f"Saving profile to: {output_path}")

        # Create a temporary file first
        temp_path = output_path.with_suffix('.tmp')

        try:
            with zipfile.ZipFile(profile.file_path, 'r') as src_zip:
                with zipfile.ZipFile(temp_path, 'w', compression=zipfile.ZIP_DEFLATED) as dst_zip:
                    for info in src_zip.infolist():
                        if info.is_dir():
                            dst_zip.writestr(info, '')
                            continue

                        if info.filename in profile.json_configs:
                            # Write updated JSON content
                            updated_content = json.dumps(
                                profile.json_configs[info.filename],
                                indent=2,
                                ensure_ascii=False
                            ).encode('utf-8')
                            dst_zip.writestr(info, updated_content)
                            self.logger.debug(f"Updated JSON file: {info.filename}")
                        else:
                            # Copy unchanged file
                            dst_zip.writestr(info, src_zip.read(info.filename))

            # Move temp file to final location
            shutil.move(temp_path, output_path)
            self.logger.info(f"Profile saved successfully: {output_path}")

        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            self.logger.exception(f"Error saving profile: {e}")
            raise IPMValidationError(f"Failed to save profile: {str(e)}")

    def cleanup(self) -> None:
        """Clean up any temporary directories."""
        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        self._temp_dirs.clear()
