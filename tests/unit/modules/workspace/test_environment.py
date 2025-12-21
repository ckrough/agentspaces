"""Tests for the environment module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agentspaces.modules.workspace import environment

if TYPE_CHECKING:
    import pytest


class TestEnvironmentInfo:
    """Tests for EnvironmentInfo dataclass."""

    def test_environment_info_attributes(self) -> None:
        """EnvironmentInfo should store all environment details."""
        info = environment.EnvironmentInfo(
            has_venv=True,
            python_version="3.12",
            has_pyproject=True,
            venv_path=Path("/some/path/.venv"),
        )

        assert info.has_venv is True
        assert info.python_version == "3.12"
        assert info.has_pyproject is True
        assert info.venv_path == Path("/some/path/.venv")


class TestSetupEnvironment:
    """Tests for setup_environment function."""

    def test_setup_environment_creates_venv(self, temp_dir: Path) -> None:
        """Should create a virtual environment."""
        result = environment.setup_environment(temp_dir)

        assert result.has_venv is True
        assert result.venv_path == temp_dir / ".venv"
        assert (temp_dir / ".venv").exists()

    def test_setup_environment_with_python_version(self, temp_dir: Path) -> None:
        """Should use specified Python version."""
        result = environment.setup_environment(temp_dir, python_version="3.12")

        assert result.has_venv is True
        # The version should be set (may include patch version)
        assert result.python_version is not None

    def test_setup_environment_detects_version(self, temp_dir: Path) -> None:
        """Should auto-detect Python version."""
        (temp_dir / ".python-version").write_text("3.12\n")

        result = environment.setup_environment(temp_dir)

        assert result.has_venv is True
        assert result.python_version is not None

    def test_setup_environment_syncs_deps_when_pyproject_exists(
        self, temp_dir: Path
    ) -> None:
        """Should sync dependencies when pyproject.toml exists."""
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []
"""
        (temp_dir / "pyproject.toml").write_text(pyproject_content)

        result = environment.setup_environment(temp_dir)

        assert result.has_venv is True
        assert result.has_pyproject is True


class TestGetEnvironmentInfo:
    """Tests for get_environment_info function."""

    def test_get_info_when_venv_exists(self, temp_dir: Path) -> None:
        """Should return info when venv exists."""
        # Create a venv first
        environment.setup_environment(temp_dir)

        info = environment.get_environment_info(temp_dir)

        assert info.has_venv is True
        assert info.venv_path == temp_dir / ".venv"

    def test_get_info_when_no_venv(self, temp_dir: Path) -> None:
        """Should return info when no venv."""
        info = environment.get_environment_info(temp_dir)

        assert info.has_venv is False
        assert info.venv_path is None

    def test_get_info_detects_pyproject(self, temp_dir: Path) -> None:
        """Should detect pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        info = environment.get_environment_info(temp_dir)

        assert info.has_pyproject is True


class TestRemoveEnvironment:
    """Tests for remove_environment function."""

    def test_remove_environment_success(self, temp_dir: Path) -> None:
        """Should remove the venv directory."""
        # Create a venv first
        environment.setup_environment(temp_dir)
        assert (temp_dir / ".venv").exists()

        # Remove it
        environment.remove_environment(temp_dir)

        assert not (temp_dir / ".venv").exists()

    def test_remove_environment_no_venv(self, temp_dir: Path) -> None:
        """Should do nothing when no venv exists."""
        # Should not raise
        environment.remove_environment(temp_dir)


class TestActivationCommand:
    """Tests for activation_command function."""

    def test_activation_command_when_venv_exists(self, temp_dir: Path) -> None:
        """Should return activation command."""
        # Create a venv first
        environment.setup_environment(temp_dir)

        cmd = environment.activation_command(temp_dir)

        assert cmd is not None
        assert "source" in cmd
        assert "activate" in cmd

    def test_activation_command_when_no_venv(self, temp_dir: Path) -> None:
        """Should return None when no venv."""
        cmd = environment.activation_command(temp_dir)

        assert cmd is None


class TestEnvironmentError:
    """Tests for EnvironmentError exception."""

    def test_environment_error_message(self) -> None:
        """EnvironmentError should store message."""
        error = environment.EnvironmentError("Something went wrong")
        assert str(error) == "Something went wrong"


class TestSetupEnvironmentErrors:
    """Tests for setup_environment error handling."""

    def test_setup_raises_when_uv_unavailable(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise EnvironmentError when uv is not installed."""
        import pytest

        from agentspaces.infrastructure import uv

        # Mock is_uv_available to return False
        monkeypatch.setattr(uv, "is_uv_available", lambda: False)

        with pytest.raises(environment.EnvironmentError, match="uv is not installed"):
            environment.setup_environment(temp_dir)


class TestSyncDependenciesErrors:
    """Tests for sync_dependencies error handling."""

    def test_sync_raises_when_uv_unavailable(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should raise EnvironmentError when uv is not installed."""
        import pytest

        from agentspaces.infrastructure import uv

        # Create pyproject.toml so we don't fail on that check
        (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        # Mock is_uv_available to return False
        monkeypatch.setattr(uv, "is_uv_available", lambda: False)

        with pytest.raises(environment.EnvironmentError, match="uv is not installed"):
            environment.sync_dependencies(temp_dir)

    def test_sync_raises_when_no_pyproject(self, temp_dir: Path) -> None:
        """Should raise EnvironmentError when no pyproject.toml exists."""
        import pytest

        with pytest.raises(environment.EnvironmentError, match=r"No pyproject\.toml"):
            environment.sync_dependencies(temp_dir)

    def test_sync_raises_on_uv_failure(self, temp_dir: Path) -> None:
        """Should raise EnvironmentError when uv sync fails."""
        import pytest

        # Create pyproject.toml with invalid content that will cause uv sync to fail
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname = 'test'\ndependencies = ['nonexistent-pkg-xyz123']\n"
        )

        # Create venv first
        environment.setup_environment(temp_dir, sync_deps=False)

        # uv sync should fail on nonexistent package
        with pytest.raises(environment.EnvironmentError, match="Failed to sync"):
            environment.sync_dependencies(temp_dir)


class TestEnvironmentInfoFrozen:
    """Tests for EnvironmentInfo immutability."""

    def test_environment_info_is_frozen(self) -> None:
        """EnvironmentInfo should be immutable."""
        from dataclasses import FrozenInstanceError

        import pytest

        info = environment.EnvironmentInfo(
            has_venv=True,
            python_version="3.12",
            has_pyproject=True,
            venv_path=Path("/some/path/.venv"),
        )

        with pytest.raises(FrozenInstanceError):
            info.has_venv = False  # type: ignore[misc]
