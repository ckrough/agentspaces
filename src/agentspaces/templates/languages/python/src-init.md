---
name: src-init
description: Package __init__.py with version.
category: python
variables:
  required:
    - project_name
  optional: []
---
"""{{ project_name }} package."""

__version__ = "0.1.0"
