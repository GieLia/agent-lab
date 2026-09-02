import asyncio
import json
import os
import tempfile
import uuid

from pathlib import Path


from app.research.graph_runner import (
    ResearchGraphRunnerError,
    run_research_graph,
)

from app.research.tool_loop import (
    ResearchLoopResult,
)

from app.workers.result import (
    WorkerExecutionResult,
)


FIXED_RUN_ID = uuid.UUID(
    "22222222-2222-4222-8222-222222222222"
)


def execution_result(
    payload,
    *,
    account,
):

    if isinstance(
        payload,
        dict,
    ):
        text = json.dumps(
            payload
        )
    else:
        text = str(
            payload
        )

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


class FakeWriter:

    def __init__(
        self,
    ):

        self.case_calls = []
        self.start_calls = []
        self.worker_calls = []
        self.tool_calls = []
        self.finish_calls = []


    def ensure_case(
        self,
        **kwargs,
    ):

        self.case_calls.append(
            kwargs
        )

        return True


    def start_run(
        self,
        **kwargs,
    ):

        self.start_calls.append(
            kwargs
        )

        return FIXED_RUN_ID


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


    def finish_run(
        self,
        **kwargs,
    ):

        self.finish_calls.append(
            kwargs
        )

        return True


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


def semantic_result():

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


async def check_missing_brave_preflight():

    previous = os.environ.pop(
        "BRAVE_SEARCH_API_KEY",
        None,
    )

    writer = FakeWriter()

    try:

        try:

            await run_research_graph(
                "Missing Brave credential.",
                writer=writer,
            )

        except ResearchGraphRunnerError as exc:

            assert (
                "BRAVE_SEARCH_API_KEY"
                in str(exc)
            )

        else:
            raise AssertionError(
                "missing Brave credential "
                "was accepted"
            )

        assert writer.case_calls == []
        assert writer.start_calls == []
        assert writer.worker_calls == []
        assert writer.tool_calls == []
        assert writer.finish_calls == []

    finally:

        if previous is not None:
            os.environ[
                "BRAVE_SEARCH_API_KEY"
            ] = previous


    print(
        "GRAPH_V4_MISSING_BRAVE_PRE_MODEL_REJECTED_OK"
    )


async def main_async():

    await check_missing_brave_preflight()

    writer = FakeWriter()


    async def fake_research_runner(
        topic,
        *,
        model_result_observer,
        measurement_writer,
        run_id,
        **kwargs,
    ):

        model_result_observer(
            execution_result(
                "research-action",
                account="primary",
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
                "contract_test":
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
            semantic_result(),

            execution_result(
                semantic_result(),
                account="secondary",
            ),
        )


    async def fake_critic_model(
        prompt,
        cwd,
        **kwargs,
    ):

        return execution_result(
            {
                "retry_required":
                    False,

                "retry_claim_ids":
                    [],

                "missing_evidence":
                    [],

                "retry_topic":
                    None,

                "critique":
                    "Claim is verified.",
            },
            account="secondary",
        )


    async def fake_synthesis_model(
        prompt,
        cwd,
        **kwargs,
    ):

        return execution_result(
            {
                "answer":
                    "The API listens on port 8000.",

                "used_claim_ids": [
                    "claim-1"
                ],

                "uncertainties":
                    [],

                "notes":
                    None,
            },
            account="primary",
        )


    with tempfile.TemporaryDirectory() as tmp:

        output_root = (
            Path(tmp)
            / "runs"
        )

        summary = (
            await run_research_graph(
                "Determine the API port.",

                max_iterations=1,

                output_root=
                    output_root,

                writer=
                    writer,

                research_runner=
                    fake_research_runner,

                semantic_runner=
                    fake_semantic_runner,

                critic_model_call=
                    fake_critic_model,

                synthesis_model_call=
                    fake_synthesis_model,
            )
        )


        assert (
            summary[
                "run_id"
            ]
            == str(
                FIXED_RUN_ID
            )
        )

        assert (
            summary[
                "status"
            ]
            == "finished"
        )

        assert (
            summary[
                "acceptance_decision"
            ]
            == "accepted"
        )

        assert (
            summary[
                "verified_claim_ids"
            ]
            == [
                "claim-1"
            ]
        )

        assert (
            summary[
                "rejected_claim_ids"
            ]
            == []
        )


        run_dir = Path(
            summary[
                "run_dir"
            ]
        )

        assert (
            run_dir
            / "checkpoints.sqlite"
        ).exists()

        assert (
            run_dir
            / "final_state.json"
        ).exists()

        assert (
            run_dir
            / "worker_result.json"
        ).exists()

        assert (
            run_dir
            / "verification_summary.json"
        ).exists()

        assert (
            run_dir
            / "acceptance_gate.json"
        ).exists()

        assert (
            run_dir
            / "synthesis_input.json"
        ).exists()

        assert (
            run_dir
            / "synthesis_result.json"
        ).exists()

        assert (
            run_dir
            / "final.md"
        ).exists()

        assert (
            run_dir
            / "summary.json"
        ).exists()


        state = json.loads(
            (
                run_dir
                / "final_state.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        assert (
            state[
                "final_result"
            ]
            == (
                "The API listens "
                "on port 8000."
            )
        )


        roles = [
            item[
                "role"
            ]
            for item
            in writer.worker_calls
        ]

        assert roles == [
            "researcher",
            "evidence-verifier",
            "critic",
            "synthesizer",
        ]


        assert len(
            writer.tool_calls
        ) == 1

        assert (
            writer.tool_calls[0][
                "worker_invocation_id"
            ]
            == "worker-inv-1"
        )


        assert len(
            writer.finish_calls
        ) == 1

        assert (
            writer.finish_calls[0][
                "status"
            ]
            == "success"
        )


        measurement = summary[
            "measurement"
        ]

        assert (
            measurement[
                "worker_invocation_count"
            ]
            == 4
        )

        assert (
            measurement[
                "research_worker_invocation_count"
            ]
            == 1
        )

        assert (
            measurement[
                "semantic_worker_invocation_count"
            ]
            == 1
        )

        assert (
            measurement[
                "critic_worker_invocation_count"
            ]
            == 1
        )

        assert (
            measurement[
                "synthesis_worker_invocation_count"
            ]
            == 1
        )

        assert (
            measurement[
                "tool_invocation_count"
            ]
            == 1
        )


        json.dumps(
            state
        )

        json.dumps(
            summary
        )


        print(
            "GRAPH_V4_EXECUTABLE_RUNNER_OK"
        )

        print(
            "GRAPH_V4_PER_RUN_SQLITE_CHECKPOINT_OK"
        )

        print(
            "GRAPH_V4_RUN_ARTIFACTS_OK"
        )

        print(
            "GRAPH_V4_FULL_ROLE_TELEMETRY_OK"
        )

        print(
            "GRAPH_V4_MEASUREMENT_LIFECYCLE_OK"
        )

        print(
            "GRAPH_V4_FINAL_STATE_JSON_SAFE_OK"
        )


    print()
    print(
        "RESEARCH_GRAPH_RUNNER_V1_OK"
    )


def main():

    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()
