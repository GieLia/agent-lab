import asyncio
import json
import tempfile
import uuid

from pathlib import Path

from app.research.direct_anchor import (
    run_direct_anchor,
)
from app.research.tool_loop import (
    ResearchLoopLimits,
)
from app.tools.executor import (
    ToolExecutionResult,
)
from app.workers.result import (
    WorkerExecutionResult,
)


class FakeWriter:
    def __init__(
        self,
    ):
        self.worker_records = []
        self.tool_records = []
        self.finished = []

        self.run_id = uuid.uuid4()

    def ensure_case(
        self,
        **kwargs,
    ):
        return True

    def start_run(
        self,
        **kwargs,
    ):
        return self.run_id

    def record_worker_invocation(
        self,
        **kwargs,
    ):
        invocation_id = (
            "worker-"
            f"{len(self.worker_records) + 1}"
        )

        self.worker_records.append(
            {
                **kwargs,
                "invocation_id":
                    invocation_id,
            }
        )

        return invocation_id

    def record_tool_invocation(
        self,
        **kwargs,
    ):
        self.tool_records.append(
            kwargs
        )

        return (
            "tool-"
            f"{len(self.tool_records)}"
        )

    def finish_run(
        self,
        *,
        run_id,
        status,
    ):
        self.finished.append(
            (
                run_id,
                status,
            )
        )

        return True


class FakeModel:
    def __init__(
        self,
    ):
        self.calls = 0

    async def __call__(
        self,
        prompt,
        cwd,
        **kwargs,
    ):
        self.calls += 1

        if self.calls == 1:
            payload = {
                "action":
                    "search",
                "query":
                    "python venv official",
                "url":
                    None,
                "reason":
                    "Find official docs.",
                "result":
                    None,
            }

        elif self.calls == 2:
            payload = {
                "action":
                    "fetch",
                "query":
                    None,
                "url":
                    "https://docs.python.org/venv",
                "reason":
                    "Retrieve evidence.",
                "result":
                    None,
            }

        elif self.calls == 3:
            payload = {
                "action":
                    "finish",
                "query":
                    None,
                "url":
                    None,
                "reason":
                    "Evidence sufficient.",
                "result": {
                    "status":
                        "success",

                    "claims": [
                        {
                            "claim_id":
                                "claim-1",
                            "text":
                                "venv creates "
                                "virtual environments.",
                            "claim_type":
                                "fact",
                        }
                    ],

                    "sources": [],

                    "evidence": [
                        {
                            "evidence_id":
                                "evidence-1",
                            "claim_id":
                                "claim-1",
                            "source_id":
                                "source-001",
                            "relationship":
                                "supports",
                            "excerpt":
                                "venv creates "
                                "virtual environments.",
                        }
                    ],

                    "gaps": [],
                    "notes":
                        None,
                },
            }

        else:
            raise AssertionError(
                "Unexpected model call"
            )

        return WorkerExecutionResult(
            text=json.dumps(
                payload
            ),
            provider="claude",
            account="primary",
            model="test-model",
            request_id=
                f"request-{self.calls}",
            session_id=None,
            status="success",
            duration_ms=10,
            input_tokens=10,
            output_tokens=10,
            cache_read_tokens=0,
            cache_write_tokens=0,
            reasoning_output_tokens=0,
            reported_cost_usd=None,
            cost_source=None,
            raw_metadata={},
        )


async def fake_tool(
    profile_id,
    tool_name,
    arguments,
    *,
    allow_experimental=False,
):

    assert (
        profile_id
        == "research-readonly"
    )

    assert (
        allow_experimental
        is True
    )

    if tool_name == "web.search":

        return ToolExecutionResult(
            tool_name="web.search",
            capability_id=
                "web.search",
            binding_id=
                "web.search.brave",
            duration_ms=5,
            value={
                "provider":
                    "brave",
                "query":
                    arguments[
                        "query"
                    ],
                "result_count":
                    1,
                "results": [
                    {
                        "rank":
                            1,
                        "title":
                            "Python venv",
                        "url":
                            "https://docs.python.org/venv",
                        "snippet":
                            "Official docs.",
                    }
                ],
            },
        )

    if tool_name == "web.fetch":

        return ToolExecutionResult(
            tool_name="web.fetch",
            capability_id=
                "web.fetch",
            binding_id=
                "web.fetch.guarded",
            duration_ms=7,
            value={
                "final_url":
                    arguments[
                        "url"
                    ],
                "status_code":
                    200,
                "content_type":
                    "text/html",
                "title":
                    "Python venv",
                "text":
                    (
                        "venv creates "
                        "virtual environments."
                    ),
                "text_sha256":
                    "c" * 64,
                "fetched_at":
                    "2026-09-02T19:00:00+00:00",
                "byte_count":
                    35,
                "text_char_count":
                    35,
                "truncated":
                    False,
            },
        )

    raise AssertionError(
        f"Unexpected tool: {tool_name}"
    )


async def main():

    writer = FakeWriter()
    model = FakeModel()

    with tempfile.TemporaryDirectory() as tmp:

        summary = await run_direct_anchor(
            "Test Direct Anchor.",
            account="primary",
            writer=writer,
            model_call=model,
            tool_executor=
                fake_tool,
            output_root=
                Path(tmp),
            limits=
                ResearchLoopLimits(
                    max_steps=5,
                    max_search_calls=2,
                    max_fetch_calls=2,
                    max_protocol_errors=2,
                ),
        )

        assert (
            Path(
                summary[
                    "worker_result_path"
                ]
            ).is_file()
        )

    assert (
        len(
            writer.worker_records
        )
        == 3
    )

    assert (
        len(
            writer.tool_records
        )
        == 2
    )

    assert (
        writer.tool_records[
            0
        ][
            "worker_invocation_id"
        ]
        == "worker-1"
    )

    assert (
        writer.tool_records[
            1
        ][
            "worker_invocation_id"
        ]
        == "worker-2"
    )

    assert all(
        record[
            "tool_profile"
        ]
        == "reasoning"
        for record
        in writer.worker_records
    )

    assert all(
        record[
            "tools_exposed_count"
        ]
        == 0
        for record
        in writer.worker_records
    )

    assert all(
        record[
            "tool_profile"
        ]
        == "research-readonly"
        for record
        in writer.tool_records
    )

    assert (
        writer.finished[-1][1]
        == "success"
    )

    print(
        "DIRECT_ANCHOR_WORKER_TURNS_MEASURED_OK"
    )

    print(
        "DIRECT_ANCHOR_TOOL_WORKER_FK_LINKAGE_OK"
    )

    print(
        "DIRECT_ANCHOR_PROFILE_SEPARATION_OK"
    )

    print(
        "DIRECT_ANCHOR_ARTIFACT_CONTRACT_OK"
    )

    print()
    print(
        "DIRECT_ANCHOR_CONTRACT_OK"
    )


asyncio.run(
    main()
)
