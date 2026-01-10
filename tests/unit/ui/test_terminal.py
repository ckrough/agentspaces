"""Tests for terminal detection."""

from unittest.mock import patch

import pytest

from agentspaces.ui.terminal import (
    detect_terminal,
    is_ghostty_available,
)


class TestIsGhosttyAvailable:
    """Tests for Ghostty availability check."""

    def test_returns_true_when_ghostty_in_path(self) -> None:
        """Ghostty is available when command exists in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/ghostty"):
            assert is_ghostty_available() is True

    def test_returns_false_when_ghostty_not_in_path(self) -> None:
        """Ghostty is not available when command not in PATH."""
        with patch("shutil.which", return_value=None):
            assert is_ghostty_available() is False


class TestDetectTerminal:
    """Tests for terminal detection."""

    def test_detects_ghostty_when_env_set_and_installed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ghostty detected when TERM_PROGRAM=ghostty and ghostty in PATH."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/zsh")

        with patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True):
            is_ghostty, shell = detect_terminal()

        assert is_ghostty is True
        assert shell == "zsh"

    def test_not_ghostty_when_env_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ghostty not detected when TERM_PROGRAM != ghostty."""
        monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
        monkeypatch.setenv("SHELL", "/bin/bash")

        is_ghostty, _ = detect_terminal()
        assert is_ghostty is False

    def test_not_ghostty_when_not_installed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ghostty not detected when not in PATH."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/bash")

        with patch("agentspaces.ui.terminal.is_ghostty_available", return_value=False):
            is_ghostty, _ = detect_terminal()

        assert is_ghostty is False

    def test_detects_shell_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Correctly extracts shell type from SHELL env var."""
        monkeypatch.setenv("SHELL", "/usr/local/bin/fish")

        _, shell = detect_terminal()
        assert shell == "fish"

    def test_defaults_to_bash_when_shell_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defaults to bash when SHELL env var not set."""
        monkeypatch.delenv("SHELL", raising=False)

        _, shell = detect_terminal()
        assert shell == "bash"
