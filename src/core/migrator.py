"""Settings migration between profiles."""
import zipfile
import json
import copy
from pathlib import Path
from typing import Any
from ipm_handler import IPMProfile


def migrate_settings(source: IPMProfile, target: IPMProfile, keys: list[str], output_path: str) -> str:
    """Migrate selected settings from source to target profile.
    
    Args:
        source: Source profile to copy settings from
        target: Target profile to apply settings to
        keys: List of setting keys to migrate (flat format)
        output_path: Path for the new IPM file
    
    Returns:
        Path to the created IPM file
    """
    # Deep copy target raw data
    new_data = copy.deepcopy(target._raw_data)
    source_flat = source.get_flat_settings()
    
    # Apply selected settings
    for key in keys:
        if key not in source_flat:
            continue
        _apply_setting(new_data, key, source_flat[key])
    
    # Create new IPM file
    with zipfile.ZipFile(target.file_path, 'r') as src_zip:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
            for item in src_zip.namelist():
                if item.startswith("PROFILES/") and item.endswith(".json"):
                    # Write modified profile
                    dst_zip.writestr(item, json.dumps(new_data, indent=2))
                else:
                    # Copy other files as-is
                    dst_zip.writestr(item, src_zip.read(item))
    
    return output_path


def _apply_setting(data: dict, flat_key: str, setting: dict):
    """Apply a flat setting key to the raw profile data."""
    # Parse the flat key format: base.path[instance_id].nested.key
    params = data.setdefault("parameterDescriptions", {})
    
    # Check if it's an instance key
    if "[" in flat_key:
        base, rest = flat_key.split("[", 1)
        inst_id, nested = rest.split("]", 1)
        nested = nested.lstrip(".")
        
        if base not in params:
            params[base] = {"instances": {}, "type": 1}
        if "instances" not in params[base]:
            params[base]["instances"] = {}
        if inst_id not in params[base]["instances"]:
            params[base]["instances"][inst_id] = {}
        
        _set_nested(params[base]["instances"][inst_id], nested.split("."), setting)
    else:
        params[flat_key] = {
            "value": setting["value"],
            "systemSettings": False,
            "type": 2
        }


def _set_nested(d: dict, keys: list[str], value: dict):
    """Set a nested dictionary value."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = {"value": value["value"], "systemSettings": False}
