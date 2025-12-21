"""CLI context state management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

__all__ = ["CLIContext"]


@dataclass
class CLIContext:
    """Global CLI context for verbosity and other state.

    Uses singleton pattern to share state across all CLI commands.
    """

    verbose: bool = False
    quiet: bool = False

    _instance: ClassVar[CLIContext | None] = None

    @classmethod
    def get(cls) -> CLIContext:
        """Get the singleton CLI context instance.

        Returns:
            The shared CLIContext instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance.

        Useful for testing to ensure clean state.
        """
        cls._instance = None
