"""Tests for beads integration module."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from agentspaces.infrastructure.beads import (
    BeadsError,
    BeadsIssue,
    get_issue_by_id,
    get_ready_issues,
    is_beads_available,
)


class TestIsBeadsAvailable:
    """Tests for is_beads_available()."""

    def test_returns_true_when_bd_in_path(self) -> None:
        """Should return True when bd command is available."""
        with patch("shutil.which", return_value="/usr/bin/bd"):
            assert is_beads_available() is True

    def test_returns_false_when_bd_not_in_path(self) -> None:
        """Should return False when bd command is not available."""
        with patch("shutil.which", return_value=None):
            assert is_beads_available() is False


class TestGetReadyIssues:
    """Tests for get_ready_issues()."""

    def test_raises_error_when_bd_not_available(self) -> None:
        """Should raise BeadsError when bd not in PATH."""
        with patch(
            "agentspaces.infrastructure.beads.is_beads_available", return_value=False
        ):
            with pytest.raises(BeadsError, match="bd command not found"):
                get_ready_issues()

    def test_returns_unassigned_issues_only(self) -> None:
        """Should filter to unassigned issues only."""
        issues_data = [
            {
                "id": "test-1",
                "title": "Unassigned task",
                "description": "Desc",
                "status": "open",
                "priority": 2,
                "issue_type": "task",
                "owner": None,
            },
            {
                "id": "test-2",
                "title": "Assigned task",
                "description": "Desc",
                "status": "open",
                "priority": 2,
                "issue_type": "task",
                "owner": "user@example.com",
            },
            {
                "id": "test-3",
                "title": "Empty owner",
                "description": "Desc",
                "status": "open",
                "priority": 2,
                "issue_type": "task",
                "owner": "",
            },
        ]

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(issues_data)

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            issues = get_ready_issues()

        assert len(issues) == 2
        assert issues[0].id == "test-1"
        assert issues[1].id == "test-3"

    def test_raises_error_on_command_failure(self) -> None:
        """Should raise BeadsError when bd command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(BeadsError, match="bd ready failed"):
                get_ready_issues()

    def test_raises_error_on_invalid_json(self) -> None:
        """Should raise BeadsError when output is not valid JSON."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(BeadsError, match="Failed to parse"):
                get_ready_issues()

    def test_raises_error_on_timeout(self) -> None:
        """Should raise BeadsError when command times out."""
        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("bd", 5)),
        ):
            with pytest.raises(BeadsError, match="timed out"):
                get_ready_issues()


class TestGetIssueById:
    """Tests for get_issue_by_id()."""

    def test_raises_error_when_bd_not_available(self) -> None:
        """Should raise BeadsError when bd not in PATH."""
        with patch(
            "agentspaces.infrastructure.beads.is_beads_available", return_value=False
        ):
            with pytest.raises(BeadsError, match="bd command not found"):
                get_issue_by_id("test-1")

    def test_returns_issue_from_list_response(self) -> None:
        """Should parse issue from list response (single item)."""
        issue_data = [
            {
                "id": "test-1",
                "title": "Test Issue",
                "description": "Test description",
                "status": "open",
                "priority": 2,
                "issue_type": "task",
                "owner": None,
            }
        ]

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(issue_data)

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            issue = get_issue_by_id("test-1")

        assert issue.id == "test-1"
        assert issue.title == "Test Issue"
        assert issue.priority == 2

    def test_returns_issue_from_dict_response(self) -> None:
        """Should parse issue from dict response."""
        issue_data = {
            "id": "test-1",
            "title": "Test Issue",
            "description": "Test description",
            "status": "open",
            "priority": 2,
            "issue_type": "task",
            "owner": None,
        }

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(issue_data)

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            issue = get_issue_by_id("test-1")

        assert issue.id == "test-1"
        assert issue.title == "Test Issue"

    def test_raises_error_when_issue_not_found(self) -> None:
        """Should raise BeadsError when issue not found."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Issue not found: test-1"

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(BeadsError, match="Issue not found: test-1"):
                get_issue_by_id("test-1")

    def test_raises_error_on_empty_list(self) -> None:
        """Should raise BeadsError when list is empty."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with (
            patch(
                "agentspaces.infrastructure.beads.is_beads_available", return_value=True
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(BeadsError, match="Issue not found"):
                get_issue_by_id("test-1")


class TestBeadsIssue:
    """Tests for BeadsIssue dataclass."""

    def test_issue_is_frozen(self) -> None:
        """Should be immutable."""
        issue = BeadsIssue(
            id="test-1",
            title="Test",
            description="Desc",
            status="open",
            priority=2,
            issue_type="task",
            owner=None,
        )

        with pytest.raises(AttributeError):
            issue.title = "Changed"  # type: ignore[misc]

    def test_issue_equality(self) -> None:
        """Should support equality comparison."""
        issue1 = BeadsIssue(
            id="test-1",
            title="Test",
            description="Desc",
            status="open",
            priority=2,
            issue_type="task",
            owner=None,
        )
        issue2 = BeadsIssue(
            id="test-1",
            title="Test",
            description="Desc",
            status="open",
            priority=2,
            issue_type="task",
            owner=None,
        )

        assert issue1 == issue2
