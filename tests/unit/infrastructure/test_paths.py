"""Tests for the paths module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentspaces.infrastructure.paths import PathResolver


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
            resolver.base / "my-project" / "eager-turing" / ".agentspace" / "workspace.json"
        )
        assert path == expected

    def test_skills_dir(self, resolver: PathResolver) -> None:
        """skills_dir should return skills directory path."""
        path = resolver.skills_dir("my-project", "eager-turing")
        expected = resolver.base / "my-project" / "eager-turing" / ".agentspace" / "skills"
        assert path == expected

    def test_workspace_context_skill(self, resolver: PathResolver) -> None:
        """workspace_context_skill should return skill directory path."""
        path = resolver.workspace_context_skill("my-project", "eager-turing")
        expected = (
            resolver.base
            / "my-project"
            / "eager-turing"
            / ".agentspace"
            / "skills"
            / "workspace-context"
        )
        assert path == expected

    def test_sessions_dir(self, resolver: PathResolver) -> None:
        """sessions_dir should return sessions directory path."""
        path = resolver.sessions_dir("my-project", "eager-turing")
        expected = (
            resolver.base / "my-project" / "eager-turing" / ".agentspace" / "sessions"
        )
        assert path == expected

    def test_session_dir(self, resolver: PathResolver) -> None:
        """session_dir should return specific session directory."""
        path = resolver.session_dir("my-project", "eager-turing", "abc123")
        expected = (
            resolver.base
            / "my-project"
            / "eager-turing"
            / ".agentspace"
            / "sessions"
            / "abc123"
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
