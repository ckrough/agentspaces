"""Terminal detection and navigation helpers for TUI."""

from __future__ import annotations

import os
import shlex
import subprocess  # nosec B404 - subprocess needed for Ghostty integration
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from rich.console import Console

if TYPE_CHECKING:
    from agentspaces.modules.workspace.service import WorkspaceInfo

__all__ = [
    "detect_terminal",
    "navigate_to_workspace",
]

logger = structlog.get_logger()


def detect_terminal() -> tuple[bool, str]:
    """Detect if running in Ghostty terminal.

    Returns:
        Tuple of (is_ghostty, shell_type).
        is_ghostty: True if running in Ghostty terminal
        shell_type: Name of current shell (e.g., 'bash', 'zsh', 'fish')
    """
    # Check TERM_PROGRAM environment variable (set by Ghostty)
    term_program = os.environ.get("TERM_PROGRAM", "")
    is_ghostty = term_program == "ghostty"

    # Detect shell type
    shell_path = os.environ.get("SHELL", "")
    shell_type = Path(shell_path).name if shell_path else "bash"

    logger.debug(
        "terminal_detected",
        is_ghostty=is_ghostty,
        shell_type=shell_type,
        term_program=term_program,
    )

    return is_ghostty, shell_type


def navigate_to_workspace(workspace: WorkspaceInfo) -> None:
    """Navigate to workspace - create Ghostty tab or print instructions.

    For Ghostty: Creates a new tab with CD, venv activation, and claude command.
    For other terminals: Prints commands for manual execution.

    Args:
        workspace: Workspace to navigate to.
    """
    is_ghostty, _shell_type = detect_terminal()

    # Build command sequence
    commands = [f"cd {shlex.quote(str(workspace.path))}"]

    if workspace.has_venv:
        venv_activate = workspace.path / ".venv" / "bin" / "activate"
        if venv_activate.exists():
            commands.append(f"source {shlex.quote(str(venv_activate))}")

    commands.append("claude")

    # Join with && for sequential execution
    full_command = " && ".join(commands)

    if is_ghostty:
        _navigate_ghostty(full_command, workspace.name)
    else:
        _navigate_fallback(commands, workspace.name)


def _navigate_ghostty(command: str, workspace_name: str) -> None:
    """Create new Ghostty tab and execute navigation command.

    Args:
        command: Full command to execute in new tab.
        workspace_name: Name of workspace (for logging).
    """
    try:
        # Create new Ghostty tab with command
        subprocess.Popen(  # nosec B603,B607
            ["ghostty", "+new-tab", command],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("ghostty_tab_created", workspace=workspace_name)
    except (FileNotFoundError, OSError) as e:
        logger.warning(
            "ghostty_tab_failed",
            workspace=workspace_name,
            error=str(e),
        )
        # Fallback to print mode
        _navigate_fallback(command.split(" && "), workspace_name)


def _navigate_fallback(commands: list[str], workspace_name: str) -> None:
    """Print navigation commands for manual execution.

    Args:
        commands: List of commands to execute.
        workspace_name: Name of workspace (for logging).
    """
    console = Console()

    console.print()
    console.print(f"[bold cyan]Navigate to workspace:[/bold cyan] {workspace_name}")
    console.print()
    console.print("[dim]Run these commands:[/dim]")

    for cmd in commands:
        console.print(f"  [yellow]{cmd}[/yellow]")

    console.print()
    console.print("[dim]TIP: Copy and paste the commands above[/dim]")

    logger.info("navigation_commands_printed", workspace=workspace_name)
