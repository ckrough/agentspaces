"""Tests for the workspace service module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentspaces.infrastructure.paths import PathResolver
from agentspaces.modules.workspace.service import (
    WorkspaceError,
    WorkspaceInfo,
    WorkspaceNotFoundError,
    WorkspaceService,
)


class TestWorkspaceInfo:
    """Tests for WorkspaceInfo dataclass."""

    def test_workspace_info_attributes(self) -> None:
        """WorkspaceInfo should store all attributes."""
        info = WorkspaceInfo(
            name="test-workspace",
            path=Path("/path/to/workspace"),
            branch="test-workspace",
            base_branch="main",
            project="test-project",
            python_version="3.13",
            has_venv=True,
        )

        assert info.name == "test-workspace"
        assert info.path == Path("/path/to/workspace")
        assert info.branch == "test-workspace"
        assert info.base_branch == "main"
        assert info.project == "test-project"
        assert info.python_version == "3.13"
        assert info.has_venv is True

    def test_workspace_info_defaults(self) -> None:
        """WorkspaceInfo should have sensible defaults."""
        info = WorkspaceInfo(
            name="test-workspace",
            path=Path("/path/to/workspace"),
            branch="test-workspace",
            base_branch="main",
            project="test-project",
        )

        assert info.python_version is None
        assert info.has_venv is False


class TestWorkspaceError:
    """Tests for WorkspaceError exceptions."""

    def test_workspace_error_message(self) -> None:
        """WorkspaceError should store message."""
        error = WorkspaceError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_workspace_not_found_error_message(self) -> None:
        """WorkspaceNotFoundError should store message."""
        error = WorkspaceNotFoundError("Workspace not found")
        assert str(error) == "Workspace not found"
        assert isinstance(error, WorkspaceError)


class TestWorkspaceServiceCreate:
    """Tests for WorkspaceService.create method."""

    def test_create_workspace_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should create a workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        result = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        assert result.name  # Generated name
        assert result.path.exists()
        assert result.branch == result.name
        assert result.base_branch == "HEAD"
        assert result.project == "test-repo"
        assert result.has_venv is False

    def test_create_workspace_with_venv(self, git_repo: Path, temp_dir: Path) -> None:
        """Should create a workspace with venv."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        result = service.create(
            base_branch="HEAD",
            setup_venv=True,
            cwd=git_repo,
        )

        assert result.name
        assert result.path.exists()
        assert result.has_venv is True
        assert (result.path / ".venv").exists()

    def test_create_workspace_creates_metadata_dir(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should create .agentspace metadata directory."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        result = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        metadata_dir = resolver.metadata_dir("test-repo", result.name)
        assert metadata_dir.exists()

    def test_create_workspace_adds_agentspace_to_git_exclude(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should add .agentspace/ to the main repo's git exclude file.

        Uses .git/info/exclude instead of .gitignore so the exclude itself
        doesn't become an untracked file that blocks worktree removal.
        Git only reads exclude from the main repo, not from worktree git dirs.
        """
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        # Check the main repo's exclude file (not the worktree's)
        exclude_path = git_repo / ".git" / "info" / "exclude"
        assert exclude_path.exists()
        content = exclude_path.read_text()
        assert ".agentspace/" in content

    def test_create_workspace_git_exclude_idempotent(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should not duplicate .agentspace/ entry if already present."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create workspace
        service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        # Check the main repo's exclude file
        exclude_path = git_repo / ".git" / "info" / "exclude"
        original_content = exclude_path.read_text()

        # Call _ensure_git_exclude_entry again (simulating another create)
        service._ensure_git_exclude_entry(git_repo, ".agentspace/")

        # Content should be unchanged
        new_content = exclude_path.read_text()
        assert new_content == original_content
        assert new_content.count(".agentspace/") == 1

    def test_create_workspace_not_in_repo(self, temp_dir: Path) -> None:
        """Should raise error when not in a git repo."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        with pytest.raises(WorkspaceError, match="Not in a git repository"):
            service.create(cwd=temp_dir)


class TestWorkspaceServiceCreateAttach:
    """Tests for WorkspaceService.create with attach_branch."""

    def test_create_with_attach_branch(self, git_repo: Path, temp_dir: Path) -> None:
        """Should create workspace attached to existing branch."""
        import subprocess

        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create a branch first
        subprocess.run(
            ["git", "branch", "existing-branch"],
            cwd=git_repo,
            check=True,
        )

        result = service.create(
            attach_branch="existing-branch",
            setup_venv=False,
            cwd=git_repo,
        )

        assert result.name == "existing-branch"
        assert result.branch == "existing-branch"
        assert result.path.exists()

    def test_create_attach_branch_with_slash(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should handle branch names with slashes."""
        import subprocess

        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create a branch with slash
        subprocess.run(
            ["git", "branch", "feature/auth"],
            cwd=git_repo,
            check=True,
        )

        result = service.create(
            attach_branch="feature/auth",
            setup_venv=False,
            cwd=git_repo,
        )

        assert result.name == "feature-auth"  # Sanitized for directory
        assert result.branch == "feature/auth"  # Original preserved
        assert result.path.exists()

    def test_create_attach_nonexistent_branch(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should raise WorkspaceError for non-existent branch."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        with pytest.raises(WorkspaceError, match="Branch does not exist"):
            service.create(
                attach_branch="nonexistent-branch",
                setup_venv=False,
                cwd=git_repo,
            )

    def test_create_attach_creates_metadata(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should create metadata for attached workspace."""
        import subprocess

        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        subprocess.run(
            ["git", "branch", "attach-test-branch"],
            cwd=git_repo,
            check=True,
        )

        result = service.create(
            attach_branch="attach-test-branch",
            purpose="Testing attach",
            setup_venv=False,
            cwd=git_repo,
        )

        metadata_dir = resolver.metadata_dir("test-repo", result.name)
        assert metadata_dir.exists()
        assert result.purpose == "Testing attach"


class TestWorkspaceServiceList:
    """Tests for WorkspaceService.list method."""

    def test_list_workspaces_empty(self, git_repo: Path, temp_dir: Path) -> None:
        """Should return only main repo when no workspaces exist."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        result = service.list(cwd=git_repo)

        assert len(result) == 1
        # Main repo workspace has the repo directory name
        assert result[0].name == git_repo.name

    def test_list_workspaces_with_workspace(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should return all workspaces."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create a workspace
        created = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        result = service.list(cwd=git_repo)

        assert len(result) == 2
        names = [wt.path.name for wt in result]
        assert created.name in names


class TestWorkspaceServiceRemove:
    """Tests for WorkspaceService.remove method."""

    def test_remove_workspace_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should remove an existing workspace without force.

        The .agentspace/ directory is added to git's exclude file on creation,
        so it doesn't block worktree removal.
        """
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create a workspace
        created = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )
        assert created.path.exists()

        # Remove it - no force needed because .agentspace/ is gitignored
        service.remove(created.name, cwd=git_repo)

        assert not created.path.exists()

    def test_remove_workspace_not_found(self, git_repo: Path, temp_dir: Path) -> None:
        """Should raise WorkspaceNotFoundError for non-existent workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        with pytest.raises(WorkspaceNotFoundError):
            service.remove("nonexistent-workspace", cwd=git_repo)


class TestWorkspaceServiceGetProjectName:
    """Tests for WorkspaceService.get_project_name method."""

    def test_get_project_name_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should return the project name."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        name = service.get_project_name(cwd=git_repo)

        assert name == "test-repo"

    def test_get_project_name_not_in_repo(self, temp_dir: Path) -> None:
        """Should raise error when not in a git repo."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        with pytest.raises(WorkspaceError, match="Not in a git repository"):
            service.get_project_name(cwd=temp_dir)


class TestWorkspaceServiceGetWorkspacePath:
    """Tests for WorkspaceService.get_workspace_path method."""

    def test_get_workspace_path(self, temp_dir: Path) -> None:
        """Should return path to workspace directory."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        path = service.get_workspace_path("test-project", "test-workspace")

        expected = temp_dir / ".agentspaces" / "test-project" / "test-workspace"
        assert path == expected


class TestWorkspaceServiceActiveWorkspace:
    """Tests for active workspace management methods."""

    def test_get_active_returns_none_when_not_set(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should return None when no active workspace is set."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        result = service.get_active(cwd=git_repo)

        assert result is None

    def test_set_active_and_get_active(self, git_repo: Path, temp_dir: Path) -> None:
        """Should set and retrieve active workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create a workspace
        created = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        # Set it as active
        service.set_active(created.name, cwd=git_repo)

        # Retrieve active
        active = service.get_active(cwd=git_repo)

        assert active is not None
        assert active.name == created.name

    def test_set_active_not_found(self, git_repo: Path, temp_dir: Path) -> None:
        """Should raise WorkspaceNotFoundError for non-existent workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        with pytest.raises(WorkspaceNotFoundError):
            service.set_active("nonexistent-workspace", cwd=git_repo)

    def test_get_active_returns_none_when_workspace_deleted(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should return None if active workspace was deleted."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create and activate
        created = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )
        service.set_active(created.name, cwd=git_repo)

        # Delete the workspace (no force needed, .agentspace/ is gitignored)
        service.remove(created.name, cwd=git_repo)

        # Active should return None now
        result = service.get_active(cwd=git_repo)
        assert result is None


class TestWorkspaceServiceUpdateActivity:
    """Tests for update_activity method."""

    def test_update_activity_updates_timestamp(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should update last_activity_at timestamp."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        # Create a workspace
        created = service.create(
            base_branch="HEAD",
            setup_venv=False,
            cwd=git_repo,
        )

        # Initially no activity
        assert created.last_activity_at is None

        # Update activity
        service.update_activity(created.name, cwd=git_repo)

        # Check timestamp is set
        updated = service.get(created.name, cwd=git_repo)
        assert updated.last_activity_at is not None

    def test_update_activity_not_found(self, git_repo: Path, temp_dir: Path) -> None:
        """Should raise WorkspaceNotFoundError for non-existent workspace."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")
        service = WorkspaceService(resolver=resolver)

        with pytest.raises(WorkspaceNotFoundError):
            service.update_activity("nonexistent-workspace", cwd=git_repo)
