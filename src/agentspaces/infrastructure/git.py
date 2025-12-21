"""Git operations via subprocess."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DEFAULT_TIMEOUT",
    "GitError",
    "GitTimeoutError",
    "WorktreeInfo",
    "branch_delete",
    "branch_exists",
    "get_current_branch",
    "get_main_git_dir",
    "get_repo_name",
    "get_repo_root",
    "is_dirty",
    "is_git_repo",
    "is_in_worktree",
    "worktree_add",
    "worktree_add_existing",
    "worktree_list",
    "worktree_remove",
]

logger = structlog.get_logger()


# Default timeout for git operations (30 seconds)
DEFAULT_TIMEOUT = 30


class GitError(Exception):
    """Raised when a git operation fails."""

    def __init__(self, message: str, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class GitTimeoutError(GitError):
    """Raised when a git operation times out."""

    def __init__(self, message: str, timeout: float) -> None:
        super().__init__(
            message, returncode=-1, stderr=f"Operation timed out after {timeout}s"
        )
        self.timeout = timeout


@dataclass(frozen=True)
class WorktreeInfo:
    """Information about a git worktree."""

    path: Path
    branch: str
    commit: str
    is_bare: bool = False
    is_main: bool = False


def _run_git(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        args: Git command arguments (without 'git' prefix).
        cwd: Working directory for the command.
        check: Whether to raise GitError on non-zero exit.
        timeout: Maximum time in seconds to wait for the command.

    Returns:
        CompletedProcess with stdout/stderr.

    Raises:
        GitError: If check=True and command fails.
        GitTimeoutError: If the command times out.
    """
    cmd = ["git", *args]
    logger.debug("git_command", cmd=cmd, cwd=str(cwd) if cwd else None)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise GitTimeoutError(
            f"Git command timed out: {' '.join(cmd)}",
            timeout=timeout,
        ) from e

    if check and result.returncode != 0:
        raise GitError(
            f"Git command failed: {' '.join(cmd)}",
            returncode=result.returncode,
            stderr=result.stderr.strip(),
        )

    return result


def get_repo_root(cwd: Path | None = None) -> Path:
    """Get the root directory of the current git repository.

    Args:
        cwd: Directory to start from (defaults to current directory).

    Returns:
        Path to repository root.

    Raises:
        GitError: If not in a git repository.
    """
    result = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(result.stdout.strip())


def get_repo_name(cwd: Path | None = None) -> str:
    """Get the name of the current git repository.

    Args:
        cwd: Directory to start from.

    Returns:
        Repository name (directory name of repo root).
    """
    return get_repo_root(cwd).name


def get_current_branch(cwd: Path | None = None) -> str:
    """Get the current branch name.

    Args:
        cwd: Directory to check.

    Returns:
        Current branch name.
    """
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return result.stdout.strip()


def get_main_git_dir(cwd: Path | None = None) -> Path:
    """Get the main .git directory (handles worktrees).

    Args:
        cwd: Directory to check.

    Returns:
        Path to the main .git directory.
    """
    result = _run_git(["rev-parse", "--git-common-dir"], cwd=cwd)
    git_dir = Path(result.stdout.strip())
    # Return parent if it's a .git directory
    if git_dir.name == ".git":
        return git_dir.parent
    return git_dir.parent


def is_in_worktree(cwd: Path | None = None) -> bool:
    """Check if the current directory is in a git worktree (not main repo).

    Args:
        cwd: Directory to check.

    Returns:
        True if in a worktree, False if in main repo.
    """
    # In a worktree, .git is a file pointing to the actual git dir
    git_path = (cwd or Path.cwd()) / ".git"
    return git_path.is_file()


def worktree_add(
    path: Path,
    branch: str,
    base: str = "HEAD",
    *,
    cwd: Path | None = None,
) -> None:
    """Create a new git worktree with a new branch.

    Args:
        path: Path where the worktree will be created.
        branch: Name of the new branch to create.
        base: Base commit/branch for the new branch.
        cwd: Repository directory.

    Raises:
        GitError: If worktree creation fails.
    """
    logger.info("worktree_add", path=str(path), branch=branch, base=base)
    _run_git(["worktree", "add", "-b", branch, str(path), base], cwd=cwd)


def worktree_add_existing(
    path: Path,
    branch: str,
    *,
    cwd: Path | None = None,
) -> None:
    """Create a new git worktree for an existing branch.

    Unlike worktree_add, this does not create a new branch - it checks out
    an existing branch into a new worktree location.

    Args:
        path: Path where the worktree will be created.
        branch: Name of the existing branch to checkout.
        cwd: Repository directory.

    Raises:
        GitError: If worktree creation fails or branch doesn't exist.
    """
    logger.info("worktree_add_existing", path=str(path), branch=branch)
    _run_git(["worktree", "add", str(path), branch], cwd=cwd)


def branch_exists(branch: str, *, cwd: Path | None = None) -> bool:
    """Check if a local branch exists in the repository.

    Args:
        branch: Branch name to check.
        cwd: Repository directory.

    Returns:
        True if the branch exists, False otherwise.
    """
    result = _run_git(
        ["rev-parse", "--verify", f"refs/heads/{branch}"],
        cwd=cwd,
        check=False,
    )
    return result.returncode == 0


def worktree_remove(
    path: Path, *, force: bool = False, cwd: Path | None = None
) -> None:
    """Remove a git worktree.

    Args:
        path: Path to the worktree to remove.
        force: Force removal even if worktree is dirty.
        cwd: Repository directory.

    Raises:
        GitError: If removal fails.
    """
    logger.info("worktree_remove", path=str(path), force=force)
    args = ["worktree", "remove", str(path)]
    if force:
        args.append("--force")
    _run_git(args, cwd=cwd)


def worktree_list(cwd: Path | None = None) -> list[WorktreeInfo]:
    """List all worktrees for the repository.

    Args:
        cwd: Repository directory.

    Returns:
        List of WorktreeInfo for each worktree.
    """
    result = _run_git(["worktree", "list", "--porcelain"], cwd=cwd)
    worktrees: list[WorktreeInfo] = []

    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line:
            if current:
                worktrees.append(
                    WorktreeInfo(
                        path=Path(current["worktree"]),
                        branch=current.get("branch", "").removeprefix("refs/heads/"),
                        commit=current.get("HEAD", ""),
                        is_bare=current.get("bare") == "bare",
                    )
                )
                current = {}
            continue

        if line.startswith("worktree "):
            current["worktree"] = line[9:]
        elif line.startswith("HEAD "):
            current["HEAD"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]
        elif line == "bare":
            current["bare"] = "bare"

    # Handle last entry
    if current:
        worktrees.append(
            WorktreeInfo(
                path=Path(current["worktree"]),
                branch=current.get("branch", "").removeprefix("refs/heads/"),
                commit=current.get("HEAD", ""),
                is_bare=current.get("bare") == "bare",
            )
        )

    # Mark the first non-bare worktree as main
    for i, wt in enumerate(worktrees):
        if not wt.is_bare:
            worktrees[i] = WorktreeInfo(
                path=wt.path,
                branch=wt.branch,
                commit=wt.commit,
                is_bare=wt.is_bare,
                is_main=True,
            )
            break

    return worktrees


def branch_delete(branch: str, *, force: bool = False, cwd: Path | None = None) -> bool:
    """Delete a git branch.

    Args:
        branch: Branch name to delete.
        force: Force deletion with -D instead of -d.
        cwd: Repository directory.

    Returns:
        True if deletion succeeded, False otherwise.
    """
    logger.info("branch_delete", branch=branch, force=force)
    flag = "-D" if force else "-d"
    result = _run_git(["branch", flag, branch], cwd=cwd, check=False)
    if result.returncode != 0:
        logger.warning(
            "branch_delete_failed",
            branch=branch,
            returncode=result.returncode,
            stderr=result.stderr.strip(),
        )
    return result.returncode == 0


def is_git_repo(path: Path) -> bool:
    """Check if a path is inside a git repository.

    Args:
        path: Path to check.

    Returns:
        True if inside a git repo.
    """
    result = _run_git(["rev-parse", "--git-dir"], cwd=path, check=False)
    return result.returncode == 0


def is_dirty(cwd: Path | None = None) -> bool:
    """Check if the repository has uncommitted changes.

    This includes:
    - Staged changes (in index)
    - Unstaged changes to tracked files
    - Untracked files are NOT considered dirty

    Args:
        cwd: Directory to check.

    Returns:
        True if there are uncommitted changes.
    """
    # Check for staged or unstaged changes (excludes untracked files)
    result = _run_git(["status", "--porcelain"], cwd=cwd, check=False)
    if result.returncode != 0:
        return False

    # Each line represents a change; filter to only staged/modified (not untracked '??')
    for line in result.stdout.splitlines():
        if line and not line.startswith("??"):
            return True

    return False
