# Knowledge Durability Eval

Version: 1
Status: active

## Purpose

Evaluate whether durable knowledge remains traceable,
historically consistent, and usable after the originating
research run is unavailable.

## Subject

Applicable to:

- KnowledgeBundle;
- LedgerEntry lifecycle operations.

## Inputs

- KnowledgeBundle;
- LedgerEntry objects;
- Evidence;
- Source objects;
- prior ledger entries when evaluating updates.

## Pass Criteria

Pass when:

- every persisted evidence_id resolves inside the durable
  provenance boundary;
- every persisted Evidence resolves to a Source;
- durable entries preserve Claim verification state;
- supersession preserves history;
- supersedes and superseded_by relationships are coherent
  when both are recorded;
- retraction remains traceable and authorized;
- sensitive or prohibited material is not persisted.

## Fail Conditions

Fail when:

- durable evidence references become orphaned;
- provenance depends only on a discarded runtime artifact;
- old knowledge is silently overwritten;
- retracted knowledge remains treated as active;
- verification status is upgraded during persistence;
- secrets or unauthorized sensitive material are stored.

## Measurements

Prefer deterministic checks for:

- reference integrity;
- lifecycle state;
- supersession linkage;
- retraction metadata.

Evaluator judgment may assess whether a candidate
is materially appropriate for durable retention.

## Prohibited Shortcuts

Do not treat model memory, summaries, or generated prose
as replacement source provenance.
