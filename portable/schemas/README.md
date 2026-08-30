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

Key relationships:

Claim <- Evidence -> Source

AcceptanceGate determines which research material may
enter synthesis.

KnowledgeBundle is the durable persistence boundary for
knowledge provenance. It keeps LedgerEntry, Evidence,
and Source records together so evidence identifiers do
not become orphan references.

Schema files use JSON Schema Draft 2020-12.
