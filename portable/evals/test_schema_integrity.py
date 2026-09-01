import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

EXPECTED_SCHEMAS = {
    "acceptance-gate.schema.json",
    "capability-registry.schema.json",
    "claim.schema.json",
    "context-manifest.schema.json",
    "evidence.schema.json",
    "knowledge-bundle.schema.json",
    "ledger-entry.schema.json",
    "research-plan.schema.json",
    "research-report.schema.json",
    "source.schema.json",
    "tool-binding-registry.schema.json",
    "tool-profile.schema.json",
    "worker-result.schema.json",
}

DRAFT = (
    "https://json-schema.org/"
    "draft/2020-12/schema"
)


def load_schemas():
    paths = {
        path.name: path
        for path in SCHEMA_DIR.glob(
            "*.schema.json"
        )
    }

    assert set(paths) == EXPECTED_SCHEMAS

    return {
        name: json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        for name, path in paths.items()
    }


def walk_refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                yield child

            yield from walk_refs(
                child
            )

    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(
                child
            )


def check_structure(schemas):
    ids = []

    for name, schema in schemas.items():
        assert schema["$schema"] == DRAFT
        assert schema["$id"] == name
        assert schema["type"] == "object"

        assert (
            schema.get("x-version")
            == 1
        ), (
            f"{name}: missing x-version"
        )

        properties = schema.get(
            "properties"
        )

        assert isinstance(
            properties,
            dict,
        )

        for required in schema.get(
            "required",
            [],
        ):
            assert required in properties

        assert (
            schema.get(
                "additionalProperties"
            )
            is False
        )

        ids.append(
            schema["$id"]
        )

    assert len(ids) == len(set(ids))

    print(
        "SCHEMA_STRUCTURE_OK"
    )


def check_refs(schemas):
    known = set(schemas)

    for schema in schemas.values():
        for ref in walk_refs(schema):
            if "://" in ref:
                continue

            if ref.startswith("#"):
                continue

            if "#" in ref:
                ref = ref.split(
                    "#",
                    1,
                )[0]

            assert ref in known, (
                f"missing local ref: {ref}"
            )

    bundle_refs = set(
        walk_refs(
            schemas[
                "knowledge-bundle.schema.json"
            ]
        )
    )

    assert {
        "ledger-entry.schema.json",
        "source.schema.json",
        "evidence.schema.json",
    }.issubset(
        bundle_refs
    )

    print(
        "LOCAL_SCHEMA_REFS_OK"
    )


def check_contracts(schemas):
    ledger = schemas[
        "ledger-entry.schema.json"
    ]

    statuses = set(
        ledger[
            "properties"
        ][
            "status"
        ][
            "enum"
        ]
    )

    assert statuses == {
        "active",
        "superseded",
        "under_review",
        "retracted",
    }

    assert "disputed" not in statuses
    assert "retraction" in ledger["properties"]
    assert "allOf" in ledger

    assert (
        "evidence_ids"
        in ledger["required"]
    )

    assert (
        ledger["properties"]
        ["evidence_ids"]
        ["minItems"]
        == 1
    )

    assert (
        ledger["properties"]
        ["evidence_ids"]
        ["uniqueItems"]
        is True
    )

    assert (
        "superseded_by"
        in ledger["properties"]
    )

    plan = schemas[
        "research-plan.schema.json"
    ]

    assert (
        "retry_budget"
        in plan["required"]
    )

    retry = plan[
        "properties"
    ][
        "retry_budget"
    ]

    assert set(
        retry[
            "properties"
        ][
            "on_exhaustion"
        ][
            "enum"
        ]
    ) == {
        "escalate",
        "synthesize_with_gaps",
        "fail",
    }

    worker = schemas[
        "worker-result.schema.json"
    ]

    roles = set(
        worker[
            "properties"
        ][
            "role"
        ][
            "enum"
        ]
    )

    assert roles == {
        "research-lead",
        "researcher",
        "critic",
        "evidence-verifier",
        "synthesizer",
    }

    gate = schemas[
        "acceptance-gate.schema.json"
    ]

    for field in [
        "gate_id",
        "mission_id",
        "decision",
        "accepted_worker_ids",
        "accepted_claim_ids",
        "rejected_worker_ids",
        "rejected_claim_ids",
        "decided_by",
    ]:
        assert field in gate["required"]

    assert (
        "allOf"
        in gate
    )

    assert len(
        gate["allOf"]
    ) == 3

    print(
        "SCHEMA_CONTRACTS_OK"
    )


def check_worker_references(
    document,
):
    claim_ids = [
        item["claim_id"]
        for item in document["claims"]
    ]

    source_ids = [
        item["source_id"]
        for item in document["sources"]
    ]

    evidence_ids = [
        item["evidence_id"]
        for item in document["evidence"]
    ]

    assert len(claim_ids) == len(set(claim_ids))
    assert len(source_ids) == len(set(source_ids))
    assert len(evidence_ids) == len(set(evidence_ids))

    claims = set(claim_ids)
    sources = set(source_ids)

    for item in document["evidence"]:
        assert item["claim_id"] in claims
        assert item["source_id"] in sources


def check_worker_reference_cases():
    good = {
        "claims": [
            {
                "claim_id": "c-1"
            }
        ],
        "sources": [
            {
                "source_id": "s-1"
            }
        ],
        "evidence": [
            {
                "evidence_id": "e-1",
                "claim_id": "c-1",
                "source_id": "s-1",
            }
        ],
    }

    check_worker_references(
        good
    )

    broken = {
        **good,
        "evidence": [
            {
                "evidence_id": "e-1",
                "claim_id": "missing",
                "source_id": "s-1",
            }
        ],
    }

    try:
        check_worker_references(
            broken
        )

    except AssertionError:
        print(
            "ORPHAN_EVIDENCE_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "orphan evidence accepted"
        )

    print(
        "WORKER_REFERENCE_INTEGRITY_OK"
    )


def check_knowledge_bundle(
    bundle,
):
    entries = bundle[
        "ledger_entries"
    ]

    sources = bundle[
        "sources"
    ]

    evidence = bundle[
        "evidence"
    ]

    entry_ids = [
        item["entry_id"]
        for item in entries
    ]

    claim_ids = [
        item["claim"]["claim_id"]
        for item in entries
    ]

    source_ids = [
        item["source_id"]
        for item in sources
    ]

    evidence_ids = [
        item["evidence_id"]
        for item in evidence
    ]

    assert len(entry_ids) == len(set(entry_ids))
    assert len(claim_ids) == len(set(claim_ids))
    assert len(source_ids) == len(set(source_ids))
    assert len(evidence_ids) == len(set(evidence_ids))

    known_claims = set(claim_ids)
    known_sources = set(source_ids)
    known_evidence = set(evidence_ids)

    for item in evidence:
        assert (
            item["claim_id"]
            in known_claims
        )

        assert (
            item["source_id"]
            in known_sources
        )

    for entry in entries:
        for evidence_id in entry.get(
            "evidence_ids",
            [],
        ):
            assert (
                evidence_id
                in known_evidence
            )


def check_knowledge_bundle_cases():
    bundle = {
        "ledger_entries": [
            {
                "entry_id": "l-1",
                "claim": {
                    "claim_id": "c-1"
                },
                "evidence_ids": [
                    "e-1"
                ],
            }
        ],
        "sources": [
            {
                "source_id": "s-1"
            }
        ],
        "evidence": [
            {
                "evidence_id": "e-1",
                "claim_id": "c-1",
                "source_id": "s-1",
            }
        ],
    }

    check_knowledge_bundle(
        bundle
    )

    broken = {
        **bundle,
        "ledger_entries": [
            {
                "entry_id": "l-1",
                "claim": {
                    "claim_id": "c-1"
                },
                "evidence_ids": [
                    "missing-evidence"
                ],
            }
        ],
    }

    try:
        check_knowledge_bundle(
            broken
        )

    except AssertionError:
        print(
            "DURABLE_ORPHAN_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "durable orphan accepted"
        )

    print(
        "KNOWLEDGE_BUNDLE_INTEGRITY_OK"
    )


def main():
    schemas = load_schemas()

    check_structure(
        schemas
    )

    check_refs(
        schemas
    )

    check_contracts(
        schemas
    )

    check_worker_reference_cases()

    check_knowledge_bundle_cases()

    print()
    print(
        "PORTABLE_SCHEMA_INTEGRITY_OK"
    )


if __name__ == "__main__":
    main()
