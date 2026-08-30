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

Primary durable output:

- KnowledgeBundle containing LedgerEntry, Source,
  and Evidence records required for durable provenance.

Alternatively:

- an explicit no-update decision with reason.

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
- preserve under_review;
- retract with authorization;
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

## Durable Persistence Contract

A LedgerEntry must not be persisted with evidence_ids
that cannot be resolved after the originating run is gone.

Durable knowledge updates therefore use KnowledgeBundle.

The bundle preserves:

- LedgerEntry objects;
- the Evidence records referenced by those entries;
- the Source records referenced by that evidence.

The durable storage implementation must reject a bundle
containing unresolved evidence or source references.

## Ledger Lifecycle

LedgerEntry.status is a record-lifecycle state:

active:
the durable record is currently usable.

superseded:
a newer durable entry replaces this entry while history
is preserved.

under_review:
the record remains preserved but must not be treated as
settled durable knowledge until review completes.

retracted:
the record is explicitly marked unusable because it was
created in error, its provenance became invalid, or another
authorized retraction condition applies.

Ledger lifecycle does not replace or upgrade
Claim.verification_status.

## Retraction Authorization

Retraction is not deletion.

A retracted entry remains traceable but must not be used
as active knowledge.

Retraction requires an explicit authorization record
containing:

- reason;
- authorized_by;
- authorization_basis;
- authorized_at.

Authorization must come from a human gate or an explicitly
defined runtime policy. A model must not unilaterally
retract durable knowledge.

## Supersession Traceability

When one durable entry replaces another:

- the newer entry may set supersedes to the older entry_id;
- the older entry may set superseded_by to the newer entry_id;
- the older entry remains preserved with status=superseded.

Implementations must not create contradictory
supersession chains silently.

Supersession is record lifecycle metadata and does not
change Claim.verification_status by itself.
