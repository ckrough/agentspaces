"""Higher-level git worktree operations for workspace management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass

from agentspaces.infrastructure import git
from agentspaces.infrastructure.naming import generate_name
from agentspaces.infrastructure.paths import PathResolver


@dataclass
class WorktreeCreateResult:
    """Result of creating a worktree."""

    name: str
    path: Path
    branch: str
    base_branch: str


def create_worktree(
    project: str,
    base_branch: str = "HEAD",
    *,
    repo_root: Path,
    resolver: PathResolver | None = None,
) -> WorktreeCreateResult:
    """Create a new git worktree for a workspace.

    Args:
        project: Project/repository name.
        base_branch: Base branch to create from.
        repo_root: Path to the main repository.
        resolver: Path resolver instance.

    Returns:
        WorktreeCreateResult with details.

    Raises:
        git.GitError: If worktree creation fails.
    """
    resolver = resolver or PathResolver()
    resolver.ensure_base()

    # Generate unique workspace name
    def name_exists(name: str) -> bool:
        return resolver.workspace_exists(project, name)

    workspace_name = generate_name(exists_check=name_exists)
    workspace_path = resolver.workspace_dir(project, workspace_name)

    # Create parent directory
    workspace_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the worktree
    git.worktree_add(
        path=workspace_path,
        branch=workspace_name,
        base=base_branch,
        cwd=repo_root,
    )

    return WorktreeCreateResult(
        name=workspace_name,
        path=workspace_path,
        branch=workspace_name,
        base_branch=base_branch,
    )


def remove_worktree(
    project: str,
    name: str,
    *,
    repo_root: Path,
    force: bool = False,
    resolver: PathResolver | None = None,
) -> None:
    """Remove a git worktree and its branch.

    Args:
        project: Project/repository name.
        name: Workspace name.
        repo_root: Path to the main repository.
        force: Force removal even if dirty.
        resolver: Path resolver instance.

    Raises:
        git.GitError: If removal fails.
        FileNotFoundError: If workspace doesn't exist.
    """
    resolver = resolver or PathResolver()
    workspace_path = resolver.workspace_dir(project, name)

    if not workspace_path.exists():
        raise FileNotFoundError(f"Workspace not found: {name}")

    # Remove the worktree
    git.worktree_remove(workspace_path, force=force, cwd=repo_root)

    # Try to delete the branch
    git.branch_delete(name, force=force, cwd=repo_root)


def list_worktrees(repo_root: Path) -> list[git.WorktreeInfo]:
    """List all worktrees for a repository.

    Args:
        repo_root: Path to the main repository.

    Returns:
        List of WorktreeInfo objects.
    """
    return git.worktree_list(cwd=repo_root)


def get_repo_info(cwd: Path | None = None) -> tuple[Path, str]:
    """Get repository root and name.

    Handles the case where we're in a worktree by finding the main repo.

    Args:
        cwd: Current working directory.

    Returns:
        Tuple of (repo_root, project_name).

    Raises:
        git.GitError: If not in a git repository.
    """
    if git.is_in_worktree(cwd):
        repo_root = git.get_main_git_dir(cwd)
    else:
        repo_root = git.get_repo_root(cwd)

    return repo_root, repo_root.name
