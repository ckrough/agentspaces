"""Tests for docs CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from agentspaces.cli.docs import (
    ALL_GROUPS,
    SCAFFOLD_STRUCTURE,
    TEMPLATE_GROUPS,
    _detect_project_name,
    _get_templates_for_groups,
    app,
)

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class TestGetTemplatesForGroups:
    """Tests for _get_templates_for_groups helper function."""

    def test_default_excludes_root_templates(self) -> None:
        """Default behavior should exclude root templates."""
        templates = _get_templates_for_groups(include=None, exclude=None)
        root_templates = set(TEMPLATE_GROUPS["root"])
        assert not any(t in templates for t in root_templates)

    def test_default_includes_claude_docs_adr(self) -> None:
        """Default behavior should include claude, docs, and adr groups."""
        templates = _get_templates_for_groups(include=None, exclude=None)
        for group in ["claude", "docs", "adr"]:
            for template_name in TEMPLATE_GROUPS[group]:
                assert template_name in templates

    def test_include_only_specified_groups(self) -> None:
        """Should only include specified groups when include is set."""
        templates = _get_templates_for_groups(include=["root"], exclude=None)
        root_templates = set(TEMPLATE_GROUPS["root"])
        assert all(t in templates for t in root_templates)
        # Should not include other groups
        for other_group in ["claude", "docs", "adr"]:
            for template_name in TEMPLATE_GROUPS[other_group]:
                assert template_name not in templates

    def test_exclude_removes_from_defaults(self) -> None:
        """Exclude should remove groups from default set."""
        templates = _get_templates_for_groups(include=None, exclude=["adr"])
        for template_name in TEMPLATE_GROUPS["adr"]:
            assert template_name not in templates
        # Other groups should still be included
        for group in ["claude", "docs"]:
            for template_name in TEMPLATE_GROUPS[group]:
                assert template_name in templates

    def test_include_and_exclude_together(self) -> None:
        """Include and exclude should work together."""
        templates = _get_templates_for_groups(
            include=["root", "docs"], exclude=["docs"]
        )
        # Only root should remain
        for template_name in TEMPLATE_GROUPS["root"]:
            assert template_name in templates
        for template_name in TEMPLATE_GROUPS["docs"]:
            assert template_name not in templates

    def test_empty_result_when_all_excluded(self) -> None:
        """Should return empty dict when all groups excluded."""
        templates = _get_templates_for_groups(
            include=None, exclude=["claude", "docs", "adr"]
        )
        assert templates == {}


class TestDetectProjectName:
    """Tests for _detect_project_name function."""

    def test_returns_directory_name_as_fallback(self, temp_dir: Path) -> None:
        """Should return directory name when no pyproject.toml exists."""
        project_dir = temp_dir / "my-cool-project"
        project_dir.mkdir()
        assert _detect_project_name(project_dir) == "my-cool-project"

    def test_reads_name_from_pyproject_toml(self, temp_dir: Path) -> None:
        """Should read project name from pyproject.toml."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "awesome-lib"\n', encoding="utf-8")
        assert _detect_project_name(project_dir) == "awesome-lib"

    def test_fallback_when_pyproject_has_no_name(self, temp_dir: Path) -> None:
        """Should fall back to directory name if pyproject has no name."""
        project_dir = temp_dir / "fallback-project"
        project_dir.mkdir()
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n", encoding="utf-8")
        assert _detect_project_name(project_dir) == "fallback-project"


class TestRenderCommand:
    """Tests for the render command."""

    def test_renders_default_templates_to_directory(self, temp_dir: Path) -> None:
        """Should render default templates (claude, docs, adr) to directory."""
        result = runner.invoke(
            app,
            [
                "render",
                str(temp_dir),
                "-n",
                "TestProject",
                "-d",
                "A test project",
            ],
        )
        assert result.exit_code == 0
        # Check that docs files were created
        assert (temp_dir / "docs/design/architecture.md").exists()
        assert (temp_dir / "docs/design/development-standards.md").exists()
        assert (temp_dir / ".claude/agents/README.md").exists()
        assert (temp_dir / "docs/adr/000-template.md").exists()
        # Root files should NOT be created by default
        assert not (temp_dir / "README.md").exists()
        assert not (temp_dir / "CLAUDE.md").exists()

    def test_skips_existing_files(self, temp_dir: Path) -> None:
        """Should skip existing files without --force."""
        # Create an existing file
        docs_dir = temp_dir / "docs" / "design"
        docs_dir.mkdir(parents=True)
        existing = docs_dir / "architecture.md"
        existing.write_text("# Existing content\n", encoding="utf-8")

        result = runner.invoke(
            app,
            ["render", str(temp_dir), "-n", "TestProject", "-d", "Test"],
        )
        assert result.exit_code == 0
        assert "Skipped" in result.output
        # File should not be overwritten
        assert existing.read_text() == "# Existing content\n"

    def test_force_overwrites_existing_files(self, temp_dir: Path) -> None:
        """Should overwrite existing files with --force."""
        docs_dir = temp_dir / "docs" / "design"
        docs_dir.mkdir(parents=True)
        existing = docs_dir / "architecture.md"
        existing.write_text("# Existing content\n", encoding="utf-8")

        result = runner.invoke(
            app,
            ["render", str(temp_dir), "-n", "TestProject", "-d", "Test", "-f"],
        )
        assert result.exit_code == 0
        # File should be overwritten
        content = existing.read_text()
        assert "Existing content" not in content
        assert "TestProject" in content

    def test_dry_run_shows_preview_without_writing(self, temp_dir: Path) -> None:
        """Should show preview without writing files in dry-run mode."""
        result = runner.invoke(
            app,
            [
                "render",
                str(temp_dir),
                "-n",
                "TestProject",
                "-d",
                "Test",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Would create" in result.output
        # No files should be created
        assert not (temp_dir / "docs/design/architecture.md").exists()

    def test_include_specific_groups(self, temp_dir: Path) -> None:
        """Should only render specified groups with --include."""
        result = runner.invoke(
            app,
            [
                "render",
                str(temp_dir),
                "-n",
                "TestProject",
                "-d",
                "Test",
                "-i",
                "root",
            ],
        )
        assert result.exit_code == 0
        # Root files should be created
        assert (temp_dir / "README.md").exists()
        assert (temp_dir / "CLAUDE.md").exists()
        # Other groups should NOT be created
        assert not (temp_dir / "docs/design/architecture.md").exists()
        assert not (temp_dir / ".claude/agents/README.md").exists()

    def test_exclude_specific_groups(self, temp_dir: Path) -> None:
        """Should exclude specified groups with --exclude."""
        result = runner.invoke(
            app,
            [
                "render",
                str(temp_dir),
                "-n",
                "TestProject",
                "-d",
                "Test",
                "-e",
                "adr",
            ],
        )
        assert result.exit_code == 0
        # ADR files should NOT be created
        assert not (temp_dir / "docs/adr/000-template.md").exists()
        # Other groups should be created
        assert (temp_dir / "docs/design/architecture.md").exists()
        assert (temp_dir / ".claude/agents/README.md").exists()

    def test_auto_detects_project_name(self, temp_dir: Path) -> None:
        """Should auto-detect project name from pyproject.toml."""
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "auto-detected"\n', encoding="utf-8")

        result = runner.invoke(
            app,
            ["render", str(temp_dir), "-d", "Test project", "-i", "docs"],
        )
        assert result.exit_code == 0
        content = (temp_dir / "docs/design/architecture.md").read_text()
        assert "auto-detected" in content

    def test_fails_for_nonexistent_directory(self, temp_dir: Path) -> None:
        """Should fail for non-existent directory."""
        result = runner.invoke(
            app,
            [
                "render",
                str(temp_dir / "nonexistent"),
                "-n",
                "Test",
                "-d",
                "Test",
            ],
        )
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_fails_for_invalid_group_name(self, temp_dir: Path) -> None:
        """Should fail for invalid group names."""
        result = runner.invoke(
            app,
            [
                "render",
                str(temp_dir),
                "-n",
                "Test",
                "-d",
                "Test",
                "-i",
                "invalid_group",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid groups" in result.output


class TestTemplateGroups:
    """Tests for template group constants."""

    def test_all_groups_matches_template_groups_keys(self) -> None:
        """ALL_GROUPS should contain all TEMPLATE_GROUPS keys."""
        assert set(ALL_GROUPS) == set(TEMPLATE_GROUPS.keys())

    def test_all_template_names_in_scaffold_structure(self) -> None:
        """All template names in groups should exist in SCAFFOLD_STRUCTURE."""
        for group_name, templates in TEMPLATE_GROUPS.items():
            for template_name in templates:
                assert template_name in SCAFFOLD_STRUCTURE, (
                    f"{template_name} from {group_name} not in SCAFFOLD_STRUCTURE"
                )


class TestScaffoldCommand:
    """Tests for the scaffold command (existing functionality)."""

    def test_creates_all_templates(self, temp_dir: Path) -> None:
        """Should create all templates in scaffold structure."""
        target = temp_dir / "new-project"
        target.mkdir()

        result = runner.invoke(
            app,
            [
                "scaffold",
                str(target),
                "-n",
                "NewProject",
                "-d",
                "A new project",
            ],
        )
        assert result.exit_code == 0
        # Check all files from SCAFFOLD_STRUCTURE were created
        for relative_path in SCAFFOLD_STRUCTURE.values():
            assert (target / relative_path).exists(), f"Missing: {relative_path}"
