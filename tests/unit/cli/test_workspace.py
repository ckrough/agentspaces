"""Tests for workspace CLI commands."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from agentspaces.cli.workspace import app
from agentspaces.infrastructure.paths import PathResolver
from agentspaces.modules.workspace.service import WorkspaceService

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


@pytest.fixture
def isolated_env(git_repo: Path, temp_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up an isolated environment for CLI tests.

    Changes to the git_repo directory and provides a service with
    a custom resolver pointing to temp_dir.
    """
    # Change to the git repo directory
    monkeypatch.chdir(git_repo)

    # Create a service with custom resolver
    resolver = PathResolver(base=temp_dir / ".agentspaces")
    service = WorkspaceService(resolver=resolver)

    # Patch the module-level service
    with patch("agentspaces.cli.workspace._service", service):
        yield {
            "git_repo": git_repo,
            "temp_dir": temp_dir,
            "resolver": resolver,
            "service": service,
        }


class TestWorkspaceCreateAttach:
    """Tests for workspace create --attach flag."""

    def test_attach_to_existing_branch(self, isolated_env: dict) -> None:
        """Should create workspace for existing branch with --attach."""
        git_repo = isolated_env["git_repo"]

        # Create a branch first
        subprocess.run(
            ["git", "branch", "feature-test"],
            cwd=git_repo,
            check=True,
        )

        result = runner.invoke(
            app,
            ["create", "feature-test", "--attach", "--no-venv"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "feature-test" in result.output

    @pytest.mark.usefixtures("isolated_env")
    def test_attach_to_nonexistent_branch_fails(self) -> None:
        """Should fail when attaching to non-existent branch."""
        result = runner.invoke(
            app,
            ["create", "nonexistent-branch", "--attach", "--no-venv"],
        )

        assert result.exit_code == 1
        assert "does not exist" in result.output.lower()

    def test_attach_with_slash_in_branch_name(self, isolated_env: dict) -> None:
        """Should sanitize branch names with slashes."""
        git_repo = isolated_env["git_repo"]

        # Create a branch with slash
        subprocess.run(
            ["git", "branch", "feature/auth"],
            cwd=git_repo,
            check=True,
        )

        result = runner.invoke(
            app,
            ["create", "feature/auth", "--attach", "--no-venv"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Workspace name should be sanitized (/ -> -)
        assert "feature-auth" in result.output

    def test_attach_short_flag(self, isolated_env: dict) -> None:
        """Should accept -a as short form of --attach."""
        git_repo = isolated_env["git_repo"]

        subprocess.run(
            ["git", "branch", "test-short-flag"],
            cwd=git_repo,
            check=True,
        )

        result = runner.invoke(
            app,
            ["create", "test-short-flag", "-a", "--no-venv"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "test-short-flag" in result.output


class TestWorkspaceCreateDefault:
    """Tests for workspace create without --attach (default behavior)."""

    @pytest.mark.usefixtures("isolated_env")
    def test_create_generates_workspace_name(self) -> None:
        """Should create workspace with generated name when not attaching."""
        result = runner.invoke(
            app,
            ["create", "--no-venv"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should show workspace created message
        assert "workspace" in result.output.lower()
