from app.research.acceptance import (
    AcceptancePolicyError,
    build_acceptance_gate,
)

from tests.evals.test_research_verification_policy import (
    semantic_records,
    worker_result,
)

from app.research.verification import (
    build_verification_summary,
)


def main():

    worker = worker_result()

    verification = (
        build_verification_summary(
            worker,
            semantic_records(),
        )
    )

    gate = build_acceptance_gate(
        mission_id=
            "mission-e5-test",

        worker_result=
            worker,

        verification_summary=
            verification,

        gate_id=
            "gate-e5-test",

        created_at=
            "2026-09-02T20:00:00+00:00",
    )

    assert (
        gate[
            "decision"
        ]
        == "partial"
    )

    assert (
        gate[
            "accepted_claim_ids"
        ]
        == [
            "claim-full"
        ]
    )

    assert set(
        gate[
            "rejected_claim_ids"
        ]
    ) == {
        "claim-partial",
        "claim-contradicted",
        "claim-disputed",
        "claim-nonfact",
    }

    assert (
        gate[
            "accepted_worker_ids"
        ]
        == []
    )

    assert (
        gate[
            "rejected_worker_ids"
        ]
        == []
    )

    assert (
        gate[
            "decided_by"
        ][
            "actor_type"
        ]
        == "runtime"
    )

    assert (
        set(
            gate[
                "accepted_claim_ids"
            ]
        )
        .isdisjoint(
            gate[
                "rejected_claim_ids"
            ]
        )
    )

    print(
        "ACCEPTANCE_GATE_CLAIM_PARTITION_OK"
    )

    print(
        "ACCEPTANCE_GATE_FULL_ONLY_OK"
    )

    print(
        "ACCEPTANCE_GATE_RUNTIME_AUTHORITY_OK"
    )


    broken = dict(
        verification
    )

    broken[
        "worker_id"
    ] = "other-worker"

    try:
        build_acceptance_gate(
            mission_id=
                "mission-e5-test",

            worker_result=
                worker,

            verification_summary=
                broken,
        )

    except AcceptancePolicyError:
        print(
            "ACCEPTANCE_WORKER_MISMATCH_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "worker mismatch accepted"
        )


    zero_verification = dict(
        verification
    )

    zero_verification[
        "verified_claim_ids"
    ] = []

    rejected_gate = (
        build_acceptance_gate(
            mission_id=
                "mission-rejected",

            worker_result=
                worker,

            verification_summary=
                zero_verification,

            gate_id=
                "gate-rejected",

            created_at=
                "2026-09-02T20:00:00+00:00",
        )
    )

    assert (
        rejected_gate[
            "decision"
        ]
        == "rejected"
    )

    assert (
        rejected_gate[
            "accepted_claim_ids"
        ]
        == []
    )

    assert len(
        rejected_gate[
            "rejected_claim_ids"
        ]
    ) == len(
        worker[
            "claims"
        ]
    )

    print(
        "ACCEPTANCE_EMPTY_VERIFIED_SET_REJECTED_OK"
    )

    print()
    print(
        "RESEARCH_ACCEPTANCE_GATE_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
