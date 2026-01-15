"""Pytest configuration and fixtures."""

import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_left_ipm(fixtures_dir):
    """Return path to sample left IPM file."""
    return fixtures_dir / "sample_left.ipm"


@pytest.fixture
def sample_right_ipm(fixtures_dir):
    """Return path to sample right IPM file."""
    return fixtures_dir / "sample_right.ipm"


@pytest.fixture
def sample_empty_ipm(fixtures_dir):
    """Return path to empty IPM file."""
    return fixtures_dir / "sample_empty.ipm"


@pytest.fixture
def corrupted_ipm(fixtures_dir):
    """Return path to corrupted IPM file."""
    return fixtures_dir / "corrupted.ipm"


@pytest.fixture
def ipm_handler():
    """Return an IPMHandler instance."""
    from src.core.ipm_handler import IPMHandler
    handler = IPMHandler()
    yield handler
    handler.cleanup()


@pytest.fixture
def comparator():
    """Return a ProfileComparator instance."""
    from src.core.comparator import ProfileComparator
    return ProfileComparator()


@pytest.fixture
def migrator():
    """Return a ProfileMigrator instance."""
    from src.core.migrator import ProfileMigrator
    return ProfileMigrator()


@pytest.fixture
def left_profile(ipm_handler, sample_left_ipm):
    """Return loaded left profile."""
    return ipm_handler.load_profile(sample_left_ipm)


@pytest.fixture
def right_profile(ipm_handler, sample_right_ipm):
    """Return loaded right profile."""
    return ipm_handler.load_profile(sample_right_ipm)
