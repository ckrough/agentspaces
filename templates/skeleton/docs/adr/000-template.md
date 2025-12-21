---
name: adr-template
description: Read when documenting an architectural decision. Minimal Context/Decision/Consequences format.
category: decision
when_to_use:
  - Recording significant technical decisions
  - Decisions future developers will ask "why?"
variables:
  required:
    - adr_number
    - adr_title
  optional:
    - adr_date
    - adr_status
---

# {{ adr_number }}. {{ adr_title }}

Date: {{ adr_date | default("YYYY-MM-DD") }}
Status: {{ adr_status | default("Proposed") }}

## Context

## Decision

## Consequences

**Positive**:

**Negative**:

**Migration**:
