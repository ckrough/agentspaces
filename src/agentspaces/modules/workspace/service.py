"""Workspace lifecycle management service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass

import structlog

from agentspaces.infrastructure import git
from agentspaces.infrastructure.paths import PathResolver
from agentspaces.modules.workspace import worktree

logger = structlog.get_logger()


@dataclass
class WorkspaceInfo:
    """Basic workspace information (Increment 1).

    This will be expanded to a full Workspace model in Increment 3.
    """

    name: str
    path: Path
    branch: str
    base_branch: str
    project: str


class WorkspaceError(Exception):
    """Base exception for workspace operations."""

    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a workspace is not found."""

    pass


class WorkspaceService:
    """Service for managing workspace lifecycle.

    Handles creation, listing, and removal of workspaces.
    Persistence and metadata will be added in Increment 3.
    """

    def __init__(self, resolver: PathResolver | None = None) -> None:
        """Initialize the workspace service.

        Args:
            resolver: Path resolver for storage locations.
        """
        self._resolver = resolver or PathResolver()

    def create(
        self,
        *,
        base_branch: str = "HEAD",
        purpose: str | None = None,
        cwd: Path | None = None,
    ) -> WorkspaceInfo:
        """Create a new workspace.

        Args:
            base_branch: Branch to create workspace from.
            purpose: Description of workspace purpose (stored in Increment 3).
            cwd: Current working directory.

        Returns:
            WorkspaceInfo with details.

        Raises:
            WorkspaceError: If creation fails.
        """
        try:
            repo_root, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        logger.info(
            "workspace_create_start",
            project=project,
            base_branch=base_branch,
            purpose=purpose,
        )

        try:
            result = worktree.create_worktree(
                project=project,
                base_branch=base_branch,
                repo_root=repo_root,
                resolver=self._resolver,
            )
        except git.GitError as e:
            logger.error("workspace_create_failed", error=e.stderr)
            raise WorkspaceError(f"Failed to create workspace: {e.stderr}") from e

        # Create .agentspace metadata directory
        metadata_dir = self._resolver.metadata_dir(project, result.name)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # TODO: Persist workspace metadata (Increment 3)
        # TODO: Create workspace-context skill (Increment 3)

        workspace = WorkspaceInfo(
            name=result.name,
            path=result.path,
            branch=result.branch,
            base_branch=result.base_branch,
            project=project,
        )

        logger.info(
            "workspace_created",
            name=workspace.name,
            path=str(workspace.path),
        )

        return workspace

    def list(self, *, cwd: Path | None = None) -> list[git.WorktreeInfo]:
        """List all workspaces for the current repository.

        Args:
            cwd: Current working directory.

        Returns:
            List of worktree information.

        Raises:
            WorkspaceError: If listing fails.
        """
        try:
            repo_root, _ = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        try:
            return worktree.list_worktrees(repo_root)
        except git.GitError as e:
            raise WorkspaceError(f"Failed to list workspaces: {e.stderr}") from e

    def remove(
        self,
        name: str,
        *,
        force: bool = False,
        cwd: Path | None = None,
    ) -> None:
        """Remove a workspace.

        Args:
            name: Workspace name.
            force: Force removal even if workspace is dirty.
            cwd: Current working directory.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceError: If removal fails.
        """
        try:
            repo_root, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        logger.info("workspace_remove_start", name=name, project=project, force=force)

        try:
            worktree.remove_worktree(
                project=project,
                name=name,
                repo_root=repo_root,
                force=force,
                resolver=self._resolver,
            )
        except FileNotFoundError as e:
            raise WorkspaceNotFoundError(str(e)) from e
        except git.GitError as e:
            if "dirty" in e.stderr.lower() or "modified" in e.stderr.lower():
                raise WorkspaceError(
                    "Workspace has uncommitted changes. Use --force to override."
                ) from e
            raise WorkspaceError(f"Failed to remove workspace: {e.stderr}") from e

        logger.info("workspace_removed", name=name)

    def get_project_name(self, cwd: Path | None = None) -> str:
        """Get the current project name.

        Args:
            cwd: Current working directory.

        Returns:
            Project name.

        Raises:
            WorkspaceError: If not in a git repository.
        """
        try:
            _, project = worktree.get_repo_info(cwd)
            return project
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e
