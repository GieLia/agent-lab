import asyncio
import uuid

from pathlib import Path


from app.research.graph_measurement import (
    GraphMeasurementBridge,
)

from app.research.semantic_evaluator import (
    evaluate_semantic_evidence,
)

from app.workers.result import (
    WorkerExecutionResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


CLAIM = {
    "claim_id":
        "claim-1",

    "text":
        "The API uses port 8000.",

    "claim_type":
        "fact",
}


EVIDENCE = {
    "evidence_id":
        "evidence-1",

    "claim_id":
        "claim-1",

    "source_id":
        "source-1",

    "relationship":
        "supports",

    "excerpt":
        "The API uses port 8000.",
}


SOURCE = {
    "source_id":
        "source-1",

    "source_type":
        "internal",

    "title":
        "Runtime configuration",
}


class FakeWriter:

    def __init__(
        self,
    ):

        self.failures = []


    def record_worker_transport_failure(
        self,
        **kwargs,
    ):

        self.failures.append(
            kwargs
        )

        return (
            "semantic-failure-"
            + str(
                len(
                    self.failures
                )
            )
        )


async def check_turn_budget():

    captured = {}


    async def fake_model(
        prompt,
        cwd,
        **kwargs,
    ):

        captured.update(
            kwargs
        )

        return WorkerExecutionResult(
            text=(
                '{"entailment":"full",'
                '"claim_atomicity":"atomic",'
                '"support_sufficiency":"sufficient",'
                '"unsupported_clauses":[],'
                '"contradicted_clauses":[],'
                '"untrusted_instruction_detected":false,'
                '"confidence":0.99,'
                '"rationale":"Fully supported."}'
            ),
            provider="claude",
            account="secondary",
            model="test-model",
            request_id="semantic-test",
            session_id="semantic-session",
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


    evaluation, execution = (
        await evaluate_semantic_evidence(
            claim=CLAIM,
            evidence=EVIDENCE,
            source=SOURCE,
            cwd=ROOT,
            account="secondary",
            model_call=fake_model,
        )
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

    assert (
        evaluation[
            "entailment"
        ]
        == "full"
    )


    print(
        "SEMANTIC_STRUCTURED_TURN_BUDGET_OK"
    )

    print(
        "SEMANTIC_REASONING_ZERO_TOOL_PROFILE_OK"
    )


async def check_transport_failure():

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
            "synthetic semantic transport failure"
        )


    try:

        await evaluate_semantic_evidence(
            claim=CLAIM,
            evidence=EVIDENCE,
            source=SOURCE,
            cwd=ROOT,
            account="secondary",
            model_call=failing_model,
            failure_observer=(
                lambda error, duration_ms:
                bridge
                .record_semantic_transport_failure(
                    error,
                    duration_ms,
                    account="secondary",
                )
            ),
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Semantic transport failure "
            "did not propagate"
        )


    assert len(
        writer.failures
    ) == 1

    call = writer.failures[0]

    assert (
        call[
            "role"
        ]
        == "evidence-verifier"
    )

    assert (
        call[
            "account"
        ]
        == "secondary"
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

    summary = bridge.snapshot()

    assert (
        summary[
            "semantic_worker_invocation_count"
        ]
        == 1
    )

    assert (
        summary[
            "transport_failure_invocation_count"
        ]
        == 1
    )


    print(
        "SEMANTIC_TRANSPORT_FAILURE_TELEMETRY_OK"
    )


async def main_async():

    await check_turn_budget()
    await check_transport_failure()


def main():

    asyncio.run(
        main_async()
    )

    print()
    print(
        "SEMANTIC_RUNTIME_POLICY_V1_OK"
    )


if __name__ == "__main__":
    main()
