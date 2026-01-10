"""Terminal detection helpers for TUI."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import structlog

__all__ = [
    "detect_terminal",
    "is_ghostty_available",
]

logger = structlog.get_logger()


def is_ghostty_available() -> bool:
    """Check if Ghostty terminal is installed and available.

    Returns:
        True if ghostty command exists in PATH.
    """
    return shutil.which("ghostty") is not None


def detect_terminal() -> tuple[bool, str]:
    """Detect if running in Ghostty terminal and if Ghostty is available.

    Returns:
        Tuple of (is_ghostty, shell_type).
        is_ghostty: True if running in Ghostty terminal AND ghostty command is available
        shell_type: Name of current shell (e.g., 'bash', 'zsh', 'fish')
    """
    # Check TERM_PROGRAM environment variable (set by Ghostty)
    term_program = os.environ.get("TERM_PROGRAM", "")
    is_ghostty_env = term_program == "ghostty"
    is_ghostty_installed = is_ghostty_available()

    # Only consider Ghostty available if both conditions met
    is_ghostty = is_ghostty_env and is_ghostty_installed

    # Detect shell type
    shell_path = os.environ.get("SHELL", "")
    shell_type = Path(shell_path).name if shell_path else "bash"

    logger.debug(
        "terminal_detected",
        is_ghostty=is_ghostty,
        is_ghostty_env=is_ghostty_env,
        is_ghostty_installed=is_ghostty_installed,
        shell_type=shell_type,
        term_program=term_program,
    )

    return is_ghostty, shell_type
