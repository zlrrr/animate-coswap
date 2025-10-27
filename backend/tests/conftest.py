"""
Pytest configuration and fixtures
"""

import pytest
import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="class")
def test_fixtures_dir():
    """Return path to test fixtures directory"""
    return os.path.join(os.path.dirname(__file__), '..', '..', 'tests', 'fixtures')


@pytest.fixture(scope="class")
def models_dir():
    """Return path to models directory"""
    return os.path.join(os.path.dirname(__file__), '..', 'models')
