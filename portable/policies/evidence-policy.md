# Evidence Policy

Version: 1
Status: active

## Purpose

Define provider-neutral rules for linking claims to sources
and determining evidence state.

## Evidence Model

The core relationship is:

Claim <- Evidence -> Source

A Source identifies where information came from.

A Claim represents a specific assertion.

Evidence represents how a particular source relates
to a particular claim.

## Evidence Relationships

Allowed relationships are:

supports
contradicts
context
unclear

Contradictory evidence must remain attached to the claim.

## Verification States

unverified:
the claim has not been adequately checked.

partially_verified:
some evidence supports the claim, but important uncertainty
or missing coverage remains.

verified:
available evidence materially supports the claim and no known
unresolved contradiction invalidates it.

contradicted:
available evidence materially conflicts with the claim.

disputed:
credible evidence supports materially different conclusions.

## Source Selection

Prefer sources that are:

- directly relevant;
- identifiable;
- independently verifiable;
- sufficiently current for the claim;
- primary or authoritative when practical.

Source popularity alone is not evidence quality.

Multiple copies of the same underlying information
must not be treated as independent corroboration.

## Claim Granularity

Claims should be narrow enough that evidence can meaningfully
support or contradict them.

A paragraph containing several independent factual assertions
should not be represented as one indivisible claim when those
assertions require different evidence.

## Important Claims

High or critical importance claims require stronger evidence
discipline than low importance contextual claims.

Important factual claims should normally have direct supporting
evidence or be explicitly marked as not verified.

## Contradictions

When credible sources conflict:

1. preserve both sides;
2. identify the disputed claim;
3. compare source relevance and authority;
4. state what remains unresolved;
5. use the disputed state when appropriate.

Do not resolve contradictions by arbitrary majority vote.

## Uncertainty

Do not invent numeric confidence values unless the system uses
a separately validated and calibrated confidence method.

Use explicit verification states and written uncertainty instead.

## Evidence Integrity

Evidence identifiers must be unique within their document.

Every evidence.claim_id must reference an existing claim.

Every evidence.source_id must reference an existing source.

Orphan evidence is invalid.
