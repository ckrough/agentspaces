# TODO

## Active

- [ ] Add `--verbose` and `--quiet` global flags
- [ ] Add examples to help text
- [ ] Add sorting/filtering to `docs list` command
- [ ] Add `--interactive` mode for `docs create`

## Backlog

- [ ] Add "Next steps:" section to create command output
- [ ] Add "Did you mean?" suggestions for workspace not found
- [ ] Support custom template directories
- [ ] Workspace templates (pre-configured for agent types)
- [ ] Multi-agent orchestration
- [ ] Integration with other AI agents (Cursor, Aider)

## Blocked

# DONE

- [x] Skeleton feature - design document templates
- [x] Agent launching with Claude Code support
- [x] Workspace state management commands
- [x] CLI polish and UX improvements
- [x] Workspace metadata persistence and skill generation
- [x] GitHub Actions CI/CD workflow
- [x] Python environment management with uv
- [x] Foundation - Project structure, CLI skeleton
- [x] Use `@dataclass(frozen=True)` for immutable DTOs
- [x] Add `@functools.cache` to `is_uv_available()`
- [x] Add `__all__` declarations to modules
- [x] Add error path tests for environment setup
- [x] Add tests for malformed `.python-version` files
