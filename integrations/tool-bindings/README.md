# Tool Bindings

Version: 1
Status: active

## Purpose

Map provider-neutral capabilities to concrete runtime
implementations for this Agent Lab installation.

Bindings are deployment-specific.

They are intentionally stored outside portable assets.

## Authorization Chain

A concrete tool is executable only when all applicable
boundaries permit it:

    role / skill requirement
        ->
    capability
        ->
    ToolProfile authorization
        ->
    ToolBinding
        ->
    runtime enforcement
        ->
    OS / network / sandbox enforcement

A binding does not grant capability by itself.

## Tool Kinds

Supported implementation kinds:

- native
- cli
- python
- http
- mcp

## Default Deny

A discovered implementation that has no explicit binding
is not authorized.

A binding whose capability is not allowed by the selected
ToolProfile is not authorized.

A disabled binding is not authorized.

## Approval

Binding approval may be equal to or stricter than the
Capability Registry approval floor.

A binding must never weaken capability approval.

## Secrets

Binding metadata must not contain credentials.

Credentials belong in the runtime secret-management layer,
not in Git-tracked registries.
