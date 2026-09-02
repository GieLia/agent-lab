import asyncio
import json

from pathlib import Path


from app.graph_v4 import (
    ResearchGraphContractError,
    ResearchGraphNodes,
    build_graph,
    build_initial_state,
    route_after_acceptance,
    route_after_critic,
    route_after_integrity,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def reject(
    fn,
    label,
):

    try:
        fn()

    except ResearchGraphContractError:
        print(
            f"{label}_OK"
        )

    else:
        raise AssertionError(
            f"{label} was accepted"
        )


def check_initial_state():

    state = build_initial_state(
        topic=
            "Research a test subject",

        run_id=
            "run-e5-test",

        mission_id=
            "mission-e5-test",

        max_iterations=2,
    )

    assert (
        state["iteration"]
        == 0
    )

    assert (
        state["max_iterations"]
        == 2
    )

    assert (
        state["retry_required"]
        is False
    )

    assert (
        state[
            "semantic_records"
        ]
        == []
    )

    json.dumps(
        state
    )

    print(
        "GRAPH_V4_INITIAL_STATE_OK"
    )

    print(
        "GRAPH_V4_JSON_SERIALIZABLE_STATE_OK"
    )


def check_routing():

    assert (
        route_after_integrity(
            {
                "structural_integrity":
                    "pass"
            }
        )
        == "semantic_verification"
    )

    assert (
        route_after_integrity(
            {
                "structural_integrity":
                    "fail"
            }
        )
        == "critic"
    )

    reject(
        lambda:
            route_after_integrity(
                {
                    "structural_integrity":
                        "unknown"
                }
            ),
        "INVALID_INTEGRITY_STATE_REJECTED",
    )


    retry_state = {
        "iteration":
            1,

        "max_iterations":
            2,

        "retry_required":
            True,

        "retry_claim_ids": [
            "claim-1",
        ],

        "retry_topic":
            (
                "Find direct evidence "
                "for claim-1."
            ),
    }

    assert (
        route_after_critic(
            retry_state
        )
        == "research"
    )


    exhausted = dict(
        retry_state
    )

    exhausted[
        "iteration"
    ] = 2

    assert (
        route_after_critic(
            exhausted
        )
        == "acceptance_gate"
    )


    no_retry = dict(
        retry_state
    )

    no_retry[
        "retry_required"
    ] = False

    assert (
        route_after_critic(
            no_retry
        )
        == "acceptance_gate"
    )


    invalid_retry = dict(
        retry_state
    )

    invalid_retry[
        "retry_claim_ids"
    ] = []

    reject(
        lambda:
            route_after_critic(
                invalid_retry
            ),
        "EMPTY_RETRY_TARGET_REJECTED",
    )


    assert (
        route_after_acceptance(
            {
                "acceptance_gate": {
                    "decision":
                        "accepted",

                    "accepted_claim_ids": [
                        "claim-1"
                    ],
                }
            }
        )
        == "synthesis_input"
    )

    assert (
        route_after_acceptance(
            {
                "acceptance_gate": {
                    "decision":
                        "partial",

                    "accepted_claim_ids": [
                        "claim-1"
                    ],
                }
            }
        )
        == "synthesis_input"
    )

    assert (
        route_after_acceptance(
            {
                "acceptance_gate": {
                    "decision":
                        "rejected",

                    "accepted_claim_ids":
                        [],
                }
            }
        )
        == "end"
    )

    reject(
        lambda:
            route_after_acceptance(
                {
                    "acceptance_gate": {
                        "decision":
                            "accepted",

                        "accepted_claim_ids":
                            [],
                    }
                }
            ),
        "EMPTY_ACCEPTED_GATE_REJECTED",
    )

    print(
        "GRAPH_V4_FAIL_CLOSED_ROUTING_OK"
    )

    print(
        "GRAPH_V4_RETRY_BUDGET_ROUTING_OK"
    )

    print(
        "GRAPH_V4_REJECTED_GATE_ROUTING_OK"
    )


async def check_accepted_graph():

    events = []

    async def research(
        state,
    ):

        iteration = (
            state.get(
                "iteration",
                0,
            )
            + 1
        )

        events.append(
            "research"
        )

        return {
            "iteration":
                iteration,

            "research_result": {
                "worker_id":
                    "worker-test",
            },

            "status":
                "researched",
        }


    async def integrity(
        state,
    ):

        events.append(
            "evidence_integrity"
        )

        assert (
            state[
                "research_result"
            ][
                "worker_id"
            ]
            == "worker-test"
        )

        return {
            "structural_integrity":
                "pass",

            "structural_errors":
                [],

            "status":
                "integrity_checked",
        }


    async def semantic(
        state,
    ):

        events.append(
            "semantic_verification"
        )

        return {
            "semantic_records": [
                {
                    "claim_id":
                        "claim-1",

                    "evidence_id":
                        "ev-1",
                }
            ],

            "status":
                "semantically_evaluated",
        }


    async def runtime_verification(
        state,
    ):

        events.append(
            "runtime_verification"
        )

        return {
            "verification_summary": {
                "verified_claim_ids": [
                    "claim-1"
                ],
            },

            "verified_claim_ids": [
                "claim-1"
            ],

            "rejected_claim_ids":
                [],

            "status":
                "verified",
        }


    async def critic(
        state,
    ):

        events.append(
            "critic"
        )

        assert (
            state[
                "verified_claim_ids"
            ]
            == [
                "claim-1"
            ]
        )

        return {
            "critic_result": {
                "finding":
                    "no retry required"
            },

            "retry_required":
                False,

            "retry_claim_ids":
                [],

            "status":
                "critic_complete",
        }


    async def gate(
        state,
    ):

        events.append(
            "acceptance_gate"
        )

        return {
            "acceptance_gate": {
                "decision":
                    "accepted",

                "accepted_claim_ids": [
                    "claim-1"
                ],

                "rejected_claim_ids":
                    [],
            },

            "status":
                "accepted",
        }


    async def synthesis_input(
        state,
    ):

        events.append(
            "synthesis_input"
        )

        assert (
            state[
                "acceptance_gate"
            ][
                "accepted_claim_ids"
            ]
            == [
                "claim-1"
            ]
        )

        return {
            "synthesis_input": {
                "accepted_claim_ids": [
                    "claim-1"
                ],
            },

            "status":
                "synthesis_ready",
        }


    async def synthesis(
        state,
    ):

        events.append(
            "synthesis"
        )

        assert (
            state[
                "synthesis_input"
            ][
                "accepted_claim_ids"
            ]
            == [
                "claim-1"
            ]
        )

        return {
            "final_result":
                "Verified result.",

            "status":
                "finished",
        }


    graph = build_graph(
        nodes=ResearchGraphNodes(
            research=
                research,

            evidence_integrity=
                integrity,

            semantic_verification=
                semantic,

            runtime_verification=
                runtime_verification,

            critic=
                critic,

            acceptance_gate=
                gate,

            synthesis_input=
                synthesis_input,

            synthesis=
                synthesis,
        )
    )

    result = await graph.ainvoke(
        build_initial_state(
            topic=
                "Accepted path",

            run_id=
                "run-accepted",

            max_iterations=2,
        )
    )

    assert events == [
        "research",
        "evidence_integrity",
        "semantic_verification",
        "runtime_verification",
        "critic",
        "acceptance_gate",
        "synthesis_input",
        "synthesis",
    ]

    assert (
        result[
            "final_result"
        ]
        == "Verified result."
    )

    assert (
        result[
            "status"
        ]
        == "finished"
    )

    print(
        "GRAPH_V4_ACCEPTED_PATH_OK"
    )


async def check_rejected_graph():

    events = []

    async def research(
        state,
    ):

        events.append(
            "research"
        )

        return {
            "iteration":
                1,

            "research_result": {
                "worker_id":
                    "worker-rejected",
            },

            "status":
                "researched",
        }


    async def integrity(
        state,
    ):

        events.append(
            "evidence_integrity"
        )

        return {
            "structural_integrity":
                "pass",

            "structural_errors":
                [],
        }


    async def semantic(
        state,
    ):

        events.append(
            "semantic_verification"
        )

        return {
            "semantic_records":
                [],
        }


    async def runtime_verification(
        state,
    ):

        events.append(
            "runtime_verification"
        )

        return {
            "verification_summary": {
                "verified_claim_ids":
                    [],
            },

            "verified_claim_ids":
                [],

            "rejected_claim_ids": [
                "claim-rejected"
            ],
        }


    async def critic(
        state,
    ):

        events.append(
            "critic"
        )

        return {
            "retry_required":
                False,

            "retry_claim_ids":
                [],
        }


    async def gate(
        state,
    ):

        events.append(
            "acceptance_gate"
        )

        return {
            "acceptance_gate": {
                "decision":
                    "rejected",

                "accepted_claim_ids":
                    [],

                "rejected_claim_ids": [
                    "claim-rejected"
                ],
            },

            "status":
                "rejected",
        }


    async def must_not_run(
        state,
    ):

        raise AssertionError(
            "Rejected material reached "
            "synthesis boundary"
        )


    graph = build_graph(
        nodes=ResearchGraphNodes(
            research=
                research,

            evidence_integrity=
                integrity,

            semantic_verification=
                semantic,

            runtime_verification=
                runtime_verification,

            critic=
                critic,

            acceptance_gate=
                gate,

            synthesis_input=
                must_not_run,

            synthesis=
                must_not_run,
        )
    )

    result = await graph.ainvoke(
        build_initial_state(
            topic=
                "Rejected path",

            run_id=
                "run-rejected",

            max_iterations=1,
        )
    )

    assert events == [
        "research",
        "evidence_integrity",
        "semantic_verification",
        "runtime_verification",
        "critic",
        "acceptance_gate",
    ]

    assert (
        "final_result"
        not in result
    )

    assert (
        result[
            "acceptance_gate"
        ][
            "decision"
        ]
        == "rejected"
    )

    print(
        "GRAPH_V4_REJECTED_MATERIAL_BLOCKED_OK"
    )


def check_dependency_boundary():

    source = (
        ROOT
        / "app"
        / "graph_v4.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "run_claude",
        "run_codex",
        "run_research_tool_loop",
        "execute_tool",
        "AsyncSqliteSaver",
        "AsyncPostgresSaver",
    )

    for token in forbidden:
        assert (
            token
            not in source
        ), token

    print(
        "GRAPH_V4_DEPENDENCY_INJECTION_OK"
    )

    print(
        "GRAPH_V4_NO_MODEL_OR_TOOL_COUPLING_OK"
    )

    print(
        "GRAPH_V4_CHECKPOINTER_NEUTRAL_OK"
    )


def main():

    check_initial_state()
    check_routing()
    check_dependency_boundary()

    asyncio.run(
        check_accepted_graph()
    )

    asyncio.run(
        check_rejected_graph()
    )

    print()
    print(
        "RESEARCH_GRAPH_V1_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
