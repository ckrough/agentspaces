"""Fixtures for CLI integration tests."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from typer.testing import CliRunner

from agentspaces.cli.app import app

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

runner = CliRunner(mix_stderr=False)


@pytest.fixture
def empty_dir(temp_dir: Path) -> Path:
    """Create a fresh empty directory for project initialization.

    Returns the temp_dir directly (already empty).
    """
    return temp_dir


@pytest.fixture
def empty_git_dir(temp_dir: Path) -> Path:
    """Create an empty directory that is already a git repo.

    Initializes git but doesn't create any files (except .git/).
    """
    subprocess.run(
        ["git", "init"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    return temp_dir


@pytest.fixture
def non_empty_dir(temp_dir: Path) -> Path:
    """Create a directory with existing files (not git-ignored)."""
    (temp_dir / "existing.txt").write_text("existing content")
    return temp_dir


@pytest.fixture
def chdir_to(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Callable[[Path], None]]:
    """Factory fixture to change to a directory and restore after test.

    Usage:
        def test_example(chdir_to, empty_dir):
            chdir_to(empty_dir)
            # test runs in empty_dir
    """

    def _chdir_to(path: Path) -> None:
        monkeypatch.chdir(path)

    yield _chdir_to


@pytest.fixture
def invoke_project_create() -> Callable[..., Any]:
    """Factory fixture for invoking project create with defaults.

    Returns a callable that invokes the CLI with common defaults.
    """

    def _invoke(
        *args: str,
        name: str = "TestProject",
        description: str = "A test project",
        yes: bool = True,
        input: str | None = None,
    ) -> Any:
        cmd = ["project", "create"]
        if name:
            cmd.extend(["--name", name])
        if description:
            cmd.extend(["--description", description])
        if yes:
            cmd.append("--yes")
        cmd.extend(args)
        return runner.invoke(app, cmd, input=input)

    return _invoke


@pytest.fixture(autouse=True)
def isolate_git(monkeypatch: pytest.MonkeyPatch, temp_dir: Path) -> None:
    """Prevent tests from using system git config.

    Sets GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM to isolate git configuration.
    """
    git_config = temp_dir / ".gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(git_config))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
