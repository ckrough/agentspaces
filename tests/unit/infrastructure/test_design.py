"""Tests for the design template module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from agentspaces.infrastructure.design import (
    DesignError,
    get_design_template,
    list_design_templates,
    render_design_template,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestListDesignTemplates:
    """Tests for list_design_templates function."""

    def test_returns_all_templates(self) -> None:
        """Should return metadata for all templates in skeleton/."""
        templates = list_design_templates()

        # Verify expected templates exist
        names = {t.name for t in templates}
        # Docs templates
        assert "architecture" in names
        assert "development-standards" in names
        assert "deployment" in names
        assert "adr-template" in names
        assert "adr-example" in names
        # Root templates
        assert "readme" in names
        assert "claude-md" in names
        assert "todo-md" in names
        # .claude directory templates
        assert "agents-readme" in names
        assert "commands-readme" in names

    def test_parses_frontmatter(self) -> None:
        """Should parse frontmatter correctly."""
        templates = list_design_templates()
        arch = next(t for t in templates if t.name == "architecture")

        assert arch.category == "reference"
        assert "project_name" in arch.required_variables
        assert "project_description" in arch.required_variables
        assert len(arch.when_to_use) > 0

    def test_sorted_by_category_and_name(self) -> None:
        """Should return templates sorted by category then name."""
        templates = list_design_templates()

        # Verify sorted by category
        categories = [t.category for t in templates]
        assert categories == sorted(categories)

        # Verify sorted by name within category
        by_category: dict[str, list[str]] = {}
        for t in templates:
            by_category.setdefault(t.category, []).append(t.name)
        for names in by_category.values():
            assert names == sorted(names)

    def test_includes_path(self) -> None:
        """Should include path to template file."""
        templates = list_design_templates()
        arch = next(t for t in templates if t.name == "architecture")

        assert arch.path.exists()
        assert arch.path.name == "architecture.md"


class TestGetDesignTemplate:
    """Tests for get_design_template function."""

    def test_returns_template_by_name(self) -> None:
        """Should return matching template."""
        template = get_design_template("architecture")

        assert template.name == "architecture"
        assert template.category == "reference"

    def test_raises_error_for_unknown_template(self) -> None:
        """Should raise DesignError for unknown template."""
        with pytest.raises(DesignError, match="not found"):
            get_design_template("nonexistent-template")

    def test_error_lists_available_templates(self) -> None:
        """Error message should list available templates."""
        with pytest.raises(DesignError) as exc_info:
            get_design_template("nonexistent")

        error_msg = str(exc_info.value)
        assert "architecture" in error_msg
        assert "Available:" in error_msg


class TestRenderDesignTemplate:
    """Tests for render_design_template function."""

    def test_renders_with_required_variables(self, temp_dir: Path) -> None:
        """Should render template with all required variables."""
        output = temp_dir / "architecture.md"

        result = render_design_template(
            "architecture",
            {
                "project_name": "TestApp",
                "project_description": "A test application",
            },
            output,
        )

        assert result.exists()
        content = result.read_text()
        assert "TestApp" in content
        assert "A test application" in content

    def test_preserves_frontmatter_in_output(self, temp_dir: Path) -> None:
        """Should include YAML frontmatter in rendered output."""
        output = temp_dir / "architecture.md"

        render_design_template(
            "architecture",
            {
                "project_name": "TestApp",
                "project_description": "A test application",
            },
            output,
        )

        content = output.read_text()
        # Frontmatter should be present
        assert content.startswith("---\n")
        assert "name: architecture" in content
        assert "description:" in content
        assert "category: reference" in content
        # Variables section should be stripped (template metadata, not doc metadata)
        assert "variables:" not in content

    def test_error_on_missing_required_variable(self, temp_dir: Path) -> None:
        """Should raise DesignError when required variable missing."""
        output = temp_dir / "architecture.md"

        with pytest.raises(DesignError, match="Missing required variables"):
            render_design_template(
                "architecture",
                {},  # Missing required variables
                output,
            )

    def test_error_message_lists_missing_variables(self, temp_dir: Path) -> None:
        """Error should list which variables are missing."""
        output = temp_dir / "architecture.md"

        with pytest.raises(DesignError) as exc_info:
            render_design_template("architecture", {}, output)

        error_msg = str(exc_info.value)
        assert "project_name" in error_msg

    def test_creates_output_directory(self, temp_dir: Path) -> None:
        """Should create output directory if it doesn't exist."""
        output = temp_dir / "deep" / "nested" / "docs" / "architecture.md"

        result = render_design_template(
            "architecture",
            {
                "project_name": "TestApp",
                "project_description": "A test application",
            },
            output,
        )

        assert output.parent.exists()
        assert result.exists()

    def test_overwrites_existing_file(self, temp_dir: Path) -> None:
        """Should overwrite existing file."""
        output = temp_dir / "architecture.md"
        output.write_text("old content")

        render_design_template(
            "architecture",
            {
                "project_name": "NewApp",
                "project_description": "New description",
            },
            output,
        )

        content = output.read_text()
        assert "old content" not in content
        assert "NewApp" in content

    def test_uses_defaults_for_optional_variables(self, temp_dir: Path) -> None:
        """Should use default values for optional variables."""
        output = temp_dir / "development-standards.md"

        result = render_design_template(
            "development-standards",
            {"project_name": "TestApp"},
            output,
        )

        content = result.read_text()
        # Should have default values from template
        assert "GitHub Flow" in content  # Default git_workflow
        assert "80" in content  # Default test_coverage_target

    def test_renders_with_optional_variables(self, temp_dir: Path) -> None:
        """Should render template with optional variables when provided."""
        output = temp_dir / "development-standards.md"

        result = render_design_template(
            "development-standards",
            {
                "project_name": "TestApp",
                "git_workflow": "GitFlow",
                "test_coverage_target": 90,
            },
            output,
        )

        content = result.read_text()
        assert "GitFlow" in content
        assert "90" in content


class TestDesignError:
    """Tests for DesignError exception."""

    def test_error_message(self) -> None:
        """DesignError should store message."""
        error = DesignError("Template not found")
        assert str(error) == "Template not found"
