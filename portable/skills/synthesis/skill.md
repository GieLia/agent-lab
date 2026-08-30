# Synthesis Skill

Version: 1
Status: active

## Purpose

Transform supplied accepted research material into a coherent,
traceable ResearchReport without independently gathering
new evidence.

## Inputs

Required:

- research objective;
- accepted WorkerResult objects.

Optional:

- ResearchPlan;
- critic findings;
- verification results;
- existing accepted knowledge.

## Outputs

Primary output:

- ResearchReport

The report must preserve:

- material claims;
- source traceability;
- evidence relationships;
- contradictions;
- unresolved gaps.

## Procedure

### 1. Reconstruct Requested Scope

Use the research objective and ResearchPlan
to determine required report coverage.

### 2. Collect Accepted Material

Use only supplied material accepted by the workflow.

Do not independently browse for missing evidence.

### 3. Deduplicate Claims

Identify semantically duplicate or overlapping claims.

Merge representation where appropriate without losing
different evidence relationships.

### 4. Preserve Verification State

Do not upgrade:

- unverified;
- partially_verified;
- disputed;
- contradicted

claims merely to create a cleaner narrative.

### 5. Reconcile Evidence

Attach relevant evidence and sources to the resulting claims.

Preserve contradicting evidence.

### 6. Handle Contradictions

Represent unresolved disagreement explicitly.

Where evidence supports a resolution, explain the basis
without suppressing the losing evidence.

### 7. Identify Remaining Gaps

List material questions that remain unanswered
or insufficiently verified.

### 8. Produce Report

Create a concise but materially complete report.

Distinguish:

- evidence-backed findings;
- interpretation;
- uncertainty;
- recommendations.

### 9. Verify Traceability

Before completion, ensure important factual conclusions
can be traced back to supplied claims, evidence, and sources.

## Retry Conditions

Revision is required when:

- material supplied evidence was omitted;
- contradictions were lost;
- important claims became unsupported during synthesis;
- the requested scope is incomplete;
- verification states were incorrectly upgraded;
- the output violates ResearchReport structure.

## Stop Conditions

Stop when:

- requested scope is materially covered;
- important claims remain traceable;
- contradictions are represented;
- remaining gaps are explicit;
- no unsupported factual certainty was introduced.

## Prohibited Behavior

Do not:

- independently browse for evidence;
- fabricate facts or sources;
- introduce unsupported factual claims;
- suppress contradictions for readability;
- turn speculation into fact;
- modify external systems.

## Required Policies

- research-policy.md
- evidence-policy.md
- security-policy.md
