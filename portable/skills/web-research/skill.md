# Web Research Skill

Version: 1
Status: active

## Purpose

Discover, select, retrieve, and structure external information
for a defined research objective while preserving source
traceability.

## Inputs

Required:

- research objective or research question.

Optional:

- ResearchPlan;
- existing claims;
- known sources;
- known gaps;
- time or recency constraints;
- source-type constraints.

## Outputs

The skill produces research material suitable for WorkerResult:

- Source objects;
- Claim objects;
- Evidence objects;
- identified contradictions;
- unresolved gaps.

## Procedure

### 1. Clarify Scope

Translate the assigned objective into explicit questions
that can be answered with evidence.

Do not broaden the scope unless required to resolve
a material dependency.

### 2. Plan Search

Create targeted search directions based on:

- named entities;
- technical concepts;
- dates or recency requirements;
- primary-source opportunities;
- known gaps.

Prefer multiple focused searches over one excessively broad query.

### 3. Discover Sources

Collect candidate sources.

At this stage, discovery metadata is not yet treated as evidence.

### 4. Rank Sources

Prefer sources that are:

- directly relevant;
- authoritative for the specific claim;
- independently verifiable;
- sufficiently current;
- primary when practical.

Avoid treating duplicated syndication as independent confirmation.

### 5. Retrieve Selected Sources

Retrieve the highest-value candidate sources needed
to answer the assigned question.

Do not collect content solely to maximize source count.

### 6. Extract Claims

Convert material findings into granular claims.

Separate:

- facts;
- interpretation;
- assumptions;
- speculation;
- recommendations.

### 7. Create Evidence Links

For each material factual claim:

- identify the supporting or contradicting Source;
- create Evidence;
- preserve useful source location or excerpt information;
- assign the appropriate evidence relationship.

### 8. Detect Contradictions

When sources materially disagree:

- preserve both positions;
- identify the disputed claim;
- do not silently select the preferred answer.

### 9. Evaluate Coverage

Identify:

- unsupported important claims;
- missing primary evidence;
- stale evidence;
- unresolved contradictions;
- missing parts of the requested scope.

### 10. Perform Targeted Follow-Up

Search only the unresolved material gaps.

Do not restart the complete research process
when a specific missing slice can be investigated.

## Retry Conditions

Retry or targeted follow-up is appropriate when:

- an important claim lacks evidence;
- source coverage is materially incomplete;
- a source cannot be retrieved;
- significant evidence is stale;
- credible sources conflict;
- the assigned research question remains unanswered.

## Stop Conditions

Stop when:

- the assigned scope is materially addressed;
- important claims are evidence-linked;
- significant contradictions are represented;
- remaining gaps are explicit;
- additional searching is unlikely to materially change
  the answer within the mission constraints.

## Prohibited Behavior

Do not:

- fabricate sources;
- fabricate source content;
- treat search snippets alone as definitive evidence
  when the underlying source can be checked;
- hide contradictory evidence;
- inflate source count with duplicates;
- claim verification without evidence;
- execute external mutations.

## Required Policies

- research-policy.md
- evidence-policy.md
- security-policy.md
