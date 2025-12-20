"""Rich console output formatting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from agentspaces.infrastructure.git import WorktreeInfo

# Shared console instance
console = Console()
error_console = Console(stderr=True)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    error_console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]i[/blue] {message}")


def print_workspace_created(
    name: str,
    path: str,
    base_branch: str,
    *,
    python_version: str | None = None,
    has_venv: bool = False,
) -> None:
    """Print workspace creation summary."""
    lines = [
        f"[bold]Name:[/bold]     {name}",
        f"[bold]Location:[/bold] {path}",
        f"[bold]Branch:[/bold]   {name} (from {base_branch})",
    ]

    if has_venv:
        version_str = python_version or "default"
        lines.append(f"[bold]Python:[/bold]   {version_str} (.venv created)")
    elif python_version:
        lines.append(f"[bold]Python:[/bold]   {python_version}")

    panel = Panel(
        "\n".join(lines),
        title="[green]Workspace Created[/green]",
        border_style="green",
    )
    console.print(panel)


def print_workspace_table(workspaces: list[WorktreeInfo], project: str) -> None:
    """Print a table of workspaces.

    Args:
        workspaces: List of worktree info objects.
        project: Project name for the header.
    """
    if not workspaces:
        print_info(f"No workspaces found for project: {project}")
        return

    table = Table(title=f"Workspaces for {project}")
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Path")
    table.add_column("Type", style="dim")

    for wt in workspaces:
        wt_type = "main" if wt.is_main else "worktree"
        table.add_row(
            wt.path.name,
            wt.branch or "(detached)",
            str(wt.path),
            wt_type,
        )

    console.print(table)


def print_workspace_removed(name: str) -> None:
    """Print workspace removal confirmation."""
    print_success(f"Workspace '{name}' removed")
