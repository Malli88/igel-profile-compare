"""Tests for Profile Migrator module."""

import pytest
import shutil
from pathlib import Path

from src.core.comparator import ProfileComparator, DiffType
from src.core.migrator import (
    ProfileMigrator, MigrationDirection, MigrationMode,
    MigrationPlan, MigrationResult, MigrationAction
)


class TestMigrationPlanning:
    """Tests for migration planning functionality."""

    @pytest.fixture
    def comparison_result(self, comparator, left_profile, right_profile):
        """Get comparison result for testing."""
        return comparator.compare(left_profile, right_profile)

    def test_create_migration_plan_left_to_right(self, migrator, comparison_result):
        """Test creating migration plan from left to right."""
        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT
        )

        assert plan is not None
        assert isinstance(plan, MigrationPlan)
        assert plan.direction == MigrationDirection.LEFT_TO_RIGHT
        assert plan.source_profile == comparison_result.left_profile
        assert plan.target_profile == comparison_result.right_profile

    def test_create_migration_plan_right_to_left(self, migrator, comparison_result):
        """Test creating migration plan from right to left."""
        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.RIGHT_TO_LEFT
        )

        assert plan.direction == MigrationDirection.RIGHT_TO_LEFT
        assert plan.source_profile == comparison_result.right_profile
        assert plan.target_profile == comparison_result.left_profile

    def test_migration_plan_all_different(self, migrator, comparison_result):
        """Test migration plan includes all different keys."""
        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            mode=MigrationMode.ALL_DIFFERENT
        )

        # Should have actions for all non-equal entries where source has value
        assert plan.total_actions > 0

    def test_migration_plan_selected_only(self, migrator, comparison_result):
        """Test migration plan with selected keys only."""
        # Get a specific key to migrate
        different_entries = comparison_result.different
        if different_entries:
            selected_key = different_entries[0].key

            plan = migrator.create_migration_plan(
                comparison_result,
                MigrationDirection.LEFT_TO_RIGHT,
                selected_keys={selected_key},
                mode=MigrationMode.SELECTED_ONLY
            )

            assert plan.total_actions == 1
            assert plan.actions[0].key == selected_key

    def test_migration_plan_empty_selection(self, migrator, comparison_result):
        """Test migration plan with empty selection."""
        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=set(),
            mode=MigrationMode.SELECTED_ONLY
        )

        assert plan.total_actions == 0

    def test_migration_plan_summary(self, migrator, comparison_result):
        """Test migration plan summary."""
        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT
        )

        summary = plan.summary()

        assert "total" in summary
        assert "adds" in summary
        assert "updates" in summary
        assert "type_changes" in summary
        assert summary["total"] == summary["adds"] + summary["updates"] + summary["type_changes"]


class TestMigrationAction:
    """Tests for MigrationAction class."""

    def test_action_add(self):
        """Test add action description."""
        action = MigrationAction(
            key="new.key",
            source_value="new_value",
            target_value=None,
            action_type="add"
        )

        desc = action.describe()
        assert "add" in desc.lower()
        assert "new.key" in desc

    def test_action_update(self):
        """Test update action description."""
        action = MigrationAction(
            key="existing.key",
            source_value="new_value",
            target_value="old_value",
            action_type="update"
        )

        desc = action.describe()
        assert "update" in desc.lower()
        assert "existing.key" in desc

    def test_action_type_change(self):
        """Test type change action description."""
        action = MigrationAction(
            key="typed.key",
            source_value="string_value",
            target_value=123,
            action_type="type_change"
        )

        desc = action.describe()
        assert "type" in desc.lower()


class TestMigrationExecution:
    """Tests for migration execution."""

    @pytest.fixture
    def comparison_result(self, comparator, left_profile, right_profile):
        """Get comparison result for testing."""
        return comparator.compare(left_profile, right_profile)

    def test_execute_migration(self, migrator, comparison_result, tmp_path):
        """Test executing a migration."""
        # Select a few keys to migrate
        different = comparison_result.different[:3] if len(comparison_result.different) >= 3 else comparison_result.different
        selected_keys = {e.key for e in different}

        if not selected_keys:
            pytest.skip("No different keys to migrate")

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path, create_backup=True)

        assert result.success is True
        assert result.output_path == output_path
        assert output_path.exists()

    def test_execute_migration_creates_backup(self, migrator, comparison_result, tmp_path):
        """Test that migration creates backup."""
        different = comparison_result.different[:1] if comparison_result.different else []
        selected_keys = {e.key for e in different}

        if not selected_keys:
            pytest.skip("No different keys to migrate")

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path, create_backup=True)

        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_execute_migration_no_backup(self, migrator, comparison_result, tmp_path):
        """Test migration without backup."""
        different = comparison_result.different[:1] if comparison_result.different else []
        selected_keys = {e.key for e in different}

        if not selected_keys:
            pytest.skip("No different keys to migrate")

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path, create_backup=False)

        assert result.success is True
        assert result.backup_path is None

    def test_migrated_file_is_valid(self, migrator, ipm_handler, comparison_result, tmp_path):
        """Test that migrated file is a valid IPM."""
        different = comparison_result.different[:2] if len(comparison_result.different) >= 2 else comparison_result.different
        selected_keys = {e.key for e in different}

        if not selected_keys:
            pytest.skip("No different keys to migrate")

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path)

        # Verify the output is a valid IPM
        reloaded = ipm_handler.load_profile(output_path)
        assert reloaded.is_valid is True

    def test_migration_applies_changes(self, migrator, ipm_handler, comparator, comparison_result, tmp_path):
        """Test that migration actually applies the changes."""
        # Find a key with different values
        different = [e for e in comparison_result.different if e.left_value is not None]
        if not different:
            pytest.skip("No suitable keys to test")

        test_entry = different[0]
        selected_keys = {test_entry.key}

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path)

        # Reload and compare
        migrated_profile = ipm_handler.load_profile(output_path)
        new_comparison = comparator.compare(comparison_result.left_profile, migrated_profile)

        # The migrated key should now be equal
        migrated_entry = next((e for e in new_comparison.entries if e.key == test_entry.key), None)
        if migrated_entry:
            # Value should now match the source (left)
            assert migrated_entry.diff_type == DiffType.EQUAL or migrated_entry.left_value == migrated_entry.right_value


class TestBackupRestore:
    """Tests for backup and restore functionality."""

    def test_restore_from_backup(self, migrator, comparison_result, tmp_path):
        """Test restoring from backup after migration."""
        different = comparison_result.different[:1] if comparison_result.different else []
        selected_keys = {e.key for e in different}

        if not selected_keys:
            pytest.skip("No different keys to migrate")

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path, create_backup=True)

        # Restore from backup
        restore_path = tmp_path / "restored.ipm"
        success = migrator.restore_from_backup(result.backup_path, restore_path)

        assert success is True
        assert restore_path.exists()


class TestEdgeCases:
    """Tests for edge cases in migration."""

    @pytest.fixture
    def comparison_result(self, comparator, left_profile, right_profile):
        return comparator.compare(left_profile, right_profile)

    def test_migrate_empty_plan(self, migrator, comparison_result, tmp_path):
        """Test executing an empty migration plan."""
        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=set(),
            mode=MigrationMode.SELECTED_ONLY
        )

        assert plan.total_actions == 0

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path)

        # Should still succeed, just no changes
        assert result.success is True

    def test_migrate_left_only_keys(self, migrator, comparison_result, tmp_path):
        """Test migrating keys that only exist in source."""
        left_only = comparison_result.left_only[:2] if len(comparison_result.left_only) >= 2 else comparison_result.left_only
        selected_keys = {e.key for e in left_only}

        if not selected_keys:
            pytest.skip("No left-only keys to migrate")

        plan = migrator.create_migration_plan(
            comparison_result,
            MigrationDirection.LEFT_TO_RIGHT,
            selected_keys=selected_keys,
            mode=MigrationMode.SELECTED_ONLY
        )

        # All actions should be "add" type
        assert all(a.action_type == "add" for a in plan.actions)

        output_path = tmp_path / "migrated.ipm"
        result = migrator.execute_migration(plan, output_path)

        assert result.success is True
