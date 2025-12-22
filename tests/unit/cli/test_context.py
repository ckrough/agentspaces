"""Tests for CLI context module."""

from __future__ import annotations

from unittest.mock import patch

from agentspaces.cli.context import CLIContext
from agentspaces.infrastructure.config import GlobalConfig


class TestCLIContext:
    """Tests for CLIContext singleton."""

    def setup_method(self) -> None:
        """Reset context before each test."""
        CLIContext.reset()

    def teardown_method(self) -> None:
        """Reset context after each test."""
        CLIContext.reset()

    def test_get_returns_instance(self) -> None:
        """get() should return a CLIContext instance."""
        ctx = CLIContext.get()
        assert isinstance(ctx, CLIContext)

    def test_get_returns_same_instance(self) -> None:
        """get() should return the same singleton instance."""
        ctx1 = CLIContext.get()
        ctx2 = CLIContext.get()
        assert ctx1 is ctx2

    def test_default_values(self) -> None:
        """Default values should be False for both flags."""
        ctx = CLIContext.get()
        assert ctx.verbose is False
        assert ctx.quiet is False

    def test_verbose_can_be_set(self) -> None:
        """verbose flag should be settable."""
        ctx = CLIContext.get()
        ctx.verbose = True
        assert ctx.verbose is True
        # Should persist across get() calls
        assert CLIContext.get().verbose is True

    def test_quiet_can_be_set(self) -> None:
        """quiet flag should be settable."""
        ctx = CLIContext.get()
        ctx.quiet = True
        assert ctx.quiet is True
        # Should persist across get() calls
        assert CLIContext.get().quiet is True

    def test_reset_clears_instance(self) -> None:
        """reset() should clear the singleton instance."""
        ctx1 = CLIContext.get()
        ctx1.verbose = True

        CLIContext.reset()

        ctx2 = CLIContext.get()
        assert ctx2 is not ctx1
        assert ctx2.verbose is False

    def test_reset_before_get_works(self) -> None:
        """reset() should work even if get() was never called."""
        CLIContext.reset()  # Should not raise
        ctx = CLIContext.get()
        assert ctx is not None

    def test_get_config_caches_result(self) -> None:
        """get_config() should cache the loaded config."""
        ctx = CLIContext.get()

        with patch("agentspaces.infrastructure.config.load_global_config") as mock_load:
            mock_load.return_value = GlobalConfig(plan_mode_by_default=True)

            # First call should load
            config1 = ctx.get_config()
            assert mock_load.call_count == 1
            assert config1.plan_mode_by_default is True

            # Second call should use cache
            config2 = ctx.get_config()
            assert mock_load.call_count == 1  # Still 1, not 2
            assert config2 is config1  # Same instance

    def test_reset_clears_config_cache(self) -> None:
        """reset() should clear the cached config."""
        ctx1 = CLIContext.get()

        with patch("agentspaces.infrastructure.config.load_global_config") as mock_load:
            mock_load.return_value = GlobalConfig(plan_mode_by_default=True)

            # Load config
            ctx1.get_config()
            assert mock_load.call_count == 1

            # Reset and get new context
            CLIContext.reset()
            ctx2 = CLIContext.get()

            # Should reload config
            ctx2.get_config()
            assert mock_load.call_count == 2  # Called again after reset

    def test_config_is_lazy_loaded(self) -> None:
        """Config should not be loaded until get_config() is called."""
        with patch("agentspaces.infrastructure.config.load_global_config") as mock_load:
            mock_load.return_value = GlobalConfig()

            # Just getting the context should not load config
            ctx = CLIContext.get()
            assert mock_load.call_count == 0

            # Only when we call get_config()
            ctx.get_config()
            assert mock_load.call_count == 1

    def test_config_defaults_to_none(self) -> None:
        """Config field should default to None."""
        ctx = CLIContext.get()
        assert ctx.config is None
