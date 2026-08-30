# Acceptance Integrity Eval

Version: 1
Status: active

## Purpose

Evaluate whether AcceptanceGate decisions are internally
consistent and correctly bound synthesis input.

## Subject

Applicable to:

- AcceptanceGate;
- Research Lead gate decisions;
- Synthesizer input selection.

## Inputs

- AcceptanceGate;
- candidate WorkerResult objects;
- critic findings when available;
- verification results when available;
- applicable policies.

## Pass Criteria

Pass when:

- accepted and rejected identifier sets are disjoint;
- accepted decision contains accepted material
  and no rejected material;
- partial decision contains both accepted
  and rejected material;
- rejected decision contains rejected material
  and no accepted material;
- rationale explains material gate decisions;
- verification status is not upgraded by acceptance;
- Synthesizer consumes only gate-authorized material.

## Fail Conditions

Fail when:

- gate identifier sets overlap;
- decision contradicts identifier sets;
- rejected material enters synthesis;
- acceptance silently upgrades verification state;
- policy-violating material is accepted;
- gate is bypassed.

## Measurements

Deterministic checks should validate:

- set disjointness;
- decision/set consistency;
- identifier resolution;
- gate presence before synthesis.

Evaluator judgment may assess whether rationale
materially corresponds to supplied findings.

## Prohibited Shortcuts

Acceptance means eligible for synthesis.

Acceptance must not be interpreted as equivalent
to factual verification.
