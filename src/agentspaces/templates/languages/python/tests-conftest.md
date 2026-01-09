---
name: tests-conftest
description: Pytest configuration and shared fixtures.
category: python
variables:
  required: []
  optional: []
---
"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_data() -> dict[str, str]:
    """Provide sample test data."""
    return {"key": "value"}
