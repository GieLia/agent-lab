import asyncio
import uuid

from pathlib import Path


from app.research.graph_measurement import (
    GraphMeasurementBridge,
)

from app.research.graph_reasoning import (
    build_measured_critic_runner,
    build_measured_synthesis_node,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


class FakeWriter:

    def __init__(
        self,
    ):

        self.worker_failures = []


    def record_worker_transport_failure(
        self,
        **kwargs,
    ):

        self.worker_failures.append(
            kwargs
        )

        return (
            "failed-worker-"
            + str(
                len(
                    self.worker_failures
                )
            )
        )


    def record_worker_invocation(
        self,
        **kwargs,
    ):

        raise AssertionError(
            "transport failure must not "
            "be recorded as successful result"
        )


    def record_tool_invocation(
        self,
        **kwargs,
    ):

        raise AssertionError(
            "reasoning role invoked tool"
        )


async def check_critic():

    writer = FakeWriter()

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=uuid.uuid4(),
    )


    async def failing_model(
        prompt,
        cwd,
        **kwargs,
    ):

        assert (
            kwargs[
                "max_turns"
            ]
            == 3
        )

        assert (
            kwargs[
                "tool_profile"
            ]
            == "reasoning"
        )

        raise RuntimeError(
            "synthetic transport failure"
        )


    runner = build_measured_critic_runner(
        cwd=ROOT,
        account="secondary",
        measurement_bridge=bridge,
        model_call=failing_model,
    )


    try:
        await runner(
            topic="Transport failure test",
            research_result={
                "claims": [
                    {
                        "claim_id":
                            "claim-1",

                        "text":
                            "Fact.",

                        "claim_type":
                            "fact",
                    }
                ]
            },
            verification_summary={
                "verified_claim_ids":
                    []
            },
            structural_integrity="pass",
            structural_errors=[],
            rejected_claim_ids=[
                "claim-1"
            ],
            candidate_retry_claim_ids=[
                "claim-1"
            ],
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Critic transport failure "
            "did not propagate"
        )


    assert len(
        writer.worker_failures
    ) == 1

    call = writer.worker_failures[0]

    assert call[
        "role"
    ] == "critic"

    assert call[
        "account"
    ] == "secondary"

    assert call[
        "tool_profile"
    ] == "reasoning"

    assert call[
        "tools_exposed_count"
    ] == 0

    assert (
        bridge.snapshot()[
            "critic_worker_invocation_count"
        ]
        == 1
    )

    assert (
        bridge.snapshot()[
            "transport_failure_invocation_count"
        ]
        == 1
    )

    print(
        "CRITIC_TRANSPORT_FAILURE_TELEMETRY_OK"
    )


async def check_synthesis():

    writer = FakeWriter()

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=uuid.uuid4(),
    )


    async def failing_model(
        prompt,
        cwd,
        **kwargs,
    ):

        assert (
            kwargs[
                "max_turns"
            ]
            == 3
        )

        assert (
            kwargs[
                "tool_profile"
            ]
            == "reasoning"
        )

        raise RuntimeError(
            "synthetic transport failure"
        )


    node = build_measured_synthesis_node(
        cwd=ROOT,
        account="primary",
        measurement_bridge=bridge,
        model_call=failing_model,
    )


    try:
        await node(
            {
                "topic":
                    "Synthesis failure test",

                "synthesis_input": {
                    "accepted_claim_ids": [
                        "claim-1"
                    ],

                    "claims": [
                        {
                            "claim_id":
                                "claim-1",

                            "text":
                                "Fact.",

                            "claim_type":
                                "fact",
                        }
                    ],
                },
            }
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Synth transport failure "
            "did not propagate"
        )


    assert len(
        writer.worker_failures
    ) == 1

    call = writer.worker_failures[0]

    assert call[
        "role"
    ] == "synthesizer"

    assert call[
        "account"
    ] == "primary"

    assert call[
        "tools_exposed_count"
    ] == 0

    assert (
        bridge.snapshot()[
            "synthesis_worker_invocation_count"
        ]
        == 1
    )

    assert (
        bridge.snapshot()[
            "transport_failure_invocation_count"
        ]
        == 1
    )

    print(
        "SYNTH_TRANSPORT_FAILURE_TELEMETRY_OK"
    )


async def main_async():

    await check_critic()
    await check_synthesis()


def main():

    asyncio.run(
        main_async()
    )

    print()
    print(
        "RESEARCH_TRANSPORT_FAILURE_MEASUREMENT_V1_OK"
    )


if __name__ == "__main__":
    main()
