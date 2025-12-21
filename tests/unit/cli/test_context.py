"""Tests for CLI context module."""

from __future__ import annotations

from agentspaces.cli.context import CLIContext


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
