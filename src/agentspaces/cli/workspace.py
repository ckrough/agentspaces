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
    print_success,
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
        typer.Argument(help="Base branch to create workspace from"),
    ] = "HEAD",
    purpose: Annotated[
        str | None,
        typer.Option("--purpose", "-p", help="Purpose/description for this workspace"),
    ] = None,
    python_version: Annotated[
        str | None,
        typer.Option("--python", help="Python version for venv (e.g., 3.12)"),
    ] = None,
    no_venv: Annotated[
        bool,
        typer.Option("--no-venv", help="Skip virtual environment creation"),
    ] = False,
) -> None:
    """Create a new isolated workspace from a branch.

    Creates a git worktree with a unique name (e.g., eager-turing) and
    sets up a Python virtual environment using uv.

    \b
    Examples:
        as workspace create                      # From current HEAD
        as workspace create main                 # From main branch
        as workspace create -p "Fix auth bug"   # With purpose
        as workspace create --no-venv            # Skip venv setup
    """
    try:
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

    Shows all git worktrees managed by AgentSpaces.

    \b
    Examples:
        as workspace list                    # List workspaces for current repo
        as workspace list -p myproject       # List workspaces for specific project
        as workspace list --sort created     # Sort by creation date (newest first)
        as workspace list -s branch          # Sort by branch name
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
        as workspace remove eager-turing       # Remove with confirmation
        as workspace remove eager-turing -y    # Skip confirmation
        as workspace remove eager-turing -f    # Force remove dirty workspace
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
        # Try to suggest similar workspace names
        try:
            workspaces = _service.list()
            suggestions = find_similar_names(name, [ws.name for ws in workspaces])
            print_did_you_mean(suggestions)
        except WorkspaceError:
            pass  # Don't fail on suggestion lookup
        print_info("Use 'as workspace list' to see available workspaces")
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
    print_info("Use 'as workspace list' to see available workspaces")


@app.command("status")
def status(
    name: Annotated[
        str | None,
        typer.Argument(help="Workspace name (uses active if not specified)"),
    ] = None,
) -> None:
    """Show detailed workspace status.

    Displays workspace state, git status, Python environment info,
    and timestamps.

    \b
    Examples:
        as workspace status                    # Status of active workspace
        as workspace status eager-turing       # Status of specific workspace
    """
    # Determine which workspace to show
    if name is None:
        active = _service.get_active()
        if active is None:
            print_error("No workspace specified and no active workspace set.")
            print_info(
                "Use 'as workspace status <name>' or 'as workspace activate <name>'"
            )
            raise typer.Exit(1)
        name = active.name

    try:
        workspace = _service.get(name)
    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {name}")
        _suggest_similar_workspaces(name)
        raise typer.Exit(1) from None
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    # Check if this is the active workspace
    is_active = False
    try:
        active = _service.get_active()
        is_active = active is not None and active.name == name
    except WorkspaceError:
        pass

    # Check git status
    is_dirty = False
    with contextlib.suppress(git.GitError):
        is_dirty = git.is_dirty(workspace.path)

    print_workspace_status(workspace, is_dirty=is_dirty, is_active=is_active)


@app.command("activate")
def activate(
    name: Annotated[
        str,
        typer.Argument(help="Workspace name to set as active"),
    ],
) -> None:
    """Set a workspace as the active workspace.

    The active workspace is used as the default for commands like
    'as agent launch' when no workspace is specified.

    \b
    Examples:
        as workspace activate eager-turing     # Set as active
        as workspace current                   # Show current active
    """
    try:
        _service.set_active(name)
    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {name}")
        _suggest_similar_workspaces(name)
        raise typer.Exit(1) from None
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    print_success(f"Active workspace set to: {name}")


@app.command("current")
def current() -> None:
    """Show the currently active workspace.

    The active workspace is used as the default for commands like
    'as agent launch' when no workspace is specified.

    \b
    Examples:
        as workspace current                   # Show active workspace
        as workspace activate eager-turing     # Set active workspace
    """
    try:
        active = _service.get_active()
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    if active is None:
        print_info("No active workspace set.")
        print_info("Use 'as workspace activate <name>' to set one.")
        raise typer.Exit(0)

    print_info(f"Active workspace: [cyan]{active.name}[/cyan]")
    print_info(f"Path: {active.path}")


@app.command("sync")
def sync(
    name: Annotated[
        str | None,
        typer.Argument(help="Workspace name (uses active if not specified)"),
    ] = None,
) -> None:
    """Sync workspace dependencies with uv sync.

    Runs 'uv sync --all-extras' in the workspace to install or update
    dependencies from pyproject.toml.

    \b
    Examples:
        as workspace sync                      # Sync active workspace
        as workspace sync eager-turing         # Sync specific workspace
    """
    try:
        workspace = _service.sync_deps(name)
    except WorkspaceNotFoundError as e:
        print_error(f"Workspace not found: {e}")
        if name:
            _suggest_similar_workspaces(name)
        raise typer.Exit(1) from None
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    print_success(f"Dependencies synced for: {workspace.name}")
