---
name: workspace-context
description: Context and purpose for this workspace. Use when starting work, resuming after a break, or needing to understand what this workspace is for.
---

# Workspace: {{ name }}

## Purpose

{{ purpose }}

## Details

| Field | Value |
|-------|-------|
| Project | `{{ project }}` |
| Branch | `{{ branch }}` |
| Created From | `{{ base_branch }}` |
| Created | {{ created_at }} |
| Status | {{ status }} |
{% if python_version %}| Python | {{ python_version }} |{% endif %}
{% if has_venv %}| Virtual Env | .venv |{% endif %}

## When to Use This Skill

- Starting a new session in this workspace
- Resuming work after time away
- Understanding what this workspace is for
- Sharing context with other agents or developers
