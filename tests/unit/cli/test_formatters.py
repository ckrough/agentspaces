"""Tests for CLI formatter functions."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from rich.panel import Panel

from agentspaces.cli.context import CLIContext
from agentspaces.cli.formatters import (
    print_did_you_mean,
    print_info,
    print_next_steps,
)


def _find_next_steps_panel(mock_console: MagicMock) -> Any:
    """Find the Next Steps panel from console.print calls.

    Args:
        mock_console: The mocked console object.

    Returns:
        The Panel object containing "Next Steps".

    Raises:
        AssertionError: If no Next Steps panel is found.
    """
    for call in mock_console.print.call_args_list:
        if call.args and isinstance(call.args[0], Panel):
            panel = call.args[0]
            if (
                hasattr(panel, "title")
                and panel.title
                and "Next Steps" in str(panel.title)
            ):
                return panel
    msg = "Could not find Next Steps panel in console.print calls"
    raise AssertionError(msg)


class TestPrintInfo:
    """Tests for print_info function."""

    def setup_method(self) -> None:
        """Reset context before each test."""
        CLIContext.reset()

    def teardown_method(self) -> None:
        """Reset context after each test."""
        CLIContext.reset()

    def test_prints_message_normally(self) -> None:
        """Should print message when not in quiet mode."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_info("Test message")
            mock_console.print.assert_called_once()
            call_args = mock_console.print.call_args[0][0]
            assert "Test message" in call_args

    def test_suppressed_in_quiet_mode(self) -> None:
        """Should not print when quiet mode is enabled."""
        CLIContext.get().quiet = True

        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_info("Test message")
            mock_console.print.assert_not_called()


class TestPrintNextSteps:
    """Tests for print_next_steps function."""

    def setup_method(self) -> None:
        """Reset context before each test."""
        CLIContext.reset()

    def teardown_method(self) -> None:
        """Reset context after each test."""
        CLIContext.reset()

    def test_prints_cd_step(self) -> None:
        """Should include cd to workspace path."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=False)
            mock_console.print.assert_called()
            # Get all printed content - find the Panel with "Next Steps"
            panel = _find_next_steps_panel(mock_console)
            # Panel.renderable contains the content
            assert "/path/to/workspace" in panel.renderable

    def test_includes_venv_activation_when_has_venv(self) -> None:
        """Should include venv activation when has_venv is True."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=True)
            panel = _find_next_steps_panel(mock_console)
            assert "source .venv/bin/activate" in panel.renderable

    def test_excludes_venv_activation_when_no_venv(self) -> None:
        """Should not include venv activation when has_venv is False."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=False)
            panel = _find_next_steps_panel(mock_console)
            assert "source .venv/bin/activate" not in panel.renderable

    def test_includes_agent_launch(self) -> None:
        """Should include agentspaces agent launch step."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=False)
            panel = _find_next_steps_panel(mock_console)
            assert "agentspaces agent launch" in panel.renderable

    def test_includes_remove_step(self) -> None:
        """Should include workspace remove step with workspace name."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=False)
            panel = _find_next_steps_panel(mock_console)
            assert "agentspaces workspace remove test-ws" in panel.renderable

    def test_prints_quick_start_one_liner(self) -> None:
        """Should print a quick start one-liner after the panel."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=True)
            # Check all print calls for the one-liner
            calls = [str(c) for c in mock_console.print.call_args_list]
            content = " ".join(calls)
            assert "Quick start" in content
            assert "/path/to/workspace" in content
            assert "source .venv/bin/activate" in content
            assert "agentspaces agent launch" in content

    def test_suppressed_in_quiet_mode(self) -> None:
        """Should not print when quiet mode is enabled."""
        CLIContext.get().quiet = True

        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_next_steps("test-ws", "/path/to/workspace", has_venv=True)
            mock_console.print.assert_not_called()


class TestPrintDidYouMean:
    """Tests for print_did_you_mean function."""

    def test_prints_suggestions(self) -> None:
        """Should print suggestions when provided."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_did_you_mean(["eager-turing", "happy-hopper"])
            assert mock_console.print.call_count >= 3  # blank, header, 2 suggestions

    def test_does_not_print_when_empty(self) -> None:
        """Should not print anything when suggestions list is empty."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_did_you_mean([])
            mock_console.print.assert_not_called()

    def test_includes_did_you_mean_header(self) -> None:
        """Should include 'Did you mean?' header."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            print_did_you_mean(["suggestion"])
            calls = [str(c) for c in mock_console.print.call_args_list]
            content = " ".join(calls)
            assert "Did you mean?" in content

    def test_includes_all_suggestions(self) -> None:
        """Should include all provided suggestions."""
        with patch("agentspaces.cli.formatters.console") as mock_console:
            suggestions = ["first", "second", "third"]
            print_did_you_mean(suggestions)
            calls = [str(c) for c in mock_console.print.call_args_list]
            content = " ".join(calls)
            for suggestion in suggestions:
                assert suggestion in content
