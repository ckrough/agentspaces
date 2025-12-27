"""Workspace lifecycle management service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass

import structlog

from agentspaces.infrastructure import git
from agentspaces.infrastructure.metadata import (
    WorkspaceMetadata,
    load_workspace_metadata,
    save_workspace_metadata,
)
from agentspaces.infrastructure.paths import InvalidNameError, PathResolver
from agentspaces.modules.workspace import environment, worktree

__all__ = [
    "WorkspaceError",
    "WorkspaceInfo",
    "WorkspaceNotFoundError",
    "WorkspaceService",
]

logger = structlog.get_logger()


@dataclass(frozen=True)
class WorkspaceInfo:
    """Immutable workspace information.

    Combines git worktree data with persisted metadata.
    """

    name: str
    path: Path
    branch: str
    base_branch: str
    project: str
    created_at: datetime | None = None
    purpose: str | None = None
    python_version: str | None = None
    has_venv: bool = False
    status: str = "active"
    deps_synced_at: datetime | None = None
    last_activity_at: datetime | None = None


class WorkspaceError(Exception):
    """Base exception for workspace operations."""

    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a workspace is not found."""

    pass


class WorkspaceService:
    """Service for managing workspace lifecycle.

    Handles creation, listing, and removal of workspaces.
    Persists workspace metadata to JSON files.
    """

    def __init__(self, resolver: PathResolver | None = None) -> None:
        """Initialize the workspace service.

        Args:
            resolver: Path resolver for storage locations.
        """
        self._resolver = resolver or PathResolver()

    def get_workspace_path(self, project: str, workspace: str) -> Path:
        """Get the path to a workspace directory.

        Args:
            project: Project name.
            workspace: Workspace name.

        Returns:
            Path to the workspace directory.
        """
        return self._resolver.workspace_dir(project, workspace)

    def create(
        self,
        *,
        base_branch: str = "HEAD",
        attach_branch: str | None = None,
        purpose: str | None = None,
        python_version: str | None = None,
        setup_venv: bool = True,
        cwd: Path | None = None,
    ) -> WorkspaceInfo:
        """Create a new workspace.

        Creates a git worktree, sets up the Python environment,
        and persists workspace metadata.

        Args:
            base_branch: Branch to create workspace from (ignored if attach_branch set).
            attach_branch: Existing branch to attach to. When set, no new branch is
                created and the workspace name matches the branch name.
            purpose: Description of workspace purpose.
            python_version: Python version for venv (auto-detected if not specified).
            setup_venv: Whether to create a virtual environment.
            cwd: Current working directory.

        Returns:
            WorkspaceInfo with details.

        Raises:
            WorkspaceError: If creation fails or attach_branch doesn't exist.
        """
        try:
            repo_root, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        logger.info(
            "workspace_create_start",
            project=project,
            base_branch=base_branch,
            attach_branch=attach_branch,
            purpose=purpose,
            python_version=python_version,
        )

        try:
            if attach_branch is not None:
                result = worktree.attach_worktree(
                    project=project,
                    branch=attach_branch,
                    repo_root=repo_root,
                    resolver=self._resolver,
                )
            else:
                result = worktree.create_worktree(
                    project=project,
                    base_branch=base_branch,
                    repo_root=repo_root,
                    resolver=self._resolver,
                )
        except ValueError as e:
            # attach_worktree raises ValueError for branch/workspace issues
            raise WorkspaceError(str(e)) from e
        except git.GitError as e:
            logger.error("workspace_create_failed", error=e.stderr)
            raise WorkspaceError(f"Failed to create workspace: {e.stderr}") from e

        # Create .agentspace metadata directory
        metadata_dir = self._resolver.metadata_dir(project, result.name)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # Add .agentspace/ to the main repo's git exclude file so it doesn't
        # block worktree removal. We use .git/info/exclude instead of .gitignore
        # because .gitignore would itself be an untracked file that blocks removal.
        # Note: Git only reads exclude from the main repo, not from worktree git dirs.
        self._ensure_git_exclude_entry(repo_root, ".agentspace/")

        # Set up Python environment if requested
        env_info = None
        if setup_venv:
            try:
                env_info = environment.setup_environment(
                    result.path,
                    python_version=python_version,
                    sync_deps=True,
                )
            except environment.EnvironmentError as e:
                # Log warning but don't fail workspace creation
                logger.warning("environment_setup_failed", error=str(e))

        # Create and persist workspace metadata
        metadata = WorkspaceMetadata(
            name=result.name,
            project=project,
            branch=result.branch,
            base_branch=result.base_branch,
            created_at=datetime.now(UTC),
            purpose=purpose,
            python_version=env_info.python_version if env_info else None,
            has_venv=env_info.has_venv if env_info else False,
        )

        metadata_path = self._resolver.workspace_json(project, result.name)
        try:
            save_workspace_metadata(metadata, metadata_path)
        except Exception as e:
            # Metadata save is critical - attempt cleanup and fail
            logger.error("metadata_save_failed", error=str(e))
            try:
                worktree.remove_worktree(
                    project=project,
                    name=result.name,
                    repo_root=repo_root,
                    force=True,
                    resolver=self._resolver,
                )
            except Exception as cleanup_error:
                logger.warning(
                    "workspace_cleanup_failed",
                    workspace=result.name,
                    error=str(cleanup_error),
                    original_error=str(e),
                )
            raise WorkspaceError(f"Failed to save workspace metadata: {e}") from e

        workspace = WorkspaceInfo(
            name=result.name,
            path=result.path,
            branch=result.branch,
            base_branch=result.base_branch,
            project=project,
            created_at=metadata.created_at,
            purpose=purpose,
            python_version=env_info.python_version if env_info else None,
            has_venv=env_info.has_venv if env_info else False,
        )

        logger.info(
            "workspace_created",
            name=workspace.name,
            path=str(workspace.path),
            has_venv=workspace.has_venv,
            purpose=workspace.purpose,
        )

        return workspace

    def list(self, *, cwd: Path | None = None) -> list[WorkspaceInfo]:
        """List all workspaces for the current repository.

        Returns WorkspaceInfo objects with metadata loaded from
        workspace.json files when available.

        Args:
            cwd: Current working directory.

        Returns:
            List of workspace information.

        Raises:
            WorkspaceError: If listing fails.
        """
        try:
            repo_root, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        try:
            worktrees = worktree.list_worktrees(repo_root)
        except git.GitError as e:
            raise WorkspaceError(f"Failed to list workspaces: {e.stderr}") from e

        # Convert worktrees to WorkspaceInfo, loading metadata when available
        workspaces: list[WorkspaceInfo] = []
        for wt in worktrees:
            # Try to load metadata for agentspaces-managed workspaces
            metadata = None
            workspace_name = wt.path.name

            # Check if this workspace has metadata
            metadata_path = self._resolver.workspace_json(project, workspace_name)
            if metadata_path.exists():
                metadata = load_workspace_metadata(metadata_path)

            workspaces.append(
                WorkspaceInfo(
                    name=workspace_name,
                    path=wt.path,
                    branch=wt.branch or "",
                    base_branch=metadata.base_branch if metadata else "",
                    project=project,
                    created_at=metadata.created_at if metadata else None,
                    purpose=metadata.purpose if metadata else None,
                    python_version=metadata.python_version if metadata else None,
                    has_venv=metadata.has_venv if metadata else False,
                    status=metadata.status if metadata else "active",
                    deps_synced_at=metadata.deps_synced_at if metadata else None,
                    last_activity_at=metadata.last_activity_at if metadata else None,
                )
            )

        return workspaces

    def get(self, name: str, *, cwd: Path | None = None) -> WorkspaceInfo:
        """Get details for a specific workspace.

        Args:
            name: Workspace name.
            cwd: Current working directory.

        Returns:
            WorkspaceInfo with full details.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceError: If operation fails.
        """
        try:
            repo_root, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        workspace_path = self._resolver.workspace_dir(project, name)
        metadata_path = self._resolver.workspace_json(project, name)

        # Load metadata - handles missing file gracefully
        # This avoids TOCTOU race by not pre-checking existence
        metadata = load_workspace_metadata(metadata_path)

        # Get worktree info from git to verify workspace exists
        try:
            worktrees = worktree.list_worktrees(repo_root)
            wt = next((w for w in worktrees if w.path.name == name), None)
            if wt is None:
                raise WorkspaceNotFoundError(f"Workspace not found: {name}")
            branch = wt.branch or name
        except git.GitError as e:
            raise WorkspaceError(f"Failed to list worktrees: {e.stderr}") from e

        return WorkspaceInfo(
            name=name,
            path=workspace_path,
            branch=branch,
            base_branch=metadata.base_branch if metadata else "",
            project=project,
            created_at=metadata.created_at if metadata else None,
            purpose=metadata.purpose if metadata else None,
            python_version=metadata.python_version if metadata else None,
            has_venv=metadata.has_venv
            if metadata
            else (workspace_path / ".venv").exists(),
            status=metadata.status if metadata else "active",
            deps_synced_at=metadata.deps_synced_at if metadata else None,
            last_activity_at=metadata.last_activity_at if metadata else None,
        )

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
        except InvalidNameError as e:
            raise WorkspaceError(str(e)) from e
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

    def _ensure_git_exclude_entry(self, repo_root: Path, entry: str) -> None:
        """Ensure an entry exists in the repository's git exclude file.

        Uses .git/info/exclude instead of .gitignore because .gitignore would
        itself be an untracked file that blocks worktree removal. The exclude
        file lives in the git metadata and has the same effect.

        Args:
            repo_root: Path to the main repository root (not a worktree).
            entry: The gitignore pattern to add (e.g., ".agentspace/").
        """
        git_dir = repo_root / ".git"

        if not git_dir.exists() or not git_dir.is_dir():
            logger.warning("git_dir_not_found", path=str(git_dir))
            return

        # Ensure info directory exists
        info_dir = git_dir / "info"
        info_dir.mkdir(parents=True, exist_ok=True)

        exclude_path = info_dir / "exclude"

        # Read existing content if file exists
        existing_lines: set[str] = set()
        if exclude_path.exists():
            content = exclude_path.read_text()
            existing_lines = {line.strip() for line in content.splitlines()}

        # Check if entry already exists (strip to handle trailing whitespace)
        if entry.strip() in existing_lines:
            return

        # Append entry to exclude file
        with exclude_path.open("a") as f:
            # Add newline before if file exists and doesn't end with newline
            if exclude_path.exists():
                content = exclude_path.read_text()
                if content and not content.endswith("\n"):
                    f.write("\n")
            f.write(f"{entry}\n")
