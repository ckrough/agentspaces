"""Claude Code operations via subprocess."""

from __future__ import annotations

import functools
import subprocess
from pathlib import Path  # noqa: TC003 - used at runtime for cwd

import structlog

__all__ = [
    "ClaudeError",
    "ClaudeNotFoundError",
    "is_claude_available",
    "launch",
]

logger = structlog.get_logger()

# Maximum prompt length to prevent excessive command line arguments
MAX_PROMPT_LENGTH = 10000


class ClaudeError(Exception):
    """Raised when a Claude Code operation fails."""

    def __init__(self, message: str, returncode: int) -> None:
        super().__init__(message)
        self.returncode = returncode


class ClaudeNotFoundError(ClaudeError):
    """Raised when Claude Code is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Claude Code not found. Install from: https://claude.ai/download",
            returncode=-1,
        )


@functools.cache
def is_claude_available() -> bool:
    """Check if Claude Code is installed and available.

    Returns:
        True if Claude Code is available.

    Note:
        Result is cached for performance. Restart process if Claude is installed.
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        # If it times out, claude exists but something is wrong
        return False


def launch(
    cwd: Path,
    *,
    prompt: str | None = None,
) -> int:
    """Launch Claude Code interactively.

    Unlike git/uv operations, this does NOT capture output.
    It runs interactively, streaming to the user's terminal.

    Args:
        cwd: Working directory to launch in.
        prompt: Optional initial prompt/instruction (max 10000 chars).

    Returns:
        Exit code from Claude Code process.

    Raises:
        ClaudeNotFoundError: If Claude Code is not installed.
        ClaudeError: If launch fails.
        ValueError: If prompt exceeds maximum length.
    """
    cmd = ["claude"]

    if prompt:
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt too long: {len(prompt)} chars (max {MAX_PROMPT_LENGTH})"
            )
        # Prompt is a positional argument in Claude Code CLI
        cmd.append(prompt)

    logger.info("claude_launch", cwd=str(cwd), has_prompt=prompt is not None)

    try:
        # Interactive mode: don't capture output, stream to terminal
        result = subprocess.run(
            cmd,
            cwd=cwd,
            # No capture_output - streams to terminal
        )
        return result.returncode
    except FileNotFoundError as e:
        raise ClaudeNotFoundError() from e
    except OSError as e:
        raise ClaudeError(f"Failed to launch Claude Code: {e}", returncode=-1) from e
