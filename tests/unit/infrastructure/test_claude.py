"""Tests for Claude Code subprocess operations."""

from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003 - used at runtime with tmp_path
from unittest.mock import MagicMock, patch

import pytest

from agentspaces.infrastructure.claude import (
    ClaudeError,
    ClaudeNotFoundError,
    is_claude_available,
    launch,
)


class TestIsClaudeAvailable:
    """Tests for is_claude_available function."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        is_claude_available.cache_clear()

    def teardown_method(self) -> None:
        """Clear cache after each test."""
        is_claude_available.cache_clear()

    def test_returns_true_when_claude_installed(self) -> None:
        """Should return True when claude --version succeeds."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert is_claude_available() is True

    def test_returns_false_when_claude_not_found(self) -> None:
        """Should return False when claude command not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert is_claude_available() is False

    def test_returns_false_on_timeout(self) -> None:
        """Should return False when claude --version times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=5)
            assert is_claude_available() is False

    def test_returns_false_on_nonzero_exit(self) -> None:
        """Should return False when claude returns non-zero exit code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert is_claude_available() is False


class TestLaunch:
    """Tests for launch function."""

    def test_launch_uses_correct_cwd(self, tmp_path: Path) -> None:
        """Should pass cwd to subprocess.run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = launch(tmp_path)

            assert result == 0
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs["cwd"] == tmp_path

    def test_launch_builds_correct_command(self, tmp_path: Path) -> None:
        """Should build correct command without prompt."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            launch(tmp_path)

            call_args = mock_run.call_args[0][0]
            assert call_args == ["claude"]

    def test_launch_with_prompt(self, tmp_path: Path) -> None:
        """Should include prompt as positional argument when provided."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            launch(tmp_path, prompt="Fix the bug")

            call_args = mock_run.call_args[0][0]
            assert call_args == ["claude", "Fix the bug"]

    def test_launch_returns_exit_code(self, tmp_path: Path) -> None:
        """Should return the process exit code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=42)

            result = launch(tmp_path)

            assert result == 42

    def test_launch_raises_not_found_when_claude_missing(self, tmp_path: Path) -> None:
        """Should raise ClaudeNotFoundError when claude not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(ClaudeNotFoundError) as exc_info:
                launch(tmp_path)

            assert "Claude Code not found" in str(exc_info.value)
            assert exc_info.value.returncode == -1

    def test_launch_raises_error_on_os_error(self, tmp_path: Path) -> None:
        """Should raise ClaudeError on other OS errors."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            with pytest.raises(ClaudeError) as exc_info:
                launch(tmp_path)

            assert "Failed to launch" in str(exc_info.value)
            assert exc_info.value.returncode == -1

    def test_launch_rejects_oversized_prompt(self, tmp_path: Path) -> None:
        """Should raise ValueError for prompts exceeding max length."""
        long_prompt = "x" * 10001  # Exceeds MAX_PROMPT_LENGTH

        with pytest.raises(ValueError) as exc_info:
            launch(tmp_path, prompt=long_prompt)

        assert "Prompt too long" in str(exc_info.value)
        assert "10001" in str(exc_info.value)

    def test_launch_accepts_max_length_prompt(self, tmp_path: Path) -> None:
        """Should accept prompts at exactly max length."""
        max_prompt = "x" * 10000  # Exactly MAX_PROMPT_LENGTH

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = launch(tmp_path, prompt=max_prompt)

            assert result == 0
            call_args = mock_run.call_args[0][0]
            assert call_args == ["claude", max_prompt]

    def test_launch_with_plan_mode_enabled(self, tmp_path: Path) -> None:
        """Should include --permission-mode plan flag when plan_mode=True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            launch(tmp_path, plan_mode=True)

            call_args = mock_run.call_args[0][0]
            assert call_args == ["claude", "--permission-mode", "plan"]

    def test_launch_with_plan_mode_and_custom_prompt(self, tmp_path: Path) -> None:
        """Should include both plan mode flag and prompt when both provided."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            launch(tmp_path, prompt="Fix the bug", plan_mode=True)

            call_args = mock_run.call_args[0][0]
            assert call_args == ["claude", "--permission-mode", "plan", "Fix the bug"]

    def test_launch_without_plan_mode(self, tmp_path: Path) -> None:
        """Should not include plan mode flag when plan_mode=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            launch(tmp_path, plan_mode=False)

            call_args = mock_run.call_args[0][0]
            assert call_args == ["claude"]

    def test_launch_default_plan_mode_is_false(self, tmp_path: Path) -> None:
        """Plan mode should default to False when not specified."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Not passing plan_mode at all
            launch(tmp_path)

            call_args = mock_run.call_args[0][0]
            # Should not include permission-mode flag
            assert call_args == ["claude"]


class TestExceptions:
    """Tests for exception classes."""

    def test_claude_error_stores_returncode(self) -> None:
        """ClaudeError should store returncode."""
        error = ClaudeError("test error", returncode=42)
        assert error.returncode == 42
        assert str(error) == "test error"

    def test_claude_not_found_error_has_install_instructions(self) -> None:
        """ClaudeNotFoundError should have installation instructions."""
        error = ClaudeNotFoundError()
        assert "claude.ai/download" in str(error)
        assert error.returncode == -1


class TestCaching:
    """Tests for caching behavior."""

    def test_is_claude_available_is_cached(self) -> None:
        """is_claude_available should cache results."""
        # Clear the cache first
        is_claude_available.cache_clear()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Call twice
            result1 = is_claude_available()
            result2 = is_claude_available()

            # Should only call subprocess once due to caching
            assert result1 is True
            assert result2 is True
            assert mock_run.call_count == 1

        # Clear cache after test
        is_claude_available.cache_clear()
