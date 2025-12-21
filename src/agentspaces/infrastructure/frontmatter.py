"""YAML frontmatter parsing for template files.

Parses YAML frontmatter from Markdown files, extracting metadata
from the content between --- delimiters at the start of a file.
"""

from __future__ import annotations

from typing import Any

import yaml

__all__ = [
    "FrontmatterError",
    "parse_frontmatter",
]


class FrontmatterError(Exception):
    """Raised when frontmatter parsing fails."""


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from Markdown content.

    Extracts YAML metadata from the content between --- delimiters
    at the start of a file.

    Args:
        content: Markdown content with optional frontmatter.

    Returns:
        Tuple of (frontmatter_dict, body_content).
        If no frontmatter exists, returns ({}, content).

    Raises:
        FrontmatterError: If frontmatter is malformed or YAML is invalid.

    Example:
        >>> content = '''---
        ... name: example
        ... description: An example
        ... ---
        ... # Body content
        ... '''
        >>> meta, body = parse_frontmatter(content)
        >>> meta['name']
        'example'
        >>> body.strip()
        '# Body content'
    """
    # Check for frontmatter delimiter
    if not content.startswith("---"):
        return {}, content

    # Find the closing delimiter
    # Start searching after the first "---" (position 3)
    end_pos = content.find("---", 3)
    if end_pos == -1:
        raise FrontmatterError(
            "Frontmatter started but closing '---' delimiter not found"
        )

    # Extract the YAML content (between the delimiters)
    yaml_content = content[3:end_pos].strip()

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise FrontmatterError(f"Invalid YAML in frontmatter: {e}") from e

    # Handle empty frontmatter (just ---)
    if frontmatter is None:
        frontmatter = {}

    # Ensure frontmatter is a dict
    if not isinstance(frontmatter, dict):
        raise FrontmatterError(
            f"Frontmatter must be a YAML mapping, got {type(frontmatter).__name__}"
        )

    # Extract the body (everything after the closing delimiter)
    # Skip the "---" and any immediately following newline
    body_start = end_pos + 3
    body = content[body_start:].lstrip("\n")

    return frontmatter, body
