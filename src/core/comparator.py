"""Comparison Engine for IGEL Profile Compare & Migration Tool.

Compares two IPM profiles and identifies differences between configurations.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Tuple
from natsort import natsorted

from src.core.ipm_handler import IPMProfile
from src.utils.logger import get_logger


class DiffType(Enum):
    """Types of differences between configurations."""
    LEFT_ONLY = auto()      # Key exists only in left profile
    RIGHT_ONLY = auto()     # Key exists only in right profile
    EQUAL = auto()          # Key exists in both with same value
    DIFFERENT = auto()      # Key exists in both with different values
    TYPE_MISMATCH = auto()  # Key exists in both but with different types


@dataclass
class DiffEntry:
    """Represents a single difference between profiles."""
    key: str
    diff_type: DiffType
    left_value: Optional[Any] = None
    right_value: Optional[Any] = None
    left_type: Optional[str] = None
    right_type: Optional[str] = None

    @property
    def has_left(self) -> bool:
        """Check if key exists in left profile."""
        return self.diff_type not in (DiffType.RIGHT_ONLY,)

    @property
    def has_right(self) -> bool:
        """Check if key exists in right profile."""
        return self.diff_type not in (DiffType.LEFT_ONLY,)

    def get_display_left(self) -> str:
        """Get display string for left value."""
        if not self.has_left:
            return "<not present>"
        return self._format_value(self.left_value)

    def get_display_right(self) -> str:
        """Get display string for right value."""
        if not self.has_right:
            return "<not present>"
        return self._format_value(self.right_value)

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, str):
            # Truncate long strings
            if len(value) > 100:
                return f'"{value[:100]}..."'
            return f'"{value}"'
        if isinstance(value, (list, dict)):
            import json
            s = json.dumps(value, ensure_ascii=False)
            if len(s) > 100:
                return f"{s[:100]}..."
            return s
        return str(value)


@dataclass
class ComparisonResult:
    """Result of comparing two profiles."""
    left_profile: IPMProfile
    right_profile: IPMProfile
    entries: List[DiffEntry] = field(default_factory=list)

    # Cached filtered lists
    _left_only: List[DiffEntry] = field(default_factory=list, repr=False)
    _right_only: List[DiffEntry] = field(default_factory=list, repr=False)
    _equal: List[DiffEntry] = field(default_factory=list, repr=False)
    _different: List[DiffEntry] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize cached lists."""
        self._update_caches()

    def _update_caches(self):
        """Update cached filtered lists."""
        self._left_only = [e for e in self.entries if e.diff_type == DiffType.LEFT_ONLY]
        self._right_only = [e for e in self.entries if e.diff_type == DiffType.RIGHT_ONLY]
        self._equal = [e for e in self.entries if e.diff_type == DiffType.EQUAL]
        self._different = [e for e in self.entries if e.diff_type in (DiffType.DIFFERENT, DiffType.TYPE_MISMATCH)]

    @property
    def left_only(self) -> List[DiffEntry]:
        """Get entries only in left profile."""
        return self._left_only

    @property
    def right_only(self) -> List[DiffEntry]:
        """Get entries only in right profile."""
        return self._right_only

    @property
    def equal(self) -> List[DiffEntry]:
        """Get entries with equal values."""
        return self._equal

    @property
    def different(self) -> List[DiffEntry]:
        """Get entries with different values."""
        return self._different

    @property
    def total_keys(self) -> int:
        """Get total number of unique keys."""
        return len(self.entries)

    @property
    def summary(self) -> Dict[str, int]:
        """Get summary statistics."""
        return {
            'total': self.total_keys,
            'left_only': len(self._left_only),
            'right_only': len(self._right_only),
            'equal': len(self._equal),
            'different': len(self._different),
        }


class ProfileComparator:
    """Compares two IPM profiles."""

    def __init__(self):
        """Initialize the comparator."""
        self.logger = get_logger()

    def compare(self, left: IPMProfile, right: IPMProfile) -> ComparisonResult:
        """Compare two IPM profiles.

        Args:
            left: Left profile to compare
            right: Right profile to compare

        Returns:
            ComparisonResult with all differences
        """
        self.logger.info("Starting profile comparison")

        left_keys = set(left.flattened_config.keys())
        right_keys = set(right.flattened_config.keys())
        all_keys = left_keys | right_keys

        entries = []

        for key in natsorted(all_keys):
            in_left = key in left_keys
            in_right = key in right_keys

            if in_left and not in_right:
                # Left only
                entries.append(DiffEntry(
                    key=key,
                    diff_type=DiffType.LEFT_ONLY,
                    left_value=left.flattened_config[key],
                    left_type=type(left.flattened_config[key]).__name__
                ))
            elif in_right and not in_left:
                # Right only
                entries.append(DiffEntry(
                    key=key,
                    diff_type=DiffType.RIGHT_ONLY,
                    right_value=right.flattened_config[key],
                    right_type=type(right.flattened_config[key]).__name__
                ))
            else:
                # Both have the key
                left_val = left.flattened_config[key]
                right_val = right.flattened_config[key]
                left_type = type(left_val).__name__
                right_type = type(right_val).__name__

                if left_type != right_type:
                    diff_type = DiffType.TYPE_MISMATCH
                elif left_val == right_val:
                    diff_type = DiffType.EQUAL
                else:
                    diff_type = DiffType.DIFFERENT

                entries.append(DiffEntry(
                    key=key,
                    diff_type=diff_type,
                    left_value=left_val,
                    right_value=right_val,
                    left_type=left_type,
                    right_type=right_type
                ))

        result = ComparisonResult(
            left_profile=left,
            right_profile=right,
            entries=entries
        )
        result._update_caches()

        self.logger.info(
            f"Comparison complete: {result.summary}"
        )

        return result

    def filter_entries(
        self,
        result: ComparisonResult,
        search_text: str = "",
        show_left_only: bool = True,
        show_right_only: bool = True,
        show_equal: bool = True,
        show_different: bool = True,
        search_in_keys: bool = True,
        search_in_values: bool = True
    ) -> List[DiffEntry]:
        """Filter comparison entries based on criteria.

        Args:
            result: ComparisonResult to filter
            search_text: Text to search for (case-insensitive)
            show_left_only: Include left-only entries
            show_right_only: Include right-only entries
            show_equal: Include equal entries
            show_different: Include different entries
            search_in_keys: Search in key names
            search_in_values: Search in values

        Returns:
            Filtered list of DiffEntry objects
        """
        filtered = []
        search_lower = search_text.lower() if search_text else ""

        for entry in result.entries:
            # Filter by diff type
            if entry.diff_type == DiffType.LEFT_ONLY and not show_left_only:
                continue
            if entry.diff_type == DiffType.RIGHT_ONLY and not show_right_only:
                continue
            if entry.diff_type == DiffType.EQUAL and not show_equal:
                continue
            if entry.diff_type in (DiffType.DIFFERENT, DiffType.TYPE_MISMATCH) and not show_different:
                continue

            # Filter by search text
            if search_lower:
                matches = False

                if search_in_keys and search_lower in entry.key.lower():
                    matches = True

                if search_in_values and not matches:
                    left_str = str(entry.left_value).lower() if entry.left_value is not None else ""
                    right_str = str(entry.right_value).lower() if entry.right_value is not None else ""
                    if search_lower in left_str or search_lower in right_str:
                        matches = True

                if not matches:
                    continue

            filtered.append(entry)

        return filtered

    def get_tree_structure(self, entries: List[DiffEntry]) -> Dict[str, Any]:
        """Convert flat entries to a tree structure for hierarchical display.

        Args:
            entries: List of DiffEntry objects

        Returns:
            Nested dictionary representing the tree structure
        """
        tree = {}

        for entry in entries:
            parts = entry.key.split('.')
            current = tree

            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {'_children': {}, '_entries': []}
                current = current[part]['_children']

            # Add the entry at the leaf
            leaf_key = parts[-1]
            if leaf_key not in current:
                current[leaf_key] = {'_children': {}, '_entries': []}
            current[leaf_key]['_entries'].append(entry)

        return tree
