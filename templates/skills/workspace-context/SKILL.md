---
name: workspace-context
description: Context and purpose for this workspace. Use when starting work, resuming after a break, or needing to understand what this workspace is for.
---

# Workspace: {{ workspace_name }}

## Purpose

{{ purpose | default("No purpose specified. Use `as workspace purpose` to set one.", true) }}

## Details

| Field | Value |
|-------|-------|
| Branch | `{{ branch }}` |
| Created From | `{{ base_branch }}` |
| Created | {{ created_at }} |
| Status | {{ status }} |

## Recent Activity

{% if activity_log %}
{% for entry in activity_log %}
- {{ entry.timestamp }}: {{ entry.message }}
{% endfor %}
{% else %}
No activity recorded yet.
{% endif %}

## Related Workspaces

{% if related_workspaces %}
{% for ws in related_workspaces %}
- **{{ ws.name }}** ({{ ws.relationship }}): {{ ws.purpose | default("No purpose") }}
{% endfor %}
{% else %}
No related workspaces.
{% endif %}

## When to Use This Skill

- Starting a new session in this workspace
- Resuming work after time away
- Understanding what this workspace is for
- Sharing context with other agents or developers
