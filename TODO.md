# AgentSpaces Development TODO

Development backlog organized by priority and category. Items come from code reviews and feature planning.

## High Priority

### Python Best Practices
- [x] Use `@dataclass(frozen=True)` for immutable DTOs
  - `EnvironmentInfo` in `modules/workspace/environment.py`
  - `WorktreeCreateResult` in `modules/workspace/worktree.py`
  - `WorkspaceInfo` in `modules/workspace/service.py` (already frozen)
- [x] Add `@functools.cache` to `is_uv_available()` for performance
- [x] Add `__all__` declarations to define public API in modules

### Testing Gaps
- [x] Add error path tests for `setup_environment` when uv unavailable
- [x] Add tests for failed dependency sync scenarios
- [x] Add tests for malformed `.python-version` files

## Medium Priority

### CLI Enhancements
- [ ] Add `--verbose` and `--quiet` global flags to `app.py`
- [ ] Add examples to help text using `\b` blocks in docstrings
- [ ] Add "Next steps:" section to create command output
- [ ] Add sorting/filtering options to `list` command (`--sort`, `--all`)
- [ ] Add "Did you mean?" suggestions for workspace not found errors

### Environment Management
- [ ] Add `deps_synced` field to `EnvironmentInfo` to track sync success
- [ ] Add venv verification after creation (check Python executable exists)
- [ ] Make uv timeout configurable via environment variable
- [ ] Add public `get_workspace_path()` method to service

## Low Priority

### Code Quality
- [ ] Use pattern matching for version parsing in `_get_venv_python_version()`
- [ ] Consider using walrus operator for cleaner code patterns

### UX Polish
- [ ] Consider top-level command aliases (`as create`, `as ls`)
- [ ] Document shell completion installation

---

## Completed Increments

1. ✅ **Increment 1**: Foundation - Project structure, CLI skeleton
2. ✅ **Increment 2**: Python environment management with uv
3. ✅ **Increment 3**: GitHub Actions CI/CD workflow
4. ✅ **Increment 4**: Workspace metadata persistence and skill generation
5. ✅ **Increment 5**: Agent launching with Claude Code support
6. ✅ **Increment 6**: CLI polish and UX improvements
7. ✅ **Increment 7**: Workspace state management commands

---

## Future Features (Ideas)

- [ ] Workspace templates (pre-configured for specific agent types)
- [ ] Multi-agent orchestration (run multiple agents in parallel)
- [ ] Workspace snapshots/restore
- [ ] Integration with other AI coding agents (Cursor, Aider, etc.)
- [ ] Web UI for workspace management
- [ ] Workspace sharing/collaboration features
