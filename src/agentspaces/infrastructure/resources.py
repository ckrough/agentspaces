"""Package resource access for bundled templates.

Provides a unified API for accessing template files that works correctly
whether running from source or from an installed package.

Uses importlib.resources (Python 3.9+) which is the standard way to access
non-code files bundled with a Python package.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

__all__ = [
    "ResourceError",
    "get_skeleton_templates_dir",
    "get_skills_templates_dir",
]


class ResourceError(Exception):
    """Raised when package resources cannot be accessed."""


def _get_templates_dir() -> Path:
    """Get the templates directory from package resources.

    Returns:
        Path to the templates directory.

    Raises:
        ResourceError: If the templates directory cannot be accessed.
    """
    try:
        # Access the templates directory as a package resource
        templates_ref = files("agentspaces.templates")

        # Convert to a path - works for both source and installed packages
        # Using as_file context manager ensures proper resource extraction
        # for zip-imported packages, but for simplicity we use the traversable
        # interface which works for most use cases
        templates_path = Path(str(templates_ref))

        if not templates_path.exists():
            raise ResourceError(
                f"Templates directory not found at package location: {templates_path}"
            )

        return templates_path

    except ModuleNotFoundError as e:
        raise ResourceError(
            "Cannot access package templates. "
            "Ensure agentspaces is installed correctly."
        ) from e
    except TypeError as e:
        # Happens if files() returns something that can't be converted to Path
        raise ResourceError(f"Cannot resolve templates path: {e}") from e


def get_skeleton_templates_dir() -> Path:
    """Get the skeleton templates directory.

    Returns:
        Path to the templates/skeleton directory.

    Raises:
        ResourceError: If the directory cannot be accessed or doesn't exist.
    """
    templates_dir = _get_templates_dir()
    skeleton_dir = templates_dir / "skeleton"

    if not skeleton_dir.exists():
        raise ResourceError(f"Skeleton templates directory not found: {skeleton_dir}")

    return skeleton_dir


def get_skills_templates_dir() -> Path:
    """Get the skills templates directory.

    Returns:
        Path to the templates/skills directory.

    Raises:
        ResourceError: If the directory cannot be accessed or doesn't exist.
    """
    templates_dir = _get_templates_dir()
    skills_dir = templates_dir / "skills"

    if not skills_dir.exists():
        raise ResourceError(f"Skills templates directory not found: {skills_dir}")

    return skills_dir
