"""Minimal conftest for goal-centric unit tests.

These tests do not need a database, server, or the root conftest fixtures.
They test pure Python logic only.
"""

import pytest


# Enable asyncio mode for all tests in this directory
pytest_plugins = ("pytest_asyncio",)
