import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RUNNER = (
    ROOT
    / "tests"
    / "evals"
    / "run_direct_anchor.py"
)

CASE = (
    ROOT
    / "tests"
    / "evals"
    / "direct_anchor"
    / "case_v1.json"
)


def load_runner():
    spec = (
        importlib.util
        .spec_from_file_location(
            "direct_anchor_runner",
            RUNNER,
        )
    )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


def check_case():
    case = json.loads(
        CASE.read_text(
            encoding="utf-8"
        )
    )

    assert (
        case["case_id"]
        == "state_storage_boundary_v1"
    )

    assert case["version"] == 1

    source_ids = [
        item[
            "source"
        ][
            "source_id"
        ]
        for item in case[
            "source_packet"
        ]
    ]

    assert len(source_ids) >= 5
    assert len(source_ids) == len(
        set(source_ids)
    )

    assert (
        "src-redis-old-v1"
        in source_ids
    )

    print(
        "DIRECT_ANCHOR_CASE_OK"
    )


def check_schema(module):
    schema = (
        module.inline_worker_schema()
    )

    encoded = json.dumps(
        schema
    )

    assert '"$ref"' not in encoded

    assert (
        schema["title"]
        == "WorkerResult"
    )

    print(
        "DIRECT_ANCHOR_SCHEMA_OK"
    )


def check_validator(module):
    case = json.loads(
        CASE.read_text(
            encoding="utf-8"
        )
    )

    source = case[
        "source_packet"
    ][0][
        "source"
    ]

    good = {
        "worker_id":
            "direct-anchor-researcher-v1",

        "role":
            "researcher",

        "status":
            "success",

        "claims": [
            {
                "claim_id":
                    "c-1",

                "text":
                    "Example.",

                "claim_type":
                    "fact",

                "importance":
                    "medium",

                "verification_status":
                    "verified",
            }
        ],

        "sources": [
            source,
        ],

        "evidence": [
            {
                "evidence_id":
                    "e-1",

                "claim_id":
                    "c-1",

                "source_id":
                    source["source_id"],

                "relationship":
                    "supports",

                "excerpt":
                    "Example.",

                "location":
                    None,

                "strength":
                    "moderate",

                "notes":
                    None,
            }
        ],

        "gaps": [],
        "notes": None,
    }

    module.validate_result(
        good,
        case,
    )

    broken = deepcopy_json(
        good
    )

    broken[
        "sources"
    ][0][
        "source_id"
    ] = "invented-source"

    try:
        module.validate_result(
            broken,
            case,
        )

    except RuntimeError:
        print(
            "DIRECT_ANCHOR_INVENTED_SOURCE_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "invented source was accepted"
        )


def deepcopy_json(value):
    return json.loads(
        json.dumps(value)
    )


def main():
    module = load_runner()

    check_case()
    check_schema(module)
    check_validator(module)

    print()
    print(
        "DIRECT_ANCHOR_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
