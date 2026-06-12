# Architecture Decision Records (ADR)

## Purpose

Document all major architectural decisions for AIMirror.

Each ADR answers:
- **Why** was this decision made?
- **What** alternatives were considered?
- **Why** was this design chosen?
- **What** are the trade-offs?
- **How** can it evolve?

---

## Benefits

1. **Engineering** - Future changes remain disciplined
2. **Research** - Easier to justify choices in papers
3. **Product** - New contributors understand quickly

---

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001_architecture.md) | Core Architecture | ✅ Accepted | 2026-06-12 |
| [002](002_memory_system.md) | Multi-Memory System | ✅ Accepted | 2026-06-12 |
| [003](003_behavior_objects.md) | Behavior Objects as Canonical Representation | ✅ Accepted | 2026-06-12 |
| [004](004_identity_model.md) | Identity vs Self Model Separation | ✅ Accepted | 2026-06-12 |
| [005](005_character_core.md) | Character Core Architecture | ✅ Accepted | 2026-06-12 |
| [006](006_reasoning_layer.md) | Evidence-Based Reasoning | ✅ Accepted | 2026-06-12 |
| [007](007_cognitive_planning.md) | Cognitive Planning Layer | ✅ Accepted | 2026-06-12 |

---

## Template

```markdown
# ADR-XXX: [Title]

**Status**: [Proposed | Accepted | Deprecated | Superseded]  
**Date**: YYYY-MM-DD  
**Deciders**: [Names]

## Context

What is the issue we're addressing?

## Decision

What decision did we make?

## Alternatives Considered

1. Alternative 1
   - Pros: ...
   - Cons: ...

2. Alternative 2
   - Pros: ...
   - Cons: ...

## Rationale

Why did we choose this?

## Consequences

### Positive
- ...

### Negative
- ...

### Neutral
- ...

## Trade-offs

What are we giving up?

## Evolution Path

How can this evolve in the future?

## References

- Related ADRs
- External resources
```

---

**Last Updated**: June 12, 2026, 1:05 AM IST
