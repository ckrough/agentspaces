"""Project skeleton structure definitions.

Defines the mapping between template names and their output paths for
project initialization. Separates base skeleton (language-agnostic) from
language-specific packs.
"""

from __future__ import annotations

__all__ = [
    "PYTHON_STRUCTURE",
    "SKELETON_STRUCTURE",
]


# Base project skeleton structure (language-agnostic)
# Maps template name -> output path relative to project root
SKELETON_STRUCTURE: dict[str, str] = {
    # Root files
    "readme": "README.md",
    "claude-md": "CLAUDE.md",
    # .claude directory
    "agents-readme": ".claude/agents/README.md",
    "commands-readme": ".claude/commands/README.md",
    # Design docs
    "architecture": "docs/design/architecture.md",
    "development-standards": "docs/design/development-standards.md",
    # ADR
    "adr-template": "docs/adr/000-template.md",
    "adr-example": "docs/adr/001-example.md",
}


# Python language pack structure
# Uses chezmoi-style naming: dot_ prefix for dotfiles
# Maps template name -> output path relative to project root
PYTHON_STRUCTURE: dict[str, str] = {
    "pyproject-toml": "pyproject.toml",
    "dot_gitignore-python": ".gitignore",
    "dot_python-version": ".python-version",
    "dot_pre-commit-config": ".pre-commit-config.yaml",
    "dot_github-ci": ".github/workflows/ci.yml",
    "src-init": "src/{package_name}/__init__.py",
    "tests-conftest": "tests/conftest.py",
}
