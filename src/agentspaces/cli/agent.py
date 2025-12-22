"""Agent management CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agentspaces.cli.formatters import (
    print_did_you_mean,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from agentspaces.infrastructure.similarity import find_similar_names
from agentspaces.modules.agent.launcher import (
    AgentError,
    AgentLauncher,
    AgentNotFoundError,
)
from agentspaces.modules.workspace.service import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceService,
)

app = typer.Typer(
    name="agent",
    help="Launch AI coding agents in workspaces.",
    no_args_is_help=True,
)

# Shared launcher instance
_launcher = AgentLauncher()


@app.command("launch")
def launch(
    workspace: Annotated[
        str | None,
        typer.Argument(
            help="Workspace name (omit to auto-detect from current directory)"
        ),
    ] = None,
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-p", help="Initial prompt/instruction for the agent"),
    ] = None,
    use_purpose: Annotated[
        bool,
        typer.Option(
            "--use-purpose",
            help="Use workspace purpose as initial prompt (mutually exclusive with --prompt)",
        ),
    ] = False,
    plan_mode: Annotated[
        bool,
        typer.Option(
            "--plan-mode",
            help="Enable plan mode (explore before making changes)",
        ),
    ] = False,
    no_plan_mode: Annotated[
        bool,
        typer.Option(
            "--no-plan-mode",
            help="Disable plan mode even if enabled in config",
        ),
    ] = False,
) -> None:
    """Launch Claude Code in a workspace.

    If no workspace is specified, attempts to detect if currently in a
    workspace directory.

    \b
    Examples:
        agentspaces agent launch eager-turing       # Launch in specific workspace
        agentspaces agent launch                    # Auto-detect from current directory
        agentspaces agent launch -p "Fix auth bug"  # With initial prompt
        agentspaces agent launch --use-purpose      # Use workspace purpose as prompt
    """
    # Validate mutually exclusive flags
    if use_purpose and prompt:
        print_error("Cannot use both --prompt and --use-purpose")
        print_info(
            "Choose one: provide a prompt with -p, or use workspace purpose with --use-purpose"
        )
        raise typer.Exit(1)

    if plan_mode and no_plan_mode:
        print_error("Cannot use both --plan-mode and --no-plan-mode")
        print_info("Choose one or omit both to use config default")
        raise typer.Exit(1)

    # Handle --use-purpose flag
    effective_prompt = prompt
    if use_purpose:
        if not workspace:
            print_error("--use-purpose requires a workspace name")
            print_info(
                "Specify workspace: agentspaces agent launch <workspace-name> --use-purpose"
            )
            raise typer.Exit(1)

        try:
            service = WorkspaceService()
            ws_info = service.get(workspace)
            if ws_info.purpose:
                effective_prompt = ws_info.purpose
                print_info(f"Using workspace purpose: {effective_prompt}")
            else:
                print_error("Workspace has no purpose set")
                print_info("Create workspace with --purpose or use --prompt instead")
                raise typer.Exit(1)
        except WorkspaceNotFoundError:
            print_error(f"Workspace not found: {workspace}")
            _suggest_similar_workspaces(workspace)
            print_info("Use 'agentspaces workspace list' to see available workspaces")
            raise typer.Exit(1) from None
        except WorkspaceError as e:
            print_error(f"Could not read workspace: {e}")
            raise typer.Exit(1) from None

    # Determine plan mode setting: CLI flag > config > default
    from agentspaces.cli.context import CLIContext

    effective_plan_mode = False
    if no_plan_mode:
        effective_plan_mode = False  # Explicit override to disable
    elif plan_mode:
        effective_plan_mode = True  # Explicit override to enable
    else:
        # Use config default
        ctx = CLIContext.get()
        config = ctx.get_config()
        effective_plan_mode = config.plan_mode_by_default

    try:
        # Show which workspace we're launching in
        if workspace:
            print_info(f"Launching Claude Code in '{workspace}'...")
        else:
            print_info("Launching Claude Code (auto-detecting workspace)...")

        result = _launcher.launch_claude(
            workspace,
            prompt=effective_prompt,
            plan_mode=effective_plan_mode,
            cwd=Path.cwd(),
        )

        if result.exit_code == 0:
            print_success(f"Claude Code session ended in '{result.workspace_name}'")
        else:
            print_warning(f"Claude Code exited with code {result.exit_code}")

    except AgentNotFoundError as e:
        print_error(str(e))
        print_info("Visit https://claude.ai/download to install Claude Code")
        raise typer.Exit(1) from e

    except WorkspaceNotFoundError:
        print_error(f"Workspace not found: {workspace}")
        _suggest_similar_workspaces(workspace)
        print_info("Use 'agentspaces workspace list' to see available workspaces")
        raise typer.Exit(1) from None

    except (AgentError, WorkspaceError) as e:
        print_error(str(e))
        raise typer.Exit(1) from e


def _suggest_similar_workspaces(workspace_name: str | None) -> None:
    """Try to suggest similar workspace names.

    Args:
        workspace_name: The workspace name that was not found.
    """
    if not workspace_name:
        return

    try:
        service = WorkspaceService()
        workspaces = service.list()
        suggestions = find_similar_names(workspace_name, [ws.name for ws in workspaces])
        print_did_you_mean(suggestions)
    except WorkspaceError:
        pass  # Don't fail on suggestion lookup
