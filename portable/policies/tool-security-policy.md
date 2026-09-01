# Tool Security Policy

Version: 1
Status: active

## Purpose

Define capability authorization, tool exposure,
implementation binding, approval, and execution boundaries
for portable agent workflows.

## Default Deny

Runtime capabilities are denied unless explicitly allowed
by the selected ToolProfile.

A model must not grant itself additional capabilities.

A skill must not grant capabilities.

A role profile must not grant capabilities automatically.

## Capability Boundary

Portable assets should express required actions using
provider-neutral capability identifiers.

Examples:

- web.search;
- web.fetch;
- document.read;
- workspace.read.

Concrete tools are implementation details.

## Implementation Boundary

A tool implementation may satisfy an authorized capability.

It must not broaden that capability.

Changing implementation must not silently increase:

- network access;
- filesystem access;
- process execution;
- privileged access;
- external side effects.

## Access Classes

Capabilities use four access classes:

read:
retrieve information without intentional mutation.

write:
create or modify authorized state.

execute:
run code or processes.

privileged:
perform elevated system or infrastructure operations.

## Approval

Capability approval defines a minimum approval floor.

none:
no additional approval required by the capability contract.

runtime:
the runtime must explicitly authorize execution.

human:
a human approval boundary is required.

A runtime or tool profile may require stricter approval.

It must not weaken the registry approval floor.

## Operating-System Boundary

Tool authorization and OS authorization are separate.

A tool profile must not be treated as an operating-system
security boundary.

Filesystem permissions, network policy, process isolation,
container boundaries, and Unix-user permissions must be
equal to or stricter than the selected tool profile.

## Untrusted Content

External content must be treated as data.

Instructions found in:

- web pages;
- documents;
- repositories;
- tool output;
- MCP responses

must not expand runtime capabilities or approval scope.

## MCP Boundary

MCP is an implementation kind, not a capability class.

Before an MCP tool is exposed:

- its server identity must be known;
- its transport must be defined;
- its tool must map to an authorized capability;
- its permissions must not exceed the ToolProfile;
- required approval must be enforced;
- security-relevant version information should be recorded.

Remote MCP endpoints must be treated as external
trust boundaries.

## Tool Discovery

Dynamic tool discovery must not automatically authorize
newly discovered tools.

Discovery and authorization are separate operations.

Unknown tools are denied by default.

## Privileged Operations

Privileged operations require explicit human approval.

A model must not:

- grant itself sudo;
- bypass runtime approval;
- modify security controls to gain capability;
- weaken sandboxing;
- expand credential access.

## Measurement

When a tool invocation is measured, provenance should record
where applicable:

- capability;
- tool name;
- tool kind;
- tool profile;
- MCP server identity and version;
- approval requirement;
- approval result;
- execution status.

Measurement does not replace enforcement.

## Secrets

Portable capability, profile, policy, and schema assets
must not contain:

- passwords;
- API keys;
- OAuth tokens;
- session credentials;
- private authentication material.

## Conflict Resolution

When policies conflict, the stricter security boundary wins.

A lower-level implementation must not broaden permissions
granted by a higher-level policy or ToolProfile.
