"""Migration Engine for IGEL Profile Compare & Migration Tool.

Handles migrating configuration values between IPM profiles.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pathlib import Path
import copy
import json

from src.core.ipm_handler import IPMProfile, IPMHandler, IPMValidationError
from src.core.comparator import DiffEntry, DiffType, ComparisonResult
from src.utils.logger import get_logger


class MigrationDirection(Enum):
    """Direction of migration."""
    LEFT_TO_RIGHT = auto()  # Copy values from left to right
    RIGHT_TO_LEFT = auto()  # Copy values from right to left


class MigrationMode(Enum):
    """Mode of migration."""
    ALL_DIFFERENT = auto()    # Migrate all differing keys
    SELECTED_ONLY = auto()    # Migrate only selected keys


@dataclass
class MigrationAction:
    """Represents a single migration action."""
    key: str
    source_value: Any
    target_value: Any  # Value before migration (for undo)
    action_type: str   # "add", "update", "type_change"

    def describe(self) -> str:
        """Get human-readable description of the action."""
        if self.action_type == "add":
            return f"Add key '{self.key}' with value: {self._format_value(self.source_value)}"
        elif self.action_type == "update":
            return f"Update '{self.key}': {self._format_value(self.target_value)} → {self._format_value(self.source_value)}"
        elif self.action_type == "type_change":
            return f"Type change '{self.key}': {type(self.target_value).__name__} → {type(self.source_value).__name__}"
        return f"Unknown action on '{self.key}'"

    def _format_value(self, value: Any) -> str:
        """Format value for display."""
        if value is None:
            return "null"
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:50]}..."'
            return f'"{value}"'
        if isinstance(value, (list, dict)):
            s = json.dumps(value, ensure_ascii=False)
            if len(s) > 50:
                return f"{s[:50]}..."
            return s
        return str(value)


@dataclass
class MigrationPlan:
    """Plan for migrating configurations."""
    direction: MigrationDirection
    source_profile: IPMProfile
    target_profile: IPMProfile
    actions: List[MigrationAction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_actions(self) -> int:
        """Get total number of actions."""
        return len(self.actions)

    @property
    def adds(self) -> List[MigrationAction]:
        """Get add actions."""
        return [a for a in self.actions if a.action_type == "add"]

    @property
    def updates(self) -> List[MigrationAction]:
        """Get update actions."""
        return [a for a in self.actions if a.action_type == "update"]

    @property
    def type_changes(self) -> List[MigrationAction]:
        """Get type change actions."""
        return [a for a in self.actions if a.action_type == "type_change"]

    def summary(self) -> Dict[str, int]:
        """Get summary of planned actions."""
        return {
            'total': self.total_actions,
            'adds': len(self.adds),
            'updates': len(self.updates),
            'type_changes': len(self.type_changes)
        }


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    plan: MigrationPlan
    backup_path: Optional[Path] = None
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)


class ProfileMigrator:
    """Handles migration of configurations between profiles."""

    def __init__(self):
        """Initialize the migrator."""
        self.logger = get_logger()
        self.ipm_handler = IPMHandler()

    def create_migration_plan(
        self,
        comparison: ComparisonResult,
        direction: MigrationDirection,
        selected_keys: Optional[Set[str]] = None,
        mode: MigrationMode = MigrationMode.ALL_DIFFERENT
    ) -> MigrationPlan:
        """Create a migration plan based on comparison results.

        Args:
            comparison: ComparisonResult from comparing profiles
            direction: Direction of migration
            selected_keys: Set of keys to migrate (for SELECTED_ONLY mode)
            mode: Migration mode

        Returns:
            MigrationPlan with all planned actions
        """
        self.logger.info(f"Creating migration plan: {direction.name}, mode: {mode.name}")

        if direction == MigrationDirection.LEFT_TO_RIGHT:
            source = comparison.left_profile
            target = comparison.right_profile
        else:
            source = comparison.right_profile
            target = comparison.left_profile

        plan = MigrationPlan(
            direction=direction,
            source_profile=source,
            target_profile=target
        )

        for entry in comparison.entries:
            # Skip if using selected mode and key not selected
            if mode == MigrationMode.SELECTED_ONLY:
                if selected_keys is None or entry.key not in selected_keys:
                    continue

            # Determine if this entry should be migrated
            action = self._create_action_for_entry(entry, direction)
            if action:
                plan.actions.append(action)

        self.logger.info(f"Migration plan created: {plan.summary()}")
        return plan

    def _create_action_for_entry(
        self,
        entry: DiffEntry,
        direction: MigrationDirection
    ) -> Optional[MigrationAction]:
        """Create a migration action for a diff entry.

        Args:
            entry: DiffEntry to process
            direction: Migration direction

        Returns:
            MigrationAction or None if no action needed
        """
        if direction == MigrationDirection.LEFT_TO_RIGHT:
            source_value = entry.left_value
            target_value = entry.right_value
            source_exists = entry.has_left
            target_exists = entry.has_right
        else:
            source_value = entry.right_value
            target_value = entry.left_value
            source_exists = entry.has_right
            target_exists = entry.has_left

        # Skip if source doesn't have the value
        if not source_exists:
            return None

        # Skip if values are equal
        if entry.diff_type == DiffType.EQUAL:
            return None

        # Determine action type
        if not target_exists:
            action_type = "add"
        elif entry.diff_type == DiffType.TYPE_MISMATCH:
            action_type = "type_change"
        else:
            action_type = "update"

        return MigrationAction(
            key=entry.key,
            source_value=source_value,
            target_value=target_value,
            action_type=action_type
        )

    def execute_migration(
        self,
        plan: MigrationPlan,
        output_path: Optional[Path] = None,
        create_backup: bool = True
    ) -> MigrationResult:
        """Execute a migration plan.

        Args:
            plan: MigrationPlan to execute
            output_path: Path for output file (None = overwrite target)
            create_backup: Whether to create a backup before modifying

        Returns:
            MigrationResult with execution details
        """
        self.logger.info(f"Executing migration plan with {plan.total_actions} actions")

        backup_path = None
        target_path = plan.target_profile.file_path

        if output_path is None:
            output_path = target_path

        try:
            # Create backup if requested
            if create_backup:
                backup_path = self.ipm_handler.create_backup(target_path)
                self.logger.info(f"Backup created: {backup_path}")

            # Create a deep copy of the target profile for modification
            modified_profile = self._clone_profile(plan.target_profile)

            # Apply all migration actions
            for action in plan.actions:
                self._apply_action(modified_profile, action)

            # Rebuild the flattened config from JSON configs
            modified_profile.flattened_config = self.ipm_handler._flatten_all_configs(
                modified_profile.json_configs
            )

            # Save the modified profile
            self.ipm_handler.save_profile(modified_profile, output_path)

            self.logger.info(f"Migration completed successfully: {output_path}")

            return MigrationResult(
                success=True,
                plan=plan,
                backup_path=backup_path,
                output_path=output_path
            )

        except Exception as e:
            self.logger.exception(f"Migration failed: {e}")
            return MigrationResult(
                success=False,
                plan=plan,
                backup_path=backup_path,
                error_message=str(e)
            )

    def _clone_profile(self, profile: IPMProfile) -> IPMProfile:
        """Create a deep copy of a profile."""
        cloned = IPMProfile(
            file_path=profile.file_path,
            files=copy.deepcopy(profile.files),
            json_configs=copy.deepcopy(profile.json_configs),
            flattened_config=copy.deepcopy(profile.flattened_config),
            is_valid=profile.is_valid,
            load_timestamp=profile.load_timestamp
        )
        return cloned

    def _apply_action(self, profile: IPMProfile, action: MigrationAction) -> None:
        """Apply a single migration action to a profile.

        Args:
            profile: Profile to modify
            action: Action to apply
        """
        self.logger.debug(f"Applying action: {action.describe()}")

        # Parse the key to find the JSON file and path within it
        key_parts = action.key.split('.')

        # Find which JSON file this key belongs to
        for json_file, config in profile.json_configs.items():
            file_prefix = json_file.replace('.json', '').replace('/', '.').replace('\\', '.')

            if action.key.startswith(file_prefix + '.'):
                # This key belongs to this JSON file
                relative_key = action.key[len(file_prefix) + 1:]
                self._set_nested_value(config, relative_key, action.source_value)
                return
            elif action.key.startswith(file_prefix + '['):
                # Array access at root level
                relative_key = action.key[len(file_prefix):]
                self._set_nested_value(config, relative_key, action.source_value)
                return

        # If we get here, we need to determine which file to add to
        # For now, log a warning
        self.logger.warning(f"Could not find target JSON file for key: {action.key}")

    def _set_nested_value(self, obj: Any, key_path: str, value: Any) -> None:
        """Set a value in a nested structure using a dot-notation path.

        Args:
            obj: Object to modify (dict or list)
            key_path: Path like "config.items[0].name"
            value: Value to set
        """
        import re

        # Parse the key path into components
        parts = []
        remaining = key_path

        while remaining:
            # Check for array index
            if remaining.startswith('['):
                match = re.match(r'\[(\d+)\]', remaining)
                if match:
                    parts.append(int(match.group(1)))
                    remaining = remaining[match.end():]
                    if remaining.startswith('.'):
                        remaining = remaining[1:]
                    continue

            # Find next separator
            dot_pos = remaining.find('.')
            bracket_pos = remaining.find('[')

            if dot_pos == -1 and bracket_pos == -1:
                parts.append(remaining)
                break
            elif dot_pos == -1:
                parts.append(remaining[:bracket_pos])
                remaining = remaining[bracket_pos:]
            elif bracket_pos == -1:
                parts.append(remaining[:dot_pos])
                remaining = remaining[dot_pos + 1:]
            elif dot_pos < bracket_pos:
                parts.append(remaining[:dot_pos])
                remaining = remaining[dot_pos + 1:]
            else:
                parts.append(remaining[:bracket_pos])
                remaining = remaining[bracket_pos:]

        # Navigate to the parent and set the value
        current = obj
        for i, part in enumerate(parts[:-1]):
            next_part = parts[i + 1]

            if isinstance(part, int):
                # Extend list if needed
                while len(current) <= part:
                    current.append(None)
                if current[part] is None:
                    current[part] = [] if isinstance(next_part, int) else {}
                current = current[part]
            else:
                if part not in current:
                    current[part] = [] if isinstance(next_part, int) else {}
                current = current[part]

        # Set the final value
        final_part = parts[-1]
        if isinstance(final_part, int):
            while len(current) <= final_part:
                current.append(None)
            current[final_part] = value
        else:
            current[final_part] = value

    def restore_from_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore a profile from backup.

        Args:
            backup_path: Path to backup file
            target_path: Path to restore to

        Returns:
            True if successful
        """
        try:
            self.ipm_handler.restore_backup(backup_path, target_path)
            self.logger.info(f"Restored from backup: {backup_path} -> {target_path}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to restore from backup: {e}")
            return False
