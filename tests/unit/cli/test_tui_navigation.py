"""Tests for TUI navigation logic."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agentspaces.cli.tui import (
    _build_navigation_commands,
    _get_tab_title,
)
from agentspaces.modules.workspace.service import WorkspaceInfo


@pytest.fixture
def mock_workspace(tmp_path: Path) -> WorkspaceInfo:
    """Create mock workspace with venv."""
    venv_path = tmp_path / ".venv" / "bin" / "activate"
    venv_path.parent.mkdir(parents=True)
    venv_path.touch()

    return WorkspaceInfo(
        name="test-workspace",
        path=tmp_path,
        branch="test-branch",
        base_branch="main",
        project="test-project",
        created_at=None,
        has_venv=True,
        python_version="3.13.0",
        purpose="agentspaces-abc",
    )


@pytest.fixture
def mock_workspace_no_venv(tmp_path: Path) -> WorkspaceInfo:
    """Create mock workspace without venv."""
    return WorkspaceInfo(
        name="test-workspace-no-venv",
        path=tmp_path,
        branch="test-branch",
        base_branch="main",
        project="test-project",
        created_at=None,
        has_venv=False,
        python_version=None,
        purpose=None,
    )


@pytest.fixture
def mock_workspace_no_purpose(tmp_path: Path) -> WorkspaceInfo:
    """Create mock workspace without purpose."""
    return WorkspaceInfo(
        name="my-workspace",
        path=tmp_path,
        branch="feature-branch",
        base_branch="main",
        project="test-project",
        created_at=None,
        has_venv=False,
        python_version=None,
        purpose=None,
    )


class TestGetTabTitle:
    """Tests for _get_tab_title function."""

    def test_returns_beads_title_when_available(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Returns beads issue title when available."""
        beads_response = [{"id": "agentspaces-abc", "title": "Fix the widget bug"}]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(beads_response),
            )
            title = _get_tab_title(mock_workspace)

        assert title == "Fix the widget bug"
        mock_run.assert_called_once()

    def test_truncates_long_beads_title(self, mock_workspace: WorkspaceInfo) -> None:
        """Truncates beads title to 30 characters."""
        beads_response = [
            {
                "id": "agentspaces-abc",
                "title": "This is a very long title that exceeds thirty characters",
            }
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(beads_response),
            )
            title = _get_tab_title(mock_workspace)

        assert len(title) == 30
        assert title == "This is a very long title that"

    def test_falls_back_to_workspace_name_on_beads_failure(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Falls back to workspace name when beads fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            title = _get_tab_title(mock_workspace)

        assert title == "test-workspace"

    def test_falls_back_to_workspace_name_on_timeout(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Falls back to workspace name when beads times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("bd", 5)
            title = _get_tab_title(mock_workspace)

        assert title == "test-workspace"

    def test_falls_back_to_workspace_name_on_json_error(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Falls back to workspace name when beads returns invalid JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="not json")
            title = _get_tab_title(mock_workspace)

        assert title == "test-workspace"

    def test_uses_workspace_name_when_no_purpose(
        self, mock_workspace_no_purpose: WorkspaceInfo
    ) -> None:
        """Uses workspace name when purpose is not set."""
        title = _get_tab_title(mock_workspace_no_purpose)
        assert title == "my-workspace"

    def test_uses_workspace_name_when_purpose_not_beads_id(
        self, tmp_path: Path
    ) -> None:
        """Uses workspace name when purpose doesn't look like beads ID."""
        workspace = WorkspaceInfo(
            name="my-workspace",
            path=tmp_path,
            branch="main",
            base_branch="main",
            project="test",
            created_at=None,
            has_venv=False,
            python_version=None,
            purpose="some random purpose text",
        )
        title = _get_tab_title(workspace)
        assert title == "my-workspace"


class TestBuildNavigationCommands:
    """Tests for _build_navigation_commands function."""

    def test_includes_cd_command(
        self, mock_workspace: WorkspaceInfo, tmp_path: Path
    ) -> None:
        """Includes cd to workspace path."""
        commands = _build_navigation_commands(mock_workspace, "Test Title")
        # shlex.quote only adds quotes when necessary, so check for path presence
        assert f"cd {tmp_path}" in commands or f"cd '{tmp_path}'" in commands

    def test_includes_tab_title_escape_sequence(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Includes OSC escape sequence for tab title."""
        commands = _build_navigation_commands(mock_workspace, "My Tab Title")
        # printf with %s format and shlex-quoted title
        assert "printf '\\033]1;%s\\a'" in commands
        assert "'My Tab Title'" in commands

    def test_escapes_quotes_in_tab_title(self, mock_workspace: WorkspaceInfo) -> None:
        """Escapes quotes in tab title using shlex.quote."""
        commands = _build_navigation_commands(mock_workspace, 'Title with "quotes"')
        # shlex.quote handles the escaping
        assert "printf '\\033]1;%s\\a'" in commands

    def test_includes_venv_activation_when_present(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Includes venv activation when workspace has venv."""
        commands = _build_navigation_commands(mock_workspace, "Title")
        assert "source" in commands
        assert ".venv/bin/activate" in commands

    def test_skips_venv_activation_when_not_present(
        self, mock_workspace_no_venv: WorkspaceInfo
    ) -> None:
        """Skips venv activation when workspace has no venv."""
        commands = _build_navigation_commands(mock_workspace_no_venv, "Title")
        assert ".venv" not in commands

    def test_includes_claude_with_plan_when_purpose_is_beads_id(
        self, mock_workspace: WorkspaceInfo
    ) -> None:
        """Includes claude with plan command when purpose is beads ID."""
        commands = _build_navigation_commands(mock_workspace, "Title")
        # Command uses shlex.quote for safety (no quotes needed for simple alphanumeric)
        assert "claude 'plan'" in commands
        assert "agentspaces-abc" in commands

    def test_includes_plain_claude_when_no_purpose(
        self, mock_workspace_no_purpose: WorkspaceInfo
    ) -> None:
        """Includes plain claude command when no purpose."""
        commands = _build_navigation_commands(mock_workspace_no_purpose, "Title")
        assert "claude" in commands
        assert "plan" not in commands

    def test_commands_joined_with_and(self, mock_workspace: WorkspaceInfo) -> None:
        """Commands are joined with && for sequential execution."""
        commands = _build_navigation_commands(mock_workspace, "Title")
        assert " && " in commands
        # Count number of && separators (should have at least 3 parts)
        parts = commands.split(" && ")
        assert len(parts) >= 3  # cd, printf, claude (and maybe source)
