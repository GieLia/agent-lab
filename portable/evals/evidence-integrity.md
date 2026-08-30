# Evidence Integrity Eval

Version: 1
Status: active

## Purpose

Evaluate whether research artifacts preserve correct,
traceable Claim -> Evidence -> Source relationships.

## Subject

Applicable to:

- WorkerResult;
- ResearchReport;
- KnowledgeBundle.

## Inputs

- claims;
- evidence;
- sources;
- applicable evidence policy.

## Pass Criteria

Pass when:

- every evidence.claim_id resolves to an existing Claim;
- every evidence.source_id resolves to an existing Source;
- identifiers are unique within the mission namespace;
- important factual claims represented as supported have
  corresponding evidence;
- contradictory evidence is preserved;
- evidence relationships are not fabricated.

## Fail Conditions

Fail when any material case includes:

- orphan evidence;
- orphan source references;
- identifier collision;
- fabricated evidence;
- unsupported verification upgrade;
- silent removal of material contradiction.

## Measurements

Deterministic measurements should be preferred for:

- identifier uniqueness;
- reference resolution;
- orphan detection;
- structural validity.

Model judgment may be used for:

- material evidence sufficiency;
- contradiction significance;
- source relevance.

## Prohibited Shortcuts

Do not:

- infer evidence from writing confidence;
- count duplicate sources as independent corroboration;
- treat output length as evidence quality;
- invent numeric confidence without calibration.
