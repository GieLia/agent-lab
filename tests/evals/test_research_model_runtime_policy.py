import asyncio
import uuid

from pathlib import Path


import app.research.tool_loop as tool_loop

from app.research.graph_measurement import (
    GraphMeasurementBridge,
)

from app.workers.result import (
    WorkerExecutionResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def result():

    return WorkerExecutionResult(
        text="{}",
        provider="claude",
        account="primary",
        model="test-model",
        request_id="request-test",
        session_id="session-test",
        status="success",
        duration_ms=1,
        input_tokens=1,
        output_tokens=1,
        cache_read_tokens=0,
        cache_write_tokens=0,
        reasoning_output_tokens=0,
        reported_cost_usd=None,
        cost_source=None,
        raw_metadata={},
    )


class FakeWriter:

    def __init__(self):
        self.failures = []


    def record_worker_transport_failure(
        self,
        **kwargs,
    ):

        self.failures.append(
            kwargs
        )

        return (
            "research-failure-"
            + str(
                len(
                    self.failures
                )
            )
        )


async def check_turn_budget():

    captured = {}

    original = (
        tool_loop
        .run_claude_detailed
    )


    async def fake_claude(
        prompt,
        cwd,
        **kwargs,
    ):

        captured.update(
            kwargs
        )

        return result()


    try:

        tool_loop.run_claude_detailed = (
            fake_claude
        )

        await (
            tool_loop
            ._default_model_runner(
                "test",
                cwd=ROOT,
                account="primary",
                timeout_seconds=10,
            )
        )

    finally:

        tool_loop.run_claude_detailed = (
            original
        )


    assert (
        captured[
            "max_turns"
        ]
        == 3
    )

    assert (
        captured[
            "tool_profile"
        ]
        == "reasoning"
    )


    print(
        "RESEARCH_STRUCTURED_TURN_BUDGET_OK"
    )

    print(
        "RESEARCH_MODEL_ZERO_TOOL_PROFILE_OK"
    )


async def check_failure_bridge():

    writer = FakeWriter()

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=uuid.uuid4(),
    )

    bridge.record_research_transport_failure(
        RuntimeError(
            "synthetic failure"
        ),
        12,
        account="primary",
    )

    assert len(
        writer.failures
    ) == 1

    call = writer.failures[0]

    assert (
        call[
            "role"
        ]
        == "researcher"
    )

    assert (
        call[
            "tool_profile"
        ]
        == "reasoning"
    )

    assert (
        call[
            "tools_exposed_count"
        ]
        == 0
    )

    assert (
        bridge.snapshot()[
            "research_worker_invocation_count"
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
        "RESEARCH_TRANSPORT_FAILURE_TELEMETRY_OK"
    )


async def main_async():

    await check_turn_budget()
    await check_failure_bridge()


def main():

    asyncio.run(
        main_async()
    )

    print()
    print(
        "RESEARCH_MODEL_RUNTIME_POLICY_V1_OK"
    )


if __name__ == "__main__":
    main()
