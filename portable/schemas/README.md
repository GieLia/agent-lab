# Schemas

Provider-neutral structured data contracts.

Current core schemas:

- ResearchPlan
- Source
- Claim
- Evidence
- WorkerResult
- ResearchReport
- AcceptanceGate
- LedgerEntry
- KnowledgeBundle
- CapabilityRegistry
- ContextManifest
- ToolProfile
- ToolBindingRegistry

Key relationships:

Claim <- Evidence -> Source

AcceptanceGate determines which research material may
enter synthesis.

KnowledgeBundle is the durable persistence boundary for
knowledge provenance. It keeps LedgerEntry, Evidence,
and Source records together so evidence identifiers do
not become orphan references.

Schema files use JSON Schema Draft 2020-12.

CapabilityRegistry defines provider-neutral runtime actions
such as web.search, workspace.write, and process.execute.

ToolProfile defines the maximum capability set and runtime
constraints available to a worker invocation.

Capabilities remain separate from concrete implementations
such as native tools, CLI adapters, HTTP APIs, or MCP.

ToolBindingRegistry defines the contract used by a deployment
to map authorized capabilities to concrete native, CLI,
Python, HTTP, or MCP implementations.

Concrete binding registries are deployment-specific and
remain outside portable assets.

ContextManifest selects the minimal Role Profile, Skills,
ToolProfile, schemas, and context budget required for a
worker configuration.

Required policies are resolved from canonical selected
assets rather than duplicated in the manifest.
