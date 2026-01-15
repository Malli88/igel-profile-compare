"""Core modules for IGEL Profile Compare & Migration Tool."""

from src.core.ipm_handler import IPMHandler, IPMProfile, IPMValidationError, IPMFileInfo
from src.core.comparator import ProfileComparator, ComparisonResult, DiffEntry, DiffType
from src.core.migrator import (
    ProfileMigrator, MigrationDirection, MigrationMode,
    MigrationPlan, MigrationResult, MigrationAction
)

__all__ = [
    "IPMHandler", "IPMProfile", "IPMValidationError", "IPMFileInfo",
    "ProfileComparator", "ComparisonResult", "DiffEntry", "DiffType",
    "ProfileMigrator", "MigrationDirection", "MigrationMode",
    "MigrationPlan", "MigrationResult", "MigrationAction"
]
