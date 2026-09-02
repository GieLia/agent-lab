import asyncio
import json
import uuid

from pathlib import Path


from app.research.graph_measurement import (
    GraphMeasurementBridge,
)

from app.research.graph_nodes import (
    GraphNodeDependencies,
    build_research_node,
    build_semantic_verification_node,
)

from app.research.tool_loop import (
    ResearchLoopError,
    ResearchLoopLimits,
    ResearchLoopResult,
    run_research_tool_loop,
)

from app.workers.result import (
    WorkerExecutionResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def execution_result(
    text: str,
    account: str,
):

    return WorkerExecutionResult(
        text=text,
        provider="claude",
        account=account,
        model="test-model",
        request_id="request-test",
        session_id="session-test",
        status="success",
        duration_ms=10,
        input_tokens=10,
        output_tokens=5,
        cache_read_tokens=0,
        cache_write_tokens=0,
        reasoning_output_tokens=0,
        reported_cost_usd=None,
        cost_source=None,
        raw_metadata={},
    )


def worker_result():

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
                    "claim-1",

                "text":
                    "API listens on port 8000.",

                "claim_type":
                    "fact",
            }
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
                    "evidence-1",

                "claim_id":
                    "claim-1",

                "source_id":
                    "source-1",

                "relationship":
                    "supports",

                "excerpt":
                    "API listens on port 8000.",
            }
        ],

        "gaps":
            [],

        "notes":
            None,
    }


def semantic_evaluation():

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
            0.99,

        "rationale":
            "Fully supported.",
    }


class FakeWriter:

    def __init__(
        self,
    ):

        self.worker_calls = []
        self.tool_calls = []


    def record_worker_invocation(
        self,
        **kwargs,
    ):

        self.worker_calls.append(
            kwargs
        )

        return (
            "worker-inv-"
            + str(
                len(
                    self.worker_calls
                )
            )
        )


    def record_tool_invocation(
        self,
        **kwargs,
    ):

        self.tool_calls.append(
            kwargs
        )

        return (
            "tool-inv-"
            + str(
                len(
                    self.tool_calls
                )
            )
        )


async def check_tool_loop_observer():

    observed = []


    async def invalid_model_runner(
        prompt,
    ):

        return {}


    try:

        await run_research_tool_loop(
            "Observer contract",
            cwd=ROOT,

            limits=
                ResearchLoopLimits(
                    max_steps=1
                ),

            model_runner=
                invalid_model_runner,

            model_result_observer=
                observed.append,
        )

    except ResearchLoopError:
        pass

    else:
        raise AssertionError(
            "invalid one-step research "
            "unexpectedly succeeded"
        )


    assert len(
        observed
    ) == 1

    assert observed[0] == {}

    print(
        "RESEARCH_TOOL_LOOP_MODEL_OBSERVER_OK"
    )


async def check_graph_measurement():

    run_id = uuid.uuid4()

    writer = FakeWriter()

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=run_id,
    )


    async def fake_research_runner(
        topic,
        *,
        model_result_observer,
        measurement_writer,
        run_id,
        **kwargs,
    ):

        assert (
            measurement_writer
            is bridge
        )

        assert (
            run_id
            == bridge.run_id
        )

        assert (
            model_result_observer
            is not None
        )


        model_result_observer(
            execution_result(
                "research result",
                "primary",
            )
        )


        measurement_writer.record_tool_invocation(
            run_id=
                run_id,

            worker_invocation_id=
                None,

            capability=
                "web.search",

            tool_name=
                "web.search",

            tool_kind=
                "python",

            status=
                "success",

            tool_profile=
                "research-readonly",

            duration_ms=
                5,

            error_code=
                None,

            metadata={
                "test":
                    True,
            },
        )


        return ResearchLoopResult(
            worker_result=
                worker_result(),

            steps=2,
            model_calls=1,
            search_calls=1,
            fetch_calls=0,
            sources_retrieved=1,
        )


    async def fake_semantic_runner(
        **kwargs,
    ):

        return (
            semantic_evaluation(),

            execution_result(
                "semantic result",
                "secondary",
            ),
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

            measurement_bridge=
                bridge,
        )
    )


    state = {
        "topic":
            "Measurement contract",

        "run_id":
            str(
                run_id
            ),

        "mission_id":
            "mission-e5-e1",

        "iteration":
            0,

        "max_iterations":
            1,

        "retry_required":
            False,

        "retry_claim_ids":
            [],
    }


    state.update(
        await build_research_node(
            dependencies
        )(
            state
        )
    )


    assert len(
        writer.worker_calls
    ) == 1

    research_call = (
        writer.worker_calls[0]
    )

    assert (
        research_call[
            "role"
        ]
        == "researcher"
    )

    assert (
        research_call[
            "tool_profile"
        ]
        == "reasoning"
    )

    assert (
        research_call[
            "tools_exposed_count"
        ]
        == 0
    )


    assert len(
        writer.tool_calls
    ) == 1

    assert (
        writer.tool_calls[0][
            "worker_invocation_id"
        ]
        == "worker-inv-1"
    )

    assert (
        writer.tool_calls[0][
            "tool_profile"
        ]
        == "research-readonly"
    )

    print(
        "RESEARCHER_MODEL_TELEMETRY_OK"
    )

    print(
        "RESEARCH_TOOL_TO_MODEL_FK_OK"
    )


    state[
        "structural_integrity"
    ] = "pass"

    state.update(
        await (
            build_semantic_verification_node(
                dependencies
            )(
                state
            )
        )
    )


    assert len(
        writer.worker_calls
    ) == 2

    semantic_call = (
        writer.worker_calls[1]
    )

    assert (
        semantic_call[
            "role"
        ]
        == "evidence-verifier"
    )

    assert (
        semantic_call[
            "tool_profile"
        ]
        == "reasoning"
    )

    assert (
        semantic_call[
            "tools_exposed_count"
        ]
        == 0
    )


    summary = state[
        "measurement_summary"
    ]

    assert (
        summary[
            "worker_invocation_count"
        ]
        == 2
    )

    assert (
        summary[
            "research_worker_invocation_count"
        ]
        == 1
    )

    assert (
        summary[
            "semantic_worker_invocation_count"
        ]
        == 1
    )

    assert (
        summary[
            "tool_invocation_count"
        ]
        == 1
    )


    json.dumps(
        summary
    )

    json.dumps(
        state
    )


    print(
        "SEMANTIC_VERIFIER_TELEMETRY_OK"
    )

    print(
        "MEASUREMENT_SUMMARY_JSON_SAFE_OK"
    )

    print(
        "WORKER_EXECUTION_RESULT_NOT_CHECKPOINTED_OK"
    )


async def main_async():

    await check_tool_loop_observer()

    await check_graph_measurement()


def main():

    asyncio.run(
        main_async()
    )

    print()
    print(
        "RESEARCH_GRAPH_MEASUREMENT_V1_OK"
    )


if __name__ == "__main__":
    main()
