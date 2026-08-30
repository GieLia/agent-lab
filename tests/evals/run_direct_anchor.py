import argparse
import asyncio
import hashlib
import json
import os
import uuid

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from app.workers.claude_worker import run_claude


ROOT = Path(__file__).resolve().parents[2]

CASE_DIR = (
    ROOT
    / "tests"
    / "evals"
    / "direct_anchor"
)

SCHEMA_DIR = (
    ROOT
    / "portable"
    / "schemas"
)

RESULTS_DIR = (
    ROOT
    / "tests"
    / "evals"
    / "results"
    / "direct_anchor"
)


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def resolve_account():
    value = os.getenv(
        "CLAUDE_DIRECT_ANCHOR_ACCOUNT",
        "secondary",
    )

    value = value.strip().lower()

    aliases = {
        "a": "primary",
        "primary": "primary",
        "b": "secondary",
        "secondary": "secondary",
    }

    return aliases.get(
        value,
        value,
    )


def inline_worker_schema():
    worker = deepcopy(
        load_json(
            SCHEMA_DIR
            / "worker-result.schema.json"
        )
    )

    claim = deepcopy(
        load_json(
            SCHEMA_DIR
            / "claim.schema.json"
        )
    )

    source = deepcopy(
        load_json(
            SCHEMA_DIR
            / "source.schema.json"
        )
    )

    evidence = deepcopy(
        load_json(
            SCHEMA_DIR
            / "evidence.schema.json"
        )
    )

    for nested in [
        claim,
        source,
        evidence,
    ]:
        nested.pop(
            "$schema",
            None,
        )

        nested.pop(
            "$id",
            None,
        )

        nested.pop(
            "x-version",
            None,
        )

    worker[
        "properties"
    ][
        "claims"
    ][
        "items"
    ] = claim

    worker[
        "properties"
    ][
        "sources"
    ][
        "items"
    ] = source

    worker[
        "properties"
    ][
        "evidence"
    ][
        "items"
    ] = evidence

    worker.pop(
        "$schema",
        None,
    )

    worker.pop(
        "$id",
        None,
    )

    worker.pop(
        "x-version",
        None,
    )

    encoded = json.dumps(
        worker,
        ensure_ascii=False,
    )

    if '"$ref"' in encoded:
        raise RuntimeError(
            "direct anchor schema "
            "contains unresolved $ref"
        )

    return worker


def case_hash(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def validate_result(
    result,
    case,
):
    required = {
        "worker_id",
        "role",
        "status",
        "claims",
        "sources",
        "evidence",
    }

    missing = (
        required
        - set(result)
    )

    if missing:
        raise RuntimeError(
            f"missing result fields: "
            f"{sorted(missing)}"
        )

    if (
        result["worker_id"]
        != "direct-anchor-researcher-v1"
    ):
        raise RuntimeError(
            "unexpected worker_id"
        )

    if result["role"] != "researcher":
        raise RuntimeError(
            "direct anchor role "
            "must be researcher"
        )

    if result["status"] == "failed":
        raise RuntimeError(
            "direct anchor returned "
            "failed status"
        )

    if not result["claims"]:
        raise RuntimeError(
            "direct anchor returned "
            "no claims"
        )

    if not result["sources"]:
        raise RuntimeError(
            "direct anchor returned "
            "no sources"
        )

    if not result["evidence"]:
        raise RuntimeError(
            "direct anchor returned "
            "no evidence"
        )

    claim_ids = [
        item["claim_id"]
        for item in result["claims"]
    ]

    source_ids = [
        item["source_id"]
        for item in result["sources"]
    ]

    evidence_ids = [
        item["evidence_id"]
        for item in result["evidence"]
    ]

    for label, values in [
        (
            "claim_id",
            claim_ids,
        ),
        (
            "source_id",
            source_ids,
        ),
        (
            "evidence_id",
            evidence_ids,
        ),
    ]:
        if len(values) != len(
            set(values)
        ):
            raise RuntimeError(
                f"duplicate {label}"
            )

    packet_sources = {
        item[
            "source"
        ][
            "source_id"
        ]:
            item[
                "source"
            ]
        for item in case[
            "source_packet"
        ]
    }

    unknown_sources = (
        set(source_ids)
        - set(packet_sources)
    )

    if unknown_sources:
        raise RuntimeError(
            "invented source ids: "
            f"{sorted(unknown_sources)}"
        )

    result_sources = {
        item["source_id"]:
            item
        for item in result["sources"]
    }

    for source_id, actual in (
        result_sources.items()
    ):
        expected = packet_sources[
            source_id
        ]

        for field in [
            "source_type",
            "title",
        ]:
            if (
                actual[field]
                != expected[field]
            ):
                raise RuntimeError(
                    f"source metadata mismatch: "
                    f"{source_id}.{field}"
                )

    known_claims = set(
        claim_ids
    )

    known_sources = set(
        source_ids
    )

    for item in result["evidence"]:
        if (
            item["claim_id"]
            not in known_claims
        ):
            raise RuntimeError(
                "orphan evidence claim_id: "
                f"{item['claim_id']}"
            )

        if (
            item["source_id"]
            not in known_sources
        ):
            raise RuntimeError(
                "orphan evidence source_id: "
                f"{item['source_id']}"
            )


def build_prompt(case):
    packet = json.dumps(
        case["source_packet"],
        indent=2,
        ensure_ascii=False,
    )

    constraints = "\n".join(
        "- " + value
        for value in case[
            "constraints"
        ]
    )

    return f"""
You are the sole Researcher in a direct research baseline.

This is intentionally NOT a multi-agent workflow.

OBJECTIVE

{case["objective"]}

CONSTRAINTS

{constraints}

Return one complete WorkerResult.

Required identity:

worker_id = direct-anchor-researcher-v1
role = researcher

Use status=success when the supplied packet materially
supports a useful answer.

Use status=partial when important requested conclusions
cannot responsibly be reached from the supplied packet.

Rules:

1. Use ONLY the supplied source packet.
2. Do not use external knowledge.
3. Do not invent source identifiers.
4. Copy source_type and title accurately for each source used.
5. Form granular claims.
6. Every material factual claim should have explicit evidence.
7. Preserve contradictions and superseded material.
8. Do not convert a superseded source into current authority.
9. verification_status must reflect supplied evidence.
10. gaps must identify material unresolved questions.
11. provider/account/model fields may be null; runtime
    provenance will be applied after generation.

SOURCE PACKET

{packet}
""".strip()


async def run_anchor(
    case_path,
):
    case = load_json(
        case_path
    )

    schema = inline_worker_schema()

    account = resolve_account()

    started = now()

    raw = await run_claude(
        prompt=build_prompt(
            case
        ),
        cwd=ROOT,
        timeout=900,
        max_turns=5,
        tool_profile="reasoning",
        account=account,
        system_prompt=(
            "You are a constrained research baseline. "
            "Use only supplied evidence. "
            "Do not browse, use tools, or introduce "
            "external facts."
        ),
        json_schema=schema,
    )

    result = json.loads(
        raw
    )

    validate_result(
        result,
        case,
    )

    result["provider"] = "claude"
    result["account"] = account

    # The current worker abstraction does not expose
    # the exact resolved model name to the caller.
    result["model"] = None

    run_id = str(
        uuid.uuid4()
    )

    run_dir = (
        RESULTS_DIR
        / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    result_file = (
        run_dir
        / "worker-result.json"
    )

    result_file.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    metadata = {
        "run_id":
            run_id,

        "case_id":
            case["case_id"],

        "case_version":
            case["version"],

        "case_sha256":
            case_hash(
                case_path
            ),

        "created_at":
            started,

        "provider":
            "claude",

        "account":
            account,

        "model":
            None,

        "model_note":
            (
                "Exact resolved model is not exposed "
                "by the current run_claude abstraction."
            ),

        "tool_profile":
            "reasoning",

        "external_tools":
            False,

        "model_invocations":
            1,

        "max_turns":
            5,

        "orchestration":
            "none",

        "critic":
            False,

        "evidence_verifier":
            False,

        "synthesizer":
            False,

        "result_file":
            str(
                result_file.relative_to(
                    ROOT
                )
            ),
    }

    (
        run_dir
        / "metadata.json"
    ).write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 68)
    print("DIRECT RESEARCH ANCHOR")
    print("=" * 68)
    print("run_id:", run_id)
    print("case:", case["case_id"])
    print("provider:", "claude")
    print("account:", account)
    print("claims:", len(result["claims"]))
    print("sources:", len(result["sources"]))
    print("evidence:", len(result["evidence"]))
    print("status:", result["status"])
    print("result:", result_file)

    return run_id


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--case",
        default=str(
            CASE_DIR
            / "case_v1.json"
        ),
    )

    args = parser.parse_args()

    asyncio.run(
        run_anchor(
            Path(args.case)
        )
    )


if __name__ == "__main__":
    main()
