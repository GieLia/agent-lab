from __future__ import annotations

import json
import uuid

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path
from typing import Any

from jsonschema import (
    Draft202012Validator,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SCHEMA_PATH = (
    ROOT
    / "portable"
    / "schemas"
    / "acceptance-gate.schema.json"
)


class AcceptancePolicyError(
    RuntimeError
):
    pass


def _fail(
    message: str,
) -> None:
    raise AcceptancePolicyError(
        message
    )


def _load_schema(
) -> dict[str, Any]:

    try:
        value = json.loads(
            SCHEMA_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:
        raise AcceptancePolicyError(
            "unable to load "
            "AcceptanceGate schema"
        ) from exc

    Draft202012Validator.check_schema(
        value
    )

    return value


ACCEPTANCE_GATE_SCHEMA = (
    _load_schema()
)


def _now(
) -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def build_acceptance_gate(
    *,
    mission_id: str,
    worker_result: dict[str, Any],
    verification_summary: dict[str, Any],
    gate_id: str | None = None,
    created_at: str | None = None,
    actor_id: str =
        "e5-full-only-verifier-v1",
) -> dict[str, Any]:

    if (
        not isinstance(
            mission_id,
            str,
        )
        or not mission_id.strip()
    ):
        _fail(
            "mission_id must be "
            "a non-empty string"
        )

    if not isinstance(
        worker_result,
        dict,
    ):
        _fail(
            "worker_result must "
            "be an object"
        )

    if not isinstance(
        verification_summary,
        dict,
    ):
        _fail(
            "verification_summary must "
            "be an object"
        )

    worker_id = worker_result.get(
        "worker_id"
    )

    if (
        verification_summary.get(
            "worker_id"
        )
        != worker_id
    ):
        _fail(
            "verification summary "
            "worker_id mismatch"
        )

    if (
        verification_summary.get(
            "structural_integrity"
        )
        != "pass"
    ):
        _fail(
            "acceptance requires "
            "structural integrity pass"
        )

    claim_ids = [
        item["claim_id"]
        for item
        in worker_result.get(
            "claims",
            [],
        )
    ]

    if (
        len(claim_ids)
        != len(
            set(claim_ids)
        )
    ):
        _fail(
            "duplicate claim_id"
        )

    accepted = list(
        verification_summary.get(
            "verified_claim_ids",
            [],
        )
    )

    accepted_set = set(
        accepted
    )

    all_claim_ids = set(
        claim_ids
    )

    if not (
        accepted_set
        <= all_claim_ids
    ):
        _fail(
            "verification summary "
            "accepted unknown claim"
        )

    rejected = [
        claim_id
        for claim_id
        in claim_ids
        if (
            claim_id
            not in accepted_set
        )
    ]

    if (
        accepted
        and rejected
    ):
        decision = "partial"

    elif accepted:
        decision = "accepted"

    else:
        decision = "rejected"

    if gate_id is None:
        gate_id = (
            "gate-"
            + str(
                uuid.uuid4()
            )
        )

    if created_at is None:
        created_at = _now()

    rationale = (
        "Runtime FULL-only verification policy: "
        f"{len(accepted)} claim(s) accepted for "
        "synthesis and "
        f"{len(rejected)} claim(s) rejected. "
        "Acceptance does not upgrade factual "
        "verification state."
    )

    gate = {
        "gate_id":
            gate_id,

        "mission_id":
            mission_id.strip(),

        "decision":
            decision,

        "accepted_worker_ids":
            [],

        "accepted_claim_ids":
            accepted,

        "rejected_claim_ids":
            rejected,

        "decided_by": {
            "actor_type":
                "runtime",

            "actor_id":
                actor_id,
        },

        "rationale":
            rationale,

        "created_at":
            created_at,

        "rejected_worker_ids":
            [],
    }

    try:
        Draft202012Validator(
            ACCEPTANCE_GATE_SCHEMA
        ).validate(
            gate
        )

    except Exception as exc:
        raise AcceptancePolicyError(
            "generated AcceptanceGate "
            "failed canonical schema"
        ) from exc

    if (
        set(
            gate[
                "accepted_claim_ids"
            ]
        )
        & set(
            gate[
                "rejected_claim_ids"
            ]
        )
    ):
        _fail(
            "acceptance and rejection "
            "sets overlap"
        )

    if (
        set(
            gate[
                "accepted_claim_ids"
            ]
        )
        | set(
            gate[
                "rejected_claim_ids"
            ]
        )
        != all_claim_ids
    ):
        _fail(
            "AcceptanceGate does not "
            "cover all claims"
        )

    return gate
