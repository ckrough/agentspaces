"""Tests for the frontmatter parsing module."""

from __future__ import annotations

import pytest

from agentspaces.infrastructure.frontmatter import FrontmatterError, parse_frontmatter


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parses_valid_frontmatter(self) -> None:
        """Should parse YAML frontmatter correctly."""
        content = """---
name: test-template
description: A test template
category: reference
---

# Body Content

This is the body.
"""
        meta, body = parse_frontmatter(content)

        assert meta["name"] == "test-template"
        assert meta["description"] == "A test template"
        assert meta["category"] == "reference"
        assert "# Body Content" in body
        assert "This is the body." in body

    def test_returns_empty_dict_for_no_frontmatter(self) -> None:
        """Should return empty dict when no frontmatter present."""
        content = """# Just a Title

No frontmatter here.
"""
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert "# Just a Title" in body

    def test_handles_empty_frontmatter(self) -> None:
        """Should return empty dict for empty frontmatter block."""
        content = """---
---

# Body
"""
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert "# Body" in body

    def test_parses_lists_in_frontmatter(self) -> None:
        """Should correctly parse YAML lists."""
        content = """---
when_to_use:
  - Starting a new project
  - Onboarding contributors
variables:
  required:
    - project_name
    - project_description
---

Body content.
"""
        meta, _body = parse_frontmatter(content)

        assert meta["when_to_use"] == [
            "Starting a new project",
            "Onboarding contributors",
        ]
        assert meta["variables"]["required"] == ["project_name", "project_description"]

    def test_raises_error_for_unclosed_frontmatter(self) -> None:
        """Should raise error when closing delimiter is missing."""
        content = """---
name: incomplete
description: Missing closing delimiter

# Body Content
"""
        with pytest.raises(FrontmatterError, match="closing '---' delimiter not found"):
            parse_frontmatter(content)

    def test_raises_error_for_invalid_yaml(self) -> None:
        """Should raise error for malformed YAML."""
        content = """---
name: bad yaml
  indentation: wrong
---

Body
"""
        with pytest.raises(FrontmatterError, match="Invalid YAML"):
            parse_frontmatter(content)

    def test_raises_error_for_non_dict_frontmatter(self) -> None:
        """Should raise error when frontmatter is not a mapping."""
        content = """---
- item1
- item2
---

Body
"""
        with pytest.raises(FrontmatterError, match="must be a YAML mapping"):
            parse_frontmatter(content)

    def test_preserves_multiline_values(self) -> None:
        """Should preserve multiline string values."""
        content = """---
description: |
  This is a multiline
  description that spans
  multiple lines.
---

Body
"""
        meta, _body = parse_frontmatter(content)

        assert "multiline" in meta["description"]
        assert "multiple lines" in meta["description"]

    def test_handles_content_starting_with_dashes(self) -> None:
        """Should not confuse content starting with dashes as frontmatter."""
        content = """-- This is a SQL comment
SELECT * FROM users;
"""
        meta, body = parse_frontmatter(content)

        assert meta == {}
        assert "-- This is a SQL comment" in body

    def test_strips_leading_newline_from_body(self) -> None:
        """Should strip leading newline from body content."""
        content = """---
name: test
---

Body starts here.
"""
        _meta, body = parse_frontmatter(content)

        assert body.startswith("Body starts here.")
        assert not body.startswith("\n")


class TestFrontmatterError:
    """Tests for FrontmatterError exception."""

    def test_error_message(self) -> None:
        """FrontmatterError should store message."""
        error = FrontmatterError("Parse failed")
        assert str(error) == "Parse failed"
