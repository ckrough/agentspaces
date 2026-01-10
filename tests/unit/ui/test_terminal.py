"""Tests for terminal detection and navigation."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agentspaces.modules.workspace.service import WorkspaceInfo
from agentspaces.ui.terminal import (
    detect_terminal,
    is_ghostty_available,
    navigate_to_workspace,
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


class TestNavigateWorkspace:
    """Tests for workspace navigation."""

    @pytest.fixture
    def mock_workspace(self, tmp_path: Path) -> WorkspaceInfo:
        """Create mock workspace with venv."""
        venv_path = tmp_path / ".venv" / "bin" / "activate"
        venv_path.parent.mkdir(parents=True)
        venv_path.touch()

        return WorkspaceInfo(
            name="test-workspace",
            path=tmp_path,
            branch="test-branch",
            base_branch="main",
            project="test-project",
            created_at=None,
            has_venv=True,
            python_version="3.13.0",
            purpose=None,
        )

    @pytest.fixture
    def mock_workspace_no_venv(self, tmp_path: Path) -> WorkspaceInfo:
        """Create mock workspace without venv."""
        return WorkspaceInfo(
            name="test-workspace-no-venv",
            path=tmp_path,
            branch="test-branch",
            base_branch="main",
            project="test-project",
            created_at=None,
            has_venv=False,
            python_version=None,
            purpose=None,
        )

    def test_creates_ghostty_tab_when_available(
        self, mock_workspace: WorkspaceInfo, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Creates new Ghostty tab when Ghostty is available."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/bash")

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)
            navigate_to_workspace(mock_workspace)

        # Verify subprocess called with correct arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "ghostty"
        assert args[1] == "--command"
        assert args[2] == "/bin/bash"
        assert args[3] == "-c"
        assert str(mock_workspace.path) in args[4]
        assert "claude" in args[4]

    def test_falls_back_when_ghostty_not_found(
        self,
        mock_workspace: WorkspaceInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Falls back to printing instructions when Ghostty not found."""
        monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
        monkeypatch.setenv("SHELL", "/bin/bash")

        navigate_to_workspace(mock_workspace)

        captured = capsys.readouterr()
        # Check for workspace name and key command elements
        # (Rich may wrap long paths across lines, so check for parts)
        assert "test-workspace" in captured.out
        assert "cd" in captured.out
        assert "claude" in captured.out

    def test_includes_venv_activation_when_present(
        self, mock_workspace: WorkspaceInfo, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Includes venv activation in command when venv exists."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/bash")

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)
            navigate_to_workspace(mock_workspace)

        args = " ".join(mock_run.call_args[0][0])
        assert ".venv/bin/activate" in args

    def test_skips_venv_activation_when_not_present(
        self, mock_workspace_no_venv: WorkspaceInfo, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Skips venv activation when workspace has no venv."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/bash")

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)
            navigate_to_workspace(mock_workspace_no_venv)

        args = " ".join(mock_run.call_args[0][0])
        assert ".venv" not in args

    def test_handles_subprocess_failure_gracefully(
        self,
        mock_workspace: WorkspaceInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Falls back to print mode when subprocess fails."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/bash")

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "ghostty", stderr="error"),
            ),
        ):
            navigate_to_workspace(mock_workspace)

        # Should print fallback instructions
        captured = capsys.readouterr()
        assert "test-workspace" in captured.out

    def test_handles_timeout_gracefully(
        self,
        mock_workspace: WorkspaceInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Falls back to print mode when subprocess times out."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/bin/bash")

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch(
                "subprocess.run", side_effect=subprocess.TimeoutExpired("ghostty", 5)
            ),
        ):
            navigate_to_workspace(mock_workspace)

        # Should print fallback instructions
        captured = capsys.readouterr()
        assert "test-workspace" in captured.out

    def test_uses_custom_shell_from_env(
        self, mock_workspace: WorkspaceInfo, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uses SHELL environment variable for shell invocation."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)
            navigate_to_workspace(mock_workspace)

        args = mock_run.call_args[0][0]
        assert args[2] == "/usr/bin/zsh"

    def test_defaults_to_bash_when_shell_not_set(
        self, mock_workspace: WorkspaceInfo, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defaults to bash when SHELL env var not set."""
        monkeypatch.setenv("TERM_PROGRAM", "ghostty")
        monkeypatch.delenv("SHELL", raising=False)

        with (
            patch("agentspaces.ui.terminal.is_ghostty_available", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)
            navigate_to_workspace(mock_workspace)

        args = mock_run.call_args[0][0]
        assert args[2] == "/bin/bash"
