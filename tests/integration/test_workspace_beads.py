"""Integration tests for beads workspace creation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentspaces.infrastructure.beads import BeadsIssue
from agentspaces.modules.workspace.service import WorkspaceService


@pytest.fixture
def mock_beads_issue() -> BeadsIssue:
    """Create a mock beads issue for testing."""
    return BeadsIssue(
        id="agentspaces-1a2b",
        title="Test Feature Implementation",
        description="Implement test feature",
        status="open",
        priority=2,
        issue_type="feature",
        owner=None,
    )


@pytest.fixture
def service(tmp_path: Path) -> WorkspaceService:
    """Create a workspace service with temp resolver."""
    from agentspaces.infrastructure.paths import PathResolver

    resolver = PathResolver(base=tmp_path)
    return WorkspaceService(resolver=resolver)


class TestCreateFromIssue:
    """Test create_from_issue() method."""

    def test_creates_workspace_with_issue_id_as_name(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should create workspace with issue ID as name and branch."""
        with patch("agentspaces.infrastructure.git.worktree_add") as mock_git:
            workspace = service.create_from_issue(
                mock_beads_issue,
                base_branch="main",
                setup_venv=False,
            )

            # Verify git was called correctly
            mock_git.assert_called_once()
            call_args = mock_git.call_args
            assert call_args[1]["branch"] == "agentspaces-1a2b"

        assert workspace.name == "agentspaces-1a2b"
        assert workspace.branch == "agentspaces-1a2b"
        assert workspace.issue_id == "agentspaces-1a2b"

    def test_sets_purpose_from_issue(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should set purpose to 'issue_id: title'."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            workspace = service.create_from_issue(
                mock_beads_issue,
                setup_venv=False,
            )

        assert workspace.purpose == "agentspaces-1a2b: Test Feature Implementation"

    def test_persists_issue_id_in_metadata(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should persist issue_id in workspace.json metadata."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            workspace = service.create_from_issue(
                mock_beads_issue,
                setup_venv=False,
            )

        # Read metadata file (use actual workspace path)
        metadata_path = workspace.path / ".agentspace" / "workspace.json"
        assert metadata_path.exists()

        data = json.loads(metadata_path.read_text())
        assert data["issue_id"] == "agentspaces-1a2b"
        assert data["version"] == "4"

    def test_uses_provided_base_branch(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should use provided base_branch parameter."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            workspace = service.create_from_issue(
                mock_beads_issue,
                base_branch="develop",
                setup_venv=False,
            )

        assert workspace.base_branch == "develop"

    def test_respects_setup_venv_flag(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should respect setup_venv parameter."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            # With venv
            with patch(
                "agentspaces.modules.workspace.environment.setup_environment"
            ) as mock_setup:
                from agentspaces.modules.workspace.environment import EnvironmentInfo

                mock_setup.return_value = EnvironmentInfo(
                    has_venv=True,
                    python_version="3.13",
                    has_pyproject=True,
                    venv_path=None,
                )

                workspace = service.create_from_issue(
                    mock_beads_issue,
                    setup_venv=True,
                )
                assert mock_setup.called

            # Without venv - create different issue to avoid name collision
            issue_no_venv = BeadsIssue(
                id="agentspaces-2b3c",
                title="Another Test Feature",
                description="Test without venv",
                status="open",
                priority=2,
                issue_type="feature",
                owner=None,
            )
            workspace = service.create_from_issue(
                issue_no_venv,
                setup_venv=False,
            )
            assert not workspace.has_venv

    def test_rejects_duplicate_issue_workspace(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should reject creating workspace for same issue twice."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            # Create first workspace
            service.create_from_issue(mock_beads_issue, setup_venv=False)

            # Try to create duplicate
            from agentspaces.modules.workspace.service import WorkspaceError

            with pytest.raises(WorkspaceError, match="already exists"):
                service.create_from_issue(mock_beads_issue, setup_venv=False)


class TestWorkspaceListWithIssues:
    """Test listing workspaces with issue_id field."""

    def test_list_includes_issue_id(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should include issue_id in listed workspaces."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            service.create_from_issue(mock_beads_issue, setup_venv=False)

        with patch("agentspaces.infrastructure.git.worktree_list") as mock_list:
            from agentspaces.infrastructure.git import WorktreeInfo

            mock_list.return_value = [
                WorktreeInfo(
                    path=Path("/fake/path/agentspaces-1a2b"),
                    branch="agentspaces-1a2b",
                    commit="abc123",
                    is_main=False,
                )
            ]

            workspaces = service.list()

        assert len(workspaces) == 1
        assert workspaces[0].issue_id == "agentspaces-1a2b"

    def test_list_handles_workspaces_without_issue_id(
        self, service: WorkspaceService
    ) -> None:
        """Should handle workspaces without issue_id (backward compat)."""
        # Create workspace without issue_id (old-style)
        with patch("agentspaces.infrastructure.git.worktree_add"):
            workspace = service.create(
                base_branch="main",
                setup_venv=False,
            )

        with patch("agentspaces.infrastructure.git.worktree_list") as mock_list:
            from agentspaces.infrastructure.git import WorktreeInfo

            mock_list.return_value = [
                WorktreeInfo(
                    path=workspace.path,
                    branch=workspace.branch,
                    commit="abc123",
                    is_main=False,
                )
            ]

            workspaces = service.list()

        assert len(workspaces) == 1
        assert workspaces[0].issue_id is None


class TestCustomWorkspaceName:
    """Test custom workspace names."""

    def test_create_with_custom_name(self, service: WorkspaceService) -> None:
        """Should create workspace with custom name."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            workspace = service.create(
                base_branch="main",
                workspace_name="custom-workspace",
                setup_venv=False,
            )

        assert workspace.name == "custom-workspace"
        assert workspace.branch == "custom-workspace"

    def test_rejects_duplicate_workspace_name(self, service: WorkspaceService) -> None:
        """Should reject duplicate custom workspace names."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            # Create first workspace
            service.create(
                workspace_name="duplicate-name",
                setup_venv=False,
            )

            # Try to create duplicate
            from agentspaces.modules.workspace.service import WorkspaceError

            with pytest.raises(WorkspaceError, match="already exists"):
                service.create(
                    workspace_name="duplicate-name",
                    setup_venv=False,
                )


class TestMetadataSchemaV4:
    """Test metadata schema v4 with issue_id."""

    def test_metadata_v4_round_trip(
        self, service: WorkspaceService, mock_beads_issue: BeadsIssue
    ) -> None:
        """Should save and load v4 metadata correctly."""
        with patch("agentspaces.infrastructure.git.worktree_add"):
            # Create workspace with issue
            workspace = service.create_from_issue(
                mock_beads_issue,
                setup_venv=False,
            )

        # Load it back (outside patch context, mock worktree_list)
        with patch("agentspaces.infrastructure.git.worktree_list") as mock_list:
            from agentspaces.infrastructure.git import WorktreeInfo

            mock_list.return_value = [
                WorktreeInfo(
                    path=workspace.path,
                    branch=workspace.branch,
                    commit="abc123",
                    is_main=False,
                )
            ]

            loaded_workspace = service.get(workspace.name)

        assert loaded_workspace.issue_id == "agentspaces-1a2b"
        assert loaded_workspace.name == "agentspaces-1a2b"

    def test_v3_metadata_loads_without_issue_id(
        self, service: WorkspaceService
    ) -> None:
        """Should load v3 metadata with issue_id=None."""
        # Create old-style workspace (no issue_id)
        with patch("agentspaces.infrastructure.git.worktree_add"):
            workspace = service.create(
                base_branch="main",
                setup_venv=False,
            )

        # Manually modify metadata to v3 format (remove issue_id)
        metadata_path = workspace.path / ".agentspace" / "workspace.json"
        data = json.loads(metadata_path.read_text())
        data["version"] = "3"
        data.pop("issue_id", None)
        metadata_path.write_text(json.dumps(data, indent=2))

        # Load it back (mock worktree_list)
        with patch("agentspaces.infrastructure.git.worktree_list") as mock_list:
            from agentspaces.infrastructure.git import WorktreeInfo

            mock_list.return_value = [
                WorktreeInfo(
                    path=workspace.path,
                    branch=workspace.branch,
                    commit="abc123",
                    is_main=False,
                )
            ]

            loaded_workspace = service.get(workspace.name)

        assert loaded_workspace.issue_id is None
        assert loaded_workspace.name == workspace.name
