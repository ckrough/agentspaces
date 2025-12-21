---
name: agents-readme
description: Read when creating or modifying specialized subagents for repeated workflows.
category: claude-config
when_to_use:
  - Setting up a new project skeleton
variables:
  required: []
  optional: []
---

# Specialized Agents

Focused subagents for repeated workflows. Filename becomes the agent name.

## Format

```markdown
---
name: agent-name
description: Brief description. Use PROACTIVELY when [trigger].
tools: Read, Edit, Write, Bash
---

Concise instructions:
1. First step
2. Second step
3. Verify result
```

## Examples

**test-runner.md** - Run after code changes:
```markdown
---
name: test-runner
description: Run tests and fix failures. Use PROACTIVELY after code changes.
tools: Read, Edit, Write, Bash
---

Run `make test`. For failures:
1. Analyze stack trace
2. Read failing test
3. Identify root cause
4. Propose minimal fix
5. Verify fix works
```

**adr-writer.md** - Document decisions:
```markdown
---
name: adr-writer
description: Create ADRs from design discussions
tools: Read, Write
---

When asked to document a decision:
1. Find next ADR number in docs/adr/
2. Use template from docs/adr/README.md
3. Extract context from discussion
4. Document decision and consequences
```
