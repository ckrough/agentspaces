"""Tests for the paths module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentspaces.infrastructure.paths import (
    InvalidNameError,
    PathResolver,
    _validate_name,
)


class TestValidateName:
    """Tests for name validation security."""

    def test_valid_simple_name(self) -> None:
        """Simple alphanumeric names should be valid."""
        _validate_name("myproject", "project")  # Should not raise

    def test_valid_name_with_hyphens(self) -> None:
        """Names with hyphens should be valid."""
        _validate_name("my-project", "project")  # Should not raise

    def test_valid_name_with_underscores(self) -> None:
        """Names with underscores should be valid."""
        _validate_name("my_project", "project")  # Should not raise

    def test_valid_name_with_numbers(self) -> None:
        """Names with numbers should be valid."""
        _validate_name("project123", "project")  # Should not raise

    def test_valid_docker_style_name(self) -> None:
        """Docker-style adjective-noun names should be valid."""
        _validate_name("eager-turing", "workspace")  # Should not raise

    def test_invalid_empty_name(self) -> None:
        """Empty names should be rejected."""
        with pytest.raises(InvalidNameError, match="cannot be empty"):
            _validate_name("", "project")

    def test_invalid_too_long(self) -> None:
        """Names over 100 characters should be rejected."""
        long_name = "a" * 101
        with pytest.raises(InvalidNameError, match="too long"):
            _validate_name(long_name, "project")

    def test_invalid_path_traversal(self) -> None:
        """Path traversal attempts should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name("../etc", "project")

    def test_invalid_absolute_path(self) -> None:
        """Absolute paths should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name("/etc/passwd", "project")

    def test_invalid_path_separator(self) -> None:
        """Path separators should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name("foo/bar", "project")

    def test_invalid_starts_with_hyphen(self) -> None:
        """Names starting with hyphen should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name("-invalid", "project")

    def test_invalid_starts_with_underscore(self) -> None:
        """Names starting with underscore should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name("_invalid", "project")

    def test_invalid_special_characters(self) -> None:
        """Special characters should be rejected."""
        for char in [".", " ", "@", "!", "#", "$", "%"]:
            with pytest.raises(InvalidNameError):
                _validate_name(f"invalid{char}name", "project")

    def test_invalid_dot_only(self) -> None:
        """Single dot should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name(".", "project")

    def test_invalid_double_dot(self) -> None:
        """Double dot should be rejected."""
        with pytest.raises(InvalidNameError):
            _validate_name("..", "project")


class TestPathResolver:
    """Tests for PathResolver class."""

    @pytest.fixture
    def resolver(self, temp_dir: Path) -> PathResolver:
        """Create a PathResolver with temporary base directory."""
        return PathResolver(base=temp_dir / ".agentspaces")

    def test_default_base_is_home(self) -> None:
        """Default base should be ~/.agentspaces."""
        resolver = PathResolver()
        assert resolver.base == Path.home() / ".agentspaces"

    def test_custom_base(self, temp_dir: Path) -> None:
        """Should accept custom base directory."""
        custom_base = temp_dir / "custom"
        resolver = PathResolver(base=custom_base)
        assert resolver.base == custom_base

    def test_ensure_base_creates_directory(self, resolver: PathResolver) -> None:
        """ensure_base should create the base directory."""
        assert not resolver.base.exists()
        result = resolver.ensure_base()
        assert resolver.base.exists()
        assert result == resolver.base

    def test_global_config_path(self, resolver: PathResolver) -> None:
        """global_config should return path to config.json."""
        path = resolver.global_config()
        assert path == resolver.base / "config.json"

    def test_project_dir(self, resolver: PathResolver) -> None:
        """project_dir should return project directory path."""
        path = resolver.project_dir("my-project")
        assert path == resolver.base / "my-project"

    def test_workspace_dir(self, resolver: PathResolver) -> None:
        """workspace_dir should return workspace directory path."""
        path = resolver.workspace_dir("my-project", "eager-turing")
        assert path == resolver.base / "my-project" / "eager-turing"

    def test_metadata_dir(self, resolver: PathResolver) -> None:
        """metadata_dir should return .agentspace directory path."""
        path = resolver.metadata_dir("my-project", "eager-turing")
        expected = resolver.base / "my-project" / "eager-turing" / ".agentspace"
        assert path == expected

    def test_workspace_json(self, resolver: PathResolver) -> None:
        """workspace_json should return workspace.json path."""
        path = resolver.workspace_json("my-project", "eager-turing")
        expected = (
            resolver.base
            / "my-project"
            / "eager-turing"
            / ".agentspace"
            / "workspace.json"
        )
        assert path == expected

    def test_venv_dir(self, resolver: PathResolver) -> None:
        """venv_dir should return .venv directory path."""
        path = resolver.venv_dir("my-project", "eager-turing")
        expected = resolver.base / "my-project" / "eager-turing" / ".venv"
        assert path == expected

    def test_workspace_exists_false(self, resolver: PathResolver) -> None:
        """workspace_exists should return False for non-existent workspace."""
        assert not resolver.workspace_exists("my-project", "nonexistent")

    def test_workspace_exists_true(self, resolver: PathResolver) -> None:
        """workspace_exists should return True for existing workspace."""
        resolver.ensure_base()
        workspace_dir = resolver.workspace_dir("my-project", "eager-turing")
        workspace_dir.mkdir(parents=True)
        assert resolver.workspace_exists("my-project", "eager-turing")

    def test_list_workspaces_empty(self, resolver: PathResolver) -> None:
        """list_workspaces should return empty list for non-existent project."""
        assert resolver.list_workspaces("nonexistent") == []

    def test_list_workspaces(self, resolver: PathResolver) -> None:
        """list_workspaces should return workspace names with .agentspace dir."""
        resolver.ensure_base()

        # Create some workspaces with .agentspace directories
        for name in ["eager-turing", "bold-einstein"]:
            metadata_dir = resolver.metadata_dir("my-project", name)
            metadata_dir.mkdir(parents=True)

        # Create a directory without .agentspace (should be excluded)
        other_dir = resolver.workspace_dir("my-project", "not-a-workspace")
        other_dir.mkdir(parents=True)

        workspaces = resolver.list_workspaces("my-project")
        assert set(workspaces) == {"eager-turing", "bold-einstein"}

    def test_list_projects_empty(self, resolver: PathResolver) -> None:
        """list_projects should return empty list if base doesn't exist."""
        assert resolver.list_projects() == []

    def test_list_projects(self, resolver: PathResolver) -> None:
        """list_projects should return project directory names."""
        resolver.ensure_base()

        # Create project directories
        (resolver.base / "project-a").mkdir()
        (resolver.base / "project-b").mkdir()

        projects = resolver.list_projects()
        assert set(projects) == {"project-a", "project-b"}

    def test_project_dir_validates_name(self, resolver: PathResolver) -> None:
        """project_dir should reject invalid names."""
        with pytest.raises(InvalidNameError):
            resolver.project_dir("../escape")

    def test_workspace_dir_validates_project_name(self, resolver: PathResolver) -> None:
        """workspace_dir should reject invalid project names."""
        with pytest.raises(InvalidNameError):
            resolver.workspace_dir("../escape", "valid-name")

    def test_workspace_dir_validates_workspace_name(
        self, resolver: PathResolver
    ) -> None:
        """workspace_dir should reject invalid workspace names."""
        with pytest.raises(InvalidNameError):
            resolver.workspace_dir("valid-project", "../escape")
