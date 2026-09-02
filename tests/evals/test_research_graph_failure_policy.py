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


def failed_worker_result():

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
            "failed",

        "claims":
            [],

        "sources":
            [],

        "evidence":
            [],

        "gaps": [
            "External search runtime was unavailable."
        ],

        "notes":
            "No source could be retrieved.",
    }


async def main_async():

    critic_model_calls = []
    semantic_model_calls = []
    synthesis_calls = []


    async def fake_research(
        topic,
        **kwargs,
    ):

        return ResearchLoopResult(
            worker_result=
                failed_worker_result(),

            steps=1,
            model_calls=1,
            search_calls=1,
            fetch_calls=0,
            sources_retrieved=0,
        )


    async def semantic_must_not_run(
        **kwargs,
    ):

        semantic_model_calls.append(
            True
        )

        raise AssertionError(
            "failed worker caused semantic model call"
        )


    async def critic_must_not_run(
        **kwargs,
    ):

        critic_model_calls.append(
            True
        )

        raise AssertionError(
            "failed worker caused model Critic call"
        )


    async def synthesis_must_not_run(
        state,
    ):

        synthesis_calls.append(
            True
        )

        raise AssertionError(
            "rejected worker reached synthesis"
        )


    dependencies = GraphNodeDependencies(
        cwd=ROOT,
        research_runner=
            fake_research,
        semantic_runner=
            semantic_must_not_run,
    )


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
                        critic_must_not_run
                ),

            acceptance_gate=
                build_acceptance_gate_node(
                    dependencies
                ),

            synthesis_input=
                synthesis_input_node,

            synthesis=
                synthesis_must_not_run,
        )
    )


    result = await graph.ainvoke(
        build_initial_state(
            topic=
                "Failed research contract",

            run_id=
                "run-failed-research",

            mission_id=
                "mission-failed-research",

            max_iterations=2,
        )
    )


    assert (
        result[
            "research_result"
        ][
            "status"
        ]
        == "failed"
    )

    assert (
        result[
            "structural_integrity"
        ]
        == "pass"
    )

    assert (
        result[
            "semantic_records"
        ]
        == []
    )

    assert critic_model_calls == []
    assert semantic_model_calls == []
    assert synthesis_calls == []


    assert (
        result[
            "critic_result"
        ][
            "retry_required"
        ]
        is False
    )


    gate = result[
        "acceptance_gate"
    ]

    assert (
        gate[
            "decision"
        ]
        == "rejected"
    )

    assert (
        gate[
            "accepted_claim_ids"
        ]
        == []
    )

    assert (
        gate[
            "rejected_worker_ids"
        ]
        == [
            "research-graph-v1-researcher"
        ]
    )

    assert (
        result[
            "status"
        ]
        == "rejected"
    )

    assert (
        "final_result"
        not in result
    )


    print(
        "FAILED_WORKER_STRUCTURALLY_VALID_OK"
    )

    print(
        "FAILED_WORKER_MODEL_CRITIC_BYPASSED_OK"
    )

    print(
        "FAILED_WORKER_RUNTIME_REJECTED_OK"
    )

    print(
        "FAILED_WORKER_SYNTHESIS_BLOCKED_OK"
    )

    print()
    print(
        "RESEARCH_GRAPH_FAILURE_POLICY_V1_OK"
    )


def main():

    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()
