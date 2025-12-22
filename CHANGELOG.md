# CHANGELOG

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.

## [Unreleased]

### Added
- Version consistency validation CI check to prevent version drift
- Comprehensive release process documentation in RELEASING.md
- Python-semantic-release integration for automated versioning
- CHANGELOG.md for tracking project changes

### Changed
- Updated CI workflow to include version validation step

## [0.1.0] - 2024-12-22

### Added
- Core workspace management functionality
- Git worktree integration for isolated workspaces
- CLI commands: `workspace create`, `workspace list`, `workspace remove`
- Agent launching capabilities
- Template system for project scaffolding
- Documentation generation from design templates
- Python virtual environment support per workspace
- Metadata tracking for workspace configuration

### Infrastructure
- Structured logging with structlog
- Type-safe configuration with Pydantic
- Comprehensive test suite with pytest
- Code quality tooling (ruff, mypy)
- CI/CD pipeline with GitHub Actions

[Unreleased]: https://github.com/ckrough/agentspaces/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ckrough/agentspaces/releases/tag/v0.1.0
