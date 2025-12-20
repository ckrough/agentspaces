"""Workspace management CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agentspaces.cli.formatters import (
    print_error,
    print_info,
    print_workspace_created,
    print_workspace_removed,
    print_workspace_table,
)
from agentspaces.infrastructure import git
from agentspaces.infrastructure.naming import generate_name
from agentspaces.infrastructure.paths import PathResolver

app = typer.Typer(
    name="workspace",
    help="Manage isolated development workspaces.",
    no_args_is_help=True,
)


@app.command("create")
def create(
    branch: Annotated[
        str,
        typer.Argument(help="Base branch to create workspace from"),
    ] = "HEAD",
    purpose: Annotated[
        str | None,
        typer.Option("--purpose", "-p", help="Purpose/description for this workspace"),
    ] = None,
    python_version: Annotated[
        str | None,
        typer.Option("--python-version", help="Python version for venv (e.g., 3.12)"),
    ] = None,
) -> None:
    """Create a new isolated workspace from a branch.

    Creates a git worktree with a unique name (e.g., eager-turing) and
    optionally sets up a Python virtual environment.
    """
    # Verify we're in a git repository
    try:
        repo_root = git.get_repo_root()
        project = git.get_repo_name()
    except git.GitError as e:
        print_error(f"Not in a git repository: {e.stderr}")
        raise typer.Exit(1) from e

    # Handle case where we're in a worktree - find main repo
    if git.is_in_worktree():
        repo_root = git.get_main_git_dir()
        project = repo_root.name

    # Set up paths
    resolver = PathResolver()
    resolver.ensure_base()

    # Generate unique workspace name
    def name_exists(name: str) -> bool:
        return resolver.workspace_exists(project, name)

    workspace_name = generate_name(exists_check=name_exists)
    workspace_path = resolver.workspace_dir(project, workspace_name)

    # Create parent directory
    workspace_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the worktree
    try:
        git.worktree_add(
            path=workspace_path,
            branch=workspace_name,
            base=branch,
            cwd=repo_root,
        )
    except git.GitError as e:
        print_error(f"Failed to create workspace: {e.stderr}")
        raise typer.Exit(1) from e

    # Create .agentspace metadata directory
    metadata_dir = resolver.metadata_dir(project, workspace_name)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Create workspace.json with metadata (Increment 3)
    # TODO: Set up Python venv if detected/requested (Increment 2)
    # TODO: Create workspace-context skill (Increment 3)

    if purpose:
        print_info(f"Purpose: {purpose}")

    print_workspace_created(
        name=workspace_name,
        path=str(workspace_path),
        base_branch=branch,
        python_version=python_version,
    )

    # Print hint about changing to the workspace
    print_info(f"cd {workspace_path}")


@app.command("list")
def list_workspaces(
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Filter by project name"),
    ] = None,
) -> None:
    """List all workspaces.

    Shows all git worktrees managed by AgentSpaces.
    """
    # If no project specified, try to detect from current directory
    if project is None:
        try:
            project = git.get_repo_name()
        except git.GitError:
            print_error("Not in a git repository. Use --project to specify.")
            raise typer.Exit(1) from None

    # Get repo root for worktree list
    try:
        if git.is_in_worktree():
            repo_root = git.get_main_git_dir()
        else:
            repo_root = git.get_repo_root()

        worktrees = git.worktree_list(cwd=repo_root)
    except git.GitError as e:
        print_error(f"Failed to list worktrees: {e.stderr}")
        raise typer.Exit(1) from e

    print_workspace_table(worktrees, project)


@app.command("remove")
def remove(
    name: Annotated[
        str,
        typer.Argument(help="Workspace name to remove"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force removal even if workspace is dirty"),
    ] = False,
) -> None:
    """Remove a workspace and its branch.

    This removes the git worktree and deletes the associated branch.
    """
    # Verify we're in a git repository
    try:
        if git.is_in_worktree():
            repo_root = git.get_main_git_dir()
        else:
            repo_root = git.get_repo_root()
        project = repo_root.name
    except git.GitError as e:
        print_error(f"Not in a git repository: {e.stderr}")
        raise typer.Exit(1) from e

    # Find the workspace
    resolver = PathResolver()
    workspace_path = resolver.workspace_dir(project, name)

    if not workspace_path.exists():
        print_error(f"Workspace not found: {name}")
        print_info("Use 'as workspace list' to see available workspaces")
        raise typer.Exit(1)

    # Check we're not removing the current worktree
    try:
        current_path = Path.cwd().resolve()
        if current_path == workspace_path.resolve() or str(current_path).startswith(
            str(workspace_path.resolve())
        ):
            print_error("Cannot remove the current workspace. Change directory first.")
            raise typer.Exit(1)
    except OSError:
        pass  # If we can't resolve paths, continue anyway

    # Remove the worktree
    try:
        git.worktree_remove(workspace_path, force=force, cwd=repo_root)
    except git.GitError as e:
        if "dirty" in e.stderr.lower() or "modified" in e.stderr.lower():
            print_error("Workspace has uncommitted changes. Use --force to override.")
        else:
            print_error(f"Failed to remove workspace: {e.stderr}")
        raise typer.Exit(1) from e

    # Try to delete the branch (may fail if it's checked out elsewhere)
    git.branch_delete(name, force=force, cwd=repo_root)

    print_workspace_removed(name)
