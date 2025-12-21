"""Active workspace tracking.

Manages the .active file that stores the currently active workspace
for a project. This enables the 'agentspaces agent launch' command to fall back
to the active workspace when not inside a workspace directory.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - used at runtime in function signatures

import structlog

__all__ = [
    "clear_active_workspace",
    "get_active_workspace",
    "set_active_workspace",
]

logger = structlog.get_logger()


def get_active_workspace(project_dir: Path) -> str | None:
    """Read the active workspace name from the .active file.

    Args:
        project_dir: Path to the project directory (e.g., ~/.agentspaces/myproject/).

    Returns:
        Workspace name if .active exists and contains a valid name, None otherwise.
    """
    active_file = project_dir / ".active"

    if not active_file.exists():
        return None

    try:
        content = active_file.read_text(encoding="utf-8").strip()
        if content:
            logger.debug(
                "active_workspace_read", project=project_dir.name, workspace=content
            )
            return content
        return None
    except OSError as e:
        logger.warning(
            "active_workspace_read_error", path=str(active_file), error=str(e)
        )
        return None


def set_active_workspace(project_dir: Path, workspace_name: str) -> None:
    """Write the active workspace name to the .active file.

    Args:
        project_dir: Path to the project directory.
        workspace_name: Name of the workspace to set as active.
    """
    active_file = project_dir / ".active"

    try:
        # Ensure project directory exists
        project_dir.mkdir(parents=True, exist_ok=True)

        active_file.write_text(workspace_name + "\n", encoding="utf-8")
        logger.debug(
            "active_workspace_set",
            project=project_dir.name,
            workspace=workspace_name,
        )
    except OSError as e:
        logger.warning(
            "active_workspace_write_error", path=str(active_file), error=str(e)
        )
        raise


def clear_active_workspace(project_dir: Path) -> None:
    """Remove the .active file, clearing the active workspace.

    Args:
        project_dir: Path to the project directory.
    """
    active_file = project_dir / ".active"

    try:
        active_file.unlink(missing_ok=True)
        logger.debug("active_workspace_cleared", project=project_dir.name)
    except OSError as e:
        logger.warning(
            "active_workspace_clear_error", path=str(active_file), error=str(e)
        )
        raise
