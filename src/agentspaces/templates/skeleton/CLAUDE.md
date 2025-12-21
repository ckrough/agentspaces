---
name: claude-md
description: Read at session start for project context, tech stack, build commands, and conventions.
category: root
when_to_use:
  - Starting a new project
  - Documenting non-obvious patterns
variables:
  required:
    - project_name
  optional:
    - tech_stack
    - dependencies
    - structure_notes
    - commands
    - conventions
    - architecture
---

# {{ project_name }}

## Tech Stack
{{ tech_stack | default("Python 3.12+, pytest, ruff, mypy") }}
{% if dependencies %}
Dependencies: {{ dependencies }}
{% endif %}

## Project Structure
{% if structure_notes %}
{{ structure_notes }}
{% else %}
- `src/{{ project_name | lower | replace(" ", "_") }}/` - Main package
- `tests/` - Test suite
- `docs/` - Documentation
{% endif %}

## Build/Test Commands
{% if commands %}
{% for cmd in commands %}
- {{ cmd }}
{% endfor %}
{% else %}
- `uv run pytest` - Run tests
- `uv run ruff check src/` - Lint
{% endif %}

## Coding Conventions
{% if conventions %}
{% for convention in conventions %}
- {{ convention }}
{% endfor %}
{% else %}
<!-- Add non-obvious conventions here. Don't repeat what's in ruff/mypy config. -->
{% endif %}

## Architecture Principles
{% if architecture %}
{{ architecture }}
{% else %}
<!-- Add project-specific patterns that aren't obvious from code structure. -->
{% endif %}

## Subdirectory Context

Add scoped CLAUDE.md files for area-specific patterns:
- `src/api/CLAUDE.md` - API conventions, auth patterns
- `tests/CLAUDE.md` - Testing utilities, fixtures
- `src/db/CLAUDE.md` - Migration patterns, query conventions
