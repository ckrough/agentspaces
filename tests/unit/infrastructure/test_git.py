"""Tests for the git module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentspaces.infrastructure import git


class TestGitError:
    """Tests for GitError exception."""

    def test_git_error_attributes(self) -> None:
        """GitError should store returncode and stderr."""
        error = git.GitError("Command failed", returncode=1, stderr="error message")
        assert str(error) == "Command failed"
        assert error.returncode == 1
        assert error.stderr == "error message"


class TestGitTimeoutError:
    """Tests for GitTimeoutError exception."""

    def test_timeout_error_attributes(self) -> None:
        """GitTimeoutError should store timeout value."""
        error = git.GitTimeoutError("Command timed out", timeout=30.0)
        assert str(error) == "Command timed out"
        assert error.timeout == 30.0
        assert error.returncode == -1
        assert "30" in error.stderr

    def test_timeout_error_is_git_error(self) -> None:
        """GitTimeoutError should be a subclass of GitError."""
        error = git.GitTimeoutError("Command timed out", timeout=30.0)
        assert isinstance(error, git.GitError)


class TestGetRepoRoot:
    """Tests for get_repo_root function."""

    def test_get_repo_root(self, git_repo: Path) -> None:
        """Should return repository root."""
        root = git.get_repo_root(cwd=git_repo)
        # Use resolve() to handle macOS symlinks (/var -> /private/var)
        assert root.resolve() == git_repo.resolve()

    def test_get_repo_root_from_subdirectory(self, git_repo: Path) -> None:
        """Should return repo root from subdirectory."""
        subdir = git_repo / "subdir"
        subdir.mkdir()

        root = git.get_repo_root(cwd=subdir)
        assert root.resolve() == git_repo.resolve()

    def test_get_repo_root_not_in_repo(self, temp_dir: Path) -> None:
        """Should raise GitError when not in a repo."""
        with pytest.raises(git.GitError):
            git.get_repo_root(cwd=temp_dir)


class TestGetRepoName:
    """Tests for get_repo_name function."""

    def test_get_repo_name(self, git_repo: Path) -> None:
        """Should return repository directory name."""
        name = git.get_repo_name(cwd=git_repo)
        assert name == "test-repo"


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_get_current_branch(self, git_repo: Path) -> None:
        """Should return current branch name."""
        # Default branch on new repo
        branch = git.get_current_branch(cwd=git_repo)
        # Could be 'main' or 'master' depending on git config
        assert branch in ("main", "master")


class TestIsInWorktree:
    """Tests for is_in_worktree function."""

    def test_not_in_worktree_main_repo(self, git_repo: Path) -> None:
        """Should return False for main repository."""
        assert not git.is_in_worktree(cwd=git_repo)


class TestIsGitRepo:
    """Tests for is_git_repo function."""

    def test_is_git_repo_true(self, git_repo: Path) -> None:
        """Should return True for git repository."""
        assert git.is_git_repo(git_repo)

    def test_is_git_repo_false(self, temp_dir: Path) -> None:
        """Should return False for non-repository."""
        assert not git.is_git_repo(temp_dir)


class TestWorktreeOperations:
    """Tests for worktree operations."""

    def test_worktree_add_and_list(self, git_repo: Path, temp_dir: Path) -> None:
        """Should create and list worktrees."""
        worktree_path = temp_dir / "worktree"

        # Create worktree
        git.worktree_add(
            path=worktree_path,
            branch="test-branch",
            base="HEAD",
            cwd=git_repo,
        )

        # Verify worktree exists
        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

        # List worktrees
        worktrees = git.worktree_list(cwd=git_repo)
        assert len(worktrees) == 2  # Main + new worktree

        # Find our worktree (use resolve() for macOS symlink handling)
        wt = next(w for w in worktrees if w.path.resolve() == worktree_path.resolve())
        assert wt.branch == "test-branch"
        assert not wt.is_main

    def test_worktree_remove(self, git_repo: Path, temp_dir: Path) -> None:
        """Should remove worktree."""
        worktree_path = temp_dir / "worktree"

        # Create and then remove
        git.worktree_add(
            path=worktree_path,
            branch="test-branch",
            base="HEAD",
            cwd=git_repo,
        )

        git.worktree_remove(worktree_path, cwd=git_repo)

        # Verify removed
        worktrees = git.worktree_list(cwd=git_repo)
        assert len(worktrees) == 1  # Only main remains

    def test_worktree_list_marks_main(self, git_repo: Path) -> None:
        """worktree_list should mark main worktree."""
        worktrees = git.worktree_list(cwd=git_repo)

        assert len(worktrees) == 1
        assert worktrees[0].is_main
        # Use resolve() for macOS symlink handling
        assert worktrees[0].path.resolve() == git_repo.resolve()


class TestBranchDelete:
    """Tests for branch_delete function."""

    def test_branch_delete_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should delete merged branch."""
        worktree_path = temp_dir / "worktree"

        # Create worktree with branch
        git.worktree_add(
            path=worktree_path,
            branch="test-branch",
            base="HEAD",
            cwd=git_repo,
        )

        # Remove worktree first
        git.worktree_remove(worktree_path, cwd=git_repo)

        # Delete branch
        result = git.branch_delete("test-branch", cwd=git_repo)
        assert result is True

    def test_branch_delete_nonexistent(self, git_repo: Path) -> None:
        """Should return False for nonexistent branch."""
        result = git.branch_delete("nonexistent-branch", cwd=git_repo)
        assert result is False


class TestWorktreeInfo:
    """Tests for WorktreeInfo dataclass."""

    def test_worktree_info_frozen(self) -> None:
        """WorktreeInfo should be immutable."""
        from dataclasses import FrozenInstanceError

        info = git.WorktreeInfo(
            path=Path("/some/path"),
            branch="main",
            commit="abc123",
        )

        with pytest.raises(FrozenInstanceError):
            info.branch = "other"  # type: ignore[misc]


class TestBranchExists:
    """Tests for branch_exists function."""

    def test_branch_exists_true(self, git_repo: Path) -> None:
        """Should return True for existing branch."""
        branch = git.get_current_branch(cwd=git_repo)
        assert git.branch_exists(branch, cwd=git_repo) is True

    def test_branch_exists_false(self, git_repo: Path) -> None:
        """Should return False for non-existent branch."""
        assert git.branch_exists("nonexistent-branch", cwd=git_repo) is False

    def test_branch_exists_after_create(self, git_repo: Path, temp_dir: Path) -> None:
        """Should return True for branch created via worktree."""
        worktree_path = temp_dir / "worktree"
        git.worktree_add(
            path=worktree_path,
            branch="new-test-branch",
            base="HEAD",
            cwd=git_repo,
        )
        assert git.branch_exists("new-test-branch", cwd=git_repo) is True

        # Cleanup
        git.worktree_remove(worktree_path, cwd=git_repo)


class TestWorktreeAddExisting:
    """Tests for worktree_add_existing function."""

    def test_worktree_add_existing_success(self, git_repo: Path, temp_dir: Path) -> None:
        """Should create worktree for existing branch."""
        import subprocess

        # Create a branch first (without a worktree)
        subprocess.run(
            ["git", "branch", "existing-branch"],
            cwd=git_repo,
            check=True,
        )

        worktree_path = temp_dir / "existing-worktree"
        git.worktree_add_existing(
            path=worktree_path,
            branch="existing-branch",
            cwd=git_repo,
        )

        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

        # Verify branch is checked out
        worktrees = git.worktree_list(cwd=git_repo)
        wt = next(w for w in worktrees if w.path.resolve() == worktree_path.resolve())
        assert wt.branch == "existing-branch"

    def test_worktree_add_existing_nonexistent_branch(
        self, git_repo: Path, temp_dir: Path
    ) -> None:
        """Should raise GitError for non-existent branch."""
        worktree_path = temp_dir / "nonexistent-worktree"

        with pytest.raises(git.GitError):
            git.worktree_add_existing(
                path=worktree_path,
                branch="nonexistent-branch",
                cwd=git_repo,
            )


class TestIsDirty:
    """Tests for is_dirty function."""

    def test_clean_repo_returns_false(self, git_repo: Path) -> None:
        """Clean repo should return False."""
        # Initial repo state should be clean
        assert git.is_dirty(git_repo) is False

    def test_staged_changes_returns_true(self, git_repo: Path) -> None:
        """Staged changes should make repo dirty."""
        # Modify a file
        readme = git_repo / "README.md"
        readme.write_text("Modified content")

        # Stage the change
        import subprocess

        subprocess.run(["git", "add", "README.md"], cwd=git_repo, check=True)

        assert git.is_dirty(git_repo) is True

    def test_unstaged_changes_returns_true(self, git_repo: Path) -> None:
        """Unstaged changes to tracked files should make repo dirty."""
        # Modify a tracked file without staging
        readme = git_repo / "README.md"
        readme.write_text("Modified content")

        assert git.is_dirty(git_repo) is True

    def test_untracked_files_returns_false(self, git_repo: Path) -> None:
        """Untracked files should NOT make repo dirty."""
        # Create a new file but don't stage it
        new_file = git_repo / "untracked.txt"
        new_file.write_text("Untracked content")

        assert git.is_dirty(git_repo) is False

    def test_not_git_repo_returns_false(self, temp_dir: Path) -> None:
        """Non-git directory should return False (no error)."""
        assert git.is_dirty(temp_dir) is False
