# Portable Evals

Provider-neutral quality and behavioral evaluation contracts.

Current contracts:

- evidence-integrity.md
- role-boundary.md
- acceptance-integrity.md
- synthesis-traceability.md
- knowledge-durability.md
- revision-quality.md

These contracts define WHAT should be evaluated.

Provider-specific prompts, model routing, repetition counts,
position balancing implementations, and runtime telemetry
belong to the evaluation harness rather than these contracts.

Evaluation principle:

deterministic checks where possible
> structured semantic evaluation where necessary
> unstructured model opinion

A model evaluator must not override deterministic contract
violations.
