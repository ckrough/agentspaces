"""TUI command for interactive workspace management."""

from __future__ import annotations

import typer

from agentspaces.ui.app import WorkspacesTUI

__all__ = ["app"]

app = typer.Typer(
    name="tui",
    help="Interactive TUI for workspace management.",
    no_args_is_help=False,
)


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
        tui.run()
