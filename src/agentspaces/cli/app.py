"""Main CLI application."""

from __future__ import annotations

import typer

from agentspaces import __version__
from agentspaces.cli import agent, workspace
from agentspaces.cli.context import CLIContext
from agentspaces.infrastructure.logging import configure_logging

# Main application
app = typer.Typer(
    name="agentspaces",
    help="Workspace orchestration tool for AI coding agents.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Register subcommand groups
app.add_typer(agent.app, name="agent")
app.add_typer(workspace.app, name="workspace")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"agentspaces {__version__}")
        raise typer.Exit()


@app.callback()
def main(
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
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress info messages.",
    ),
) -> None:
    """AgentSpaces: Workspace orchestration for AI coding agents.

    Create isolated workspaces, launch agents with context, and orchestrate
    multi-step workflows.
    """
    # Validate mutually exclusive flags
    if verbose and quiet:
        import sys

        from agentspaces.cli.formatters import print_error

        print_error("Cannot use both --verbose and --quiet")
        sys.exit(1)

    # Set up CLI context for verbosity control
    ctx = CLIContext.get()
    ctx.verbose = verbose
    ctx.quiet = quiet

    # Configure logging (debug only when verbose)
    configure_logging(debug=verbose)
