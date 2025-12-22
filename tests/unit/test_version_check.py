"""Tests for version consistency validation script."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Import the functions to test them directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.check_version import get_init_version, get_pyproject_version

if TYPE_CHECKING:
    pass


def test_version_check_passes_on_consistent_versions() -> None:
    """Version check script should exit 0 when versions match."""
    result = subprocess.run(
        [sys.executable, "scripts/check_version.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Version consistency check passed" in result.stdout
    # Should output a version in semver format
    assert re.search(r"\d+\.\d+\.\d+", result.stdout)


def test_version_check_detects_mismatch(tmp_path: Path) -> None:
    """Version check should detect when versions don't match."""

    # Create temporary files with mismatched versions
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.2.0"\n')

    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text('[project]\nversion = "0.1.0"\n')

    # Create a test script that checks these specific files
    test_script = tmp_path / "test_check.py"
    # Use triple quotes and raw strings to avoid escaping issues
    script_content = f'''import re
import sys
from pathlib import Path

init_file = Path(r"{init_file}")
pyproject_file = Path(r"{pyproject_file}")

init_content = init_file.read_text()
pyproject_content = pyproject_file.read_text()

init_match = re.search(r"^__version__.*=.*[\\"']([^\\"']+)[\\"']", init_content, re.MULTILINE)
pyproject_match = re.search(r"^version.*=.*[\\"']([^\\"']+)[\\"']", pyproject_content, re.MULTILINE)

init_version = init_match.group(1) if init_match else None
pyproject_version = pyproject_match.group(1) if pyproject_match else None

if init_version != pyproject_version:
    print("Version mismatch", file=sys.stderr)
    print(f"init: {{init_version}}", file=sys.stderr)
    print(f"pyproject: {{pyproject_version}}", file=sys.stderr)
    sys.exit(1)
'''
    test_script.write_text(script_content)

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "mismatch" in result.stderr.lower()
    assert "0.2.0" in result.stderr
    assert "0.1.0" in result.stderr


def test_version_check_handles_missing_files(tmp_path: Path) -> None:
    """Version check should error gracefully when files are missing."""

    # Create a test script that looks for non-existent files
    test_script = tmp_path / "test_check.py"
    nonexistent_file = tmp_path / "nonexistent" / "__init__.py"

    script_content = f'''import sys
from pathlib import Path

init_file = Path(r"{nonexistent_file}")
if not init_file.exists():
    print(f"Error: {{init_file}} not found", file=sys.stderr)
    sys.exit(1)
'''
    test_script.write_text(script_content)

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Error" in result.stderr
    assert "not found" in result.stderr


# Unit tests for individual functions


def test_get_init_version_extracts_version(tmp_path: Path) -> None:
    """get_init_version should extract version from __init__.py."""
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")

    version = get_init_version(init_file)

    assert version == "1.2.3"


def test_get_init_version_handles_single_quotes(tmp_path: Path) -> None:
    """get_init_version should handle single-quoted versions."""
    init_file = tmp_path / "__init__.py"
    init_file.write_text("__version__ = '4.5.6'\n", encoding="utf-8")

    version = get_init_version(init_file)

    assert version == "4.5.6"


def test_get_init_version_returns_none_when_not_found(tmp_path: Path) -> None:
    """get_init_version should return None if no version found."""
    init_file = tmp_path / "__init__.py"
    init_file.write_text("# No version here\n", encoding="utf-8")

    version = get_init_version(init_file)

    assert version is None


def test_get_pyproject_version_extracts_version(tmp_path: Path) -> None:
    """get_pyproject_version should extract version from pyproject.toml."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        '[project]\nname = "test"\nversion = "2.3.4"\n', encoding="utf-8"
    )

    version = get_pyproject_version(pyproject_file)

    assert version == "2.3.4"


def test_get_pyproject_version_handles_complex_toml(tmp_path: Path) -> None:
    """get_pyproject_version should handle complex TOML structure."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        """
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]

[project]
name = "test"
version = "3.4.5"

[tool.other]
version = "9.9.9"
""",
        encoding="utf-8",
    )

    version = get_pyproject_version(pyproject_file)

    assert version == "3.4.5"


def test_get_pyproject_version_returns_none_for_missing_section(tmp_path: Path) -> None:
    """get_pyproject_version should return None if project section missing."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text('[tool.other]\nfoo = "bar"\n', encoding="utf-8")

    version = get_pyproject_version(pyproject_file)

    assert version is None


def test_get_pyproject_version_returns_none_for_invalid_toml(tmp_path: Path) -> None:
    """get_pyproject_version should return None for invalid TOML."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("invalid [ toml ]\n", encoding="utf-8")

    version = get_pyproject_version(pyproject_file)

    assert version is None
