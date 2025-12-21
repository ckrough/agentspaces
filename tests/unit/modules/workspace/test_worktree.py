"""Tests for the worktree module."""

from __future__ import annotations

from pathlib import Path

from agentspaces.infrastructure.paths import PathResolver
from agentspaces.modules.workspace import worktree


class TestWorktreeCreateResult:
    """Tests for WorktreeCreateResult dataclass."""

    def test_create_result_attributes(self) -> None:
        """WorktreeCreateResult should store all attributes."""
        result = worktree.WorktreeCreateResult(
            name="test-workspace",
            path=Path("/path/to/workspace"),
            branch="test-workspace",
            base_branch="main",
        )

        assert result.name == "test-workspace"
        assert result.path == Path("/path/to/workspace")
        assert result.branch == "test-workspace"
        assert result.base_branch == "main"

    def test_create_result_is_frozen(self) -> None:
        """WorktreeCreateResult should be immutable."""
        from dataclasses import FrozenInstanceError

        import pytest

        result = worktree.WorktreeCreateResult(
            name="test-workspace",
            path=Path("/path/to/workspace"),
            branch="test-workspace",
            base_branch="main",
        )

        with pytest.raises(FrozenInstanceError):
            result.name = "new-name"  # type: ignore[misc]


class TestSanitizeBranchName:
    """Tests for sanitize_branch_name function."""

    def test_simple_branch_unchanged(self) -> None:
        """Simple branch names should remain unchanged."""
        assert worktree.sanitize_branch_name("main") == "main"
        assert worktree.sanitize_branch_name("develop") == "develop"
        assert worktree.sanitize_branch_name("my-branch") == "my-branch"

    def test_branch_with_slash(self) -> None:
        """Slashes should be replaced with hyphens."""
        assert worktree.sanitize_branch_name("feature/auth") == "feature-auth"
        assert worktree.sanitize_branch_name("fix/bug-123") == "fix-bug-123"

    def test_multiple_slashes(self) -> None:
        """Multiple slashes should all be replaced."""
        assert worktree.sanitize_branch_name("feature/auth/login") == "feature-auth-login"
        assert worktree.sanitize_branch_name("a/b/c/d") == "a-b-c-d"


class TestAttachWorktree:
    """Tests for attach_worktree function."""

    def test_attach_worktree_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should attach to an existing branch."""
        import subprocess

        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create a branch first (without a worktree)
        subprocess.run(
            ["git", "branch", "existing-branch"],
            cwd=git_repo,
            check=True,
        )

        result = worktree.attach_worktree(
            project="test-repo",
            branch="existing-branch",
            repo_root=git_repo,
            resolver=resolver,
        )

        assert result.name == "existing-branch"
        assert result.branch == "existing-branch"
        assert result.base_branch == "existing-branch"
        assert result.path.exists()

    def test_attach_worktree_with_slash_in_name(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should handle branch names with slashes."""
        import subprocess

        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create a branch with slash
        subprocess.run(
            ["git", "branch", "feature/auth"],
            cwd=git_repo,
            check=True,
        )

        result = worktree.attach_worktree(
            project="test-repo",
            branch="feature/auth",
            repo_root=git_repo,
            resolver=resolver,
        )

        assert result.name == "feature-auth"  # Sanitized
        assert result.branch == "feature/auth"  # Original preserved
        assert result.path.exists()

    def test_attach_worktree_nonexistent_branch(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should raise ValueError for non-existent branch."""
        import pytest

        resolver = PathResolver(base=temp_dir / ".agentspaces")

        with pytest.raises(ValueError, match="Branch does not exist"):
            worktree.attach_worktree(
                project="test-repo",
                branch="nonexistent-branch",
                repo_root=git_repo,
                resolver=resolver,
            )

    def test_attach_worktree_already_exists(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should raise ValueError if workspace already exists."""
        import subprocess

        import pytest

        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create a branch
        subprocess.run(
            ["git", "branch", "test-branch"],
            cwd=git_repo,
            check=True,
        )

        # Attach first time
        worktree.attach_worktree(
            project="test-repo",
            branch="test-branch",
            repo_root=git_repo,
            resolver=resolver,
        )

        # Try to attach again - should fail
        with pytest.raises(ValueError, match="Workspace already exists"):
            worktree.attach_worktree(
                project="test-repo",
                branch="test-branch",
                repo_root=git_repo,
                resolver=resolver,
            )


class TestCreateWorktree:
    """Tests for create_worktree function."""

    def test_create_worktree_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should create a worktree with generated name."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        result = worktree.create_worktree(
            project="test-repo",
            base_branch="HEAD",
            repo_root=git_repo,
            resolver=resolver,
        )

        assert result.name  # Generated name
        assert result.path.exists()
        assert result.branch == result.name
        assert result.base_branch == "HEAD"

    def test_create_worktree_creates_branch(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should create a branch with the workspace name."""
        import subprocess

        resolver = PathResolver(base=temp_dir / ".agentspaces")

        result = worktree.create_worktree(
            project="test-repo",
            base_branch="HEAD",
            repo_root=git_repo,
            resolver=resolver,
        )

        # Verify branch exists
        branches_result = subprocess.run(
            ["git", "branch", "--list", result.name],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.name in branches_result.stdout


class TestRemoveWorktree:
    """Tests for remove_worktree function."""

    def test_remove_worktree_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should remove an existing worktree."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create a worktree first
        result = worktree.create_worktree(
            project="test-repo",
            base_branch="HEAD",
            repo_root=git_repo,
            resolver=resolver,
        )
        assert result.path.exists()

        # Remove it
        worktree.remove_worktree(
            project="test-repo",
            name=result.name,
            repo_root=git_repo,
            resolver=resolver,
        )

        assert not result.path.exists()

    def test_remove_worktree_not_found(self, git_repo: Path, temp_dir: Path) -> None:
        """Should raise FileNotFoundError for non-existent worktree."""
        import pytest

        resolver = PathResolver(base=temp_dir / ".agentspaces")

        with pytest.raises(FileNotFoundError, match="Workspace not found"):
            worktree.remove_worktree(
                project="test-repo",
                name="nonexistent-workspace",
                repo_root=git_repo,
                resolver=resolver,
            )


class TestListWorktrees:
    """Tests for list_worktrees function."""

    def test_list_worktrees_empty(self, git_repo: Path) -> None:
        """Should return only main repo when no worktrees exist."""
        result = worktree.list_worktrees(git_repo)

        assert len(result) == 1
        assert result[0].is_main is True

    def test_list_worktrees_with_worktree(self, git_repo: Path, temp_dir: Path) -> None:
        """Should return all worktrees including created ones."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create a worktree
        created = worktree.create_worktree(
            project="test-repo",
            base_branch="HEAD",
            repo_root=git_repo,
            resolver=resolver,
        )

        result = worktree.list_worktrees(git_repo)

        assert len(result) == 2
        names = [wt.path.name for wt in result]
        assert created.name in names


class TestGetRepoInfo:
    """Tests for get_repo_info function."""

    def test_get_repo_info_from_repo(self, git_repo: Path) -> None:
        """Should return repo root and name."""
        repo_root, project = worktree.get_repo_info(git_repo)

        # Use resolve() to handle macOS /private/var symlink
        assert repo_root.resolve() == git_repo.resolve()
        assert project == "test-repo"

    def test_get_repo_info_from_worktree(self, git_repo: Path, temp_dir: Path) -> None:
        """Should return main repo info when in a worktree."""
        resolver = PathResolver(base=temp_dir / ".agentspaces")

        # Create a worktree
        result = worktree.create_worktree(
            project="test-repo",
            base_branch="HEAD",
            repo_root=git_repo,
            resolver=resolver,
        )

        # Get repo info from within the worktree
        repo_root, project = worktree.get_repo_info(result.path)

        # Use resolve() to handle macOS /private/var symlink
        assert repo_root.resolve() == git_repo.resolve()
        assert project == "test-repo"
