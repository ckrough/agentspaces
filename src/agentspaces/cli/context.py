"""CLI context state management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from agentspaces.infrastructure.config import GlobalConfig

__all__ = ["CLIContext"]


@dataclass
class CLIContext:
    """Global CLI context for verbosity and other state.

    Uses singleton pattern to share state across all CLI commands.

    Note: Mutable dataclass to allow setting verbose/quiet flags at runtime.
    Assumes single-threaded CLI environment.
    """

    verbose: bool = False
    quiet: bool = False
    config: GlobalConfig | None = None

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

    def get_config(self) -> GlobalConfig:
        """Get global config, loading and caching on first access.

        Returns:
            Loaded or default GlobalConfig instance.
        """
        if self.config is None:
            from agentspaces.infrastructure.config import load_global_config

            # Cache config after first load
            self.config = load_global_config()

        assert self.config is not None  # Always set in the if block above
        return self.config

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance.

        Useful for testing to ensure clean state.
        """
        cls._instance = None
