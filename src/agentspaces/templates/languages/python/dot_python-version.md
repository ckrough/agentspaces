---
name: dot_python-version
description: Python version specification for pyenv/asdf.
category: python
variables:
  required: []
  optional:
    - python_version
---
{{ python_version | default('3.13') }}
