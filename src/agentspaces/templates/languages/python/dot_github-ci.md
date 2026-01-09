---
name: dot_github-ci
description: GitHub Actions CI workflow for Python projects.
category: python
variables:
  required:
    - project_name
  optional:
    - python_version
---
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install {{ python_version | default('3.13') }}

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run linter
        run: uv run ruff check src/ tests/

      - name: Run formatter check
        run: uv run ruff format --check src/ tests/

      - name: Run type checker
        run: uv run mypy src/

      - name: Run tests
        run: uv run pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false
