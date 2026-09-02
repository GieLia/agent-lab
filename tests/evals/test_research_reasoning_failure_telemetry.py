import asyncio
import json
import uuid

from pathlib import Path


from app.research.graph_measurement import (
    GraphMeasurementBridge,
)

from app.research.graph_reasoning import (
    GraphReasoningError,
    build_measured_critic_runner,
    build_measured_synthesis_node,
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
    payload,
    *,
    account,
):

    return WorkerExecutionResult(
        text=json.dumps(
            payload
        ),
        provider="claude",
        account=account,
        model="test-model",
        request_id="request-invalid",
        session_id="session-invalid",
        status="success",
        duration_ms=11,
        input_tokens=20,
        output_tokens=10,
        cache_read_tokens=0,
        cache_write_tokens=0,
        reasoning_output_tokens=0,
        reported_cost_usd=None,
        cost_source=None,
        raw_metadata={
            "contract_test":
                "invalid-output"
        },
    )


class FakeWriter:

    def __init__(
        self,
    ):

        self.worker_calls = []


    def record_worker_invocation(
        self,
        **kwargs,
    ):

        self.worker_calls.append(
            kwargs
        )

        return (
            "worker-invalid-"
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

        raise AssertionError(
            "reasoning worker invoked a tool"
        )


async def check_invalid_critic_telemetry():

    writer = FakeWriter()

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=uuid.uuid4(),
    )


    async def invalid_critic_model(
        prompt,
        cwd,
        **kwargs,
    ):

        return execution_result(
            {
                # Deliberately inconsistent.
                "retry_required":
                    True,

                "retry_claim_ids":
                    [],

                "missing_evidence": [
                    "Evidence is missing."
                ],

                "retry_topic":
                    "Find more evidence.",

                "critique":
                    "Retry requested without target.",
            },
            account="secondary",
        )


    runner = build_measured_critic_runner(
        cwd=ROOT,
        account="secondary",
        measurement_bridge=bridge,
        model_call=invalid_critic_model,
    )


    try:

        await runner(
            topic=
                "Failure telemetry test",

            research_result={
                "claims": [
                    {
                        "claim_id":
                            "claim-a",

                        "text":
                            "Test claim.",

                        "claim_type":
                            "fact",
                    }
                ]
            },

            verification_summary={
                "verified_claim_ids":
                    []
            },

            structural_integrity=
                "pass",

            structural_errors=
                [],

            rejected_claim_ids=[
                "claim-a"
            ],

            candidate_retry_claim_ids=[
                "claim-a"
            ],
        )

    except GraphReasoningError:
        pass

    else:
        raise AssertionError(
            "invalid Critic output "
            "was not rejected"
        )


    assert len(
        writer.worker_calls
    ) == 1

    assert (
        writer.worker_calls[0][
            "role"
        ]
        == "critic"
    )

    assert (
        writer.worker_calls[0][
            "tools_exposed_count"
        ]
        == 0
    )

    assert (
        bridge.snapshot()[
            "critic_worker_invocation_count"
        ]
        == 1
    )


    print(
        "INVALID_CRITIC_OUTPUT_REJECTED_OK"
    )

    print(
        "INVALID_CRITIC_OUTPUT_TELEMETRY_PRESERVED_OK"
    )


async def check_invalid_synthesis_telemetry():

    writer = FakeWriter()

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=uuid.uuid4(),
    )


    async def invalid_synthesis_model(
        prompt,
        cwd,
        **kwargs,
    ):

        return execution_result(
            {
                "answer":
                    "Invented answer.",

                # Deliberately escapes gate.
                "used_claim_ids": [
                    "claim-rejected"
                ],

                "uncertainties":
                    [],

                "notes":
                    None,
            },
            account="primary",
        )


    node = build_measured_synthesis_node(
        cwd=ROOT,
        account="primary",
        measurement_bridge=bridge,
        model_call=
            invalid_synthesis_model,
    )


    state = {
        "topic":
            "Failure telemetry synthesis",

        "synthesis_input": {
            "accepted_claim_ids": [
                "claim-accepted"
            ],

            "claims": [
                {
                    "claim_id":
                        "claim-accepted",

                    "text":
                        "Accepted fact.",

                    "claim_type":
                        "fact",
                }
            ],
        },
    }


    try:

        await node(
            state
        )

    except GraphReasoningError:
        pass

    else:
        raise AssertionError(
            "invalid Synthesizer output "
            "was not rejected"
        )


    assert len(
        writer.worker_calls
    ) == 1

    assert (
        writer.worker_calls[0][
            "role"
        ]
        == "synthesizer"
    )

    assert (
        writer.worker_calls[0][
            "tools_exposed_count"
        ]
        == 0
    )

    assert (
        bridge.snapshot()[
            "synthesis_worker_invocation_count"
        ]
        == 1
    )


    print(
        "INVALID_SYNTHESIS_OUTPUT_REJECTED_OK"
    )

    print(
        "INVALID_SYNTHESIS_OUTPUT_TELEMETRY_PRESERVED_OK"
    )


async def main_async():

    await check_invalid_critic_telemetry()
    await check_invalid_synthesis_telemetry()


def main():

    asyncio.run(
        main_async()
    )

    print()
    print(
        "REASONING_FAILURE_TELEMETRY_V1_OK"
    )


if __name__ == "__main__":
    main()
