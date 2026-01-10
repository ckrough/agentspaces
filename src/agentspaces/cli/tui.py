"""TUI command for interactive workspace management."""

from __future__ import annotations

import json
import os
import shlex
import subprocess  # nosec B404 - subprocess needed for beads integration
from typing import TYPE_CHECKING

import structlog
import typer

from agentspaces.ui.app import WorkspacesTUI

if TYPE_CHECKING:
    from agentspaces.modules.workspace.service import WorkspaceInfo

__all__ = ["app"]

logger = structlog.get_logger()

app = typer.Typer(
    name="tui",
    help="Interactive TUI for workspace management.",
    no_args_is_help=False,
)


def _get_tab_title(workspace: WorkspaceInfo) -> str:
    """Get tab title from beads issue or workspace name.

    If workspace purpose contains a beads issue ID, fetches the issue
    title from beads. Otherwise falls back to workspace name.

    Args:
        workspace: Workspace to get title for.

    Returns:
        Tab title string (truncated to 30 chars).
    """
    # Check if purpose looks like a beads issue ID
    if workspace.purpose and workspace.purpose.startswith("agentspaces-"):
        try:
            result = subprocess.run(  # nosec B603,B607
                ["bd", "show", workspace.purpose, "--json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                issues = json.loads(result.stdout)
                if issues and isinstance(issues, list) and "title" in issues[0]:
                    title: str = str(issues[0]["title"])
                    logger.debug(
                        "tab_title_from_beads",
                        issue_id=workspace.purpose,
                        title=title,
                    )
                    return title[:30]
        except subprocess.TimeoutExpired:
            logger.warning("beads_timeout", issue_id=workspace.purpose)
        except json.JSONDecodeError:
            logger.warning("beads_json_error", issue_id=workspace.purpose)
        except (KeyError, IndexError, TypeError):
            logger.warning("beads_data_error", issue_id=workspace.purpose)

    # Fallback to workspace name
    return workspace.name[:30]


def _build_navigation_commands(workspace: WorkspaceInfo, tab_title: str) -> str:
    """Build shell command string for workspace navigation.

    Args:
        workspace: Workspace to navigate to.
        tab_title: Title to set for the terminal tab.

    Returns:
        Shell command string joining all navigation commands with &&.
    """
    commands = []

    # CD to workspace
    commands.append(f"cd {shlex.quote(str(workspace.path))}")

    # Set tab title via OSC escape sequence (OSC 1 sets icon/tab name)
    # Use printf with %s and shlex.quote to safely insert the title
    quoted_title = shlex.quote(tab_title)
    commands.append(f"printf '\\033]1;%s\\a' {quoted_title}")

    # Activate venv if present
    if workspace.has_venv:
        venv_activate = workspace.path / ".venv" / "bin" / "activate"
        if venv_activate.exists():
            commands.append(f"source {shlex.quote(str(venv_activate))}")

    # Launch claude with plan prompt (if issue ID exists in purpose)
    if workspace.purpose and workspace.purpose.startswith("agentspaces-"):
        # Use shlex.quote to prevent shell injection via workspace.purpose
        quoted_purpose = shlex.quote(workspace.purpose)
        commands.append(f"claude 'plan' {quoted_purpose}")
    else:
        commands.append("claude")

    return " && ".join(commands)


def _execute_workspace_navigation(workspace: WorkspaceInfo) -> None:
    """Execute shell commands to navigate to workspace.

    Replaces current process with shell running navigation commands.
    This function does not return.

    Args:
        workspace: Workspace to navigate to.
    """
    tab_title = _get_tab_title(workspace)
    shell = os.environ.get("SHELL", "/bin/bash")
    commands = _build_navigation_commands(workspace, tab_title)

    logger.info(
        "executing_workspace_navigation",
        workspace=workspace.name,
        tab_title=tab_title,
        shell=shell,
    )

    # Replace current process with shell running commands
    # This does not return - the Python process is replaced
    # nosec B606 - intentional shell execution for workspace navigation
    os.execvp(shell, [shell, "-c", commands])  # nosec B606


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Launch interactive TUI for browsing and managing workspaces.

    Features:
    - Browse workspaces with arrow keys
    - Navigate to workspace (CD + activate venv + start claude)
    - Remove single or multiple workspaces
    - Preview workspace details before actions

    Keybindings:
        ↑/↓         : Navigate list
        Space       : Toggle selection (for bulk removal)
        Enter       : Navigate to workspace
        d           : Remove selected workspace(s)
        r           : Refresh workspace list
        q           : Quit

    Examples:
        agentspaces tui              # Launch TUI
    """
    # If no subcommand provided, launch TUI
    if ctx.invoked_subcommand is None:
        tui = WorkspacesTUI()
        result = tui.run()

        # If user selected a workspace (pressed Enter), navigate to it
        if result is not None:
            _execute_workspace_navigation(result)
