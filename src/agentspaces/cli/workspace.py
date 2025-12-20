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
        typer.Option("--python-version", help="Python version for venv (e.g., 3.12)"),
    ] = None,
) -> None:
    """Create a new isolated workspace from a branch.

    Creates a git worktree with a unique name (e.g., eager-turing) and
    optionally sets up a Python virtual environment.
    """
    try:
        workspace = _service.create(base_branch=branch, purpose=purpose)
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    if purpose:
        print_info(f"Purpose: {purpose}")

    # TODO: Set up Python venv if detected/requested (Increment 2)

    print_workspace_created(
        name=workspace.name,
        path=str(workspace.path),
        base_branch=workspace.base_branch,
        python_version=python_version,
    )

    # Print hint about changing to the workspace
    print_info(f"cd {workspace.path}")


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
            project = _service.get_project_name()
        except WorkspaceError:
            print_error("Not in a git repository. Use --project to specify.")
            raise typer.Exit(1) from None

    try:
        worktrees = _service.list()
    except WorkspaceError as e:
        print_error(str(e))
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
    # Check we're not removing the current worktree
    try:
        project = _service.get_project_name()
        workspace_path = _service._resolver.workspace_dir(project, name)
        current_path = Path.cwd().resolve()
        if current_path == workspace_path.resolve() or str(current_path).startswith(
            str(workspace_path.resolve())
        ):
            print_error("Cannot remove the current workspace. Change directory first.")
            raise typer.Exit(1)
    except (OSError, WorkspaceError):
        pass  # If we can't resolve paths, continue anyway

    try:
        _service.remove(name, force=force)
    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {name}")
        print_info("Use 'as workspace list' to see available workspaces")
        raise typer.Exit(1) from None
    except WorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    print_workspace_removed(name)
