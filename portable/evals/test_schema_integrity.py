import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

EXPECTED_SCHEMAS = {
    "claim.schema.json",
    "evidence.schema.json",
    "ledger-entry.schema.json",
    "research-plan.schema.json",
    "research-report.schema.json",
    "source.schema.json",
    "worker-result.schema.json",
}

DRAFT_2020_12 = (
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

    assert set(paths) == EXPECTED_SCHEMAS, (
        "schema set mismatch: "
        f"{set(paths)}"
    )

    schemas = {
        name: json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        for name, path in paths.items()
    }

    return schemas


def check_schema_structure(
    schemas,
):
    ids = []
    titles = []

    for name, schema in schemas.items():

        assert isinstance(
            schema,
            dict,
        )

        assert (
            schema.get("$schema")
            == DRAFT_2020_12
        ), name

        assert (
            schema.get("$id")
            == name
        ), name

        assert isinstance(
            schema.get("title"),
            str,
        )

        assert schema["title"]

        assert (
            schema.get("type")
            == "object"
        )

        properties = schema.get(
            "properties"
        )

        assert isinstance(
            properties,
            dict,
        )

        required = schema.get(
            "required",
            []
        )

        assert isinstance(
            required,
            list,
        )

        for field in required:
            assert (
                field in properties
            ), (
                f"{name}: required field "
                f"{field!r} missing from "
                "properties"
            )

        assert (
            schema.get(
                "additionalProperties"
            )
            is False
        ), (
            f"{name}: "
            "additionalProperties "
            "must be false"
        )

        ids.append(
            schema["$id"]
        )

        titles.append(
            schema["title"]
        )

    assert (
        len(ids)
        == len(set(ids))
    ), "duplicate schema $id"

    assert (
        len(titles)
        == len(set(titles))
    ), "duplicate schema title"

    print(
        "SCHEMA_STRUCTURE_OK"
    )


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


def check_local_refs(
    schemas,
):
    known = set(schemas)

    refs = []

    for schema in schemas.values():
        refs.extend(
            walk_refs(schema)
        )

    assert refs, (
        "no local schema references found"
    )

    for ref in refs:

        if "://" in ref:
            continue

        assert ref in known, (
            f"missing local $ref: {ref}"
        )

    print(
        "LOCAL_SCHEMA_REFS_OK"
    )


def check_expected_contract_refs(
    schemas,
):
    worker_refs = set(
        walk_refs(
            schemas[
                "worker-result.schema.json"
            ]
        )
    )

    assert {
        "claim.schema.json",
        "source.schema.json",
        "evidence.schema.json",
    }.issubset(
        worker_refs
    )

    report_refs = set(
        walk_refs(
            schemas[
                "research-report.schema.json"
            ]
        )
    )

    assert {
        "claim.schema.json",
        "source.schema.json",
        "evidence.schema.json",
    }.issubset(
        report_refs
    )

    ledger_refs = set(
        walk_refs(
            schemas[
                "ledger-entry.schema.json"
            ]
        )
    )

    assert (
        "claim.schema.json"
        in ledger_refs
    )

    print(
        "EXPECTED_CONTRACT_REFS_OK"
    )


def check_referential_integrity(
    document,
):
    claims = document.get(
        "claims",
        []
    )

    sources = document.get(
        "sources",
        []
    )

    evidence = document.get(
        "evidence",
        []
    )

    claim_ids = [
        item["claim_id"]
        for item in claims
    ]

    source_ids = [
        item["source_id"]
        for item in sources
    ]

    evidence_ids = [
        item["evidence_id"]
        for item in evidence
    ]

    assert (
        len(claim_ids)
        == len(set(claim_ids))
    ), "duplicate claim_id"

    assert (
        len(source_ids)
        == len(set(source_ids))
    ), "duplicate source_id"

    assert (
        len(evidence_ids)
        == len(set(evidence_ids))
    ), "duplicate evidence_id"

    known_claims = set(
        claim_ids
    )

    known_sources = set(
        source_ids
    )

    for item in evidence:

        assert (
            item["claim_id"]
            in known_claims
        ), (
            "orphan evidence claim_id: "
            f"{item['claim_id']}"
        )

        assert (
            item["source_id"]
            in known_sources
        ), (
            "orphan evidence source_id: "
            f"{item['source_id']}"
        )


def check_positive_reference_case():
    sample = {
        "claims": [
            {
                "claim_id":
                    "claim-1"
            }
        ],

        "sources": [
            {
                "source_id":
                    "source-1"
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "evidence-1",

                "claim_id":
                    "claim-1",

                "source_id":
                    "source-1"
            }
        ]
    }

    check_referential_integrity(
        sample
    )

    print(
        "REFERENCE_INTEGRITY_OK"
    )


def check_negative_reference_case():
    broken = {
        "claims": [
            {
                "claim_id":
                    "claim-1"
            }
        ],

        "sources": [
            {
                "source_id":
                    "source-1"
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "evidence-1",

                "claim_id":
                    "missing-claim",

                "source_id":
                    "source-1"
            }
        ]
    }

    try:
        check_referential_integrity(
            broken
        )

    except AssertionError:
        print(
            "ORPHAN_EVIDENCE_REJECTED_OK"
        )
        return

    raise AssertionError(
        "orphan evidence was accepted"
    )


def main():
    schemas = load_schemas()

    check_schema_structure(
        schemas
    )

    check_local_refs(
        schemas
    )

    check_expected_contract_refs(
        schemas
    )

    check_positive_reference_case()

    check_negative_reference_case()

    print()
    print(
        "PORTABLE_SCHEMA_INTEGRITY_OK"
    )


if __name__ == "__main__":
    main()
