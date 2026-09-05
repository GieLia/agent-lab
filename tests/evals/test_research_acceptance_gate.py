import copy

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


    inconsistent_verified_set = (
        copy.deepcopy(
            verification
        )
    )

    inconsistent_verified_set[
        "verified_claim_ids"
    ] = []

    try:
        build_acceptance_gate(
            mission_id=
                "mission-inconsistent",

            worker_result=
                worker,

            verification_summary=
                inconsistent_verified_set,
        )

    except AcceptancePolicyError:
        print(
            "ACCEPTANCE_VERIFIED_SET_MISMATCH_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "inconsistent verified set accepted"
        )


    missing_claim_result = (
        copy.deepcopy(
            verification
        )
    )

    missing_claim_result[
        "claim_results"
    ] = (
        missing_claim_result[
            "claim_results"
        ][1:]
    )

    try:
        build_acceptance_gate(
            mission_id=
                "mission-missing-result",

            worker_result=
                worker,

            verification_summary=
                missing_claim_result,
        )

    except AcceptancePolicyError:
        print(
            "ACCEPTANCE_CLAIM_RESULT_COVERAGE_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "incomplete claim_results accepted"
        )


    no_full_evidence = (
        copy.deepcopy(
            verification
        )
    )

    for result in (
        no_full_evidence[
            "claim_results"
        ]
    ):
        if (
            result[
                "claim_id"
            ]
            == "claim-full"
        ):
            result[
                "full_evidence_ids"
            ] = []

    try:
        build_acceptance_gate(
            mission_id=
                "mission-no-full",

            worker_result=
                worker,

            verification_summary=
                no_full_evidence,
        )

    except AcceptancePolicyError:
        print(
            "ACCEPTANCE_VERIFIED_WITHOUT_FULL_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "verified claim without FULL "
            "evidence accepted"
        )


    zero_verification = (
        copy.deepcopy(
            verification
        )
    )

    zero_verification[
        "verified_claim_ids"
    ] = []

    for result in (
        zero_verification[
            "claim_results"
        ]
    ):
        if (
            result[
                "claim_id"
            ]
            == "claim-full"
        ):
            result[
                "runtime_verification_status"
            ] = "unverified"

            result[
                "verification_eligible"
            ] = False

            result[
                "full_evidence_ids"
            ] = []

    if (
        "claim-full"
        not in zero_verification[
            "unverified_claim_ids"
        ]
    ):
        zero_verification[
            "unverified_claim_ids"
        ].append(
            "claim-full"
        )

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
