# Knowledge Update Skill

Version: 1
Status: active

## Purpose

Determine which accepted research findings should be proposed
for durable knowledge storage while preserving provenance,
verification state, and update history.

## Inputs

Required:

- accepted ResearchReport or accepted Claim objects.

Optional:

- existing LedgerEntry objects;
- existing knowledge entries;
- mission context;
- retention policy.

## Outputs

One or more proposed LedgerEntry objects or an explicit
no-update decision.

## Procedure

### 1. Select Durable Candidates

Prefer information that is:

- likely to remain useful;
- reusable across future missions;
- specific enough to retrieve meaningfully;
- supported by traceable evidence.

Avoid storing transient conversational filler.

### 2. Check Existing Knowledge

Determine whether the candidate:

- is new;
- duplicates existing knowledge;
- refines an existing entry;
- contradicts an existing entry;
- supersedes an existing entry.

### 3. Preserve Provenance

A durable entry must retain enough information
to trace the underlying claim and evidence.

Do not convert remembered output into source truth.

### 4. Preserve Verification State

Knowledge storage does not upgrade verification state.

A partially verified or disputed claim remains
partially verified or disputed after storage.

### 5. Handle Updates

When newer accepted evidence materially replaces
an older entry:

- create or update the replacement entry;
- preserve the old entry;
- mark the relationship using supersedes;
- mark obsolete knowledge as superseded
  rather than silently deleting history.

### 6. Handle Contradictions

When new accepted evidence conflicts with existing knowledge:

- preserve the conflicting entry;
- mark disputed state where appropriate;
- avoid silently overwriting uncertain knowledge.

### 7. Apply Retention Decision

Do not store a candidate when it is:

- trivial;
- purely transient;
- unsupported;
- redundant without added value;
- sensitive and not explicitly authorized for retention.

### 8. Produce Proposed Update

Return either:

- proposed LedgerEntry objects; or
- an explicit no-update result with reason.

## Retry Conditions

Review is required when:

- source provenance is missing;
- verification state is ambiguous;
- an existing entry may be superseded;
- contradictory durable knowledge exists;
- retention authorization is unclear.

## Stop Conditions

Stop when every candidate has a clear outcome:

- add;
- update/supersede;
- preserve disputed;
- no-update.

## Prohibited Behavior

Do not:

- store secrets or credentials;
- silently overwrite contradictory history;
- treat model output as original evidence;
- upgrade verification state during storage;
- persist sensitive information without authorization;
- delete provenance to reduce storage size.

## Required Policies

- research-policy.md
- evidence-policy.md
- security-policy.md
