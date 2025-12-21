"""Tests for the agent launcher service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentspaces.infrastructure.paths import PathResolver
from agentspaces.modules.agent.launcher import (
    AgentError,
    AgentLauncher,
    AgentNotFoundError,
    LaunchResult,
)
from agentspaces.modules.workspace.service import (
    WorkspaceInfo,
    WorkspaceNotFoundError,
    WorkspaceService,
)


class TestLaunchResult:
    """Tests for LaunchResult dataclass."""

    def test_launch_result_attributes(self) -> None:
        """LaunchResult should store all attributes."""
        result = LaunchResult(
            workspace_name="test-workspace",
            workspace_path=Path("/path/to/workspace"),
            exit_code=0,
        )

        assert result.workspace_name == "test-workspace"
        assert result.workspace_path == Path("/path/to/workspace")
        assert result.exit_code == 0

    def test_launch_result_is_frozen(self) -> None:
        """LaunchResult should be immutable."""
        result = LaunchResult(
            workspace_name="test",
            workspace_path=Path("/test"),
            exit_code=0,
        )

        with pytest.raises(AttributeError):
            result.exit_code = 1  # type: ignore[misc]


class TestAgentExceptions:
    """Tests for agent exception classes."""

    def test_agent_error_message(self) -> None:
        """AgentError should store message."""
        error = AgentError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_agent_not_found_error(self) -> None:
        """AgentNotFoundError should be an AgentError."""
        error = AgentNotFoundError("Claude not found")
        assert str(error) == "Claude not found"
        assert isinstance(error, AgentError)


class TestAgentLauncherInit:
    """Tests for AgentLauncher initialization."""

    def test_init_with_defaults(self) -> None:
        """Should initialize with default services."""
        launcher = AgentLauncher()

        assert launcher._resolver is not None
        assert launcher._workspace_service is not None

    def test_init_with_custom_resolver(self, temp_dir: Path) -> None:
        """Should accept custom resolver."""
        resolver = PathResolver(base=temp_dir)
        launcher = AgentLauncher(resolver=resolver)

        assert launcher._resolver == resolver


class TestAgentLauncherLaunchClaude:
    """Tests for AgentLauncher.launch_claude method."""

    def test_launch_claude_success(self, temp_dir: Path) -> None:
        """Should launch Claude in workspace and return result."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create mock workspace service
        mock_service = MagicMock(spec=WorkspaceService)
        mock_service.get.return_value = WorkspaceInfo(
            name="test-workspace",
            path=temp_dir / "test-workspace",
            branch="test-workspace",
            base_branch="main",
            project="test-project",
        )

        launcher = AgentLauncher(workspace_service=mock_service, resolver=resolver)

        with (
            patch(
                "agentspaces.modules.agent.launcher.claude.is_claude_available"
            ) as mock_available,
            patch("agentspaces.modules.agent.launcher.claude.launch") as mock_launch,
        ):
            mock_available.return_value = True
            mock_launch.return_value = 0

            result = launcher.launch_claude("test-workspace")

            assert result.workspace_name == "test-workspace"
            assert result.exit_code == 0
            mock_launch.assert_called_once_with(
                temp_dir / "test-workspace",
                prompt=None,
            )

    def test_launch_claude_with_prompt(self, temp_dir: Path) -> None:
        """Should pass prompt to Claude."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        mock_service = MagicMock(spec=WorkspaceService)
        mock_service.get.return_value = WorkspaceInfo(
            name="test-workspace",
            path=temp_dir / "test-workspace",
            branch="test-workspace",
            base_branch="main",
            project="test-project",
        )

        launcher = AgentLauncher(workspace_service=mock_service, resolver=resolver)

        with (
            patch(
                "agentspaces.modules.agent.launcher.claude.is_claude_available"
            ) as mock_available,
            patch("agentspaces.modules.agent.launcher.claude.launch") as mock_launch,
        ):
            mock_available.return_value = True
            mock_launch.return_value = 0

            launcher.launch_claude("test-workspace", prompt="Fix the bug")

            mock_launch.assert_called_once_with(
                temp_dir / "test-workspace",
                prompt="Fix the bug",
            )

    def test_launch_claude_not_installed(self, temp_dir: Path) -> None:
        """Should raise AgentNotFoundError when Claude not installed."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        with patch(
            "agentspaces.modules.agent.launcher.claude.is_claude_available"
        ) as mock_available:
            mock_available.return_value = False

            with pytest.raises(AgentNotFoundError) as exc_info:
                launcher.launch_claude("test-workspace")

            assert "Claude Code not found" in str(exc_info.value)

    def test_launch_claude_workspace_not_found(self, temp_dir: Path) -> None:
        """Should raise WorkspaceNotFoundError for missing workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        mock_service = MagicMock(spec=WorkspaceService)
        mock_service.get.side_effect = WorkspaceNotFoundError("Not found")

        launcher = AgentLauncher(workspace_service=mock_service, resolver=resolver)

        with patch(
            "agentspaces.modules.agent.launcher.claude.is_claude_available"
        ) as mock_available:
            mock_available.return_value = True

            with pytest.raises(WorkspaceNotFoundError):
                launcher.launch_claude("missing-workspace")

    def test_launch_claude_no_workspace_no_detection(self, temp_dir: Path) -> None:
        """Should raise AgentError when no workspace specified and not in workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        with patch(
            "agentspaces.modules.agent.launcher.claude.is_claude_available"
        ) as mock_available:
            mock_available.return_value = True

            with pytest.raises(AgentError) as exc_info:
                # cwd is temp_dir which is not a workspace
                launcher.launch_claude(cwd=temp_dir)

            assert "No workspace specified" in str(exc_info.value)


class TestAgentLauncherDetectWorkspace:
    """Tests for AgentLauncher.detect_workspace method."""

    def test_detect_workspace_when_in_workspace(self, temp_dir: Path) -> None:
        """Should detect workspace name when inside workspace directory."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        # Create workspace structure
        workspace_path = temp_dir / ".agentspaces" / "test-project" / "test-workspace"
        workspace_path.mkdir(parents=True)
        (workspace_path / ".agentspace").mkdir()

        result = launcher.detect_workspace(cwd=workspace_path)

        assert result == "test-workspace"

    def test_detect_workspace_when_in_subdirectory(self, temp_dir: Path) -> None:
        """Should detect workspace when in a subdirectory of workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        # Create workspace structure with subdirectory
        workspace_path = temp_dir / ".agentspaces" / "test-project" / "test-workspace"
        workspace_path.mkdir(parents=True)
        (workspace_path / ".agentspace").mkdir()
        subdir = workspace_path / "src" / "components"
        subdir.mkdir(parents=True)

        result = launcher.detect_workspace(cwd=subdir)

        assert result == "test-workspace"

    def test_detect_workspace_when_outside(self, temp_dir: Path) -> None:
        """Should return None when not in a workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        result = launcher.detect_workspace(cwd=temp_dir)

        assert result is None

    def test_detect_workspace_in_base_but_not_workspace(self, temp_dir: Path) -> None:
        """Should return None when in base dir but not a workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        # Create project dir but not a workspace (no .agentspace)
        project_path = temp_dir / ".agentspaces" / "test-project"
        project_path.mkdir(parents=True)

        result = launcher.detect_workspace(cwd=project_path)

        assert result is None

    def test_detect_workspace_directory_without_marker(self, temp_dir: Path) -> None:
        """Should return None when directory exists but lacks .agentspace marker."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        launcher = AgentLauncher(resolver=resolver)

        # Create directory structure but no .agentspace marker
        workspace_path = temp_dir / ".agentspaces" / "test-project" / "test-workspace"
        workspace_path.mkdir(parents=True)
        # Note: NOT creating .agentspace

        result = launcher.detect_workspace(cwd=workspace_path)

        assert result is None
