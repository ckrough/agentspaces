"""Design document template generation.

Generates design documents from Jinja2 templates for project documentation.
Templates are organized to match project skeleton structure:
- Root files (CLAUDE.md, TODO.md)
- .claude/ directory (agents, commands)
- docs/ directory (adr, design, planning)

Each template includes YAML frontmatter with metadata for agent discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, UndefinedError

from agentspaces.infrastructure.frontmatter import FrontmatterError, parse_frontmatter

__all__ = [
    "DesignError",
    "DesignTemplate",
    "get_design_template",
    "list_design_templates",
    "render_design_template",
]

logger = structlog.get_logger()


class DesignError(Exception):
    """Raised when design template operations fail."""


@dataclass(frozen=True)
class DesignTemplate:
    """Metadata about a design document template.

    Attributes:
        name: Template identifier (e.g., "architecture").
        category: Template category (reference, process, planning, etc.).
        description: What the template is for.
        when_to_use: Guidance on when to create this document.
        required_variables: Variables that must be provided.
        optional_variables: Variables with defaults.
        dependencies: Other documents this template references.
        path: Path to the template file.
    """

    name: str
    category: str
    description: str
    when_to_use: list[str]
    required_variables: list[str]
    optional_variables: list[str]
    dependencies: list[str]
    path: Path


def _get_design_template_dir() -> Path:
    """Get and validate the skeleton templates directory path.

    Returns:
        Path to the validated templates/skeleton directory.

    Raises:
        DesignError: If templates directory not found or invalid.
    """
    # Start from package root (4 levels up from this file)
    package_root = Path(__file__).parent.parent.parent.parent
    templates_dir = package_root / "templates" / "skeleton"

    if not templates_dir.exists():
        raise DesignError(
            "Skeleton templates directory not found. "
            "Expected at: <project>/templates/skeleton/"
        )

    # Ensure templates_dir is within package root (prevent symlink attacks)
    try:
        resolved = templates_dir.resolve()
        package_resolved = package_root.resolve()
        if not str(resolved).startswith(str(package_resolved)):
            raise DesignError("Templates directory escapes package root")
    except OSError as e:
        raise DesignError(f"Cannot resolve templates directory: {e}") from e

    return templates_dir


def _parse_template_metadata(path: Path) -> DesignTemplate:
    """Parse a template file and extract its metadata.

    Args:
        path: Path to the template file.

    Returns:
        DesignTemplate with parsed metadata.

    Raises:
        DesignError: If parsing fails.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DesignError(f"Cannot read template {path}: {e}") from e

    try:
        frontmatter, _ = parse_frontmatter(content)
    except FrontmatterError as e:
        raise DesignError(f"Invalid frontmatter in {path}: {e}") from e

    # Extract and validate required fields
    name = frontmatter.get("name")
    if not name:
        raise DesignError(f"Template {path} missing required 'name' field")

    category = frontmatter.get("category", "unknown")
    description = frontmatter.get("description", "")
    when_to_use = frontmatter.get("when_to_use", [])
    dependencies = frontmatter.get("dependencies", [])

    # Extract variable information
    variables = frontmatter.get("variables", {})
    required_vars = variables.get("required", [])
    optional_vars = variables.get("optional", [])

    return DesignTemplate(
        name=name,
        category=category,
        description=description.strip() if isinstance(description, str) else "",
        when_to_use=when_to_use if isinstance(when_to_use, list) else [],
        required_variables=required_vars if isinstance(required_vars, list) else [],
        optional_variables=optional_vars if isinstance(optional_vars, list) else [],
        dependencies=dependencies if isinstance(dependencies, list) else [],
        path=path,
    )


def list_design_templates() -> list[DesignTemplate]:
    """List all available design templates.

    Recursively scans the templates/skeleton directory for .md files
    and parses their frontmatter to extract metadata.

    Returns:
        List of DesignTemplate metadata objects, sorted by category then name.

    Raises:
        DesignError: If template directory is invalid.
    """
    templates_dir = _get_design_template_dir()
    templates: list[DesignTemplate] = []

    # Recursively find all .md files
    for template_file in templates_dir.rglob("*.md"):
        try:
            template = _parse_template_metadata(template_file)
            templates.append(template)
        except DesignError as e:
            logger.warning(
                "template_parse_failed",
                path=str(template_file),
                error=str(e),
            )

    # Sort by category, then by name
    templates.sort(key=lambda t: (t.category, t.name))

    return templates


def get_design_template(name: str) -> DesignTemplate:
    """Get a specific design template by name.

    Args:
        name: Template name (e.g., "architecture", "adr-template").

    Returns:
        The matching DesignTemplate.

    Raises:
        DesignError: If template not found.
    """
    templates = list_design_templates()

    for template in templates:
        if template.name == name:
            return template

    available = [t.name for t in templates]
    raise DesignError(f"Template '{name}' not found. Available: {', '.join(available)}")


def render_design_template(
    template_name: str,
    context: dict[str, Any],
    output_path: Path,
) -> Path:
    """Render a design template with the given context.

    Loads the template, validates required variables are present,
    renders with Jinja2, and writes to the output path.

    Args:
        template_name: Name of the template (e.g., "architecture").
        context: Variables to pass to the template.
        output_path: Where to write the rendered document.

    Returns:
        Path to the generated document.

    Raises:
        DesignError: If rendering fails or required variables missing.
    """
    # Get template metadata
    template = get_design_template(template_name)

    # Validate required variables
    missing = [var for var in template.required_variables if var not in context]
    if missing:
        raise DesignError(
            f"Missing required variables for '{template_name}': {', '.join(missing)}"
        )

    # Read and parse template
    try:
        content = template.path.read_text(encoding="utf-8")
    except OSError as e:
        raise DesignError(f"Cannot read template: {e}") from e

    try:
        _frontmatter, body = parse_frontmatter(content)
    except FrontmatterError as e:
        raise DesignError(f"Invalid template frontmatter: {e}") from e

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(template.path.parent)),
        autoescape=False,  # Markdown doesn't need HTML escaping
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Render the body (not the frontmatter)
    try:
        jinja_template = env.from_string(body)
        rendered = jinja_template.render(**context)
    except TemplateNotFound as e:
        raise DesignError(f"Template include not found: {e}") from e
    except UndefinedError as e:
        raise DesignError(f"Undefined variable in template: {e}") from e
    except Exception as e:
        raise DesignError(f"Template rendering failed: {e}") from e

    # Ensure output directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    except OSError as e:
        raise DesignError(f"Cannot write output file: {e}") from e

    logger.debug(
        "design_template_rendered",
        template=template_name,
        output=str(output_path),
    )

    return output_path
