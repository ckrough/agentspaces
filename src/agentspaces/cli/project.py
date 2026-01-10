"""Project initialization CLI commands."""

from __future__ import annotations

import keyword
import re
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel

from agentspaces.infrastructure import git
from agentspaces.infrastructure.design import (
    DesignError,
    render_design_template,
    render_language_template,
)
from agentspaces.infrastructure.skeleton import PYTHON_STRUCTURE, SKELETON_STRUCTURE

app = typer.Typer(
    name="project",
    help="Initialize new projects with templates and best practices.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


def _is_valid_python_package_name(name: str) -> bool:
    """Check if name is a valid Python package name."""
    # Must start with letter, contain only letters, numbers, underscores
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name))


def _to_package_name(project_name: str) -> str:
    """Convert project name to valid Python package name."""
    # Replace spaces and hyphens with underscores, lowercase
    package_name = project_name.lower().replace(" ", "_").replace("-", "_")
    # Remove any invalid characters
    package_name = re.sub(r"[^a-z0-9_]", "", package_name)
    # Ensure it starts with a letter
    if package_name and not package_name[0].isalpha():
        package_name = "pkg_" + package_name
    package_name = package_name or "project"
    # Avoid Python keywords
    if keyword.iskeyword(package_name):
        package_name = f"{package_name}_pkg"
    return package_name


def _validate_output_path(output_path: Path, cwd: Path) -> None:
    """Validate that output path stays within the project directory.

    Args:
        output_path: Path to validate.
        cwd: Project root directory.

    Raises:
        ValueError: If path escapes project directory.
    """
    try:
        output_path.resolve().relative_to(cwd.resolve())
    except ValueError as e:
        raise ValueError(
            f"Invalid path escapes project directory: {output_path}"
        ) from e


def _is_directory_empty(path: Path) -> bool:
    """Check if directory is empty (ignoring hidden files like .git)."""
    if not path.exists():
        return True
    # Allow .git directory but nothing else
    contents = list(path.iterdir())
    non_git = [f for f in contents if f.name != ".git"]
    return len(non_git) == 0


def _print_preview(
    project_name: str,
    project_description: str,
    python: bool,
    python_version: str,
    will_init_git: bool,
) -> None:
    """Print preview of what will be created."""
    console.print("\n[bold]Project Configuration[/bold]")
    console.print(f"  Name:        [cyan]{project_name}[/cyan]")
    console.print(f"  Description: {project_description}")
    if python:
        package_name = _to_package_name(project_name)
        console.print(f"  Language:    [green]Python {python_version}[/green]")
        console.print(f"  Package:     [dim]{package_name}[/dim]")

    console.print("\n[bold]Files to create:[/bold]")

    # Base skeleton
    console.print("\n  [dim]Base skeleton:[/dim]")
    for relative_path in sorted(SKELETON_STRUCTURE.values()):
        console.print(f"    [dim]•[/dim] {relative_path}")

    # Python language pack
    if python:
        package_name = _to_package_name(project_name)
        console.print("\n  [dim]Python language pack:[/dim]")
        for relative_path in sorted(PYTHON_STRUCTURE.values()):
            # Replace {package_name} placeholder
            display_path = relative_path.replace("{package_name}", package_name)
            console.print(f"    [dim]•[/dim] {display_path}")

    if will_init_git:
        console.print("\n[blue]Git repository will be initialized.[/blue]")

    console.print()


def _print_success(
    path: Path,
    created_count: int,
    python: bool,
    python_version: str,
) -> None:
    """Print success message with next steps."""
    lines = [
        f"[bold]Location:[/bold] {path}",
        f"[bold]Files:[/bold]    {created_count} created",
    ]
    if python:
        lines.append(f"[bold]Python:[/bold]   {python_version}")

    panel = Panel(
        "\n".join(lines),
        title="[green]Project Created[/green]",
        border_style="green",
    )
    console.print(panel)

    # Next steps
    next_steps = ["cd " + str(path)]
    if python:
        next_steps.extend(
            [
                "uv sync --all-extras",
                "uv run pre-commit install",
            ]
        )
    next_steps.append("Start coding!")

    step_lines = [
        f"  {i + 1}. [cyan]{step}[/cyan]" for i, step in enumerate(next_steps)
    ]
    next_panel = Panel(
        "\n".join(step_lines),
        title="[blue]Next Steps[/blue]",
        border_style="blue",
    )
    console.print(next_panel)


@app.command("create")
def create(
    project_name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Project name"),
    ] = None,
    project_description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Project description"),
    ] = None,
    python: Annotated[
        bool,
        typer.Option("--python", "-p", help="Include Python language pack"),
    ] = False,
    python_version: Annotated[
        str,
        typer.Option("--python-version", help="Python version (default: 3.13)"),
    ] = "3.13",
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Initialize a new project in the current directory.

    Creates a complete project skeleton with documentation templates,
    development standards, and optionally a Python language pack.

    The current directory must be empty (or contain only .git).

    \b
    Examples:
        agentspaces project create -n "My Project" -d "A cool project"
        agentspaces project create --python -n "CLI Tool" -d "Command-line app"
        agentspaces project create -p -n "api" -d "REST API" --python-version 3.12
        agentspaces project create -y -n "quick" -d "Quick start"  # Skip confirmation
    """
    cwd = Path.cwd()

    # Validate directory is empty
    if not _is_directory_empty(cwd):
        error_console.print(
            "[red]✗[/red] Directory is not empty. "
            "Project initialization requires an empty directory."
        )
        console.print("[dim]Create a new directory and cd into it first.[/dim]")
        raise typer.Exit(1)

    # Prompt for required values if not provided
    if not project_name:
        project_name = typer.prompt("Project name")
    if not project_description:
        project_description = typer.prompt("Project description")

    # Validate Python package name if using Python pack
    if python:
        package_name = _to_package_name(project_name)
        if not _is_valid_python_package_name(package_name):
            error_console.print(
                f"[red]✗[/red] Cannot create valid Python package name from '{project_name}'"
            )
            raise typer.Exit(1)

    # Check if we need to init git
    will_init_git = not git.is_git_repo(cwd)

    # Show preview and confirm
    if not yes:
        _print_preview(
            project_name=project_name,
            project_description=project_description,
            python=python,
            python_version=python_version,
            will_init_git=will_init_git,
        )

        if not typer.confirm("Continue?", default=True):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    # Initialize git if needed
    if will_init_git:
        try:
            git.init(cwd)
            console.print("[green]✓[/green] Initialized git repository")
        except git.GitError as e:
            error_console.print(f"[red]✗[/red] Failed to initialize git: {e}")
            raise typer.Exit(1) from e

    # Build template context
    context: dict[str, Any] = {
        "project_name": project_name,
        "project_description": project_description,
    }

    if python:
        context["python_version"] = python_version
        context["package_name"] = _to_package_name(project_name)

    # Track results
    created: list[Path] = []
    failed: list[tuple[str, str]] = []

    # Render skeleton templates
    for template_name, relative_path in SKELETON_STRUCTURE.items():
        output_path = cwd / relative_path
        try:
            _validate_output_path(output_path, cwd)
            # Skip frontmatter for CLAUDE.md (users see it as project doc, not template metadata)
            preserve_frontmatter = template_name != "claude-md"
            render_design_template(
                template_name, context, output_path, preserve_frontmatter
            )
            created.append(output_path)
        except (DesignError, ValueError) as e:
            failed.append((template_name, str(e)))

    # Render Python language pack if requested
    if python:
        package_name = _to_package_name(project_name)
        for template_name, relative_path in PYTHON_STRUCTURE.items():
            # Replace {package_name} placeholder in path
            actual_path = relative_path.replace("{package_name}", package_name)
            output_path = cwd / actual_path
            try:
                _validate_output_path(output_path, cwd)
                render_language_template("python", template_name, context, output_path)
                created.append(output_path)
            except (DesignError, ValueError) as e:
                failed.append((template_name, str(e)))

    # Report results
    if failed:
        console.print()
        for template_name, error in failed:
            error_console.print(f"[red]✗[/red] {template_name}: {error}")

    if created:
        _print_success(
            path=cwd,
            created_count=len(created),
            python=python,
            python_version=python_version,
        )

    if failed and not created:
        error_console.print("[red]✗[/red] Project creation failed")
        raise typer.Exit(1)
