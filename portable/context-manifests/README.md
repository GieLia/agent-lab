# Context Manifests

Version: 1
Status: active

## Purpose

Define the minimal portable context required for a specific
worker configuration.

A ContextManifest selects canonical assets.

It does not duplicate their instructions.

## Selected Context

A manifest identifies:

- one Role Profile;
- one or more Skills;
- one ToolProfile;
- zero or more structured schemas;
- a deterministic context budget.

## Policy Resolution

Policies are not manually duplicated in the manifest.

The runtime resolves required policies from:

- the selected Role Profile;
- selected Skills;
- the selected ToolProfile.

The resulting policy set is the union of all requirements.

A missing required policy is an invalid context assembly.

## Progressive Disclosure

Only explicitly selected assets and their required policy
closure may be loaded.

The loader must not recursively load the complete portable
directory.

README files are documentation and are not implicitly loaded
as runtime context.

## Security

Manifest paths are logical identifiers, not arbitrary paths.

A manifest must not provide filesystem paths.

The loader resolves identifiers only inside approved
portable asset roots.

Path traversal and escape outside the repository-approved
roots are invalid.

## Context Budget

Context assembly must fail before model execution when the
resolved context exceeds either:

- max_files;
- max_bytes.

The budget is an enforcement boundary, not a suggestion.

## Runtime Adoption

The existence of a ContextManifest does not automatically
change production graph behavior.

Runtime adoption is a separate explicit integration step.
