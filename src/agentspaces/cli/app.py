"""Main CLI application."""

from __future__ import annotations

import typer

from agentspaces import __version__
from agentspaces.cli import docs, project, tui, workspace
from agentspaces.infrastructure.logging import configure_logging

# Main application
app = typer.Typer(
    name="agentspaces",
    help="Workspace orchestration tool for AI coding agents.",
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Register subcommand groups
app.add_typer(docs.app, name="docs")
app.add_typer(project.app, name="project")
app.add_typer(tui.app, name="tui")
app.add_typer(workspace.app, name="workspace")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"agentspaces {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: ARG001 - handled by callback
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show debug output.",
    ),
) -> None:
    """agentspaces: Workspace orchestration for AI coding agents.

    Create isolated workspaces for development tasks.
    """
    # Configure logging (debug only when verbose)
    configure_logging(debug=verbose)

    # Launch TUI if no subcommand provided
    if ctx.invoked_subcommand is None:
        tui.main(ctx)
