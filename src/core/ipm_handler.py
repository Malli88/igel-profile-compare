"""IPM file handler for IGEL profile exports."""
import zipfile
import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProfileMeta:
    """Profile metadata."""
    version: str = "1.0.0"
    profile_id: Optional[int] = None
    profile_name: str = ""
    profile_description: str = ""
    profile_type: str = "PROFILE"
    path: list[str] = field(default_factory=list)


@dataclass 
class ParameterValue:
    """Single parameter value with metadata."""
    value: Any
    system_settings: bool = False
    activated_in_profile: str = ""
    editable: bool = True
    source: str = ""
    ui_type: str = "string"
    param_type: int = 2
    
    @classmethod
    def from_dict(cls, data: dict) -> "ParameterValue":
        return cls(
            value=data.get("value"),
            system_settings=data.get("systemSettings", False),
            activated_in_profile=data.get("activatedInProfile", ""),
            editable=data.get("editable", True),
            source=data.get("source", ""),
            ui_type=data.get("uiType", "string"),
            param_type=data.get("type", 2)
        )


@dataclass
class InstanceParameter:
    """Complex parameter with instances (sessions, etc)."""
    template_parameters: dict[str, Any] = field(default_factory=dict)
    instances: dict[str, dict[str, Any]] = field(default_factory=dict)
    param_type: int = 1
    
    @classmethod
    def from_dict(cls, data: dict) -> "InstanceParameter":
        instances = {}
        for inst_id, inst_data in data.get("instances", {}).items():
            instances[inst_id] = cls._parse_nested(inst_data)
        return cls(
            template_parameters=data.get("templateParameters", {}),
            instances=instances,
            param_type=data.get("type", 1)
        )
    
    @staticmethod
    def _parse_nested(data: Any) -> Any:
        if isinstance(data, dict):
            if "value" in data and "systemSettings" in data:
                return ParameterValue.from_dict(data)
            return {k: InstanceParameter._parse_nested(v) for k, v in data.items()}
        return data


class IPMProfile:
    """Represents a parsed IGEL IPM profile."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.meta = ProfileMeta()
        self.parameters: dict[str, ParameterValue | InstanceParameter] = {}
        self.apps_info: dict[str, dict] = {}
        self._raw_data: dict = {}
        self._parse()
    
    def _parse(self):
        """Parse the IPM file."""
        with zipfile.ZipFile(self.file_path, 'r') as zf:
            profile_files = [f for f in zf.namelist() if f.startswith("PROFILES/") and f.endswith(".json")]
            if not profile_files:
                raise ValueError("No profile JSON found in IPM file")
            
            profile_content = zf.read(profile_files[0])
            self._raw_data = json.loads(profile_content.decode('utf-8'))
            
            meta = self._raw_data.get("meta", {})
            self.meta = ProfileMeta(
                version=meta.get("version", "1.0.0"),
                profile_id=meta.get("profileId"),
                profile_name=meta.get("profileName", ""),
                profile_description=meta.get("profileDescription", ""),
                profile_type=meta.get("profileType", "PROFILE"),
                path=self._raw_data.get("path", [])
            )
            
            for key, value in self._raw_data.get("parameterDescriptions", {}).items():
                if isinstance(value, dict):
                    if "instances" in value:
                        self.parameters[key] = InstanceParameter.from_dict(value)
                    else:
                        self.parameters[key] = ParameterValue.from_dict(value)
            
            for name in zf.namelist():
                if name.startswith("APPS/") and name.endswith("/app.json"):
                    app_data = json.loads(zf.read(name).decode('utf-8'))
                    app_name = name.split("/")[1]
                    self.apps_info[app_name] = app_data
    
    def get_flat_settings(self) -> dict[str, Any]:
        """Get all settings as flat key-value pairs for comparison."""
        result = {}
        for key, param in self.parameters.items():
            if isinstance(param, ParameterValue):
                result[key] = {"value": param.value, "type": "simple", "source": param.activated_in_profile or param.source}
            elif isinstance(param, InstanceParameter):
                for inst_id, inst_data in param.instances.items():
                    self._flatten_instance(f"{key}[{inst_id}]", inst_data, result)
        return result
    
    def _flatten_instance(self, prefix: str, data: Any, result: dict):
        """Recursively flatten instance data."""
        if isinstance(data, ParameterValue):
            result[prefix] = {"value": data.value, "type": "instance", "source": data.activated_in_profile or data.source}
        elif isinstance(data, dict):
            for key, value in data.items():
                self._flatten_instance(f"{prefix}.{key}", value, result)
    
    @property
    def name(self) -> str:
        return self.meta.profile_name


def load_ipm(file_path: str) -> IPMProfile:
    """Load an IPM file and return parsed profile."""
    return IPMProfile(file_path)
