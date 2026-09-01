# Tool Profiles

Version: 1
Status: active

## Purpose

Tool profiles define the maximum runtime capability set
available to a worker invocation.

They are provider-neutral and implementation-independent.

## Role Profile vs Tool Profile

A role profile defines:

- responsibilities;
- reasoning boundaries;
- prohibited behavior.

A tool profile defines:

- allowed runtime capabilities;
- runtime constraints;
- maximum tool exposure.

A role does not automatically inherit tool capabilities.

## Default Deny

Every tool profile uses:

    default_deny = true

Any capability not explicitly listed in
allowed_capabilities is denied.

## Capability vs Implementation

Tool profiles reference capability identifiers such as:

    web.search

They must not depend directly on implementation names such as:

    playwright.browser_navigate
    mcp_server.search
    vendor_specific_tool_name

Implementation binding belongs outside portable assets.

## Runtime Constraints

Tool-profile authorization is only one security layer.

The runtime must independently enforce:

- network boundary;
- workspace boundary;
- process-execution boundary;
- privileged-operation boundary.

## Tool Exposure

max_tools_exposed is an upper bound.

The runtime should expose only the minimum concrete tools
needed for the current task.

A larger available tool inventory is not automatically better.

## MCP

MCP is an implementation transport or tool kind.

MCP does not grant capability by itself.

Every MCP tool must be mapped to an explicitly authorized
capability before exposure to an agent.
