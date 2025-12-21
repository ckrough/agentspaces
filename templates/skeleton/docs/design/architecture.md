---
name: architecture
description: Read when onboarding or making architectural decisions. Covers style, tech stack, structure.
category: reference
when_to_use:
  - Starting work on a new feature
  - Onboarding to the codebase
  - Making architectural decisions
  - Understanding how components fit together
dependencies:
  - development-standards.md
  - decisions/
variables:
  required:
    - project_name
    - project_description
  optional:
    - system_overview_diagram
    - architecture_style
    - architecture_rationale
    - tech_stack_backend
    - tech_stack_frontend
    - tech_stack_infrastructure
    - project_structure
    - design_patterns
    - python_version
---

# {{ project_name }} Architecture

{{ project_description }}

## System Overview

{% if system_overview_diagram %}
```
{{ system_overview_diagram }}
```
{% else %}
```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                               │
│  [Input] → [Processing] → [Storage] → [Output]                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       APPLICATION                               │
│  [API Layer] ←→ [Business Logic] ←→ [Data Layer]               │
└─────────────────────────────────────────────────────────────────┘
```

<!-- Replace with your system's actual data flow diagram -->
{% endif %}

## Architecture Style: {{ architecture_style | default("Layered Architecture") }}

{% if architecture_rationale %}
**Why this approach:**
{% for reason in architecture_rationale %}
- {{ reason }}
{% endfor %}
{% else %}
**Why this approach:**
- Clear separation of concerns
- Dependencies flow in one direction
- Easy to test and maintain
- Supports incremental development
{% endif %}

## Tech Stack

### Backend (Python {{ python_version | default("3.12+") }})

{% if tech_stack_backend %}
| Component | Choice | Rationale |
|-----------|--------|-----------|
{% for item in tech_stack_backend %}
| {{ item.component }} | {{ item.choice }} | {{ item.rationale }} |
{% endfor %}
{% else %}
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | FastAPI | Async, modern, excellent docs |
| Validation | Pydantic | Type-safe data validation |
| Logging | structlog | Structured JSON logging |
| Config | pydantic-settings | Environment-based configuration |

<!-- Add your tech stack choices -->
{% endif %}

{% if tech_stack_frontend %}
### Frontend

| Component | Choice | Rationale |
|-----------|--------|-----------|
{% for item in tech_stack_frontend %}
| {{ item.component }} | {{ item.choice }} | {{ item.rationale }} |
{% endfor %}
{% endif %}

{% if tech_stack_infrastructure %}
### Infrastructure

| Component | Choice | Rationale |
|-----------|--------|-----------|
{% for item in tech_stack_infrastructure %}
| {{ item.component }} | {{ item.choice }} | {{ item.rationale }} |
{% endfor %}
{% endif %}

## Project Structure

{% if project_structure %}
```
{{ project_structure }}
```
{% else %}
```
{{ project_name }}/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration settings
│   │
│   ├── modules/                # Business modules
│   │   └── <module>/
│   │       ├── __init__.py
│   │       ├── routes.py       # API endpoints
│   │       ├── services.py     # Business logic
│   │       ├── schemas.py      # Request/response models
│   │       └── models.py       # Domain models
│   │
│   └── infrastructure/         # Shared technical concerns
│       ├── database.py
│       ├── logging.py
│       └── ...
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/
├── pyproject.toml
└── README.md
```

<!-- Customize to match your project structure -->
{% endif %}

## Key Design Patterns

{% if design_patterns %}
{% for pattern in design_patterns %}
### {{ pattern.name }}

{{ pattern.description }}

{% if pattern.example %}
```python
{{ pattern.example }}
```
{% endif %}

{% if pattern.see_also %}
See [{{ pattern.see_also }}]({{ pattern.see_also_link }}).
{% endif %}

{% endfor %}
{% else %}
### Dependency Injection

Services receive dependencies through constructors for testability:

```python
class MyService:
    def __init__(self, db: Database | None = None) -> None:
        self._db = db or Database()
```

### Module Structure

Each module in `src/modules/` is self-contained:

```
module_name/
├── __init__.py
├── routes.py       # API endpoints
├── services.py     # Business logic
├── schemas.py      # Pydantic models
└── models.py       # Domain models
```

### Configuration

Use `pydantic-settings` for all configuration. Environment variables override defaults.
{% endif %}

## Related Documents

- [TODO](../../TODO.md) - Active tasks
- [Development Standards](development-standards.md)
- [Architecture Decision Records](../adr/)
