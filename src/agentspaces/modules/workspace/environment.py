"""Python environment management for workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass

import structlog

from agentspaces.infrastructure import uv

__all__ = [
    "EnvironmentError",
    "EnvironmentInfo",
    "activation_command",
    "get_environment_info",
    "remove_environment",
    "setup_environment",
    "sync_dependencies",
]

logger = structlog.get_logger()


@dataclass(frozen=True)
class EnvironmentInfo:
    """Information about a workspace's Python environment."""

    has_venv: bool
    python_version: str | None
    has_pyproject: bool
    venv_path: Path | None


class EnvironmentError(Exception):
    """Raised when environment operations fail."""

    pass


def setup_environment(
    workspace_path: Path,
    *,
    python_version: str | None = None,
    sync_deps: bool = True,
) -> EnvironmentInfo:
    """Set up a Python environment for a workspace.

    Creates a virtual environment using uv and optionally syncs dependencies
    if a pyproject.toml is present.

    Args:
        workspace_path: Path to the workspace directory.
        python_version: Python version to use (auto-detected if not specified).
        sync_deps: Whether to sync dependencies if pyproject.toml exists.

    Returns:
        EnvironmentInfo with details about the created environment.

    Raises:
        EnvironmentError: If environment setup fails.
    """
    logger.info(
        "environment_setup_start",
        workspace=str(workspace_path),
        python_version=python_version,
    )

    # Check if uv is available
    if not uv.is_uv_available():
        raise EnvironmentError(
            "uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )

    # Detect Python version if not specified
    effective_python_version = python_version
    if effective_python_version is None:
        effective_python_version = uv.detect_python_version(workspace_path)

    # Create virtual environment
    venv_path = workspace_path / ".venv"
    try:
        uv.venv_create(venv_path, python_version=effective_python_version)
    except uv.UvError as e:
        logger.error("venv_create_failed", error=e.stderr)
        raise EnvironmentError(
            f"Failed to create virtual environment: {e.stderr}"
        ) from e

    # Sync dependencies if pyproject.toml exists
    has_pyproject = uv.has_pyproject(workspace_path)
    if sync_deps and has_pyproject:
        try:
            uv.sync(workspace_path, all_extras=True)
            logger.info("dependencies_synced", workspace=str(workspace_path))
        except uv.UvError as e:
            # Log warning but don't fail - venv was created successfully
            logger.warning("dependency_sync_failed", error=e.stderr)

    logger.info(
        "environment_setup_complete",
        workspace=str(workspace_path),
        python_version=effective_python_version,
    )

    return EnvironmentInfo(
        has_venv=True,
        python_version=effective_python_version,
        has_pyproject=has_pyproject,
        venv_path=venv_path,
    )


def get_environment_info(workspace_path: Path) -> EnvironmentInfo:
    """Get information about a workspace's environment.

    Args:
        workspace_path: Path to the workspace directory.

    Returns:
        EnvironmentInfo with current state.
    """
    has_venv = uv.has_venv(workspace_path)
    venv_path = workspace_path / ".venv" if has_venv else None

    # Try to detect Python version from venv or project config
    python_version = None
    if has_venv:
        python_version = _get_venv_python_version(workspace_path)
    if python_version is None:
        python_version = uv.detect_python_version(workspace_path)

    return EnvironmentInfo(
        has_venv=has_venv,
        python_version=python_version,
        has_pyproject=uv.has_pyproject(workspace_path),
        venv_path=venv_path,
    )


def _get_venv_python_version(workspace_path: Path) -> str | None:
    """Get the Python version from an existing venv.

    Args:
        workspace_path: Path to the workspace.

    Returns:
        Python version string or None.
    """
    # Try to read pyvenv.cfg
    pyvenv_cfg = workspace_path / ".venv" / "pyvenv.cfg"
    if pyvenv_cfg.exists():
        try:
            for line in pyvenv_cfg.read_text(encoding="utf-8").splitlines():
                if line.startswith("version"):
                    # Line like "version = 3.13.0"
                    parts = line.split("=")
                    if len(parts) >= 2:
                        full_version = parts[1].strip()
                        # Return just major.minor
                        version_parts = full_version.split(".")
                        if len(version_parts) >= 2:
                            return f"{version_parts[0]}.{version_parts[1]}"
        except Exception:
            pass

    return None


def remove_environment(workspace_path: Path) -> None:
    """Remove the virtual environment from a workspace.

    Args:
        workspace_path: Path to the workspace directory.

    Raises:
        EnvironmentError: If removal fails.
    """
    import shutil

    venv_path = workspace_path / ".venv"
    if not venv_path.exists():
        return  # Nothing to remove

    try:
        shutil.rmtree(venv_path)
        logger.info("environment_removed", workspace=str(workspace_path))
    except FileNotFoundError:
        # Already removed by another process - that's fine (handles TOCTOU)
        logger.debug("environment_already_removed", workspace=str(workspace_path))
    except OSError as e:
        raise EnvironmentError(f"Failed to remove environment: {e}") from e


def activation_command(workspace_path: Path) -> str | None:
    """Get the command to activate the workspace's virtual environment.

    Args:
        workspace_path: Path to the workspace directory.

    Returns:
        Shell command to activate the venv, or None if no venv exists.
    """
    venv_path = workspace_path / ".venv"
    if not venv_path.exists():
        return None

    # Return the source command for bash/zsh
    activate_path = venv_path / "bin" / "activate"
    if activate_path.exists():
        return f"source {activate_path}"

    return None


def sync_dependencies(workspace_path: Path, *, all_extras: bool = True) -> bool:
    """Sync dependencies for a workspace using uv sync.

    Args:
        workspace_path: Path to the workspace directory.
        all_extras: Whether to install all optional dependency groups.

    Returns:
        True if sync succeeded, False otherwise.

    Raises:
        EnvironmentError: If uv is not available or no pyproject.toml exists.
    """
    if not uv.is_uv_available():
        raise EnvironmentError(
            "uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )

    if not uv.has_pyproject(workspace_path):
        raise EnvironmentError(
            f"No pyproject.toml found in {workspace_path}. Cannot sync dependencies."
        )

    logger.info("sync_dependencies_start", workspace=str(workspace_path))

    try:
        uv.sync(workspace_path, all_extras=all_extras)
        logger.info("sync_dependencies_complete", workspace=str(workspace_path))
        return True
    except uv.UvError as e:
        logger.error("sync_dependencies_failed", error=e.stderr)
        raise EnvironmentError(f"Failed to sync dependencies: {e.stderr}") from e
