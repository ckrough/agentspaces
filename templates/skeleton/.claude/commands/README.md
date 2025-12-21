---
name: commands-readme
description: Read when creating custom slash commands with examples for /test, /review, /commit, /pr.
category: claude-config
when_to_use:
  - Setting up a new project skeleton
variables:
  required: []
  optional: []
---

# Custom Commands

Slash commands for common workflows. Filename → `/command`.

## Examples

**test.md** → `/test`
```markdown
Run `uv run pytest`. If failures:
1. Show failed test names
2. Analyze root cause
3. Suggest fix
```

**review.md** → `/review`
```markdown
Review staged changes (`git diff --cached`):
1. Check for bugs or logic errors
2. Verify error handling
3. Flag security concerns
4. Suggest improvements (if significant)
```

**commit.md** → `/commit`
```markdown
1. Run tests and linter
2. Review staged changes
3. Generate commit message following conventional commits
4. Wait for confirmation before committing
```

**pr.md** → `/pr`
```markdown
1. Ensure all changes committed
2. Push branch
3. Create PR with:
   - Summary of changes
   - Test plan
   - Link to related issues
```

## Arguments

Commands accept `$ARGUMENTS`:
```markdown
# find.md → /find <pattern>
Search codebase for: $ARGUMENTS
Show file paths and line numbers.
```

## Multi-Step Workflows

**new-feature.md** → `/project:new-feature user-profiles`
```markdown
Create feature branch and structure for: $ARGUMENTS

1. `git checkout -b feature/$ARGUMENTS`
2. Create files:
   - `src/features/$ARGUMENTS/`
   - `tests/features/test_$ARGUMENTS.py`
3. Add skeleton tests
4. Create draft PR
5. Add TODO.md entry with PR number
```

## Workflow Patterns

**Research → Plan → Execute**:
```
Step 1: "Research how we handle X, don't write code yet"
Step 2: "Create a plan in docs/planning/feature-x.md"
Step 3: "Implement the plan, test-driven"
```

This prevents agents from jumping straight to code before understanding context.
