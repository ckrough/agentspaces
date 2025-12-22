---
name: readme
description: Read for project overview, setup instructions, and usage. Entry point for new contributors.
category: root
when_to_use:
  - Starting a new project
variables:
  required:
    - project_name
    - project_description
  optional:
    - features
    - prerequisites
    - installation_steps
    - usage_examples
    - configuration
    - architecture_summary
    - dev_commands
---

# {{ project_name }}

{{ project_description }}

## Features

{% if features %}
{% for feature in features %}
- {{ feature }}
{% endfor %}
{% else %}
- Feature 1
- Feature 2
- Feature 3
{% endif %}

## Quick Start

### Prerequisites

{% if prerequisites %}
{% for prereq in prerequisites %}
- {{ prereq }}
{% endfor %}
{% else %}
- Python 3.13
- [uv](https://docs.astral.sh/uv/) (Python package manager)
{% endif %}

### Installation

{% if installation_steps %}
{% for step in installation_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% else %}
```bash
# Clone the repository
git clone https://github.com/username/{{ project_name | lower | replace(" ", "-") }}.git
cd {{ project_name | lower | replace(" ", "-") }}

# Install dependencies
uv sync

# Run the application
uv run {{ project_name | lower | replace(" ", "_") }}
```
{% endif %}

## Usage

{% if usage_examples %}
{{ usage_examples }}
{% else %}
```bash
# Example command
uv run {{ project_name | lower | replace(" ", "_") }} --help
```
{% endif %}

## Configuration

{% if configuration %}
{{ configuration }}
{% else %}
Configuration is handled via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
{% endif %}

## Development

{% if dev_commands %}
{% for cmd in dev_commands %}
- {{ cmd }}
{% endfor %}
{% else %}
```bash
uv run pytest              # Run tests
uv run ruff check src/     # Lint
uv run ruff format src/    # Format
uv run mypy src/           # Type check
```
{% endif %}

## Architecture

{% if architecture_summary %}
{{ architecture_summary }}
{% else %}
See [docs/design/architecture.md](docs/design/architecture.md) for detailed system design.
{% endif %}

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

## License

MIT
