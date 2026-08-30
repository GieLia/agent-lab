# Revision Quality Eval

Version: 1
Status: active

## Purpose

Evaluate whether a revision materially improves research
quality relative to its prior version.

## Subject

Applicable to:

- before/after WorkerResult;
- before/after ResearchReport;
- iterative research outputs.

## Inputs

Required:

- before artifact;
- after artifact;
- original task objective.

Optional:

- critic feedback;
- identified missing evidence;
- applicable policies.

## Evaluation Dimensions

Evaluate material change in:

- factual support;
- source quality;
- source coverage;
- contradiction handling;
- uncertainty hygiene;
- task completion.

## Pass Criteria

A revision passes when the after version is materially
better overall without introducing a material regression.

A tie is valid when differences are not material.

## Fail Conditions

Fail when the revision:

- loses correct prior material without justification;
- introduces unsupported claims;
- reduces evidence traceability;
- hides contradictions;
- worsens uncertainty handling;
- fails to address the requested revision target.

## Comparative Method

Prefer direct before-versus-after comparison.

Do not infer which artifact is newer from style or position.

When model judgment is used:

- balance presentation order when repeated evaluations
  are performed;
- allow tie outcomes;
- evaluate material quality rather than verbosity;
- preserve individual dimension results.

A null control comparing equivalent material should
normally produce ties rather than systematic preference.

## Measurements

Absolute quality scores may be retained as diagnostics
but are not sufficient evidence that a revision improved.

Primary revision evidence should come from comparative
before/after evaluation.

## Prohibited Shortcuts

Do not:

- reward verbosity;
- reward formatting alone;
- assume the second artifact is better;
- infer revision quality from an uncalibrated confidence score;
- convert marginal stylistic differences into wins.
