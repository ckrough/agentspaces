"""Tests for the metadata module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from agentspaces.infrastructure.metadata import (
    MetadataError,
    WorkspaceMetadata,
    load_workspace_metadata,
    save_workspace_metadata,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestWorkspaceMetadata:
    """Tests for WorkspaceMetadata dataclass."""

    def test_metadata_is_frozen(self) -> None:
        """WorkspaceMetadata should be immutable."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )

        with pytest.raises(AttributeError):
            metadata.name = "new-name"  # type: ignore[misc]

    def test_metadata_defaults(self) -> None:
        """Should have sensible defaults."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )

        assert metadata.purpose is None
        assert metadata.python_version is None
        assert metadata.has_venv is False
        assert metadata.status == "active"
        assert metadata.deps_synced_at is None
        assert metadata.last_activity_at is None

    def test_metadata_all_fields(self) -> None:
        """Should store all provided fields."""
        created_at = datetime.now(UTC)
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=created_at,
            purpose="Test purpose",
            python_version="3.12",
            has_venv=True,
            status="active",
        )

        assert metadata.name == "test-workspace"
        assert metadata.project == "test-project"
        assert metadata.branch == "test-workspace"
        assert metadata.base_branch == "main"
        assert metadata.created_at == created_at
        assert metadata.purpose == "Test purpose"
        assert metadata.python_version == "3.12"
        assert metadata.has_venv is True
        assert metadata.status == "active"


class TestSaveWorkspaceMetadata:
    """Tests for save_workspace_metadata function."""

    def test_save_creates_file(self, temp_dir: Path) -> None:
        """Should create workspace.json file."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        path = temp_dir / "workspace.json"

        save_workspace_metadata(metadata, path)

        assert path.exists()

    def test_save_includes_version(self, temp_dir: Path) -> None:
        """Should include version field for schema evolution."""
        import json

        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        path = temp_dir / "workspace.json"

        save_workspace_metadata(metadata, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert "version" in data
        assert data["version"] == "2"  # Schema version 2 with timestamp fields

    def test_save_creates_parent_directories(self, temp_dir: Path) -> None:
        """Should create parent directories if needed."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        path = temp_dir / "deep" / "nested" / "workspace.json"

        save_workspace_metadata(metadata, path)

        assert path.exists()

    def test_save_overwrites_existing(self, temp_dir: Path) -> None:
        """Should overwrite existing file."""
        import json

        path = temp_dir / "workspace.json"
        path.write_text('{"old": "data"}', encoding="utf-8")

        metadata = WorkspaceMetadata(
            name="new-workspace",
            project="test-project",
            branch="new-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )

        save_workspace_metadata(metadata, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["name"] == "new-workspace"
        assert "old" not in data


class TestLoadWorkspaceMetadata:
    """Tests for load_workspace_metadata function."""

    def test_load_existing_file(self, temp_dir: Path) -> None:
        """Should load metadata from existing file."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            purpose="Test purpose",
        )
        path = temp_dir / "workspace.json"
        save_workspace_metadata(metadata, path)

        loaded = load_workspace_metadata(path)

        assert loaded is not None
        assert loaded.name == "test-workspace"
        assert loaded.project == "test-project"
        assert loaded.purpose == "Test purpose"

    def test_load_missing_file_returns_none(self, temp_dir: Path) -> None:
        """Should return None for missing file."""
        path = temp_dir / "nonexistent.json"

        result = load_workspace_metadata(path)

        assert result is None

    def test_load_invalid_json_returns_none(self, temp_dir: Path) -> None:
        """Should return None for invalid JSON."""
        path = temp_dir / "workspace.json"
        path.write_text("not valid json {{{", encoding="utf-8")

        result = load_workspace_metadata(path)

        assert result is None

    def test_load_missing_required_field_returns_none(self, temp_dir: Path) -> None:
        """Should return None when required fields missing."""
        import json

        path = temp_dir / "workspace.json"
        path.write_text(json.dumps({"name": "test", "version": "1"}), encoding="utf-8")

        result = load_workspace_metadata(path)

        assert result is None

    def test_load_preserves_datetime(self, temp_dir: Path) -> None:
        """Should preserve datetime correctly."""
        created_at = datetime(2025, 12, 20, 10, 30, 0, tzinfo=UTC)
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=created_at,
        )
        path = temp_dir / "workspace.json"
        save_workspace_metadata(metadata, path)

        loaded = load_workspace_metadata(path)

        assert loaded is not None
        assert loaded.created_at == created_at

    def test_load_handles_future_version(self, temp_dir: Path) -> None:
        """Should gracefully handle newer schema versions."""
        import json

        path = temp_dir / "workspace.json"
        data = {
            "version": "99",  # Future version
            "name": "test-workspace",
            "project": "test-project",
            "branch": "test-workspace",
            "base_branch": "main",
            "created_at": datetime.now(UTC).isoformat(),
            "new_field": "some value",  # Unknown field
        }
        path.write_text(json.dumps(data), encoding="utf-8")

        loaded = load_workspace_metadata(path)

        # Should still load successfully
        assert loaded is not None
        assert loaded.name == "test-workspace"


class TestMetadataTimestampFields:
    """Tests for new timestamp fields in WorkspaceMetadata."""

    def test_deps_synced_at_stored(self, temp_dir: Path) -> None:
        """Should store and load deps_synced_at timestamp."""
        synced_at = datetime(2025, 12, 20, 12, 0, 0, tzinfo=UTC)
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            deps_synced_at=synced_at,
        )
        path = temp_dir / "workspace.json"

        save_workspace_metadata(metadata, path)
        loaded = load_workspace_metadata(path)

        assert loaded is not None
        assert loaded.deps_synced_at == synced_at

    def test_last_activity_at_stored(self, temp_dir: Path) -> None:
        """Should store and load last_activity_at timestamp."""
        activity_at = datetime(2025, 12, 20, 14, 30, 0, tzinfo=UTC)
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            last_activity_at=activity_at,
        )
        path = temp_dir / "workspace.json"

        save_workspace_metadata(metadata, path)
        loaded = load_workspace_metadata(path)

        assert loaded is not None
        assert loaded.last_activity_at == activity_at

    def test_both_timestamps_stored(self, temp_dir: Path) -> None:
        """Should store and load both timestamps together."""
        synced_at = datetime(2025, 12, 20, 12, 0, 0, tzinfo=UTC)
        activity_at = datetime(2025, 12, 20, 14, 30, 0, tzinfo=UTC)
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            deps_synced_at=synced_at,
            last_activity_at=activity_at,
        )
        path = temp_dir / "workspace.json"

        save_workspace_metadata(metadata, path)
        loaded = load_workspace_metadata(path)

        assert loaded is not None
        assert loaded.deps_synced_at == synced_at
        assert loaded.last_activity_at == activity_at

    def test_none_timestamps_remain_none(self, temp_dir: Path) -> None:
        """None timestamps should remain None after round-trip."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        path = temp_dir / "workspace.json"

        save_workspace_metadata(metadata, path)
        loaded = load_workspace_metadata(path)

        assert loaded is not None
        assert loaded.deps_synced_at is None
        assert loaded.last_activity_at is None


class TestMetadataError:
    """Tests for MetadataError exception."""

    def test_metadata_error_message(self) -> None:
        """MetadataError should store message."""
        error = MetadataError("Something went wrong")
        assert str(error) == "Something went wrong"
