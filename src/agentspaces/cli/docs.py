"""Design document template CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentspaces.infrastructure.design import (
    DesignError,
    DesignTemplate,
    get_design_template,
    list_design_templates,
    render_design_template,
)

app = typer.Typer(
    name="docs",
    help="Generate design documents from templates.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


def _category_color(category: str) -> str:
    """Get color for a template category."""
    colors = {
        "reference": "blue",
        "process": "green",
        "planning": "yellow",
        "operational": "magenta",
        "decision": "cyan",
    }
    return colors.get(category, "white")


def _print_template_table(templates: list[DesignTemplate]) -> None:
    """Print templates in a table format."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Template", style="cyan")
    table.add_column("Category")
    table.add_column("Description")

    for template in templates:
        color = _category_color(template.category)
        # Truncate description for table
        desc = template.description
        if len(desc) > 60:
            desc = desc[:57] + "..."

        table.add_row(
            template.name,
            f"[{color}]{template.category}[/{color}]",
            desc,
        )

    console.print(table)


def _print_template_info(template: DesignTemplate) -> None:
    """Print detailed template information."""
    color = _category_color(template.category)

    lines = [
        f"[bold]Name:[/bold]     {template.name}",
        f"[bold]Category:[/bold] [{color}]{template.category}[/{color}]",
        f"[bold]Path:[/bold]     {template.path}",
        "",
        "[bold]Description:[/bold]",
        template.description,
    ]

    if template.when_to_use:
        lines.extend(["", "[bold]When to use:[/bold]"])
        for use_case in template.when_to_use:
            lines.append(f"  • {use_case}")

    if template.required_variables:
        lines.extend(["", "[bold]Required variables:[/bold]"])
        for var in template.required_variables:
            lines.append(f"  • {var}")

    if template.optional_variables:
        lines.extend(["", "[bold]Optional variables:[/bold]"])
        for var in template.optional_variables:
            lines.append(f"  • {var}")

    if template.dependencies:
        lines.extend(["", "[bold]Related docs:[/bold]"])
        for dep in template.dependencies:
            lines.append(f"  • {dep}")

    panel = Panel(
        "\n".join(lines),
        title=f"[cyan]{template.name}[/cyan]",
        border_style="dim",
    )
    console.print(panel)


@app.command("list")
def list_templates(
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Filter by category"),
    ] = None,
) -> None:
    """List available design document templates.

    Shows all templates organized by category (reference, process,
    planning, operational, decision).

    \b
    Examples:
        as docs list                    # List all templates
        as docs list -c planning        # List only planning templates
    """
    try:
        templates = list_design_templates()
    except DesignError as e:
        error_console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1) from e

    if not templates:
        console.print("[yellow]![/yellow] No templates found")
        raise typer.Exit(0)

    # Filter by category if specified
    if category:
        templates = [t for t in templates if t.category == category]
        if not templates:
            console.print(f"[yellow]![/yellow] No templates in category: {category}")
            raise typer.Exit(0)

    _print_template_table(templates)

    # Show category legend
    console.print()
    categories = sorted({t.category for t in list_design_templates()})
    legend_parts = [
        f"[{_category_color(c)}]■[/{_category_color(c)}] {c}" for c in categories
    ]
    console.print(f"[dim]Categories: {' '.join(legend_parts)}[/dim]")


@app.command("info")
def info(
    template_name: Annotated[
        str,
        typer.Argument(help="Template name to show details for"),
    ],
) -> None:
    """Show detailed information about a template.

    Displays the template's description, when to use it, required and
    optional variables, and related documents.

    \b
    Examples:
        as docs info architecture       # Show architecture template details
        as docs info adr-template       # Show ADR template details
    """
    try:
        template = get_design_template(template_name)
    except DesignError as e:
        error_console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1) from e

    _print_template_info(template)


@app.command("create")
def create(
    template_name: Annotated[
        str,
        typer.Argument(help="Template name to generate"),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory (default: docs/)"),
    ] = Path("docs"),
    project_name: Annotated[
        str | None,
        typer.Option("--project-name", "-n", help="Project name"),
    ] = None,
    project_description: Annotated[
        str | None,
        typer.Option("--project-description", "-d", help="Project description"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
) -> None:
    """Generate a document from a template.

    Creates a new document by rendering the template with the provided
    variables. Missing required variables will be prompted interactively.

    \b
    Examples:
        as docs create architecture -n "MyApp" -d "A web app"
        as docs create adr-template -o docs/decisions/
        as docs create development-standards --force
    """
    try:
        template = get_design_template(template_name)
    except DesignError as e:
        error_console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1) from e

    # Build context from options
    context: dict[str, Any] = {}

    if project_name:
        context["project_name"] = project_name
    if project_description:
        context["project_description"] = project_description

    # Prompt for missing required variables
    for var in template.required_variables:
        if var not in context:
            value = typer.prompt(f"Enter {var.replace('_', ' ')}")
            context[var] = value

    # Determine output path
    output_file = output / f"{template.name}.md"

    # Handle ADR templates specially (use adr_number in filename)
    if template.category == "decision" and "adr_number" in context:
        output_file = output / f"{context['adr_number']}-{template.name}.md"

    # Check for existing file
    if output_file.exists() and not force:
        error_console.print(f"[red]✗[/red] File exists: {output_file}")
        console.print("[dim]Use --force to overwrite[/dim]")
        raise typer.Exit(1)

    # Render template
    try:
        result_path = render_design_template(template_name, context, output_file)
    except DesignError as e:
        error_console.print(f"[red]✗[/red] {e}")
        raise typer.Exit(1) from e

    console.print(f"[green]✓[/green] Created: {result_path}")


# Mapping of template names to their output paths relative to project root
SCAFFOLD_STRUCTURE: dict[str, str] = {
    # Root files
    "readme": "README.md",
    "claude-md": "CLAUDE.md",
    "todo-md": "TODO.md",
    # .claude directory
    "agents-readme": ".claude/agents/README.md",
    "commands-readme": ".claude/commands/README.md",
    # Design docs
    "architecture": "docs/design/architecture.md",
    "development-standards": "docs/design/development-standards.md",
    # Planning/operational
    "deployment": "docs/planning/deployment.md",
    # ADR
    "adr-template": "docs/adr/000-template.md",
    "adr-example": "docs/adr/001-example.md",
}


@app.command("scaffold")
def scaffold(
    target: Annotated[
        Path,
        typer.Argument(help="Target directory to scaffold (created if needed)"),
    ],
    project_name: Annotated[
        str,
        typer.Option("--project-name", "-n", help="Project name"),
    ],
    project_description: Annotated[
        str,
        typer.Option("--project-description", "-d", help="Project description"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
) -> None:
    """Create all documentation templates in a new project directory.

    Scaffolds a complete project documentation structure with all templates
    pre-populated with your project name and description.

    \b
    Examples:
        as docs scaffold ./my-project -n "MyApp" -d "A web application"
        as docs scaffold /tmp/new-proj -n "CLI Tool" -d "Command-line utility" -f
    """
    # Create target directory
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    context: dict[str, Any] = {
        "project_name": project_name,
        "project_description": project_description,
        # Defaults for ADR template
        "adr_number": "000",
        "adr_title": "ADR Template",
    }

    created: list[Path] = []
    skipped: list[Path] = []

    for template_name, relative_path in SCAFFOLD_STRUCTURE.items():
        output_path = target / relative_path

        # Check for existing file
        if output_path.exists() and not force:
            skipped.append(output_path)
            continue

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            render_design_template(template_name, context, output_path)
            created.append(output_path)
        except DesignError as e:
            error_console.print(f"[red]✗[/red] {template_name}: {e}")

    # Summary
    console.print()
    if created:
        console.print(f"[green]✓[/green] Created {len(created)} files in {target}")
        for path in created:
            rel = path.relative_to(target)
            console.print(f"  [dim]•[/dim] {rel}")

    if skipped:
        console.print(f"\n[yellow]![/yellow] Skipped {len(skipped)} existing files")
        for path in skipped:
            rel = path.relative_to(target)
            console.print(f"  [dim]•[/dim] {rel}")
        console.print("[dim]Use --force to overwrite[/dim]")
