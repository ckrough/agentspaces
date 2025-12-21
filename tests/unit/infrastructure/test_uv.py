"""Tests for the uv module."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - used in fixture type hints

from agentspaces.infrastructure import uv


class TestUvError:
    """Tests for UvError exception."""

    def test_uv_error_attributes(self) -> None:
        """UvError should store returncode and stderr."""
        error = uv.UvError("Command failed", returncode=1, stderr="error message")
        assert str(error) == "Command failed"
        assert error.returncode == 1
        assert error.stderr == "error message"


class TestUvTimeoutError:
    """Tests for UvTimeoutError exception."""

    def test_timeout_error_attributes(self) -> None:
        """UvTimeoutError should store timeout value."""
        error = uv.UvTimeoutError("Command timed out", timeout=60.0)
        assert str(error) == "Command timed out"
        assert error.timeout == 60.0
        assert error.returncode == -1
        assert "60" in error.stderr

    def test_timeout_error_is_uv_error(self) -> None:
        """UvTimeoutError should be a subclass of UvError."""
        error = uv.UvTimeoutError("Command timed out", timeout=60.0)
        assert isinstance(error, uv.UvError)


class TestUvNotFoundError:
    """Tests for UvNotFoundError exception."""

    def test_not_found_error_message(self) -> None:
        """UvNotFoundError should have helpful install message."""
        error = uv.UvNotFoundError()
        assert "uv not found" in str(error)
        assert "install" in str(error).lower()


class TestIsUvAvailable:
    """Tests for is_uv_available function."""

    def test_uv_is_available(self) -> None:
        """Should return True when uv is installed."""
        # uv is installed in this environment
        assert uv.is_uv_available() is True


class TestGetUvVersion:
    """Tests for get_uv_version function."""

    def test_get_uv_version_returns_version(self) -> None:
        """Should return version string."""
        version = uv.get_uv_version()
        # Version should be something like "0.9.18"
        assert version
        assert "." in version


class TestVenvCreate:
    """Tests for venv_create function."""

    def test_venv_create_success(self, temp_dir: Path) -> None:
        """Should create a virtual environment."""
        venv_path = temp_dir / ".venv"

        uv.venv_create(venv_path)

        assert venv_path.exists()
        assert (venv_path / "bin" / "python").exists() or (
            venv_path / "Scripts" / "python.exe"
        ).exists()

    def test_venv_create_with_python_version(self, temp_dir: Path) -> None:
        """Should accept python version argument."""
        venv_path = temp_dir / ".venv"

        # Use the current Python version
        uv.venv_create(venv_path, python_version="3.12")

        assert venv_path.exists()

    def test_venv_create_rejects_invalid_version(self, temp_dir: Path) -> None:
        """Should reject invalid python version format."""
        import pytest

        venv_path = temp_dir / ".venv"

        with pytest.raises(ValueError, match="Invalid Python version format"):
            uv.venv_create(venv_path, python_version="invalid")

    def test_venv_create_rejects_command_injection(self, temp_dir: Path) -> None:
        """Should reject python version with shell injection."""
        import pytest

        venv_path = temp_dir / ".venv"

        with pytest.raises(ValueError, match="Invalid Python version format"):
            uv.venv_create(venv_path, python_version="3.12; rm -rf /")


class TestDetectPythonVersion:
    """Tests for detect_python_version function."""

    def test_detect_from_python_version_file(self, temp_dir: Path) -> None:
        """Should detect version from .python-version file."""
        (temp_dir / ".python-version").write_text("3.12\n")

        version = uv.detect_python_version(temp_dir)

        assert version == "3.12"

    def test_detect_from_pyproject_toml(self, temp_dir: Path) -> None:
        """Should detect version from pyproject.toml."""
        pyproject_content = """
[project]
name = "test"
requires-python = ">=3.12"
"""
        (temp_dir / "pyproject.toml").write_text(pyproject_content)

        version = uv.detect_python_version(temp_dir)

        assert version == "3.12"

    def test_detect_from_pyproject_toml_with_upper_bound(self, temp_dir: Path) -> None:
        """Should detect version from requires-python with upper bound."""
        pyproject_content = """
[project]
name = "test"
requires-python = ">=3.11,<4"
"""
        (temp_dir / "pyproject.toml").write_text(pyproject_content)

        version = uv.detect_python_version(temp_dir)

        assert version == "3.11"

    def test_detect_returns_none_when_not_found(self, temp_dir: Path) -> None:
        """Should return None when no version specifier found."""
        version = uv.detect_python_version(temp_dir)

        assert version is None

    def test_python_version_file_takes_precedence(self, temp_dir: Path) -> None:
        """Should prefer .python-version over pyproject.toml."""
        (temp_dir / ".python-version").write_text("3.13\n")
        pyproject_content = """
[project]
name = "test"
requires-python = ">=3.11"
"""
        (temp_dir / "pyproject.toml").write_text(pyproject_content)

        version = uv.detect_python_version(temp_dir)

        assert version == "3.13"


class TestParseRequiresPython:
    """Tests for _parse_requires_python function."""

    def test_parse_gte_constraint(self) -> None:
        """Should parse >=X.Y constraint."""
        assert uv._parse_requires_python(">=3.12") == "3.12"

    def test_parse_tilde_constraint(self) -> None:
        """Should parse ~=X.Y constraint."""
        assert uv._parse_requires_python("~=3.11") == "3.11"

    def test_parse_eq_constraint(self) -> None:
        """Should parse ==X.Y constraint."""
        assert uv._parse_requires_python("==3.10") == "3.10"

    def test_parse_with_upper_bound(self) -> None:
        """Should extract lower bound from range."""
        assert uv._parse_requires_python(">=3.12,<4") == "3.12"

    def test_parse_invalid_returns_none(self) -> None:
        """Should return None for invalid constraint."""
        assert uv._parse_requires_python("invalid") is None


class TestHasVenv:
    """Tests for has_venv function."""

    def test_has_venv_true(self, temp_dir: Path) -> None:
        """Should return True when .venv exists."""
        (temp_dir / ".venv").mkdir()

        assert uv.has_venv(temp_dir) is True

    def test_has_venv_false(self, temp_dir: Path) -> None:
        """Should return False when .venv doesn't exist."""
        assert uv.has_venv(temp_dir) is False


class TestHasPyproject:
    """Tests for has_pyproject function."""

    def test_has_pyproject_true(self, temp_dir: Path) -> None:
        """Should return True when pyproject.toml exists."""
        (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        assert uv.has_pyproject(temp_dir) is True

    def test_has_pyproject_false(self, temp_dir: Path) -> None:
        """Should return False when pyproject.toml doesn't exist."""
        assert uv.has_pyproject(temp_dir) is False


class TestDetectPythonVersionMalformed:
    """Tests for detect_python_version with malformed .python-version files."""

    def test_empty_python_version_file(self, temp_dir: Path) -> None:
        """Should return None for empty .python-version file."""
        (temp_dir / ".python-version").write_text("")

        version = uv.detect_python_version(temp_dir)

        assert version is None

    def test_whitespace_only_python_version_file(self, temp_dir: Path) -> None:
        """Should return None for whitespace-only .python-version file."""
        (temp_dir / ".python-version").write_text("   \n\n  ")

        version = uv.detect_python_version(temp_dir)

        # The version is just whitespace, which gets stripped
        assert version is None or version.strip() == ""

    def test_python_version_file_with_trailing_newline(self, temp_dir: Path) -> None:
        """Should handle .python-version files with trailing newlines."""
        # Standard format: version followed by newline
        (temp_dir / ".python-version").write_text("3.12\n")

        version = uv.detect_python_version(temp_dir)

        assert version == "3.12"

    def test_python_version_file_with_patch_version(self, temp_dir: Path) -> None:
        """Should handle full patch versions like 3.12.1."""
        (temp_dir / ".python-version").write_text("3.12.1\n")

        version = uv.detect_python_version(temp_dir)

        assert version == "3.12.1"

    def test_malformed_pyproject_toml(self, temp_dir: Path) -> None:
        """Should return None for malformed pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("this is not valid toml {{{{")

        version = uv.detect_python_version(temp_dir)

        assert version is None

    def test_pyproject_without_requires_python(self, temp_dir: Path) -> None:
        """Should return None when pyproject.toml lacks requires-python."""
        (temp_dir / "pyproject.toml").write_text(
            "[project]\nname = 'test'\nversion = '1.0'\n"
        )

        version = uv.detect_python_version(temp_dir)

        assert version is None

    def test_pyproject_with_invalid_requires_python(self, temp_dir: Path) -> None:
        """Should return None for unparseable requires-python."""
        (temp_dir / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = "python3"\n'
        )

        version = uv.detect_python_version(temp_dir)

        # "python3" doesn't match the expected pattern
        assert version is None


class TestIsUvAvailableCached:
    """Tests for is_uv_available caching behavior."""

    def test_is_uv_available_is_cached(self) -> None:
        """is_uv_available should be cached (returns same result on repeated calls)."""
        # Call multiple times
        result1 = uv.is_uv_available()
        result2 = uv.is_uv_available()
        result3 = uv.is_uv_available()

        # All should be True (uv is installed in test env)
        assert result1 is True
        assert result2 is True
        assert result3 is True

        # Check the function has cache_info (evidence of @functools.cache)
        assert hasattr(uv.is_uv_available, "cache_info")
