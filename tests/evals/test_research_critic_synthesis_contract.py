import asyncio

from copy import deepcopy


from app.research.critic_contract import (
    CriticContractError,
    validate_critic_result,
)

from app.research.graph_nodes import (
    build_critic_node,
    synthesis_input_node,
)

from app.research.synthesis_input import (
    SynthesisInputError,
    build_synthesis_input,
)

from app.research.acceptance import (
    build_acceptance_gate,
)

from app.research.verification import (
    build_verification_summary,
)

from tests.evals.test_research_verification_policy import (
    evaluation,
)


def worker_result():

    return {
        "worker_id":
            "worker-c4",

        "role":
            "researcher",

        "provider":
            "claude",

        "account":
            "primary",

        "model":
            None,

        "status":
            "partial",

        "claims": [
            {
                "claim_id":
                    "claim-good",

                "text":
                    "API listens on port 8000.",

                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-bad",

                "text":
                    "VM has four CPUs.",

                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-recommend",

                "text":
                    "Prefer PostgreSQL.",

                "claim_type":
                    "recommendation",
            },
        ],

        "sources": [
            {
                "source_id":
                    "source-good",

                "source_type":
                    "internal",

                "title":
                    "API configuration",
            },
            {
                "source_id":
                    "source-bad",

                "source_type":
                    "internal",

                "title":
                    "VM configuration",
            },
            {
                "source_id":
                    "source-unused",

                "source_type":
                    "internal",

                "title":
                    "Unrelated source",
            },
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-good",

                "claim_id":
                    "claim-good",

                "source_id":
                    "source-good",

                "relationship":
                    "supports",

                "excerpt":
                    "API listens on port 8000.",
            },
            {
                "evidence_id":
                    "ev-bad",

                "claim_id":
                    "claim-bad",

                "source_id":
                    "source-bad",

                "relationship":
                    "supports",

                "excerpt":
                    "VM has CPUs.",
            },
        ],

        "gaps": [
            "Exact CPU count missing."
        ],

        "notes":
            None,
    }


def semantic_records():

    return [
        {
            "claim_id":
                "claim-good",

            "evidence_id":
                "ev-good",

            "evaluation":
                evaluation(
                    "full"
                ),
        },
        {
            "claim_id":
                "claim-bad",

            "evidence_id":
                "ev-bad",

            "evaluation":
                evaluation(
                    "partial"
                ),
        },
    ]


def runtime_objects():

    worker = worker_result()

    verification = (
        build_verification_summary(
            worker,
            semantic_records(),
        )
    )

    gate = build_acceptance_gate(
        mission_id=
            "mission-c4",

        worker_result=
            worker,

        verification_summary=
            verification,

        gate_id=
            "gate-c4",

        created_at=
            "2026-09-02T20:00:00+00:00",
    )

    return (
        worker,
        verification,
        gate,
    )


def reject_critic(
    value,
    label,
):

    try:
        validate_critic_result(
            value,

            candidate_retry_claim_ids=[
                "claim-bad",
                "claim-recommend",
            ],

            structural_integrity=
                "pass",
        )

    except CriticContractError:
        print(
            f"{label}_OK"
        )

    else:
        raise AssertionError(
            f"{label} was accepted"
        )


def check_critic_contract():

    valid = {
        "retry_required":
            True,

        "retry_claim_ids": [
            "claim-bad",
        ],

        "missing_evidence": [
            "Direct evidence for CPU count."
        ],

        "retry_topic":
            (
                "Find authoritative evidence "
                "for the exact CPU count."
            ),

        "critique":
            (
                "claim-bad is only "
                "partially supported."
            ),
    }

    result = validate_critic_result(
        valid,

        candidate_retry_claim_ids=[
            "claim-bad",
            "claim-recommend",
        ],

        structural_integrity=
            "pass",
    )

    assert (
        result[
            "retry_required"
        ]
        is True
    )

    print(
        "CRITIC_RETRY_PLAN_CONTRACT_OK"
    )


    escalation = deepcopy(
        valid
    )

    escalation[
        "retry_claim_ids"
    ] = [
        "claim-good"
    ]

    reject_critic(
        escalation,
        "CRITIC_ACCEPTED_CLAIM_RETRY_REJECTED",
    )


    malformed = deepcopy(
        valid
    )

    malformed[
        "retry_topic"
    ] = None

    reject_critic(
        malformed,
        "CRITIC_EMPTY_RETRY_TOPIC_REJECTED",
    )


    structural = {
        "retry_required":
            False,

        "retry_claim_ids":
            [],

        "missing_evidence": [
            "WorkerResult failed canonical validation."
        ],

        "retry_topic":
            None,

        "critique":
            "Terminal structural rejection.",
    }

    result = validate_critic_result(
        structural,

        candidate_retry_claim_ids=
            [],

        structural_integrity=
            "fail",
    )

    assert (
        result[
            "retry_required"
        ]
        is False
    )

    print(
        "CRITIC_STRUCTURAL_FAILURE_TERMINAL_OK"
    )


def check_synthesis_partition():

    (
        worker,
        verification,
        gate,
    ) = runtime_objects()

    value = build_synthesis_input(
        mission_id=
            "mission-c4",

        worker_result=
            worker,

        verification_summary=
            verification,

        acceptance_gate=
            gate,
    )


    assert (
        value[
            "accepted_claim_ids"
        ]
        == [
            "claim-good"
        ]
    )

    assert [
        item["claim_id"]
        for item
        in value[
            "claims"
        ]
    ] == [
        "claim-good"
    ]

    assert [
        item["evidence_id"]
        for item
        in value[
            "evidence"
        ]
    ] == [
        "ev-good"
    ]

    assert [
        item["source_id"]
        for item
        in value[
            "sources"
        ]
    ] == [
        "source-good"
    ]


    serialized = str(
        value
    )

    assert (
        "claim-bad"
        not in serialized
    )

    assert (
        "ev-bad"
        not in serialized
    )

    assert (
        "source-bad"
        not in serialized
    )

    assert (
        "claim-recommend"
        not in serialized
    )

    assert (
        "source-unused"
        not in serialized
    )


    assert (
        value[
            "verification"
        ][0][
            "runtime_verification_status"
        ]
        == "verified"
    )

    print(
        "SYNTHESIS_INPUT_ACCEPTED_CLAIMS_ONLY_OK"
    )

    print(
        "SYNTHESIS_INPUT_REJECTED_MATERIAL_REMOVED_OK"
    )

    print(
        "SYNTHESIS_INPUT_UNUSED_SOURCES_REMOVED_OK"
    )

    print(
        "SYNTHESIS_INPUT_RUNTIME_VERIFICATION_ONLY_OK"
    )


    broken_gate = deepcopy(
        gate
    )

    broken_gate[
        "accepted_claim_ids"
    ] = [
        "claim-bad"
    ]

    try:

        build_synthesis_input(
            mission_id=
                "mission-c4",

            worker_result=
                worker,

            verification_summary=
                verification,

            acceptance_gate=
                broken_gate,
        )

    except SynthesisInputError:
        print(
            "SYNTHESIS_UNVERIFIED_CLAIM_BLOCKED_OK"
        )

    else:
        raise AssertionError(
            "unverified claim entered "
            "SynthesisInput"
        )


async def check_graph_node_adapters():

    (
        worker,
        verification,
        gate,
    ) = runtime_objects()


    async def fake_critic_runner(
        **kwargs,
    ):

        assert (
            kwargs[
                "rejected_claim_ids"
            ]
            == [
                "claim-bad",
                "claim-recommend",
            ]
        )

        return {
            "retry_required":
                False,

            "retry_claim_ids":
                [],

            "missing_evidence": [
                "CPU count remains unresolved."
            ],

            "retry_topic":
                None,

            "critique":
                "Stop without retry for C4.",
        }


    critic_node = build_critic_node(
        critic_runner=
            fake_critic_runner
    )


    state = {
        "topic":
            "C4 contract",

        "mission_id":
            "mission-c4",

        "structural_integrity":
            "pass",

        "structural_errors":
            [],

        "research_result":
            worker,

        "verification_summary":
            verification,

        "verified_claim_ids":
            [
                "claim-good"
            ],

        "rejected_claim_ids": [
            "claim-bad",
            "claim-recommend",
        ],
    }


    state.update(
        await critic_node(
            state
        )
    )

    assert (
        state[
            "retry_required"
        ]
        is False
    )

    print(
        "GRAPH_NODE_CRITIC_BOUNDARY_OK"
    )


    state[
        "acceptance_gate"
    ] = gate

    state.update(
        await synthesis_input_node(
            state
        )
    )

    assert [
        item["claim_id"]
        for item
        in state[
            "synthesis_input"
        ][
            "claims"
        ]
    ] == [
        "claim-good"
    ]

    print(
        "GRAPH_NODE_SYNTHESIS_INPUT_BOUNDARY_OK"
    )


def main():

    check_critic_contract()
    check_synthesis_partition()

    asyncio.run(
        check_graph_node_adapters()
    )

    print()
    print(
        "RESEARCH_CRITIC_SYNTHESIS_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
