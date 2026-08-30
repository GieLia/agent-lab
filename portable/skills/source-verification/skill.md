# Source Verification Skill

Version: 1
Status: active

## Purpose

Independently evaluate selected claims against relevant
read-only sources and recommend an evidence state.

## Inputs

Required:

- one or more Claim objects selected for verification.

Optional:

- existing Evidence objects;
- existing Source objects;
- known contradiction details;
- verification priority;
- recency requirements.

## Outputs

For each selected claim:

- Source objects used for verification;
- supporting Evidence;
- contradicting Evidence;
- recommended verification state;
- unresolved gaps;
- verification notes.

## Procedure

### 1. Identify Exact Claim

Treat the supplied Claim as the verification target.

If the claim contains multiple independently testable assertions,
split the verification task conceptually before evaluating evidence.

### 2. Inspect Existing Evidence

Review supplied evidence without assuming it is correct.

Identify:

- source independence;
- source authority;
- evidence freshness;
- contradiction signals.

### 3. Seek Independent Verification

Use explicitly allowed read-only source tools.

Prefer evidence independent from the original source
when practical.

### 4. Compare Source And Claim

Determine whether each source:

- supports;
- contradicts;
- provides context;
- remains unclear.

Do not convert partial support into full verification.

### 5. Assess Source Independence

Detect cases where multiple sources derive from
the same underlying publication, press release,
dataset, or report.

Do not count those as independent corroboration.

### 6. Assess Recency

Determine whether the source is sufficiently current
for the type of claim.

Time-sensitive claims require appropriately current evidence.

### 7. Resolve Or Preserve Contradiction

If credible evidence conflicts:

- preserve all material sides;
- compare authority and directness;
- identify what remains unresolved.

Use disputed when the conflict cannot be resolved responsibly.

### 8. Recommend Verification State

Allowed states:

- unverified;
- partially_verified;
- verified;
- contradicted;
- disputed.

The recommendation must follow the evidence,
not the desired conclusion.

## Retry Conditions

Additional verification is appropriate when:

- evidence is indirect;
- sources are not independent;
- a high-importance claim relies on weak evidence;
- material contradiction exists;
- evidence is stale;
- the source meaning is ambiguous.

## Stop Conditions

Stop when:

- available evidence supports a defensible verification state; or
- further reasonable verification cannot resolve the uncertainty
  and the unresolved status is explicitly documented.

## Prohibited Behavior

Do not:

- mutate external systems;
- alter unrelated claims;
- fabricate corroboration;
- hide contradictory evidence;
- assign certainty from source count alone;
- invent numeric confidence scores.

## Required Policies

- research-policy.md
- evidence-policy.md
- security-policy.md
