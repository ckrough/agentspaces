"""Beads issue tracker operations via subprocess."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - subprocess needed for beads CLI operations
from dataclasses import dataclass

import structlog

__all__ = [
    "BeadsError",
    "BeadsIssue",
    "get_issue_by_id",
    "get_ready_issues",
    "is_beads_available",
]

logger = structlog.get_logger()

# Default timeout for beads operations (5 seconds)
BEADS_TIMEOUT = 5


class BeadsError(Exception):
    """Raised when a beads operation fails."""

    def __init__(self, message: str, stderr: str | None = None) -> None:
        super().__init__(message)
        self.stderr = stderr


@dataclass(frozen=True)
class BeadsIssue:
    """Immutable beads issue information.

    Attributes:
        id: Issue ID (e.g., "agentspaces-1io").
        title: Issue title.
        description: Issue description.
        status: Issue status (open, in_progress, closed).
        priority: Issue priority (0-4, where 0 is highest).
        issue_type: Issue type (bug, feature, task, chore, epic).
        owner: Assignee email or None if unassigned.
    """

    id: str
    title: str
    description: str
    status: str
    priority: int
    issue_type: str
    owner: str | None


def is_beads_available() -> bool:
    """Check if beads CLI is available.

    Returns:
        True if bd command is in PATH, False otherwise.
    """
    return shutil.which("bd") is not None


def get_ready_issues() -> list[BeadsIssue]:
    """Get all ready (unblocked) issues.

    Returns list of unassigned issues only, suitable for
    automatic workspace creation.

    Returns:
        List of ready, unassigned BeadsIssue objects.

    Raises:
        BeadsError: If bd command fails or output is invalid.
    """
    if not is_beads_available():
        raise BeadsError("bd command not found in PATH")

    try:
        result = subprocess.run(  # nosec B603, B607
            ["bd", "ready", "--json"],
            capture_output=True,
            text=True,
            timeout=BEADS_TIMEOUT,
            check=False,
        )

        if result.returncode != 0:
            raise BeadsError(
                f"bd ready failed with exit code {result.returncode}",
                stderr=result.stderr,
            )

        issues_data = json.loads(result.stdout)
        if not isinstance(issues_data, list):
            raise BeadsError("bd ready returned invalid JSON (expected list)")

        # Parse issues and filter to unassigned only
        issues: list[BeadsIssue] = []
        for data in issues_data:
            issue = _parse_issue(data)
            # Filter to unassigned issues only (owner is None or empty string)
            if not issue.owner or issue.owner.strip() == "":
                issues.append(issue)

        logger.debug("beads_ready_issues", count=len(issues))
        return issues

    except subprocess.TimeoutExpired as e:
        raise BeadsError(
            f"bd ready timed out after {BEADS_TIMEOUT} seconds",
            stderr=e.stderr.decode() if e.stderr else None,
        ) from e
    except json.JSONDecodeError as e:
        raise BeadsError(f"Failed to parse bd ready JSON output: {e}") from e


def get_issue_by_id(issue_id: str) -> BeadsIssue:
    """Get a specific issue by ID.

    Args:
        issue_id: Issue identifier (e.g., "agentspaces-1io").

    Returns:
        BeadsIssue object with issue details.

    Raises:
        BeadsError: If bd command fails, issue not found, or output is invalid.
    """
    if not is_beads_available():
        raise BeadsError("bd command not found in PATH")

    try:
        result = subprocess.run(  # nosec B603, B607
            ["bd", "show", issue_id, "--json"],
            capture_output=True,
            text=True,
            timeout=BEADS_TIMEOUT,
            check=False,
        )

        if result.returncode != 0:
            # Check if issue not found
            if "not found" in result.stderr.lower():
                raise BeadsError(f"Issue not found: {issue_id}", stderr=result.stderr)
            raise BeadsError(
                f"bd show failed with exit code {result.returncode}",
                stderr=result.stderr,
            )

        issues_data = json.loads(result.stdout)

        # bd show returns a list with one item
        if isinstance(issues_data, list):
            if not issues_data:
                raise BeadsError(f"Issue not found: {issue_id}")
            issue_data = issues_data[0]
        elif isinstance(issues_data, dict):
            issue_data = issues_data
        else:
            raise BeadsError("bd show returned invalid JSON (expected list or dict)")

        issue = _parse_issue(issue_data)
        logger.debug("beads_get_issue", issue_id=issue.id)
        return issue

    except subprocess.TimeoutExpired as e:
        raise BeadsError(
            f"bd show timed out after {BEADS_TIMEOUT} seconds",
            stderr=e.stderr.decode() if e.stderr else None,
        ) from e
    except json.JSONDecodeError as e:
        raise BeadsError(f"Failed to parse bd show JSON output: {e}") from e


def _parse_issue(data: dict[str, object]) -> BeadsIssue:
    """Parse issue data from JSON dict.

    Args:
        data: JSON dict from bd command.

    Returns:
        BeadsIssue object.

    Raises:
        BeadsError: If required fields are missing or have invalid types.
    """
    try:
        # Type assertions for mypy - these are validated by try/except
        priority_val = data["priority"]
        if not isinstance(priority_val, int):
            priority_val = int(str(priority_val))

        return BeadsIssue(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            status=str(data["status"]),
            priority=priority_val,
            issue_type=str(data["issue_type"]),
            owner=str(data["owner"]) if data.get("owner") else None,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise BeadsError(f"Failed to parse issue data: {e}") from e
