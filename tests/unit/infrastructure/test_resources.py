"""Tests for the package resource access module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from agentspaces.infrastructure.resources import (
    ResourceError,
    get_skeleton_templates_dir,
    get_skills_templates_dir,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestGetSkeletonTemplatesDir:
    """Tests for get_skeleton_templates_dir function."""

    def test_returns_skeleton_directory(self) -> None:
        """Should return path to skeleton templates directory."""
        result = get_skeleton_templates_dir()

        assert result.exists()
        assert result.name == "skeleton"
        assert result.is_dir()

    def test_skeleton_contains_expected_templates(self) -> None:
        """Should contain expected template files."""
        result = get_skeleton_templates_dir()

        # Check for key template files
        assert (result / "CLAUDE.md").exists()
        assert (result / "TODO.md").exists()
        assert (result / "README.md").exists()

    def test_raises_error_when_skeleton_missing(self, tmp_path: Path) -> None:
        """Should raise ResourceError when skeleton directory doesn't exist."""
        # Create a mock templates directory without skeleton
        mock_templates = tmp_path / "templates"
        mock_templates.mkdir()

        with patch(
            "agentspaces.infrastructure.resources._get_templates_dir",
            return_value=mock_templates,
        ):
            with pytest.raises(ResourceError) as exc_info:
                get_skeleton_templates_dir()

            assert "Skeleton templates directory not found" in str(exc_info.value)


class TestGetSkillsTemplatesDir:
    """Tests for get_skills_templates_dir function."""

    def test_returns_skills_directory(self) -> None:
        """Should return path to skills templates directory."""
        result = get_skills_templates_dir()

        assert result.exists()
        assert result.name == "skills"
        assert result.is_dir()

    def test_skills_contains_expected_templates(self) -> None:
        """Should contain expected skill templates."""
        result = get_skills_templates_dir()

        # Check for workspace-context skill
        workspace_context = result / "workspace-context"
        assert workspace_context.exists()
        assert (workspace_context / "SKILL.md").exists()

    def test_raises_error_when_skills_missing(self, tmp_path: Path) -> None:
        """Should raise ResourceError when skills directory doesn't exist."""
        # Create a mock templates directory without skills
        mock_templates = tmp_path / "templates"
        mock_templates.mkdir()

        with patch(
            "agentspaces.infrastructure.resources._get_templates_dir",
            return_value=mock_templates,
        ):
            with pytest.raises(ResourceError) as exc_info:
                get_skills_templates_dir()

            assert "Skills templates directory not found" in str(exc_info.value)


class TestGetTemplatesDir:
    """Tests for _get_templates_dir internal function."""

    def test_raises_error_on_module_not_found(self) -> None:
        """Should raise ResourceError when package module not found."""
        with patch(
            "agentspaces.infrastructure.resources.files",
            side_effect=ModuleNotFoundError("No module named 'agentspaces.templates'"),
        ):
            with pytest.raises(ResourceError) as exc_info:
                get_skeleton_templates_dir()

            assert "Cannot access package templates" in str(exc_info.value)
            assert "installed correctly" in str(exc_info.value)

    def test_raises_error_on_type_error(self) -> None:
        """Should raise ResourceError when files() returns unconvertible type."""

        class BadTraversable:
            """Mock that raises TypeError when converted to string."""

            def __str__(self) -> str:
                raise TypeError("Cannot convert to string")

        with patch(
            "agentspaces.infrastructure.resources.files",
            return_value=BadTraversable(),
        ):
            with pytest.raises(ResourceError) as exc_info:
                get_skeleton_templates_dir()

            assert "Cannot resolve templates path" in str(exc_info.value)

    def test_raises_error_when_templates_dir_missing(self, tmp_path: Path) -> None:
        """Should raise ResourceError when templates directory doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent"

        class FakeTraversable:
            """Mock that returns a nonexistent path."""

            def __init__(self, path: Path) -> None:
                self._path = path

            def __str__(self) -> str:
                return str(self._path)

        with patch(
            "agentspaces.infrastructure.resources.files",
            return_value=FakeTraversable(nonexistent_path),
        ):
            with pytest.raises(ResourceError) as exc_info:
                get_skeleton_templates_dir()

            assert "Templates directory not found at package location" in str(
                exc_info.value
            )


class TestResourceError:
    """Tests for ResourceError exception."""

    def test_error_message(self) -> None:
        """Should store and display error message."""
        error = ResourceError("Test error message")

        assert str(error) == "Test error message"

    def test_is_exception(self) -> None:
        """Should be a proper Exception subclass."""
        error = ResourceError("Test")

        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """Should be raisable and catchable."""
        with pytest.raises(ResourceError):
            raise ResourceError("Test error")
