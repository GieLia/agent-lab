import asyncio

from copy import deepcopy
from pathlib import Path


from app.research.graph_nodes import (
    GraphNodeAdapterError,
    GraphNodeDependencies,
    build_acceptance_gate_node,
    build_research_node,
    build_semantic_verification_node,
    evidence_integrity_node,
    runtime_verification_node,
)

from app.research.tool_loop import (
    ResearchLoopResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def evaluation(
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
                "compound",

            "support_sufficiency":
                "insufficient",

            "unsupported_clauses": [
                "unsupported clause"
            ],

            "contradicted_clauses":
                [],

            "untrusted_instruction_detected":
                False,

            "confidence":
                0.85,

            "rationale":
                "Only partially supported.",
        }

    raise AssertionError(
        entailment
    )


def canonical_worker_result():

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
                    "claim-full",

                "text":
                    "API listens on port 8000.",

                "claim_type":
                    "fact",

                "verification_status":
                    "unverified",
            },
            {
                "claim_id":
                    "claim-partial",

                "text":
                    "VM has RAM and four CPUs.",

                "claim_type":
                    "fact",

                # Deliberately untrusted.
                "verification_status":
                    "verified",
            },
            {
                "claim_id":
                    "claim-recommendation",

                "text":
                    "Prefer PostgreSQL.",

                "claim_type":
                    "recommendation",
            },
        ],

        "sources": [
            {
                "source_id":
                    "source-1",

                "source_type":
                    "internal",

                "title":
                    "Runtime configuration",
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-full",

                "claim_id":
                    "claim-full",

                "source_id":
                    "source-1",

                "relationship":
                    "supports",

                "excerpt":
                    "API listens on port 8000.",
            },
            {
                "evidence_id":
                    "ev-partial",

                "claim_id":
                    "claim-partial",

                "source_id":
                    "source-1",

                "relationship":
                    "supports",

                "excerpt":
                    "VM has RAM.",
            },
        ],

        "gaps": [
            "CPU count evidence missing."
        ],

        "notes":
            None,
    }


async def check_core_adapter_path():

    research_calls = []
    semantic_calls = []


    async def fake_research_runner(
        topic,
        **kwargs,
    ):

        research_calls.append(
            {
                "topic":
                    topic,

                "kwargs":
                    kwargs,
            }
        )

        return ResearchLoopResult(
            worker_result=
                canonical_worker_result(),

            steps=4,
            model_calls=4,
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

        semantic_calls.append(
            {
                "claim_id":
                    claim[
                        "claim_id"
                    ],

                "evidence_id":
                    evidence[
                        "evidence_id"
                    ],

                "source_title":
                    source[
                        "title"
                    ],

                "cwd":
                    str(cwd),

                "account":
                    account,

                "timeout":
                    timeout,
            }
        )

        entailment = {
            "ev-full":
                "full",

            "ev-partial":
                "partial",
        }[
            evidence[
                "evidence_id"
            ]
        ]

        return (
            evaluation(
                entailment
            ),
            object(),
        )


    dependencies = (
        GraphNodeDependencies(
            cwd=ROOT,

            research_worker_id=
                "research-graph-v1-researcher",

            research_account=
                "primary",

            semantic_account=
                "secondary",

            semantic_timeout=120,

            research_runner=
                fake_research_runner,

            semantic_runner=
                fake_semantic_runner,
        )
    )


    state = {
        "topic":
            "Research the test system",

        "run_id":
            "run-e5-c3",

        "mission_id":
            "mission-e5-c3",

        "iteration":
            0,

        "max_iterations":
            2,

        "retry_required":
            False,

        "retry_claim_ids":
            [],

        "status":
            "starting",
    }


    research_node = (
        build_research_node(
            dependencies
        )
    )

    state.update(
        await research_node(
            state
        )
    )

    assert (
        state[
            "iteration"
        ]
        == 1
    )

    assert (
        state[
            "research_metrics"
        ]
        == {
            "steps": 4,
            "model_calls": 4,
            "search_calls": 1,
            "fetch_calls": 1,
            "sources_retrieved": 1,
        }
    )

    assert len(
        research_calls
    ) == 1

    print(
        "GRAPH_NODE_RESEARCH_ADAPTER_OK"
    )


    state.update(
        await evidence_integrity_node(
            state
        )
    )

    assert (
        state[
            "structural_integrity"
        ]
        == "pass"
    )

    print(
        "GRAPH_NODE_INTEGRITY_ADAPTER_OK"
    )


    semantic_node = (
        build_semantic_verification_node(
            dependencies
        )
    )

    state.update(
        await semantic_node(
            state
        )
    )

    assert len(
        state[
            "semantic_records"
        ]
    ) == 2

    assert len(
        semantic_calls
    ) == 2

    assert {
        item[
            "evidence_id"
        ]
        for item
        in semantic_calls
    } == {
        "ev-full",
        "ev-partial",
    }

    assert all(
        item[
            "source_title"
        ]
        == "Runtime configuration"
        for item
        in semantic_calls
    )

    assert all(
        item[
            "account"
        ]
        == "secondary"
        for item
        in semantic_calls
    )

    print(
        "GRAPH_NODE_PAIRWISE_SEMANTIC_ADAPTER_OK"
    )

    print(
        "GRAPH_NODE_NONFACT_SEMANTIC_SKIP_OK"
    )


    state.update(
        await runtime_verification_node(
            state
        )
    )

    assert (
        state[
            "verified_claim_ids"
        ]
        == [
            "claim-full"
        ]
    )

    assert set(
        state[
            "rejected_claim_ids"
        ]
    ) == {
        "claim-partial",
        "claim-recommendation",
    }

    rows = {
        item["claim_id"]:
            item
        for item
        in state[
            "verification_summary"
        ][
            "claim_results"
        ]
    }

    assert (
        rows[
            "claim-partial"
        ][
            "researcher_verification_status"
        ]
        == "verified"
    )

    assert (
        rows[
            "claim-partial"
        ][
            "runtime_verification_status"
        ]
        == "partially_verified"
    )

    print(
        "GRAPH_NODE_RUNTIME_AUTHORITY_OK"
    )


    gate_node = (
        build_acceptance_gate_node(
            dependencies
        )
    )

    state.update(
        await gate_node(
            state
        )
    )

    gate = state[
        "acceptance_gate"
    ]

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
        "claim-recommendation",
    }

    assert (
        gate[
            "decided_by"
        ][
            "actor_type"
        ]
        == "runtime"
    )

    print(
        "GRAPH_NODE_ACCEPTANCE_ADAPTER_OK"
    )

    print(
        "GRAPH_NODE_FULL_ONLY_END_TO_END_OK"
    )


async def check_structural_rejection():

    dependencies = (
        GraphNodeDependencies(
            cwd=ROOT
        )
    )

    invalid = (
        canonical_worker_result()
    )

    invalid = deepcopy(
        invalid
    )

    invalid[
        "role"
    ] = "critic"

    state = {
        "mission_id":
            "mission-invalid",

        "research_result":
            invalid,
    }

    state.update(
        await evidence_integrity_node(
            state
        )
    )

    assert (
        state[
            "structural_integrity"
        ]
        == "fail"
    )

    gate_node = (
        build_acceptance_gate_node(
            dependencies
        )
    )

    state.update(
        await gate_node(
            state
        )
    )

    gate = state[
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

    print(
        "STRUCTURALLY_INVALID_WORKER_REJECTED_OK"
    )

    print(
        "INVALID_WORKER_CANNOT_REACH_CLAIM_GATE_OK"
    )


async def check_retry_guard():

    calls = []


    async def forbidden_runner(
        *args,
        **kwargs,
    ):

        calls.append(
            True
        )

        raise AssertionError(
            "research runner must "
            "not execute"
        )


    dependencies = (
        GraphNodeDependencies(
            cwd=ROOT,

            research_runner=
                forbidden_runner,
        )
    )

    node = build_research_node(
        dependencies
    )

    state = {
        "topic":
            "Original topic",

        "run_id":
            "run-retry",

        "mission_id":
            "mission-retry",

        "iteration":
            1,

        "max_iterations":
            2,

        "retry_required":
            True,

        "retry_claim_ids": [
            "claim-1"
        ],

        "retry_topic":
            "Find better evidence.",
    }

    try:

        await node(
            state
        )

    except GraphNodeAdapterError as exc:

        assert (
            "WorkerResult merge"
            in str(exc)
        )

    else:
        raise AssertionError(
            "unsafe retry overwrite "
            "was accepted"
        )

    assert calls == []

    print(
        "TARGETED_RETRY_OVERWRITE_BLOCKED_OK"
    )


def main():

    asyncio.run(
        check_core_adapter_path()
    )

    asyncio.run(
        check_structural_rejection()
    )

    asyncio.run(
        check_retry_guard()
    )

    print()
    print(
        "RESEARCH_GRAPH_NODE_ADAPTERS_V1_OK"
    )


if __name__ == "__main__":
    main()
