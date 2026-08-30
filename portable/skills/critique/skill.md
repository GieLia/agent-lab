# Critique Skill

Version: 1
Status: active

## Purpose

Evaluate supplied research material and identify material
correctness, evidence, coverage, contradiction, uncertainty,
and task-completion defects without gathering new evidence.

## Inputs

Required:

- research objective;
- WorkerResult or ResearchReport.

Optional:

- ResearchPlan;
- supplied Evidence;
- supplied Source objects;
- evaluation criteria.

## Outputs

Structured critique containing:

- material findings;
- missing evidence;
- unresolved contradictions;
- revision targets;
- task-completion assessment.

## Procedure

### 1. Reconstruct Required Scope

Determine what the supplied material was required to address.

### 2. Evaluate Factual Support

Identify important factual claims that lack adequate
supplied evidence.

Do not independently search for evidence.

### 3. Evaluate Source Quality

Judge only the supplied source information.

Do not invent source characteristics that are not supplied.

### 4. Evaluate Source Coverage

Identify material areas where the evidence set is insufficient
for the requested scope.

### 5. Evaluate Contradiction Handling

Check whether credible conflicting evidence is represented
rather than suppressed.

### 6. Evaluate Uncertainty Hygiene

Check whether uncertainty, disputed evidence, assumptions,
and speculation are represented honestly.

### 7. Evaluate Task Completion

Determine whether the requested scope is materially complete.

### 8. Produce Revision Targets

Report concrete material defects that another worker
can act on.

## Retry Conditions

The Critic itself should retry only when its own output is:

- structurally invalid;
- incomplete against the required critique contract;
- internally contradictory.

Research retry decisions belong to the Research Lead.

## Stop Conditions

Stop when material defects and revision targets have been
identified from the supplied context.

## Prohibited Behavior

Do not:

- browse or fetch external evidence;
- introduce unsupported external facts;
- reward verbosity or formatting alone;
- convert confidence language into evidence;
- mutate supplied research artifacts;
- perform external actions.

## Required Policies

- research-policy.md
- evidence-policy.md
- security-policy.md
