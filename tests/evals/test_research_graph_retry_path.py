import asyncio

from pathlib import Path


from app.graph_v4 import (
    ResearchGraphNodes,
    build_graph,
    build_initial_state,
)

from app.research.graph_nodes import (
    GraphNodeDependencies,
    build_acceptance_gate_node,
    build_critic_node,
    build_research_node,
    build_semantic_verification_node,
    evidence_integrity_node,
    runtime_verification_node,
    synthesis_input_node,
)

from app.research.tool_loop import (
    ResearchLoopResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def semantic_result(
    entailment,
):

    if entailment == "full":

        return {
            "entailment":
                "full",

            "claim_atomicity":
                "atomic",

            "support_sufficiency":
                "sufficient",

            "unsupported_clauses":
                [],

            "contradicted_clauses":
                [],

            "untrusted_instruction_detected":
                False,

            "confidence":
                0.95,

            "rationale":
                "Fully supported.",
        }


    if entailment == "partial":

        return {
            "entailment":
                "partial",

            "claim_atomicity":
                "atomic",

            "support_sufficiency":
                "insufficient",

            "unsupported_clauses": [
                "exact CPU count"
            ],

            "contradicted_clauses":
                [],

            "untrusted_instruction_detected":
                False,

            "confidence":
                0.85,

            "rationale":
                "CPU count is not established.",
        }


    raise AssertionError(
        entailment
    )


def initial_worker_result():

    return {
        "worker_id":
            "research-graph-v1-researcher",

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
                    "claim-stable",

                "text":
                    "API listens on port 8000.",

                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-target",

                "text":
                    "VM has four CPUs.",

                "claim_type":
                    "fact",
            },
        ],

        "sources": [
            {
                "source_id":
                    "source-001",

                "source_type":
                    "internal",

                "title":
                    "Initial configuration",
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-stable",

                "claim_id":
                    "claim-stable",

                "source_id":
                    "source-001",

                "relationship":
                    "supports",

                "excerpt":
                    "API listens on port 8000.",
            },
            {
                "evidence_id":
                    "ev-target",

                "claim_id":
                    "claim-target",

                "source_id":
                    "source-001",

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


def retry_worker_result():

    return {
        "worker_id":
            "research-graph-v1-researcher",

        "role":
            "researcher",

        "provider":
            "claude",

        "account":
            "primary",

        "model":
            None,

        "status":
            "success",

        "claims": [
            {
                "claim_id":
                    "claim-target",

                "text":
                    "VM has four CPUs.",

                "claim_type":
                    "fact",
            }
        ],

        "sources": [
            {
                "source_id":
                    "source-001",

                "source_type":
                    "internal",

                "title":
                    "Targeted retry source",
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-retry",

                "claim_id":
                    "claim-target",

                "source_id":
                    "source-001",

                "relationship":
                    "supports",

                "excerpt":
                    "VM has four CPUs.",
            }
        ],

        "gaps":
            [],

        "notes":
            None,
    }


async def main_async():

    research_topics = []
    semantic_ids = []
    critic_calls = []


    async def fake_research_runner(
        topic,
        **kwargs,
    ):

        research_topics.append(
            topic
        )

        if len(
            research_topics
        ) == 1:

            worker = (
                initial_worker_result()
            )

        elif len(
            research_topics
        ) == 2:

            worker = (
                retry_worker_result()
            )

        else:
            raise AssertionError(
                "unexpected third "
                "research cycle"
            )


        return ResearchLoopResult(
            worker_result=
                worker,

            steps=2,
            model_calls=2,
            search_calls=1,
            fetch_calls=1,
            sources_retrieved=1,
        )


    async def fake_semantic_runner(
        *,
        claim,
        evidence,
        source,
        cwd,
        account,
        timeout,
    ):

        evidence_id = evidence[
            "evidence_id"
        ]

        semantic_ids.append(
            evidence_id
        )


        if (
            evidence_id
            == "ev-target"
        ):

            entailment = "partial"

        else:

            entailment = "full"


        return (
            semantic_result(
                entailment
            ),
            object(),
        )


    dependencies = (
        GraphNodeDependencies(
            cwd=ROOT,

            research_account=
                "primary",

            semantic_account=
                "secondary",

            research_runner=
                fake_research_runner,

            semantic_runner=
                fake_semantic_runner,
        )
    )


    async def fake_critic_runner(
        **kwargs,
    ):

        critic_calls.append(
            kwargs
        )


        if len(
            critic_calls
        ) == 1:

            assert (
                kwargs[
                    "rejected_claim_ids"
                ]
                == [
                    "claim-target"
                ]
            )

            assert (
                kwargs[
                    "candidate_retry_claim_ids"
                ]
                == [
                    "claim-target"
                ]
            )

            return {
                "retry_required":
                    True,

                "retry_claim_ids": [
                    "claim-target"
                ],

                "missing_evidence": [
                    (
                        "Direct evidence for "
                        "the exact CPU count."
                    )
                ],

                "retry_topic":
                    (
                        "Find direct evidence "
                        "that the VM has "
                        "four CPUs."
                    ),

                "critique":
                    (
                        "claim-target is "
                        "only partially supported."
                    ),
            }


        if len(
            critic_calls
        ) == 2:

            assert (
                kwargs[
                    "rejected_claim_ids"
                ]
                == []
            )

            assert (
                kwargs[
                    "candidate_retry_claim_ids"
                ]
                == []
            )

            return {
                "retry_required":
                    False,

                "retry_claim_ids":
                    [],

                "missing_evidence":
                    [],

                "retry_topic":
                    None,

                "critique":
                    (
                        "All factual claims "
                        "are now verified."
                    ),
            }


        raise AssertionError(
            "unexpected critic call"
        )


    async def synthesis(
        state,
    ):

        value = state[
            "synthesis_input"
        ]

        assert (
            value[
                "accepted_claim_ids"
            ]
            == [
                "claim-stable",
                "claim-target",
            ]
        )

        assert {
            item[
                "claim_id"
            ]
            for item
            in value[
                "claims"
            ]
        } == {
            "claim-stable",
            "claim-target",
        }

        return {
            "final_result":
                "Retry graph completed.",

            "status":
                "finished",
        }


    graph = build_graph(
        nodes=ResearchGraphNodes(
            research=
                build_research_node(
                    dependencies
                ),

            evidence_integrity=
                evidence_integrity_node,

            semantic_verification=
                build_semantic_verification_node(
                    dependencies
                ),

            runtime_verification=
                runtime_verification_node,

            critic=
                build_critic_node(
                    critic_runner=
                        fake_critic_runner
                ),

            acceptance_gate=
                build_acceptance_gate_node(
                    dependencies
                ),

            synthesis_input=
                synthesis_input_node,

            synthesis=
                synthesis,
        )
    )


    result = await graph.ainvoke(
        build_initial_state(
            topic=
                "Research retry path",

            run_id=
                "run-e5-d2",

            mission_id=
                "mission-e5-d2",

            max_iterations=2,
        )
    )


    assert (
        result[
            "iteration"
        ]
        == 2
    )

    assert (
        result[
            "final_result"
        ]
        == "Retry graph completed."
    )


    assert research_topics == [
        "Research retry path",
        (
            "Find direct evidence "
            "that the VM has "
            "four CPUs."
        ),
    ]


    assert semantic_ids == [
        "ev-stable",
        "ev-target",
        "ev-stable",
        "ev-target",
        "retry-2-ev-retry",
    ]


    assert len(
        critic_calls
    ) == 2


    assert (
        result[
            "verified_claim_ids"
        ]
        == [
            "claim-stable",
            "claim-target",
        ]
    )

    assert (
        result[
            "rejected_claim_ids"
        ]
        == []
    )


    assert (
        "retry-2-source-001"
        in {
            item[
                "source_id"
            ]
            for item
            in result[
                "research_result"
            ][
                "sources"
            ]
        }
    )


    assert (
        "retry-2-ev-retry"
        in {
            item[
                "evidence_id"
            ]
            for item
            in result[
                "research_result"
            ][
                "evidence"
            ]
        }
    )


    print(
        "GRAPH_V4_TARGETED_RETRY_ROUTING_OK"
    )

    print(
        "GRAPH_V4_RETRY_SCOPE_AUTHORIZATION_OK"
    )

    print(
        "GRAPH_V4_RETRY_MERGE_OK"
    )

    print(
        "GRAPH_V4_FULL_REVERIFICATION_AFTER_RETRY_OK"
    )

    print(
        "GRAPH_V4_RETRY_TO_VERIFIED_OK"
    )

    print(
        "GRAPH_V4_RETRY_TO_GATED_SYNTHESIS_OK"
    )

    print()
    print(
        "RESEARCH_GRAPH_RETRY_PATH_V1_OK"
    )


def main():

    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()
