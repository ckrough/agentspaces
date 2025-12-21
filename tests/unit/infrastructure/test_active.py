"""Tests for active workspace tracking."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agentspaces.infrastructure.active import (
    clear_active_workspace,
    get_active_workspace,
    set_active_workspace,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestGetActiveWorkspace:
    """Tests for get_active_workspace function."""

    def test_returns_none_when_no_active_file(self, tmp_path: Path) -> None:
        """Returns None when .active file doesn't exist."""
        result = get_active_workspace(tmp_path)
        assert result is None

    def test_reads_workspace_name(self, tmp_path: Path) -> None:
        """Reads workspace name from .active file."""
        active_file = tmp_path / ".active"
        active_file.write_text("eager-turing\n")

        result = get_active_workspace(tmp_path)
        assert result == "eager-turing"

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """Strips whitespace from workspace name."""
        active_file = tmp_path / ".active"
        active_file.write_text("  eager-turing  \n\n")

        result = get_active_workspace(tmp_path)
        assert result == "eager-turing"

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        """Returns None when .active file is empty."""
        active_file = tmp_path / ".active"
        active_file.write_text("")

        result = get_active_workspace(tmp_path)
        assert result is None

    def test_returns_none_for_whitespace_only_file(self, tmp_path: Path) -> None:
        """Returns None when .active file contains only whitespace."""
        active_file = tmp_path / ".active"
        active_file.write_text("   \n\n  ")

        result = get_active_workspace(tmp_path)
        assert result is None


class TestSetActiveWorkspace:
    """Tests for set_active_workspace function."""

    def test_creates_active_file(self, tmp_path: Path) -> None:
        """Creates .active file with workspace name."""
        set_active_workspace(tmp_path, "eager-turing")

        active_file = tmp_path / ".active"
        assert active_file.exists()
        assert active_file.read_text() == "eager-turing\n"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Overwrites existing .active file."""
        active_file = tmp_path / ".active"
        active_file.write_text("old-workspace\n")

        set_active_workspace(tmp_path, "new-workspace")

        assert active_file.read_text() == "new-workspace\n"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Creates parent directory if it doesn't exist."""
        project_dir = tmp_path / "project"

        set_active_workspace(project_dir, "eager-turing")

        active_file = project_dir / ".active"
        assert active_file.exists()
        assert active_file.read_text() == "eager-turing\n"


class TestClearActiveWorkspace:
    """Tests for clear_active_workspace function."""

    def test_removes_active_file(self, tmp_path: Path) -> None:
        """Removes .active file."""
        active_file = tmp_path / ".active"
        active_file.write_text("eager-turing\n")

        clear_active_workspace(tmp_path)

        assert not active_file.exists()

    def test_does_not_fail_when_no_file(self, tmp_path: Path) -> None:
        """Does not raise when .active file doesn't exist."""
        # Should not raise
        clear_active_workspace(tmp_path)


class TestActiveWorkspaceRoundTrip:
    """Tests for active workspace get/set/clear cycle."""

    def test_set_then_get(self, tmp_path: Path) -> None:
        """Can set and then get the active workspace."""
        set_active_workspace(tmp_path, "test-workspace")
        result = get_active_workspace(tmp_path)
        assert result == "test-workspace"

    def test_set_clear_get(self, tmp_path: Path) -> None:
        """After clearing, get returns None."""
        set_active_workspace(tmp_path, "test-workspace")
        clear_active_workspace(tmp_path)
        result = get_active_workspace(tmp_path)
        assert result is None
