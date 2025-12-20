"""uv operations via subprocess."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path  # noqa: TC003 - used at runtime for path operations
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = structlog.get_logger()

# Valid Python version pattern: X.Y or X.Y.Z (e.g., "3.12", "3.12.1")
_PYTHON_VERSION_PATTERN = re.compile(r"^3\.\d{1,2}(\.\d{1,2})?$")

# Default timeout for uv operations (60 seconds - longer for installs)
DEFAULT_TIMEOUT = 60


class UvError(Exception):
    """Raised when a uv operation fails."""

    def __init__(self, message: str, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class UvTimeoutError(UvError):
    """Raised when a uv operation times out."""

    def __init__(self, message: str, timeout: float) -> None:
        super().__init__(
            message, returncode=-1, stderr=f"Operation timed out after {timeout}s"
        )
        self.timeout = timeout


class UvNotFoundError(UvError):
    """Raised when uv is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh",
            returncode=-1,
            stderr="uv command not found",
        )


def _run_uv(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run a uv command and return the result.

    Args:
        args: uv command arguments (without 'uv' prefix).
        cwd: Working directory for the command.
        check: Whether to raise UvError on non-zero exit.
        timeout: Maximum time in seconds to wait for the command.

    Returns:
        CompletedProcess with stdout/stderr.

    Raises:
        UvError: If check=True and command fails.
        UvTimeoutError: If the command times out.
        UvNotFoundError: If uv is not installed.
    """
    cmd = ["uv", *args]
    logger.debug("uv_command", cmd=cmd, cwd=str(cwd) if cwd else None)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise UvNotFoundError() from e
    except subprocess.TimeoutExpired as e:
        raise UvTimeoutError(
            f"uv command timed out: {' '.join(cmd)}",
            timeout=timeout,
        ) from e

    if check and result.returncode != 0:
        raise UvError(
            f"uv command failed: {' '.join(cmd)}",
            returncode=result.returncode,
            stderr=result.stderr.strip(),
        )

    return result


def is_uv_available() -> bool:
    """Check if uv is installed and available.

    Returns:
        True if uv is available.
    """
    try:
        _run_uv(["--version"], check=False, timeout=5)
        return True
    except UvNotFoundError:
        return False


def get_uv_version() -> str:
    """Get the installed uv version.

    Returns:
        Version string (e.g., "0.9.18").

    Raises:
        UvNotFoundError: If uv is not installed.
    """
    result = _run_uv(["--version"], timeout=5)
    # Output is like "uv 0.9.18 (Homebrew 2025-12-16)"
    parts = result.stdout.strip().split()
    if len(parts) >= 2:
        return parts[1]
    return result.stdout.strip()


def venv_create(
    path: Path,
    *,
    python_version: str | None = None,
    seed: bool = True,
) -> None:
    """Create a virtual environment using uv.

    Args:
        path: Path where the venv will be created.
        python_version: Python version to use (e.g., "3.12", "3.13").
        seed: Whether to seed with pip/setuptools.

    Raises:
        UvError: If venv creation fails.
        ValueError: If python_version format is invalid.
    """
    args = ["venv", str(path)]

    if python_version:
        # Validate python_version format to prevent command injection
        if not _PYTHON_VERSION_PATTERN.match(python_version):
            raise ValueError(
                f"Invalid Python version format: {python_version}. "
                "Expected format: X.Y or X.Y.Z (e.g., '3.12', '3.12.1')"
            )
        args.extend(["--python", python_version])

    if seed:
        args.append("--seed")

    logger.info("venv_create", path=str(path), python_version=python_version)
    _run_uv(args)


def sync(
    cwd: Path,
    *,
    all_extras: bool = False,
    frozen: bool = False,
) -> None:
    """Sync dependencies in a project directory.

    Args:
        cwd: Project directory containing pyproject.toml.
        all_extras: Install all optional dependencies.
        frozen: Use exact versions from lockfile.

    Raises:
        UvError: If sync fails.
    """
    args = ["sync"]

    if all_extras:
        args.append("--all-extras")

    if frozen:
        args.append("--frozen")

    logger.info("uv_sync", cwd=str(cwd), all_extras=all_extras)
    _run_uv(args, cwd=cwd)


def pip_install(
    cwd: Path,
    packages: Sequence[str],
    *,
    editable: bool = False,
) -> None:
    """Install packages using uv pip.

    Args:
        cwd: Working directory.
        packages: Packages to install.
        editable: Install in editable mode.

    Raises:
        UvError: If installation fails.
    """
    args = ["pip", "install"]

    if editable:
        args.append("-e")

    args.extend(packages)

    logger.info("pip_install", packages=list(packages), editable=editable)
    _run_uv(args, cwd=cwd, timeout=120)  # Longer timeout for installs


def detect_python_version(project_path: Path) -> str | None:
    """Detect Python version from project configuration.

    Checks in order:
    1. .python-version file
    2. pyproject.toml requires-python

    Args:
        project_path: Path to the project directory.

    Returns:
        Python version string (e.g., "3.12") or None if not detected.
    """
    # Check .python-version file
    python_version_file = project_path / ".python-version"
    if python_version_file.exists():
        version = python_version_file.read_text(encoding="utf-8").strip()
        if version:
            logger.debug(
                "detected_python_version", source=".python-version", version=version
            )
            return version

    # Check pyproject.toml
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        import tomllib

        try:
            content = pyproject_path.read_text(encoding="utf-8")
            data = tomllib.loads(content)

            # Look for requires-python in [project]
            requires_python = data.get("project", {}).get("requires-python", "")
            if requires_python:
                # Extract version from constraint like ">=3.12" or ">=3.12,<4"
                parsed_version = _parse_requires_python(requires_python)
                if parsed_version:
                    logger.debug(
                        "detected_python_version",
                        source="pyproject.toml",
                        version=parsed_version,
                    )
                    return parsed_version
        except (OSError, UnicodeDecodeError, KeyError, tomllib.TOMLDecodeError) as e:
            # If we can't parse, just return None
            logger.debug(
                "pyproject_parse_failed", path=str(pyproject_path), error=str(e)
            )

    return None


def _parse_requires_python(constraint: str) -> str | None:
    """Parse a requires-python constraint to extract a version.

    Args:
        constraint: Version constraint like ">=3.12" or ">=3.12,<4".

    Returns:
        Version string like "3.12" or None.
    """
    # Match patterns like ">=3.12", "~=3.12", "==3.12"
    match = re.search(r"[>=~=]+\s*(\d+\.\d+)", constraint)
    if match:
        return match.group(1)
    return None


def has_venv(workspace_path: Path) -> bool:
    """Check if a workspace has a virtual environment.

    Args:
        workspace_path: Path to the workspace.

    Returns:
        True if a .venv directory exists.
    """
    venv_path = workspace_path / ".venv"
    return venv_path.is_dir()


def has_pyproject(workspace_path: Path) -> bool:
    """Check if a workspace has a pyproject.toml file.

    Args:
        workspace_path: Path to the workspace.

    Returns:
        True if pyproject.toml exists.
    """
    return (workspace_path / "pyproject.toml").exists()
