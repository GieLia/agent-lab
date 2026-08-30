# Synthesis Traceability Eval

Version: 1
Status: active

## Purpose

Evaluate whether the final ResearchReport remains
traceable to accepted research material and evidence.

## Subject

Applicable to:

- Synthesizer output;
- ResearchReport.

## Inputs

- ResearchReport;
- AcceptanceGate;
- accepted WorkerResult objects;
- Evidence;
- Source objects;
- verification results when available.

## Pass Criteria

Pass when:

- material factual conclusions originate from
  gate-authorized material;
- evidence relationships remain resolvable;
- verification states are preserved;
- material contradictions remain represented;
- remaining gaps are explicit;
- no unsupported factual certainty is introduced.

## Fail Conditions

Fail when synthesis:

- introduces material unsupported facts;
- loses evidence traceability;
- uses rejected material as accepted fact;
- suppresses material contradictions;
- upgrades verification without evidence;
- hides significant unresolved gaps.

## Measurements

Deterministic checks may validate:

- accepted identifier membership;
- evidence reference integrity;
- verification-state preservation where identifiers persist.

Evaluator judgment may assess:

- semantic claim equivalence;
- material omission;
- contradiction preservation;
- unsupported certainty.

## Prohibited Shortcuts

Do not reward:

- longer reports;
- more polished formatting;
- repetition;
- unsupported decisiveness.
