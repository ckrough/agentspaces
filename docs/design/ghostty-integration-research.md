---
name: ghostty-integration-research
description: Research findings on Ghostty terminal emulator socket/IPC API capabilities and integration possibilities with agentspaces.
category: research
date: 2026-01-10
status: Complete
---

# Ghostty Terminal Integration Research

Research into Ghostty terminal emulator's socket/IPC API capabilities for potential integration with agentspaces workspace management.

## Executive Summary

**Key Finding**: Ghostty does not currently provide a stable, public socket-based API (as of January 2026). The project is actively exploring platform-specific IPC mechanisms rather than a unified cross-platform socket API.

**Recommendation**: Monitor Ghostty development but do not invest in deep integration at this time. Current basic integration (tab creation via environment detection) is sufficient until stable APIs emerge.

**Review Triggers**:
- Ghostty announces stable socket API or cross-platform scripting interface
- Platform-specific APIs (D-Bus on Linux, AppleScript on macOS) reach production quality
- MCP server prototype becomes production-ready
- Community demand for deeper agentspaces-Ghostty integration increases

## Research Context

### Goals

Investigate Ghostty's socket API to determine if it could enhance agentspaces workflows, specifically:
1. Tab/pane management automation
2. Command execution in specific workspace tabs
3. Environment variable and directory control
4. Session state queries
5. Event notifications/hooks
6. Integration patterns with CLI tools

### Current agentspaces-Ghostty Integration

Agentspaces already includes basic Ghostty support in `src/agentspaces/ui/terminal.py`:

**Capabilities**:
- Terminal detection via `TERM_PROGRAM` environment variable
- `navigate_to_workspace()` function creates new Ghostty tabs
- Executes workspace setup: `cd <path> && source .venv/bin/activate && claude`
- Graceful fallback for non-Ghostty terminals (prints manual commands)
- TUI application (`agentspaces tui`) for interactive workspace browsing

**Implementation Pattern**:
```python
def _navigate_ghostty(workspace: WorkspaceInfo) -> None:
    """Create a new Ghostty tab for the workspace."""
    subprocess.run([
        "ghostty",
        "+new-tab",
        "--working-directory", str(workspace.path),
        "--command", activation_command(workspace, shell="bash"),
    ])
```

This approach works without any socket/IPC API because it relies on Ghostty's CLI arguments.

## Ghostty API Status (January 2026)

### Official Position

Ghostty maintainers are exploring **platform-specific IPC** rather than a unified socket API:

**Platform-Specific Approaches** (preferred):
- **Linux**: D-Bus integration (partially implemented via `ghostty +new-window`)
- **macOS**: AppleScript and App Intents framework
- **Windows**: Unix domain sockets (available on modern Windows)

**Cross-Platform Alternatives** (under discussion):
- Unix sockets with simple text protocol (memcached/redis style)
- HTTP/JSON over Unix sockets
- Escape sequences (OSC/DCS protocols like Kitty's remote control)
- Varlink protocol

### Development Blockers

**Security Concerns**: Lead maintainer mitchellh highlighted that escape sequences present security risks:
> "escape sequences can be sent by lots of sources...allowing arbitrary changes to config is very scary."

This led to shelving escape sequence-based remote control pending better security design.

**Incremental Development**: Team prefers small, scoped PRs (like `focus_surface`, `list_surfaces`) over monolithic API implementations to maintain security and maintainability.

**No Timeline**: No public roadmap or timeline for stable API release.

### Prototype Implementations

**Unix socket with JSON-RPC** (hyperb1iss branch):
- MCP (Model Context Protocol) server support
- Socket-based communication
- Not production-ready

**AppleScript wrappers** (kkilchrist branch):
- macOS App Intents framework
- Platform-specific
- Proof-of-concept stage

Reference: [Ghostty GitHub Discussion #2353 - Scripting API](https://github.com/ghostty-org/ghostty/discussions/2353)

## libghostty: Not for IPC

### What libghostty Provides

`libghostty` is an embeddable terminal emulator library, **not** an IPC/scripting interface:

**Purpose**: Allow applications to embed terminal emulators
**First Component**: `libghostty-vt` - terminal sequence parsing and state management
**Target Users**: Terminal emulators, multiplexers (tmux/zellij), IDEs (VS Code/JetBrains), build log displays

**Capabilities**:
- Parse and validate terminal sequences (VT100, xterm, etc.)
- Maintain terminal state (cursor, styles, text wrapping)
- SIMD-optimized performance
- Unicode support
- Kitty Graphics Protocol and Tmux Control Mode compatibility
- C API for cross-language integration

**Current Status**: Alpha quality API, stable core logic, Zig API available for testing, C API in development

**Timeline**: Tagged release within ~6 months (as of late 2024)

**Key Limitation**: libghostty handles terminal *rendering*, not process *control*. It won't help agentspaces create tabs, execute commands, or manage sessions.

Reference: [Mitchell Hashimoto: libghostty is Coming](https://mitchellh.com/writing/libghostty-is-coming)

## User-Requested Features

From GitHub discussion #2353, Ghostty users are requesting scripting capabilities for:

1. **Terminal multiplexing**: Native splits/tabs management (replacing tmux workflows)
2. **Editor integration**: Support for vim-dispatch, smart-splits.nvim, and similar plugins
3. **Project layouts**: Application startup with preconfigured windows/tabs/panes
4. **Window switching**: Content-aware navigation and searching across terminals
5. **Environment control**: Setting working directories, window titles, copying environment variables

### Relevance to agentspaces

**High Value Use Cases**:
- **Project layouts**: Auto-create tabs for frontend/backend/tests when initializing workspace
- **Environment control**: Set workspace-specific environment variables in new tabs
- **Window switching**: Quick navigation to workspace tabs by name or content

**Lower Value Use Cases**:
- **Terminal multiplexing**: Agentspaces uses git worktrees, not splits/panes within one directory
- **Editor integration**: Out of scope for workspace orchestration tool

## Integration Architecture (If API Becomes Available)

### Proposed Abstraction Layer

If Ghostty (or another terminal multiplexer) provides a stable API, agentspaces should implement a pluggable terminal provider system:

```
agentspaces
  └── infrastructure/
      └── terminal/
          ├── provider.py          # Abstract TerminalProvider protocol
          ├── ghostty.py           # GhosttyProvider (socket/D-Bus/AppleScript)
          ├── tmux.py              # TmuxProvider (mature API)
          ├── zellij.py            # ZellijProvider (plugin system)
          └── fallback.py          # FallbackProvider (print commands)
```

**Key Design Principles**:
1. **Detect and adapt**: Auto-detect available terminal, fall back gracefully
2. **Configuration preference**: User can override detection in `~/.agentspaces/config.json`
3. **Per-workspace preference**: Workspace metadata can specify preferred terminal
4. **Minimal coupling**: Terminal layer depends only on workspace metadata, not service logic

### Potential API Operations

If a Ghostty socket API emerges, useful operations for agentspaces:

| Operation | Use Case | Current Workaround |
|-----------|----------|-------------------|
| `create_tab(title, cwd, command)` | Open workspace in new tab | CLI args to `ghostty +new-tab` |
| `list_tabs()` | Show all open workspaces | None (user navigates manually) |
| `focus_tab(identifier)` | Switch to workspace tab | None (user navigates manually) |
| `close_tab(identifier)` | Clean up closed workspace | None (user closes manually) |
| `set_env(tab, key, value)` | Inject workspace vars | Included in `--command` string |
| `get_state(tab)` | Query active workspaces | None |

### CLI Enhancement Examples

```bash
# Create workspace and open in new Ghostty tab
agentspaces workspace create feature-auth --attach --terminal=ghostty

# List workspaces with active terminal status
agentspaces workspace list --show-terminals

# Navigate to workspace (creates or focuses tab)
agentspaces workspace goto eager-turing
```

### Metadata Extensions

Extend `WorkspaceInfo` and `workspace.json`:

```python
@dataclass(frozen=True)
class WorkspaceInfo:
    # ... existing fields ...
    terminal_preference: str | None = None      # "ghostty", "tmux", "zellij"
    terminal_session_id: str | None = None      # External session identifier
```

## Recommendations

### Short-term (Now)

**Do NOT implement Ghostty socket integration**:
1. No stable API exists
2. Platform-specific approaches don't help cross-platform tool
3. Prototype implementations are pre-alpha
4. Current CLI-based integration works well

**Maintain current implementation**:
- Continue using `ghostty +new-tab` with `--working-directory` and `--command`
- Keep terminal detection and fallback pattern
- TUI provides good UX for workspace browsing

### Medium-term (6-12 months)

**Monitor Ghostty development**:
- Watch for stable API announcements in Ghostty releases
- Track GitHub discussion #2353 for scripting API progress
- Review libghostty releases (though not directly relevant)

**Prepare for integration**:
- Design terminal provider abstraction (no implementation)
- Document desired operations in design doc
- Consider user feedback on terminal integration needs

### Long-term (Future)

**When Ghostty API stabilizes**:
1. Implement `GhosttyProvider` following established abstraction
2. Add platform-specific backends (D-Bus on Linux, AppleScript on macOS)
3. Extend workspace metadata for terminal preferences
4. Add CLI commands for terminal-aware operations

**Alternative Paths**:
- If Ghostty API doesn't emerge, consider tmux/zellij integration instead
- These multiplexers have mature, stable APIs and strong ecosystems
- May provide value sooner than waiting for Ghostty

## Conclusion

Ghostty is a promising terminal emulator but lacks the stable socket/IPC API needed for deep integration with agentspaces. The project is actively exploring platform-specific approaches (D-Bus, AppleScript) rather than unified socket APIs, with no clear timeline for production-ready scripting interfaces.

**Current agentspaces-Ghostty integration** (CLI-based tab creation) is sufficient and should be maintained without further investment until:
1. Ghostty provides stable, documented socket/IPC API
2. Platform-specific APIs reach production quality
3. User demand justifies the engineering effort

**Alternative consideration**: Tmux and Zellij offer mature multiplexer APIs today and may provide similar benefits with less risk and uncertainty.

## References

- [Ghostty GitHub Discussion #2353 - Scripting API](https://github.com/ghostty-org/ghostty/discussions/2353)
- [Mitchell Hashimoto: libghostty is Coming](https://mitchellh.com/writing/libghostty-is-coming)
- [Ghostty Official Repository](https://github.com/ghostty-org/ghostty)
- agentspaces codebase: `src/agentspaces/ui/terminal.py` (current integration)
- agentspaces codebase: `docs/design/architecture.md` (architectural patterns)

## Document History

- 2026-01-10: Initial research completed (Beads issue: agentspaces-4e2)
