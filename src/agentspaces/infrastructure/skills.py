"""Workspace skill generation.

Generates skill files (SKILL.md) using Jinja2 templates for agent discovery.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

if TYPE_CHECKING:
    from agentspaces.infrastructure.metadata import WorkspaceMetadata

__all__ = [
    "SkillError",
    "generate_workspace_context_skill",
]

logger = structlog.get_logger()

# Expected template file for validation
_EXPECTED_TEMPLATE = "skills/workspace-context/SKILL.md"


class SkillError(Exception):
    """Raised when skill operations fail."""


def _sanitize_for_markdown(text: str) -> str:
    """Sanitize user input for safe Markdown rendering.

    Escapes characters that could be interpreted as Markdown or HTML.

    Args:
        text: User-provided text to sanitize.

    Returns:
        Sanitized text safe for Markdown templates.
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Escape Markdown link syntax to prevent javascript: links
    text = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1", text)
    # Escape backticks (code blocks)
    text = text.replace("`", "\\`")
    return text


def _get_template_dir() -> Path:
    """Get and validate the templates directory path.

    Returns:
        Path to the validated templates directory.

    Raises:
        SkillError: If templates directory not found or invalid.
    """
    # Start from package root (4 levels up from this file)
    package_root = Path(__file__).parent.parent.parent.parent
    templates_dir = package_root / "templates"

    if not templates_dir.exists():
        raise SkillError(
            "Templates directory not found. "
            "Expected at: <project>/templates/skills/workspace-context/"
        )

    # Validate expected template structure exists
    expected_template = templates_dir / _EXPECTED_TEMPLATE
    if not expected_template.exists():
        raise SkillError(f"Template structure invalid: missing {_EXPECTED_TEMPLATE}")

    # Ensure templates_dir is within package root (prevent symlink attacks)
    try:
        resolved = templates_dir.resolve()
        package_resolved = package_root.resolve()
        if not str(resolved).startswith(str(package_resolved)):
            raise SkillError("Templates directory escapes package root")
    except OSError as e:
        raise SkillError(f"Cannot resolve templates directory: {e}") from e

    return templates_dir


def generate_workspace_context_skill(
    metadata: WorkspaceMetadata,
    output_dir: Path,
) -> Path:
    """Generate the workspace-context skill from template.

    Creates a SKILL.md file that agents can discover to understand
    the workspace context.

    Args:
        metadata: Workspace metadata for template variables.
        output_dir: Directory to write skill files.

    Returns:
        Path to the generated SKILL.md file.

    Raises:
        SkillError: If generation fails.
    """
    try:
        template_dir = _get_template_dir()
        skill_template_dir = template_dir / "skills" / "workspace-context"

        if not skill_template_dir.exists():
            raise SkillError(
                f"Skill template directory not found: {skill_template_dir}"
            )

        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(str(skill_template_dir)),
            autoescape=False,  # Markdown doesn't need HTML escaping
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Load and render template
        try:
            template = env.get_template("SKILL.md")
        except TemplateNotFound as e:
            raise SkillError(f"Skill template not found: {e}") from e

        # Build template context with sanitized user input
        # Purpose is user-provided and must be sanitized to prevent injection
        purpose = metadata.purpose or "No specific purpose defined"
        sanitized_purpose = _sanitize_for_markdown(purpose)

        context = {
            "name": metadata.name,
            "project": metadata.project,
            "branch": metadata.branch,
            "base_branch": metadata.base_branch,
            "created_at": metadata.created_at.isoformat(),
            "purpose": sanitized_purpose,
            "python_version": metadata.python_version,
            "has_venv": metadata.has_venv,
            "status": metadata.status,
        }

        rendered = template.render(**context)

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write skill file
        output_path = output_dir / "SKILL.md"
        output_path.write_text(rendered, encoding="utf-8")

        logger.debug(
            "skill_generated",
            skill="workspace-context",
            output=str(output_path),
        )

        return output_path

    except SkillError:
        raise
    except OSError as e:
        raise SkillError(f"Failed to write skill file: {e}") from e
    except Exception as e:
        raise SkillError(f"Failed to generate skill: {e}") from e
