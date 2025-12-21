"""Agent launching service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import structlog

from agentspaces.infrastructure import claude
from agentspaces.infrastructure.paths import PathResolver
from agentspaces.modules.workspace.service import (
    WorkspaceService,
)

__all__ = [
    "AgentError",
    "AgentLauncher",
    "AgentNotFoundError",
    "LaunchResult",
]

logger = structlog.get_logger()


class AgentError(Exception):
    """Base exception for agent operations."""


class AgentNotFoundError(AgentError):
    """Raised when an agent is not installed."""


@dataclass(frozen=True)
class LaunchResult:
    """Result of launching an agent."""

    workspace_name: str
    workspace_path: Path
    exit_code: int


class AgentLauncher:
    """Service for launching agents in workspaces."""

    def __init__(
        self,
        workspace_service: WorkspaceService | None = None,
        resolver: PathResolver | None = None,
    ) -> None:
        """Initialize the agent launcher.

        Args:
            workspace_service: Workspace service instance.
            resolver: Path resolver for storage locations.
        """
        self._resolver = resolver or PathResolver()
        self._workspace_service = workspace_service or WorkspaceService(self._resolver)

    def launch_claude(
        self,
        workspace_name: str | None = None,
        *,
        cwd: Path | None = None,
        prompt: str | None = None,
    ) -> LaunchResult:
        """Launch Claude Code in a workspace.

        Args:
            workspace_name: Workspace to launch in. If None, detects from cwd.
            cwd: Current working directory (for detection and project context).
            prompt: Optional initial prompt (e.g., workspace purpose).

        Returns:
            LaunchResult with workspace details and exit code.

        Raises:
            AgentNotFoundError: If Claude Code is not installed.
            WorkspaceNotFoundError: If workspace doesn't exist.
            AgentError: If launch fails.
        """
        # Check Claude is installed first
        if not claude.is_claude_available():
            raise AgentNotFoundError(
                "Claude Code not found. Install from: https://claude.ai/download"
            )

        # Determine workspace
        if workspace_name is None:
            workspace_name = self.detect_workspace(cwd)
            if workspace_name is None:
                raise AgentError(
                    "No workspace specified and not in a workspace directory. "
                    "Use 'as agent launch <workspace-name>' or cd into a workspace."
                )

        # Get workspace info to validate it exists and get path
        workspace = self._workspace_service.get(workspace_name, cwd=cwd)

        logger.info(
            "agent_launch_start",
            agent="claude",
            workspace=workspace_name,
            path=str(workspace.path),
            has_prompt=prompt is not None,
        )

        try:
            exit_code = claude.launch(workspace.path, prompt=prompt)
        except claude.ClaudeNotFoundError as e:
            raise AgentNotFoundError(str(e)) from e
        except claude.ClaudeError as e:
            raise AgentError(f"Failed to launch Claude Code: {e}") from e

        logger.info(
            "agent_launch_complete",
            agent="claude",
            workspace=workspace_name,
            exit_code=exit_code,
        )

        return LaunchResult(
            workspace_name=workspace_name,
            workspace_path=workspace.path,
            exit_code=exit_code,
        )

    def detect_workspace(self, cwd: Path | None = None) -> str | None:
        """Detect if cwd is within a workspace.

        Checks if the path is under ~/.agentspaces/<project>/<workspace>/

        Args:
            cwd: Directory to check. Defaults to current working directory.

        Returns:
            Workspace name if in a workspace, None otherwise.
        """
        if cwd is None:
            cwd = Path.cwd()

        cwd = cwd.resolve()
        base = self._resolver.base.resolve()

        # Check if cwd is under the agentspaces base directory
        try:
            relative = cwd.relative_to(base)
        except ValueError:
            # Not under base directory
            return None

        # Path should be at least <project>/<workspace>/... (2 parts minimum)
        parts = relative.parts
        if len(parts) < 2:
            return None

        # The workspace name is the second component
        workspace_name = parts[1]

        # Verify it's actually a workspace (has .agentspace dir)
        project_name = parts[0]
        workspace_path = base / project_name / workspace_name
        if (workspace_path / ".agentspace").exists():
            return workspace_name

        return None
