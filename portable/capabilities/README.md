# Capability Registry

Version: 1
Status: active

## Purpose

Define provider-neutral capabilities that an agent runtime
may authorize independently from specific tool implementations.

A capability describes what an agent is allowed to do.

A capability does not identify the concrete tool used to do it.

Examples:

- web.search
- web.fetch
- document.read
- workspace.read
- workspace.write
- process.execute
- system.privileged

## Capability and Tool Separation

The following are different concepts:

Capability:

    web.search

Implementation:

    native search tool
    HTTP adapter
    Python adapter
    MCP server tool

Portable skills and role profiles should depend on
capabilities rather than concrete implementations.

## Access Classes

read:

Retrieves information without intentionally mutating state.

write:

Creates or modifies authorized state.

execute:

Runs code or processes.

privileged:

Requires elevated system or infrastructure authority.

## Approval Floor

Each capability defines a default approval level:

none:

No additional approval is required by the capability contract.

runtime:

The runtime must explicitly authorize the operation.

human:

A human approval boundary is required.

A tool profile or runtime may make approval stricter.

It must not make approval weaker than the capability registry.

## Security Boundary

Capability authorization does not imply:

- filesystem permission;
- network permission;
- operating-system permission;
- container permission;
- MCP server trust;
- credential access.

Those boundaries must be independently enforced.
