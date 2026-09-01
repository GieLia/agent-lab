# Portable Agent Kit

Provider-neutral, reusable agent assets.

Core principle:

AGENT = ROLE + MODEL + SKILLS + TOOLS + MEMORY + POLICY + CONTEXT

This directory contains portable methodology and contracts.

Provider-specific adapters remain outside this directory.

Runtime knowledge is stored separately from these assets.

## Portable Layers

profiles:

Define worker roles, responsibilities, and reasoning boundaries.

skills:

Define reusable procedures and expected outputs.

policies:

Define deterministic behavioral and security constraints.

schemas:

Define provider-neutral structured data contracts.

capabilities:

Define provider-neutral actions that a runtime may authorize.

tool-profiles:

Define the maximum capability set and runtime constraints
available to a worker invocation.

evals:

Define deterministic integrity and acceptance checks.

## Capability Boundary

Portable assets should depend on capabilities rather than
specific tool implementations.

Example:

    web.search

may later be implemented by:

- a native provider tool;
- a CLI adapter;
- a Python adapter;
- an HTTP API;
- an MCP server.

Implementation choice must not silently broaden capability.

## Security Principle

Tool authorization, runtime enforcement, operating-system
permissions, network permissions, and credentials are
separate security boundaries.

A lower layer must not broaden permission granted by a
higher layer.
