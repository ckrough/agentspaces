"""Workspace management CLI commands."""

from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from agentspaces.cli.formatters import (
    print_did_you_mean,
    print_error,
    print_info,
    print_next_steps,
    print_warning,
    print_workspace_created,
    print_workspace_removed,
    print_workspace_status,
    print_workspace_table,
)
from agentspaces.infrastructure import git
from agentspaces.infrastructure.similarity import find_similar_names
from agentspaces.modules.workspace.service import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceService,
)

app = typer.Typer(
    name="workspace",
    help="Manage isolated development workspaces.",
    no_args_is_help=True,
)

# Shared service instance
_service = WorkspaceService()


@app.command("create")
def create(
    branch: Annotated[
        str,
        typer.Argument(help="Base branch (or target branch with --attach)"),
    ] = "HEAD",
    attach: Annotated[
        bool,
        typer.Option(
            "--attach", "-a", help="Attach to existing branch instead of creating new"
        ),
    ] = False,
    purpose: Annotated[
        str | None,
        typer.Option("--purpose", "-p", help="Purpose/description for this workspace"),
    ] = None,
    python_version: Annotated[
        str | None,
        typer.Option("--python", help="Python version for venv (e.g., 3.13)"),
    ] = None,
    no_venv: Annotated[
        bool,
        typer.Option("--no-venv", help="Skip virtual environment creation"),
    ] = False,
) -> None:
    """Create a new isolated workspace from a branch.

    Creates a git worktree with a unique name (e.g., eager-turing) and
    sets up a Python virtual environment using uv.

    Use --attach to create a workspace for an existing branch without
    creating a new branch. The workspace name will match the branch name.

    \b
    Examples:
        agentspaces workspace create                      # From current HEAD
        agentspaces workspace create main                 # From main branch
        agentspaces workspace create -p "Fix auth bug"   # With purpose
        agentspaces workspace create --no-venv            # Skip venv setup
        agentspaces workspace create feature/auth --attach  # Attach to existing branch
    """
    try:
        if attach:
            workspace = _service.create(
                attach_branch=branch,
                purpose=purpose,
                python_version=python_version,
                setup_venv=not no_venv,
            )
        else:
            workspace = _service.create(
                base_branch=branch,
                purpose=purpose,
                python_version=python_version,
                setup_venv=not no_venv,
            )
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    if purpose:
        print_info(f"Purpose: {purpose}")

    print_workspace_created(
        name=workspace.name,
        path=str(workspace.path),
        base_branch=workspace.base_branch,
        python_version=workspace.python_version,
        has_venv=workspace.has_venv,
    )

    print_next_steps(
        workspace_name=workspace.name,
        workspace_path=str(workspace.path),
        has_venv=workspace.has_venv,
    )


@app.command("list")
def list_workspaces(
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Filter by project name"),
    ] = None,
    sort: Annotated[
        str,
        typer.Option("--sort", "-s", help="Sort by: name, created, branch"),
    ] = "name",
) -> None:
    """List all workspaces.

    Shows all git worktrees managed by agentspaces.

    \b
    Examples:
        agentspaces workspace list                    # List workspaces for current repo
        agentspaces workspace list -p myproject       # List workspaces for specific project
        agentspaces workspace list --sort created     # Sort by creation date (newest first)
        agentspaces workspace list -s branch          # Sort by branch name
    """
    # If no project specified, try to detect from current directory
    if project is None:
        try:
            project = _service.get_project_name()
        except WorkspaceError:
            print_error("Not in a git repository. Use --project to specify.")
            raise typer.Exit(1) from None

    try:
        workspaces = _service.list()
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    # Sort workspaces
    if sort == "created":
        # Sort by created_at, None values last, newest first
        workspaces.sort(key=lambda w: w.created_at or datetime.min, reverse=True)
    elif sort == "branch":
        workspaces.sort(key=lambda w: w.branch.lower())
    else:  # Default: sort by name
        workspaces.sort(key=lambda w: w.name.lower())

    print_workspace_table(workspaces, project)


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
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Remove a workspace and its branch.

    This removes the git worktree and deletes the associated branch.
    WARNING: This cannot be undone!

    \b
    Examples:
        agentspaces workspace remove eager-turing       # Remove with confirmation
        agentspaces workspace remove eager-turing -y    # Skip confirmation
        agentspaces workspace remove eager-turing -f    # Force remove dirty workspace
    """
    # Check we're not removing the current worktree
    try:
        project = _service.get_project_name()
        workspace_path = _service.get_workspace_path(project, name)
        current_path = Path.cwd().resolve()
        if current_path == workspace_path.resolve() or str(current_path).startswith(
            str(workspace_path.resolve())
        ):
            print_error("Cannot remove the current workspace. Change directory first.")
            raise typer.Exit(1)
    except (OSError, WorkspaceError):
        pass  # If we can't resolve paths, continue anyway

    # Confirm removal unless --yes is provided
    if not yes:
        print_warning(f"About to remove workspace '{name}' and its branch.")
        confirm = typer.confirm("Are you sure you want to continue?", default=False)
        if not confirm:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        _service.remove(name, force=force)
    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {name}")
        _suggest_similar_workspaces(name)
        raise typer.Exit(1) from None
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    print_workspace_removed(name)


def _suggest_similar_workspaces(name: str) -> None:
    """Print workspace suggestions and help message on not found."""
    try:
        workspaces = _service.list()
        suggestions = find_similar_names(name, [ws.name for ws in workspaces])
        print_did_you_mean(suggestions)
    except WorkspaceError:
        pass  # Don't fail on suggestion lookup
    print_info("Use 'agentspaces workspace list' to see available workspaces")


@app.command("status")
def status(
    name: Annotated[
        str,
        typer.Argument(help="Workspace name"),
    ],
) -> None:
    """Show detailed workspace status.

    Displays workspace state, git status, Python environment info,
    and timestamps.

    \b
    Examples:
        agentspaces workspace status eager-turing       # Status of specific workspace
    """
    try:
        workspace = _service.get(name)
    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {name}")
        _suggest_similar_workspaces(name)
        raise typer.Exit(1) from None
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    # Check git status
    is_dirty = False
    with contextlib.suppress(git.GitError):
        is_dirty = git.is_dirty(workspace.path)

    print_workspace_status(workspace, is_dirty=is_dirty)
