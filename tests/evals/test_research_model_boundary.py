import asyncio

from pathlib import Path
from unittest.mock import patch

import app.research.tool_loop as tool_loop

from app.research.protocol import (
    RESEARCH_ACTION_SCHEMA,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


class FakeWorkerResult:
    text = (
        '{"action":"finish",'
        '"query":null,'
        '"url":null,'
        '"reason":"test",'
        '"result":null}'
    )


async def main():

    captured = {}

    async def fake_run_claude_detailed(
        prompt,
        cwd,
        **kwargs,
    ):

        captured[
            "prompt"
        ] = prompt

        captured[
            "cwd"
        ] = cwd

        captured.update(
            kwargs
        )

        return FakeWorkerResult()

    with patch.object(
        tool_loop,
        "run_claude_detailed",
        fake_run_claude_detailed,
    ):

        result = (
            await tool_loop
            ._default_model_runner(
                "BOUNDARY_TEST_PROMPT",
                cwd=ROOT,
                account="primary",
                timeout_seconds=77,
            )
        )

    assert isinstance(
        result,
        FakeWorkerResult,
    )

    assert (
        captured[
            "prompt"
        ]
        == "BOUNDARY_TEST_PROMPT"
    )

    assert (
        captured[
            "cwd"
        ]
        == ROOT
    )

    assert (
        captured[
            "tool_profile"
        ]
        == "reasoning"
    )

    assert (
        captured[
            "max_turns"
        ]
        == 1
    )

    assert (
        captured[
            "timeout"
        ]
        == 77
    )

    assert (
        captured[
            "account"
        ]
        == "primary"
    )

    assert (
        captured[
            "json_schema"
        ]
        == RESEARCH_ACTION_SCHEMA
    )

    system_prompt = captured[
        "system_prompt"
    ]

    assert (
        "NO native tools"
        in system_prompt
    )

    assert (
        "UNTRUSTED DATA"
        in system_prompt
    )

    assert (
        tool_loop
        .CLAUDE_TOOL_PROFILE
        == "reasoning"
    )

    assert (
        tool_loop
        .RESEARCH_TOOL_PROFILE
        == "research-readonly"
    )

    print(
        "CLAUDE_RESEARCH_REASONING_PROFILE_OK"
    )

    print(
        "CLAUDE_RESEARCH_SINGLE_TURN_OK"
    )

    print(
        "CLAUDE_NATIVE_TOOL_BOUNDARY_OK"
    )

    print(
        "RESEARCH_EXECUTOR_PROFILE_SEPARATION_OK"
    )

    print()
    print(
        "RESEARCH_MODEL_BOUNDARY_OK"
    )


asyncio.run(
    main()
)
