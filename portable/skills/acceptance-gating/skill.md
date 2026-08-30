# Acceptance Gating Skill

Version: 1
Status: active

## Purpose

Determine which supplied research material is eligible
for synthesis and produce an explicit AcceptanceGate.

Acceptance means eligible for synthesis.

Acceptance does not mean every accepted claim is verified.

## Inputs

Required:

- research objective;
- ResearchPlan;
- one or more WorkerResult objects.

Optional:

- critic findings;
- verification results;
- mission retry state.

## Outputs

Primary output:

- AcceptanceGate

The gate identifies:

- accepted workers;
- accepted claims;
- rejected workers;
- rejected claims;
- overall decision;
- decision rationale;
- deciding actor.

## Procedure

### 1. Validate Candidate Material

Reject structurally invalid WorkerResult objects.

A successful worker result must not be empty.

### 2. Check Policy Compliance

Material is not eligible when its production
or contents materially violate an active policy.

Security-policy violations are blocking.

### 3. Check Evidence Traceability

A factual claim represented as evidence-supported
must have resolvable Claim, Evidence, and Source linkage.

Fabricated, orphaned, or materially untraceable
evidence is not eligible for synthesis.

### 4. Preserve Verification State

Acceptance must not upgrade verification status.

The following may still be eligible for synthesis
when represented honestly:

- unverified;
- partially_verified;
- contradicted;
- disputed.

Synthesis may need such material to explain uncertainty
or contradictions.

### 5. Apply Critic Findings

Critic findings inform the gate decision.

Critic output does not automatically accept
or reject material.

Material findings should be evaluated against
the supplied research and policies.

### 6. Apply Verification Results

Evidence Verifier results take precedence over
unsupported worker assertions about verification state.

A claim whose stated verification status materially
misrepresents the supplied verification result
must be rejected or corrected before acceptance.

### 7. Determine Per-Item Eligibility

Accept material that is:

- relevant to the requested scope;
- structurally valid;
- honestly represented;
- traceable where evidence is claimed;
- compliant with active policies.

Reject material that is materially:

- fabricated;
- malformed;
- outside required scope;
- evidence-orphaned;
- security-policy violating;
- misleading about verification state.

### 8. Determine Gate Decision

accepted:

- at least one worker or claim is accepted;
- no worker or claim is rejected.

partial:

- at least one worker or claim is accepted;
- at least one worker or claim is rejected.

rejected:

- no worker or claim is accepted;
- at least one worker or claim is rejected.

### 9. Record Rationale

The rationale must explain material reasons
for acceptance, partial acceptance, or rejection.

## Retry Conditions

Targeted revision may be requested when material
could become eligible by fixing:

- missing evidence linkage;
- invalid structure;
- incorrect verification state;
- incomplete but repairable scope;
- a critic-identified material defect.

Retry remains subject to ResearchPlan.retry_budget.

## Stop Conditions

Stop when every candidate worker or claim has
an explicit eligibility outcome and the gate decision
is internally consistent.

## Prohibited Behavior

Do not:

- independently browse for new evidence;
- silently repair factual content;
- upgrade verification status;
- accept fabricated or orphaned evidence;
- ignore security-policy violations;
- create an internally contradictory gate;
- bypass the mission retry budget.

## Required Policies

- research-policy.md
- evidence-policy.md
- security-policy.md

## Identifier Set Integrity

Accepted and rejected identifier sets must be disjoint.

The same worker_id must not appear in both:

- accepted_worker_ids;
- rejected_worker_ids.

The same claim_id must not appear in both:

- accepted_claim_ids;
- rejected_claim_ids.

A gate containing such an overlap is invalid regardless
of its decision field and must be rejected before synthesis.
