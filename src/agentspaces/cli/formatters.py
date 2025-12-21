"""Rich console output formatting utilities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from agentspaces.modules.workspace.service import WorkspaceInfo

__all__ = [
    "console",
    "error_console",
    "format_relative_time",
    "print_error",
    "print_info",
    "print_success",
    "print_warning",
    "print_workspace_created",
    "print_workspace_removed",
    "print_workspace_table",
]

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


def format_relative_time(dt: datetime | None) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format.

    Returns:
        Human-readable relative time (e.g., "2 hours ago").
    """
    if dt is None:
        return "-"

    # Ensure both datetimes are timezone-aware
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    if seconds < 604800:
        days = seconds // 86400
        return f"{days}d ago"

    # For older dates, show the date
    return dt.strftime("%Y-%m-%d")


def _truncate(text: str, max_length: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def print_workspace_table(workspaces: list[WorkspaceInfo], project: str) -> None:
    """Print a table of workspaces.

    Args:
        workspaces: List of workspace info objects.
        project: Project name for the header.
    """
    if not workspaces:
        print_info(f"No workspaces found for project: {project}")
        return

    table = Table(title=f"Workspaces for {project}")
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Purpose", style="dim", max_width=40)
    table.add_column("Created", style="dim")
    table.add_column("Path")

    for ws in workspaces:
        purpose = _truncate(ws.purpose, 40) if ws.purpose else "-"
        table.add_row(
            ws.name,
            ws.branch or "(detached)",
            purpose,
            format_relative_time(ws.created_at),
            str(ws.path),
        )

    console.print(table)


def print_workspace_removed(name: str) -> None:
    """Print workspace removal confirmation."""
    print_success(f"Workspace '{name}' removed")
