"""Tests for the skills module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from agentspaces.infrastructure.metadata import WorkspaceMetadata
from agentspaces.infrastructure.skills import (
    SkillError,
    generate_workspace_context_skill,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestGenerateWorkspaceContextSkill:
    """Tests for generate_workspace_context_skill function."""

    def test_generates_skill_file(self, temp_dir: Path) -> None:
        """Should create SKILL.md in skill directory."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        output_dir = temp_dir / "skills" / "workspace-context"

        result = generate_workspace_context_skill(metadata, output_dir)

        assert result.exists()
        assert result.name == "SKILL.md"

    def test_includes_workspace_name(self, temp_dir: Path) -> None:
        """Should render workspace name in template."""
        metadata = WorkspaceMetadata(
            name="eager-turing",
            project="test-project",
            branch="eager-turing",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        output_dir = temp_dir / "skills" / "workspace-context"

        result = generate_workspace_context_skill(metadata, output_dir)

        content = result.read_text(encoding="utf-8")
        assert "eager-turing" in content

    def test_includes_purpose(self, temp_dir: Path) -> None:
        """Should render purpose when provided."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            purpose="Implement new authentication system",
        )
        output_dir = temp_dir / "skills" / "workspace-context"

        result = generate_workspace_context_skill(metadata, output_dir)

        content = result.read_text(encoding="utf-8")
        assert "Implement new authentication system" in content

    def test_purpose_default_when_none(self, temp_dir: Path) -> None:
        """Should use default text when purpose is None."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            purpose=None,
        )
        output_dir = temp_dir / "skills" / "workspace-context"

        result = generate_workspace_context_skill(metadata, output_dir)

        content = result.read_text(encoding="utf-8")
        # Should contain the default purpose message from the template
        assert "No specific purpose defined" in content

    def test_includes_branch_info(self, temp_dir: Path) -> None:
        """Should render branch information."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="develop",
            created_at=datetime.now(UTC),
        )
        output_dir = temp_dir / "skills" / "workspace-context"

        result = generate_workspace_context_skill(metadata, output_dir)

        content = result.read_text(encoding="utf-8")
        assert "test-workspace" in content
        assert "develop" in content

    def test_creates_output_directory(self, temp_dir: Path) -> None:
        """Should create output directory if needed."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )
        output_dir = temp_dir / "deep" / "nested" / "skills"

        result = generate_workspace_context_skill(metadata, output_dir)

        assert output_dir.exists()
        assert result.exists()

    def test_includes_python_version_when_set(self, temp_dir: Path) -> None:
        """Should include Python version when available."""
        metadata = WorkspaceMetadata(
            name="test-workspace",
            project="test-project",
            branch="test-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
            python_version="3.12",
            has_venv=True,
        )
        output_dir = temp_dir / "skills" / "workspace-context"

        result = generate_workspace_context_skill(metadata, output_dir)

        content = result.read_text(encoding="utf-8")
        assert "3.12" in content

    def test_overwrites_existing_skill(self, temp_dir: Path) -> None:
        """Should overwrite existing skill file."""
        output_dir = temp_dir / "skills" / "workspace-context"
        output_dir.mkdir(parents=True)
        existing = output_dir / "SKILL.md"
        existing.write_text("old content", encoding="utf-8")

        metadata = WorkspaceMetadata(
            name="new-workspace",
            project="test-project",
            branch="new-workspace",
            base_branch="main",
            created_at=datetime.now(UTC),
        )

        result = generate_workspace_context_skill(metadata, output_dir)

        content = result.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "new-workspace" in content


class TestSkillError:
    """Tests for SkillError exception."""

    def test_skill_error_message(self) -> None:
        """SkillError should store message."""
        error = SkillError("Template not found")
        assert str(error) == "Template not found"
