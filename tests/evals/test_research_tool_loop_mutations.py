import asyncio

from pathlib import Path

from app.research.tool_loop import (
    ResearchLoopError,
    ResearchLoopLimits,
    run_research_tool_loop,
)
from app.tools.executor import (
    ToolExecutionResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def expect_loop_failure(
    coro,
):

    async def inner():

        try:
            await coro

        except ResearchLoopError:
            return

        raise AssertionError(
            "Expected ResearchLoopError"
        )

    return inner()


async def test_direct_fetch_rejected():

    calls = []

    actions = [
        {
            "action":
                "fetch",
            "query":
                None,
            "url":
                "https://example.com/not-searched",
            "reason":
                "Try direct fetch.",
            "result":
                None,
        },
        {
            "action":
                "finish",
            "query":
                None,
            "url":
                None,
            "reason":
                "Stop.",
            "result": {
                "status":
                    "failed",
                "claims": [],
                "sources": [],
                "evidence": [],
                "gaps": [
                    "No authorized source."
                ],
                "notes":
                    None,
            },
        },
    ]

    async def model(
        prompt,
    ):
        return actions.pop(0)

    async def tool(
        *args,
        **kwargs,
    ):
        calls.append(
            (
                args,
                kwargs,
            )
        )

        raise AssertionError(
            "Unauthorized direct URL "
            "reached tool executor"
        )

    result = await run_research_tool_loop(
        "Direct fetch rejection.",
        cwd=ROOT,
        model_runner=model,
        tool_executor=tool,
        limits=ResearchLoopLimits(
            max_steps=3,
            max_protocol_errors=2,
        ),
    )

    assert calls == []

    assert (
        result.worker_result[
            "status"
        ]
        == "failed"
    )

    print(
        "MODEL_GENERATED_DIRECT_FETCH_REJECTED_OK"
    )


async def test_fake_sources_rejected():

    calls = 0

    async def model(
        prompt,
    ):
        nonlocal calls

        calls += 1

        return {
            "action":
                "finish",
            "query":
                None,
            "url":
                None,
            "reason":
                "Attempt source fabrication.",
            "result": {
                "status":
                    "success",

                "claims": [
                    {
                        "claim_id":
                            "c1",
                        "text":
                            "Fake claim.",
                        "claim_type":
                            "fact",
                    }
                ],

                "sources": [
                    {
                        "source_id":
                            "fake-source",
                        "source_type":
                            "web",
                        "title":
                            "Fabricated",
                        "url":
                            "https://fake.invalid/",
                    }
                ],

                "evidence": [],
                "gaps": [],
                "notes":
                    None,
            },
        }

    await expect_loop_failure(
        run_research_tool_loop(
            "Source fabrication rejection.",
            cwd=ROOT,
            model_runner=model,
            limits=
                ResearchLoopLimits(
                    max_steps=2,
                    max_protocol_errors=1,
                ),
        )
    )

    assert calls == 2

    print(
        "MODEL_SOURCE_FABRICATION_REJECTED_OK"
    )


async def test_hallucinated_excerpt_rejected():

    model_calls = 0

    async def model(
        prompt,
    ):

        nonlocal model_calls

        model_calls += 1

        if model_calls == 1:
            return {
                "action":
                    "search",
                "query":
                    "evidence test",
                "url":
                    None,
                "reason":
                    "discover",
                "result":
                    None,
            }

        if model_calls == 2:
            return {
                "action":
                    "fetch",
                "query":
                    None,
                "url":
                    "https://example.com/evidence",
                "reason":
                    "retrieve",
                "result":
                    None,
            }

        return {
            "action":
                "finish",
            "query":
                None,
            "url":
                None,
            "reason":
                "finish",
            "result": {
                "status":
                    "success",

                "claims": [
                    {
                        "claim_id":
                            "c1",
                        "text":
                            "Actual evidence exists.",
                        "claim_type":
                            "fact",
                    }
                ],

                "sources": [],

                "evidence": [
                    {
                        "evidence_id":
                            "e1",
                        "claim_id":
                            "c1",
                        "source_id":
                            "source-001",
                        "relationship":
                            "supports",
                        "excerpt":
                            "THIS TEXT NEVER EXISTED",
                    }
                ],

                "gaps": [],
                "notes":
                    None,
            },
        }

    async def tool(
        profile_id,
        tool_name,
        arguments,
        *,
        allow_experimental=False,
    ):

        if tool_name == "web.search":
            return ToolExecutionResult(
                tool_name=
                    "web.search",
                capability_id=
                    "web.search",
                binding_id=
                    "web.search.brave",
                duration_ms=
                    1,
                value={
                    "provider":
                        "brave",
                    "query":
                        "evidence test",
                    "result_count":
                        1,
                    "results": [
                        {
                            "rank":
                                1,
                            "title":
                                "Evidence",
                            "url":
                                "https://example.com/evidence",
                            "snippet":
                                "Evidence.",
                        }
                    ],
                },
            )

        return ToolExecutionResult(
            tool_name=
                "web.fetch",
            capability_id=
                "web.fetch",
            binding_id=
                "web.fetch.guarded",
            duration_ms=
                1,
            value={
                "final_url":
                    "https://example.com/evidence",
                "status_code":
                    200,
                "content_type":
                    "text/html",
                "title":
                    "Evidence",
                "text":
                    "Actual evidence exists.",
                "text_sha256":
                    "b" * 64,
                "fetched_at":
                    "2026-09-02T18:00:00+00:00",
                "byte_count":
                    23,
                "text_char_count":
                    23,
                "truncated":
                    False,
            },
        )

    await expect_loop_failure(
        run_research_tool_loop(
            "Hallucinated excerpt rejection.",
            cwd=ROOT,
            model_runner=model,
            tool_executor=tool,
            limits=
                ResearchLoopLimits(
                    max_steps=4,
                    max_protocol_errors=1,
                ),
        )
    )

    print(
        "HALLUCINATED_EVIDENCE_EXCERPT_REJECTED_OK"
    )


async def test_action_escape_rejected():

    async def model(
        prompt,
    ):
        return {
            "action":
                "shell",
            "query":
                None,
            "url":
                None,
            "reason":
                "escape",
            "result":
                None,
        }

    await expect_loop_failure(
        run_research_tool_loop(
            "Action escape.",
            cwd=ROOT,
            model_runner=model,
            limits=
                ResearchLoopLimits(
                    max_steps=2,
                    max_protocol_errors=1,
                ),
        )
    )

    print(
        "NON_RESEARCH_ACTION_REJECTED_OK"
    )


async def test_prompt_budget():

    try:
        await run_research_tool_loop(
            "Prompt budget.",
            cwd=ROOT,
            model_runner=lambda prompt:
                None,
            limits=
                ResearchLoopLimits(
                    max_prompt_bytes=1,
                ),
        )

    except ResearchLoopError:
        pass

    else:
        raise AssertionError(
            "Tiny prompt budget accepted"
        )

    print(
        "RESEARCH_PROMPT_BUDGET_ENFORCED_OK"
    )


async def main():

    await test_direct_fetch_rejected()
    await test_fake_sources_rejected()
    await test_hallucinated_excerpt_rejected()
    await test_action_escape_rejected()
    await test_prompt_budget()

    print()
    print(
        "RESEARCH_TOOL_LOOP_MUTATION_BOUNDARY_OK"
    )


asyncio.run(
    main()
)
