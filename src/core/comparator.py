"""Profile comparison logic."""
from dataclasses import dataclass, field
from typing import Any
from ipm_handler import IPMProfile


@dataclass
class ComparisonResult:
    """Result of comparing two profiles."""
    left_name: str
    right_name: str
    only_left: dict[str, Any] = field(default_factory=dict)
    only_right: dict[str, Any] = field(default_factory=dict)
    different: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    identical: dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_differences(self) -> int:
        return len(self.only_left) + len(self.only_right) + len(self.different)
    
    @property
    def summary(self) -> str:
        return f"Only in {self.left_name}: {len(self.only_left)}, Only in {self.right_name}: {len(self.only_right)}, Different: {len(self.different)}, Identical: {len(self.identical)}"


def compare_profiles(left: IPMProfile, right: IPMProfile) -> ComparisonResult:
    """Compare two IPM profiles and return differences."""
    left_flat = left.get_flat_settings()
    right_flat = right.get_flat_settings()
    
    left_keys = set(left_flat.keys())
    right_keys = set(right_flat.keys())
    
    result = ComparisonResult(left_name=left.name, right_name=right.name)
    
    # Keys only in left
    for key in left_keys - right_keys:
        result.only_left[key] = left_flat[key]
    
    # Keys only in right
    for key in right_keys - left_keys:
        result.only_right[key] = right_flat[key]
    
    # Common keys - check values
    for key in left_keys & right_keys:
        lv = left_flat[key]["value"]
        rv = right_flat[key]["value"]
        if lv != rv:
            result.different[key] = (left_flat[key], right_flat[key])
        else:
            result.identical[key] = left_flat[key]
    
    return result
