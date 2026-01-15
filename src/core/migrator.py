"""Settings migration between profiles."""
import zipfile
import json
import copy
from typing import Any
from core.ipm_handler import IPMProfile

def migrate_settings(source: IPMProfile, target: IPMProfile, keys: list[str], output_path: str) -> str:
    new_data = copy.deepcopy(target._raw_data)
    source_flat = source.get_flat_settings()
    for key in keys:
        if key in source_flat:
            _apply_setting(new_data, key, source_flat[key])
    with zipfile.ZipFile(target.file_path, 'r') as src_zip:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
            for item in src_zip.namelist():
                if item.startswith("PROFILES/") and item.endswith(".json"):
                    dst_zip.writestr(item, json.dumps(new_data, indent=2))
                else:
                    dst_zip.writestr(item, src_zip.read(item))
    return output_path

def _apply_setting(data: dict, flat_key: str, setting: dict):
    params = data.setdefault("parameterDescriptions", {})
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
        params[flat_key] = {"value": setting["value"], "systemSettings": False, "type": 2}

def _set_nested(d: dict, keys: list[str], value: dict):
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = {"value": value["value"], "systemSettings": False}
