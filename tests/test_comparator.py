"""Tests for Profile Comparator module."""

import pytest
from src.core.comparator import (
    ProfileComparator, ComparisonResult, DiffEntry, DiffType
)


class TestProfileComparison:
    """Tests for profile comparison functionality."""

    def test_compare_profiles(self, comparator, left_profile, right_profile):
        """Test basic profile comparison."""
        result = comparator.compare(left_profile, right_profile)

        assert result is not None
        assert isinstance(result, ComparisonResult)
        assert result.left_profile == left_profile
        assert result.right_profile == right_profile
        assert len(result.entries) > 0

    def test_comparison_finds_left_only(self, comparator, left_profile, right_profile):
        """Test that comparison finds keys only in left profile."""
        result = comparator.compare(left_profile, right_profile)

        # Security section is only in left
        left_only = result.left_only
        assert len(left_only) > 0

        # Check that security keys are in left_only
        security_keys = [e for e in left_only if "security" in e.key.lower()]
        assert len(security_keys) > 0

    def test_comparison_finds_right_only(self, comparator, left_profile, right_profile):
        """Test that comparison finds keys only in right profile."""
        result = comparator.compare(left_profile, right_profile)

        # Audio section and ntp_server are only in right
        right_only = result.right_only
        assert len(right_only) > 0

        # Check that audio keys are in right_only
        audio_keys = [e for e in right_only if "audio" in e.key.lower()]
        assert len(audio_keys) > 0

    def test_comparison_finds_equal(self, comparator, left_profile, right_profile):
        """Test that comparison finds equal values."""
        result = comparator.compare(left_profile, right_profile)

        # Timezone should be equal
        equal = result.equal
        timezone_entries = [e for e in equal if "timezone" in e.key.lower()]
        assert len(timezone_entries) > 0

    def test_comparison_finds_different(self, comparator, left_profile, right_profile):
        """Test that comparison finds different values."""
        result = comparator.compare(left_profile, right_profile)

        # Hostname should be different
        different = result.different
        assert len(different) > 0

        hostname_entries = [e for e in different if "hostname" in e.key.lower()]
        assert len(hostname_entries) > 0

    def test_comparison_summary(self, comparator, left_profile, right_profile):
        """Test comparison summary statistics."""
        result = comparator.compare(left_profile, right_profile)

        summary = result.summary

        assert "total" in summary
        assert "left_only" in summary
        assert "right_only" in summary
        assert "equal" in summary
        assert "different" in summary

        # Total should equal sum of categories
        assert summary["total"] == (
            summary["left_only"] + summary["right_only"] + 
            summary["equal"] + summary["different"]
        )

    def test_compare_identical_profiles(self, comparator, left_profile):
        """Test comparing a profile with itself."""
        result = comparator.compare(left_profile, left_profile)

        # All entries should be equal
        assert len(result.left_only) == 0
        assert len(result.right_only) == 0
        assert len(result.different) == 0
        assert len(result.equal) == len(result.entries)


class TestDiffEntry:
    """Tests for DiffEntry class."""

    def test_diff_entry_left_only(self):
        """Test DiffEntry for left-only key."""
        entry = DiffEntry(
            key="test.key",
            diff_type=DiffType.LEFT_ONLY,
            left_value="value",
            left_type="str"
        )

        assert entry.has_left is True
        assert entry.has_right is False
        assert "value" in entry.get_display_left()
        assert "not present" in entry.get_display_right().lower()

    def test_diff_entry_right_only(self):
        """Test DiffEntry for right-only key."""
        entry = DiffEntry(
            key="test.key",
            diff_type=DiffType.RIGHT_ONLY,
            right_value=123,
            right_type="int"
        )

        assert entry.has_left is False
        assert entry.has_right is True
        assert "not present" in entry.get_display_left().lower()
        assert "123" in entry.get_display_right()

    def test_diff_entry_different(self):
        """Test DiffEntry for different values."""
        entry = DiffEntry(
            key="test.key",
            diff_type=DiffType.DIFFERENT,
            left_value="left",
            right_value="right",
            left_type="str",
            right_type="str"
        )

        assert entry.has_left is True
        assert entry.has_right is True
        assert "left" in entry.get_display_left()
        assert "right" in entry.get_display_right()

    def test_diff_entry_null_value(self):
        """Test DiffEntry with null value."""
        entry = DiffEntry(
            key="test.key",
            diff_type=DiffType.DIFFERENT,
            left_value=None,
            right_value="value",
            left_type="NoneType",
            right_type="str"
        )

        assert "null" in entry.get_display_left().lower()

    def test_diff_entry_long_value_truncation(self):
        """Test that long values are truncated in display."""
        long_value = "x" * 200
        entry = DiffEntry(
            key="test.key",
            diff_type=DiffType.LEFT_ONLY,
            left_value=long_value,
            left_type="str"
        )

        display = entry.get_display_left()
        assert len(display) < len(long_value) + 10  # Some overhead for quotes/ellipsis
        assert "..." in display


class TestFiltering:
    """Tests for filtering functionality."""

    def test_filter_by_search_text_in_keys(self, comparator, left_profile, right_profile):
        """Test filtering by search text in keys."""
        result = comparator.compare(left_profile, right_profile)

        filtered = comparator.filter_entries(
            result,
            search_text="hostname",
            search_in_keys=True,
            search_in_values=False
        )

        assert len(filtered) > 0
        assert all("hostname" in e.key.lower() for e in filtered)

    def test_filter_by_search_text_in_values(self, comparator, left_profile, right_profile):
        """Test filtering by search text in values."""
        result = comparator.compare(left_profile, right_profile)

        filtered = comparator.filter_entries(
            result,
            search_text="citrix",
            search_in_keys=False,
            search_in_values=True
        )

        assert len(filtered) > 0

    def test_filter_case_insensitive(self, comparator, left_profile, right_profile):
        """Test that filtering is case-insensitive."""
        result = comparator.compare(left_profile, right_profile)

        filtered_lower = comparator.filter_entries(result, search_text="hostname")
        filtered_upper = comparator.filter_entries(result, search_text="HOSTNAME")
        filtered_mixed = comparator.filter_entries(result, search_text="HostName")

        assert len(filtered_lower) == len(filtered_upper) == len(filtered_mixed)

    def test_filter_by_diff_type(self, comparator, left_profile, right_profile):
        """Test filtering by diff type."""
        result = comparator.compare(left_profile, right_profile)

        # Only left-only
        filtered = comparator.filter_entries(
            result,
            show_left_only=True,
            show_right_only=False,
            show_equal=False,
            show_different=False
        )

        assert all(e.diff_type == DiffType.LEFT_ONLY for e in filtered)

    def test_filter_combined(self, comparator, left_profile, right_profile):
        """Test combining multiple filters."""
        result = comparator.compare(left_profile, right_profile)

        # Search for "system" in different entries only
        filtered = comparator.filter_entries(
            result,
            search_text="system",
            show_left_only=False,
            show_right_only=False,
            show_equal=False,
            show_different=True
        )

        assert all("system" in e.key.lower() for e in filtered)
        assert all(e.diff_type in (DiffType.DIFFERENT, DiffType.TYPE_MISMATCH) for e in filtered)

    def test_filter_no_results(self, comparator, left_profile, right_profile):
        """Test filtering with no matching results."""
        result = comparator.compare(left_profile, right_profile)

        filtered = comparator.filter_entries(
            result,
            search_text="nonexistent_key_xyz123"
        )

        assert len(filtered) == 0

    def test_filter_show_all(self, comparator, left_profile, right_profile):
        """Test showing all entries."""
        result = comparator.compare(left_profile, right_profile)

        filtered = comparator.filter_entries(
            result,
            show_left_only=True,
            show_right_only=True,
            show_equal=True,
            show_different=True
        )

        assert len(filtered) == len(result.entries)


class TestTreeStructure:
    """Tests for tree structure generation."""

    def test_get_tree_structure(self, comparator, left_profile, right_profile):
        """Test generating tree structure from entries."""
        result = comparator.compare(left_profile, right_profile)

        tree = comparator.get_tree_structure(result.entries)

        assert isinstance(tree, dict)
        assert len(tree) > 0
