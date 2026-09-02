from __future__ import annotations

import copy

from typing import Any


class SynthesisInputError(
    RuntimeError
):
    pass


SYNTHESIS_INPUT_VERSION = 1


def _fail(
    message: str,
) -> None:

    raise SynthesisInputError(
        message
    )


def build_synthesis_input(
    *,
    mission_id: str,
    worker_result: dict[str, Any],
    verification_summary: dict[str, Any],
    acceptance_gate: dict[str, Any],
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

    if not isinstance(
        acceptance_gate,
        dict,
    ):
        _fail(
            "acceptance_gate must "
            "be an object"
        )


    decision = acceptance_gate.get(
        "decision"
    )

    if decision not in {
        "accepted",
        "partial",
    }:
        _fail(
            "rejected AcceptanceGate "
            "cannot produce "
            "SynthesisInput"
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
            "verification worker_id "
            "mismatch"
        )


    gate_mission_id = (
        acceptance_gate.get(
            "mission_id"
        )
    )

    if (
        gate_mission_id
        != mission_id
    ):
        _fail(
            "AcceptanceGate mission_id "
            "mismatch"
        )


    accepted_ids = (
        acceptance_gate.get(
            "accepted_claim_ids"
        )
    )

    if (
        not isinstance(
            accepted_ids,
            list,
        )
        or not accepted_ids
    ):
        _fail(
            "SynthesisInput requires "
            "accepted claims"
        )

    if (
        len(accepted_ids)
        != len(
            set(accepted_ids)
        )
    ):
        _fail(
            "duplicate accepted claim ID"
        )


    runtime_verified = set(
        verification_summary.get(
            "verified_claim_ids",
            [],
        )
    )

    if not (
        set(accepted_ids)
        <= runtime_verified
    ):
        _fail(
            "AcceptanceGate attempted "
            "to expose a claim that is "
            "not runtime verified"
        )


    all_claims = {
        item["claim_id"]:
            item
        for item
        in worker_result.get(
            "claims",
            []
        )
    }

    unknown = (
        set(accepted_ids)
        - set(all_claims)
    )

    if unknown:
        _fail(
            "AcceptanceGate references "
            "unknown accepted claim"
        )


    accepted_claims = [
        copy.deepcopy(
            all_claims[
                claim_id
            ]
        )
        for claim_id
        in accepted_ids
    ]


    accepted_evidence = [
        copy.deepcopy(
            item
        )
        for item
        in worker_result.get(
            "evidence",
            []
        )
        if (
            item.get(
                "claim_id"
            )
            in set(
                accepted_ids
            )
        )
    ]


    accepted_source_ids = {
        item[
            "source_id"
        ]
        for item
        in accepted_evidence
    }

    accepted_sources = [
        copy.deepcopy(
            item
        )
        for item
        in worker_result.get(
            "sources",
            []
        )
        if (
            item.get(
                "source_id"
            )
            in accepted_source_ids
        )
    ]


    verification_rows = {
        item["claim_id"]:
            item
        for item
        in verification_summary.get(
            "claim_results",
            []
        )
    }

    accepted_verification = []

    for claim_id in accepted_ids:

        row = verification_rows.get(
            claim_id
        )

        if not isinstance(
            row,
            dict,
        ):
            _fail(
                "accepted claim lacks "
                "verification result"
            )

        if (
            row.get(
                "runtime_verification_status"
            )
            != "verified"
        ):
            _fail(
                "accepted claim is not "
                "runtime verified"
            )

        if (
            row.get(
                "verification_eligible"
            )
            is not True
        ):
            _fail(
                "accepted claim is not "
                "verification eligible"
            )

        accepted_verification.append(
            copy.deepcopy(
                row
            )
        )


    included_claim_ids = {
        item[
            "claim_id"
        ]
        for item
        in accepted_claims
    }

    if (
        included_claim_ids
        != set(
            accepted_ids
        )
    ):
        _fail(
            "SynthesisInput claim "
            "partition mismatch"
        )


    evidence_claim_ids = {
        item[
            "claim_id"
        ]
        for item
        in accepted_evidence
    }

    if not (
        evidence_claim_ids
        <= included_claim_ids
    ):
        _fail(
            "rejected claim evidence "
            "entered SynthesisInput"
        )


    source_ids = {
        item[
            "source_id"
        ]
        for item
        in accepted_sources
    }

    if (
        source_ids
        != accepted_source_ids
    ):
        _fail(
            "SynthesisInput source "
            "resolution mismatch"
        )


    return {
        "version":
            SYNTHESIS_INPUT_VERSION,

        "mission_id":
            mission_id,

        "worker_id":
            worker_id,

        "accepted_claim_ids":
            list(
                accepted_ids
            ),

        "claims":
            accepted_claims,

        "evidence":
            accepted_evidence,

        "sources":
            accepted_sources,

        "verification":
            accepted_verification,

        "gate": {
            "gate_id":
                acceptance_gate.get(
                    "gate_id"
                ),

            "decision":
                decision,

            "rationale":
                acceptance_gate.get(
                    "rationale"
                ),
        },
    }
