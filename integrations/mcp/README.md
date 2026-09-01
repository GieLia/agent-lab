# MCP Integration Boundary

Version: 1
Status: scaffold

## Purpose

Define where Model Context Protocol implementations enter
the Agent Lab runtime.

MCP is an implementation mechanism.

MCP is not an authorization mechanism.

## Required Authorization Path

An MCP tool must have:

1. a known MCP server identity;
2. an explicitly defined ToolBinding;
3. a provider-neutral Capability;
4. authorization by the selected ToolProfile;
5. required runtime or human approval;
6. runtime and operating-system enforcement.

Discovery alone is insufficient.

## Supported Transport Direction

Preferred local transport:

    stdio

Preferred remote transport:

    streamable_http

Legacy SSE transport is not part of the v1 binding contract.

## Security

Remote MCP servers are external trust boundaries.

MCP output is untrusted input.

An MCP response must not:

- grant additional capabilities;
- change approval requirements;
- modify the active ToolProfile;
- bypass runtime enforcement;
- introduce credentials into portable assets.

## Current State

No MCP server is authorized merely by the existence
of this directory.

Concrete servers will be added only after security and
capability review.
