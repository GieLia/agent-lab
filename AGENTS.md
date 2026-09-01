# Agent Lab Repository Guide

Version: 1
Status: active

## Purpose

Provide concise repository-level instructions for coding
and maintenance agents working on Agent Lab.

This file is not a runtime worker prompt.

Do not automatically inject this file into Researcher,
Critic, Synthesizer, or other workflow worker context.

## Repository Map

app/

Runtime orchestration, worker adapters, API code, and
runtime context assembly.

portable/

Provider-neutral reusable roles, skills, policies,
schemas, capabilities, tool profiles, and evaluation
contracts.

integrations/

Deployment-specific implementation bindings and external
integration boundaries.

infra/

Deployment infrastructure, services, database migrations,
and host integration.

tests/evals/

Runtime and evaluation contract tests.

runs/

Generated execution artifacts. Do not treat run artifacts
as repository instructions.

prompts/

Reserved for explicit prompt assets when needed.

## Context Discipline

Use progressive disclosure.

Load the smallest set of files required for the current task.

Do not recursively load all portable assets into model context.

Prefer canonical assets over duplicating their instructions
inside prompts or configuration files.

Repository instructions, runtime role context, durable
knowledge, and task-specific prompts are separate concerns.

## Portable Asset Boundaries

Role Profile:

Defines responsibilities and role boundaries.

Skill:

Defines how a reusable task is performed.

Policy:

Defines mandatory behavioral and security constraints.

ToolProfile:

Defines the maximum runtime capability set.

Capability:

Defines a provider-neutral authorized action.

ToolBinding:

Maps an authorized capability to a deployment-specific
implementation.

A lower-level asset must not broaden permissions granted
by a higher-level boundary.

## Runtime Safety

Default deny applies to tool access.

Do not infer authorization from tool discovery.

Do not weaken ToolProfile, runtime, operating-system,
network, sandbox, approval, or credential boundaries.

Do not place secrets in tracked configuration,
portable assets, prompts, logs, or test fixtures.

## Change Discipline

Prefer small, reviewable changes.

Do not modify production graph behavior while changing
portable contracts unless the task explicitly requires it.

Do not regenerate frozen evaluation baselines unless the
evaluation protocol explicitly requires regeneration.

Do not use destructive Git operations to hide unrelated
working-tree changes.

Run relevant integrity tests and pre-commit checks before
committing.
