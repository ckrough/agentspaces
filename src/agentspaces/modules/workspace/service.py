"""Workspace lifecycle management service."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass

import structlog

from agentspaces.infrastructure import git
from agentspaces.infrastructure.active import (
    clear_active_workspace,
    get_active_workspace,
    set_active_workspace,
)
from agentspaces.infrastructure.metadata import (
    WorkspaceMetadata,
    load_workspace_metadata,
    save_workspace_metadata,
)
from agentspaces.infrastructure.paths import InvalidNameError, PathResolver
from agentspaces.infrastructure.skills import (
    generate_workspace_context_skill,
)
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
    Persists workspace metadata to JSON files and generates
    workspace-context skills for agent discovery.
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
        purpose: str | None = None,
        python_version: str | None = None,
        setup_venv: bool = True,
        cwd: Path | None = None,
    ) -> WorkspaceInfo:
        """Create a new workspace.

        Creates a git worktree, sets up the Python environment,
        persists workspace metadata, and generates a workspace-context skill.

        Args:
            base_branch: Branch to create workspace from.
            purpose: Description of workspace purpose.
            python_version: Python version for venv (auto-detected if not specified).
            setup_venv: Whether to create a virtual environment.
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
            python_version=python_version,
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
            with contextlib.suppress(Exception):
                worktree.remove_worktree(
                    project=project,
                    name=result.name,
                    repo_root=repo_root,
                    force=True,
                    resolver=self._resolver,
                )
            raise WorkspaceError(f"Failed to save workspace metadata: {e}") from e

        # Generate workspace-context skill for agent discovery
        skill_dir = self._resolver.workspace_context_skill(project, result.name)
        try:
            generate_workspace_context_skill(metadata, skill_dir)
        except Exception as e:
            # Skill generation is non-critical - warn and continue
            logger.warning("skill_generation_failed", error=str(e))

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
            # Try to load metadata for AgentSpaces-managed workspaces
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

    def get_active(self, *, cwd: Path | None = None) -> WorkspaceInfo | None:
        """Get the currently active workspace.

        Args:
            cwd: Current working directory.

        Returns:
            WorkspaceInfo for the active workspace, or None if no active workspace.

        Raises:
            WorkspaceError: If not in a git repository.
        """
        try:
            _, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        project_dir = self._resolver.project_dir(project)
        active_name = get_active_workspace(project_dir)

        if active_name is None:
            return None

        try:
            return self.get(active_name, cwd=cwd)
        except WorkspaceNotFoundError:
            # Active workspace no longer exists - clear stale reference
            logger.warning(
                "active_workspace_missing",
                project=project,
                workspace=active_name,
            )
            clear_active_workspace(project_dir)
            return None

    def set_active(self, name: str, *, cwd: Path | None = None) -> None:
        """Set a workspace as the active workspace.

        Args:
            name: Workspace name.
            cwd: Current working directory.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceError: If operation fails.
        """
        # Verify workspace exists first
        self.get(name, cwd=cwd)

        try:
            _, project = worktree.get_repo_info(cwd)
        except git.GitError as e:
            raise WorkspaceError(f"Not in a git repository: {e.stderr}") from e

        project_dir = self._resolver.project_dir(project)
        set_active_workspace(project_dir, name)

        logger.info("workspace_activated", workspace=name, project=project)

    def sync_deps(
        self,
        name: str | None = None,
        *,
        cwd: Path | None = None,
    ) -> WorkspaceInfo:
        """Sync dependencies for a workspace.

        Args:
            name: Workspace name. If None, uses active workspace or auto-detect.
            cwd: Current working directory.

        Returns:
            Updated WorkspaceInfo with new deps_synced_at timestamp.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceError: If sync fails.
        """
        # Determine workspace
        if name is None:
            # Try active workspace first
            active = self.get_active(cwd=cwd)
            if active is not None:
                name = active.name
            else:
                raise WorkspaceError(
                    "No workspace specified and no active workspace. "
                    "Use 'as workspace sync <name>' or 'as workspace activate <name>'."
                )

        workspace = self.get(name, cwd=cwd)

        try:
            environment.sync_dependencies(workspace.path)
        except environment.EnvironmentError as e:
            raise WorkspaceError(str(e)) from e

        # Update deps_synced_at timestamp
        self._update_metadata_timestamp(
            workspace.name,
            workspace.project,
            deps_synced_at=datetime.now(UTC),
        )

        logger.info("workspace_deps_synced", workspace=name)

        # Return updated workspace info
        return self.get(name, cwd=cwd)

    def update_activity(self, name: str, *, cwd: Path | None = None) -> None:
        """Update the last_activity_at timestamp for a workspace.

        Called when an agent is launched or other activity occurs.

        Args:
            name: Workspace name.
            cwd: Current working directory.

        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist.
            WorkspaceError: If update fails.
        """
        workspace = self.get(name, cwd=cwd)

        self._update_metadata_timestamp(
            workspace.name,
            workspace.project,
            last_activity_at=datetime.now(UTC),
        )

        logger.debug("workspace_activity_updated", workspace=name)

    def _update_metadata_timestamp(
        self,
        name: str,
        project: str,
        *,
        deps_synced_at: datetime | None = None,
        last_activity_at: datetime | None = None,
    ) -> None:
        """Update timestamp fields in workspace metadata.

        Args:
            name: Workspace name.
            project: Project name.
            deps_synced_at: New deps_synced_at value.
            last_activity_at: New last_activity_at value.
        """
        metadata_path = self._resolver.workspace_json(project, name)
        metadata = load_workspace_metadata(metadata_path)

        if metadata is None:
            logger.warning(
                "metadata_not_found_for_update",
                workspace=name,
                project=project,
            )
            return

        # Create updated metadata with new timestamps
        updated = WorkspaceMetadata(
            name=metadata.name,
            project=metadata.project,
            branch=metadata.branch,
            base_branch=metadata.base_branch,
            created_at=metadata.created_at,
            purpose=metadata.purpose,
            python_version=metadata.python_version,
            has_venv=metadata.has_venv,
            status=metadata.status,
            deps_synced_at=deps_synced_at or metadata.deps_synced_at,
            last_activity_at=last_activity_at or metadata.last_activity_at,
        )

        save_workspace_metadata(updated, metadata_path)
