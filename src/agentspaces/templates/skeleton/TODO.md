---
name: todo-md
description: Read when starting work or checking priorities. Active/Backlog/Blocked/DONE task list.
category: root
when_to_use:
  - Starting a new project
  - Tracking development tasks
variables:
  required: []
  optional:
    - active_tasks
    - backlog_tasks
---

# TODO

## Active
{% if active_tasks %}
{% for task in active_tasks %}
- [ ] {{ task }}
{% endfor %}
{% else %}
- [ ] Initial project setup
{% endif %}

## Backlog
{% if backlog_tasks %}
{% for task in backlog_tasks %}
- [ ] {{ task }}
{% endfor %}
{% endif %}

## Blocked

# DONE
