"""Terminal detection and navigation helpers for TUI."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess  # nosec B404 - subprocess needed for Ghostty integration
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from rich.console import Console

if TYPE_CHECKING:
    from agentspaces.modules.workspace.service import WorkspaceInfo

__all__ = [
    "detect_terminal",
    "is_ghostty_available",
    "navigate_to_workspace",
]

logger = structlog.get_logger()


def is_ghostty_available() -> bool:
    """Check if Ghostty terminal is installed and available.

    Returns:
        True if ghostty command exists in PATH.
    """
    return shutil.which("ghostty") is not None


def detect_terminal() -> tuple[bool, str]:
    """Detect if running in Ghostty terminal and if Ghostty is available.

    Returns:
        Tuple of (is_ghostty, shell_type).
        is_ghostty: True if running in Ghostty terminal AND ghostty command is available
        shell_type: Name of current shell (e.g., 'bash', 'zsh', 'fish')
    """
    # Check TERM_PROGRAM environment variable (set by Ghostty)
    term_program = os.environ.get("TERM_PROGRAM", "")
    is_ghostty_env = term_program == "ghostty"
    is_ghostty_installed = is_ghostty_available()

    # Only consider Ghostty available if both conditions met
    is_ghostty = is_ghostty_env and is_ghostty_installed

    # Detect shell type
    shell_path = os.environ.get("SHELL", "")
    shell_type = Path(shell_path).name if shell_path else "bash"

    logger.debug(
        "terminal_detected",
        is_ghostty=is_ghostty,
        is_ghostty_env=is_ghostty_env,
        is_ghostty_installed=is_ghostty_installed,
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
        _navigate_ghostty(full_command, commands, workspace.name)
    else:
        _navigate_fallback(commands, workspace.name)


def _navigate_ghostty(command: str, commands: list[str], workspace_name: str) -> None:
    """Create new Ghostty tab and execute navigation command.

    Args:
        command: Full command to execute in new tab.
        commands: Original command list for fallback display.
        workspace_name: Name of workspace (for logging).
    """
    try:
        # Ghostty requires explicit shell invocation for compound commands
        shell = os.environ.get("SHELL", "/bin/bash")

        # Use subprocess.run with proper error handling
        subprocess.run(  # nosec B603,B607
            ["ghostty", "--command", shell, "-c", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        logger.info("ghostty_tab_created", workspace=workspace_name)

    except FileNotFoundError:
        logger.warning(
            "ghostty_not_found",
            workspace=workspace_name,
            hint="Ghostty not installed or not in PATH",
        )
        _navigate_fallback(commands, workspace_name)

    except subprocess.TimeoutExpired:
        logger.warning(
            "ghostty_timeout",
            workspace=workspace_name,
        )
        _navigate_fallback(commands, workspace_name)

    except subprocess.CalledProcessError as e:
        logger.warning(
            "ghostty_failed",
            workspace=workspace_name,
            exit_code=e.returncode,
            stderr=e.stderr,
        )
        _navigate_fallback(commands, workspace_name)


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
