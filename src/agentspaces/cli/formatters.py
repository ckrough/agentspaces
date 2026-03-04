"""Rich console output formatting utilities."""

from __future__ import annotations

import shlex
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from agentspaces.infrastructure.beads import BeadsIssue
    from agentspaces.modules.workspace.service import WorkspaceInfo

__all__ = [
    "console",
    "error_console",
    "format_relative_time",
    "print_did_you_mean",
    "print_error",
    "print_info",
    "print_issue_next_steps",
    "print_next_steps",
    "print_success",
    "print_warning",
    "print_workspace_created",
    "print_workspace_created_from_issue",
    "print_workspace_removed",
    "print_workspace_status",
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


def print_did_you_mean(suggestions: list[str]) -> None:
    """Print 'Did you mean?' suggestions.

    Args:
        suggestions: List of similar names to suggest.
    """
    if not suggestions:
        return

    console.print()
    console.print("[dim]Did you mean?[/dim]")
    for name in suggestions:
        console.print(f"  [cyan]{name}[/cyan]")


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


def print_next_steps(workspace_path: str, has_venv: bool) -> None:
    """Print actionable next steps after workspace creation.

    Args:
        workspace_path: Path to the workspace directory.
        has_venv: Whether a virtual environment was created.
    """
    # Quote path for shell safety
    quoted_path = shlex.quote(workspace_path)

    # Combine cd and venv activation into single command
    if has_venv:
        steps = [f"cd {quoted_path} && source .venv/bin/activate"]
    else:
        steps = [f"cd {quoted_path}"]

    lines = [f"  {i + 1}. [cyan]{step}[/cyan]" for i, step in enumerate(steps)]
    panel = Panel(
        "\n".join(lines),
        title="[blue]Next Steps[/blue]",
        border_style="blue",
    )
    console.print(panel)


def print_workspace_created_from_issue(
    issue: BeadsIssue,
    workspace: WorkspaceInfo,
) -> None:
    """Print workspace creation summary for issue-based workspace.

    Shows issue context prominently and guides user to claude invocation.

    Args:
        issue: Beads issue the workspace was created for.
        workspace: Created workspace information.
    """
    # Issue context header
    console.print()
    console.print(f"[bold cyan]Issue:[/bold cyan] {issue.id}")
    console.print(f"[bold]Title:[/bold] {issue.title}")
    console.print(
        f"[bold]Type:[/bold] {issue.issue_type}  [bold]Priority:[/bold] {issue.priority}"
    )
    console.print()

    # Workspace details panel
    lines = [
        f"[bold]Name:[/bold]     {workspace.name}",
        f"[bold]Location:[/bold] {workspace.path}",
        f"[bold]Branch:[/bold]   {workspace.branch} (from {workspace.base_branch})",
    ]

    if workspace.has_venv:
        version_str = workspace.python_version or "default"
        lines.append(f"[bold]Python:[/bold]   {version_str} (.venv created)")
    elif workspace.python_version:
        lines.append(f"[bold]Python:[/bold]   {workspace.python_version}")

    panel = Panel(
        "\n".join(lines),
        title="[green]Workspace Created[/green]",
        border_style="green",
    )
    console.print(panel)


def print_issue_next_steps(
    workspace_path: str,
    issue_id: str,
    has_venv: bool,
) -> None:
    """Print next steps for issue-based workspace.

    Displays a copyable command string that includes:
    - cd to workspace
    - venv activation (if applicable)
    - claude invocation with 'plan' prompt and issue ID

    Args:
        workspace_path: Path to the workspace directory.
        issue_id: Beads issue ID.
        has_venv: Whether a virtual environment was created.
    """
    # Quote values for shell safety
    quoted_path = shlex.quote(workspace_path)
    quoted_issue = shlex.quote(issue_id)

    # Build command string
    commands = [f"cd {quoted_path}"]
    if has_venv:
        commands.append("source .venv/bin/activate")
    commands.append(f"claude 'plan' {quoted_issue}")

    command_str = " && ".join(commands)

    # Display as copyable command
    panel = Panel(
        f"[cyan]{command_str}[/cyan]",
        title="[blue]Next Steps[/blue]",
        border_style="blue",
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


def print_workspace_status(
    workspace: WorkspaceInfo,
    *,
    is_dirty: bool = False,
) -> None:
    """Print detailed workspace status panel.

    Args:
        workspace: Workspace information.
        is_dirty: Whether the workspace has uncommitted changes.
    """
    # Status badge
    status_line = "[yellow]● dirty[/yellow]" if is_dirty else "[green]● clean[/green]"

    lines = [
        f"[bold]Status:[/bold]    {status_line}",
        f"[bold]Name:[/bold]      {workspace.name}",
        f"[bold]Path:[/bold]      {workspace.path}",
        f"[bold]Branch:[/bold]    {workspace.branch}",
        f"[bold]Base:[/bold]      {workspace.base_branch or '-'}",
    ]

    if workspace.purpose:
        lines.append(f"[bold]Purpose:[/bold]   {workspace.purpose}")

    lines.append("")
    lines.append("[bold]Python Environment[/bold]")
    if workspace.has_venv:
        version_str = workspace.python_version or "unknown"
        lines.append(f"  [green]✓[/green] venv: Python {version_str}")
    else:
        lines.append("  [dim]○ no venv[/dim]")

    lines.append("")
    lines.append("[bold]Timestamps[/bold]")
    lines.append(f"  Created:  {format_relative_time(workspace.created_at)}")

    panel = Panel(
        "\n".join(lines),
        title=f"[cyan]{workspace.name}[/cyan]",
        border_style="cyan",
    )
    console.print(panel)
