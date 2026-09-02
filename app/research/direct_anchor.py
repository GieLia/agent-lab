import argparse
import asyncio
import getpass
import json
import os
import subprocess
import uuid

from pathlib import Path
from typing import Any, Awaitable, Callable

from app.measurements import (
    MeasurementWriter,
)
from app.research.protocol import (
    RESEARCH_ACTION_SCHEMA,
    validate_worker_result,
)
from app.research.tool_loop import (
    RESEARCH_SYSTEM_PROMPT,
    ResearchLoopLimits,
    run_research_tool_loop,
)
from app.tools.executor import (
    execute_tool,
)
from app.workers.claude_worker import (
    run_claude_detailed,
)
from app.workers.result import (
    WorkerExecutionResult,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

OUTPUT_ROOT = (
    ROOT
    / "runs"
    / "e4.5-direct-anchor"
)

CASE_ID = (
    "e4.5-real-external-web-direct-anchor"
)

CASE_VERSION = 1

WORKER_ID = (
    "direct-web-researcher-v1"
)

DEFAULT_TOPIC = """
Using authoritative sources, determine what Python's
standard-library venv module is used for and identify
the command shown in the official Python documentation
for creating a virtual environment.

Use fetched source evidence rather than relying only
on search-result snippets.
""".strip()


class DirectAnchorError(
    RuntimeError
):
    pass


class MeasurementBridge:
    def __init__(
        self,
        *,
        writer: Any,
        run_id: uuid.UUID,
        worker_id: str,
    ):
        self.writer = writer
        self.run_id = run_id
        self.worker_id = worker_id

        self.latest_worker_invocation_id = (
            None
        )

        self.worker_invocation_ids: list[
            str
        ] = []

    def record_worker_result(
        self,
        result: WorkerExecutionResult,
    ) -> str:

        invocation_id = (
            self.writer
            .record_worker_invocation(
                run_id=self.run_id,
                worker_id=self.worker_id,
                role="researcher",
                result=result,
                tool_profile="reasoning",
                tools_exposed_count=0,
                skill_ids=[
                    "web-research"
                ],
            )
        )

        if not invocation_id:
            raise DirectAnchorError(
                "Worker invocation telemetry "
                "was not persisted"
            )

        self.latest_worker_invocation_id = (
            invocation_id
        )

        self.worker_invocation_ids.append(
            invocation_id
        )

        return invocation_id

    def record_tool_invocation(
        self,
        **kwargs,
    ):

        worker_invocation_id = (
            kwargs.get(
                "worker_invocation_id"
            )
        )

        if worker_invocation_id is None:
            worker_invocation_id = (
                self
                .latest_worker_invocation_id
            )

        if worker_invocation_id is None:
            raise DirectAnchorError(
                "Tool invocation occurred "
                "before a measured worker turn"
            )

        kwargs[
            "worker_invocation_id"
        ] = worker_invocation_id

        return (
            self.writer
            .record_tool_invocation(
                **kwargs
            )
        )


def _git_sha() -> str:

    return (
        subprocess.check_output(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            cwd=ROOT,
            text=True,
        )
        .strip()
    )


def _ensure_brave_key() -> None:

    existing = os.getenv(
        "BRAVE_SEARCH_API_KEY"
    )

    if existing:
        print(
            "BRAVE_KEY_SOURCE=environment"
        )
        return

    key = getpass.getpass(
        "Brave Search API key: "
    )

    if not key:
        raise DirectAnchorError(
            "Brave Search API key "
            "was not supplied"
        )

    os.environ[
        "BRAVE_SEARCH_API_KEY"
    ] = key

    key = None

    print(
        "BRAVE_KEY_SOURCE=interactive"
    )


def _write_json(
    path: Path,
    value: Any,
) -> None:

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


async def run_direct_anchor(
    topic: str,
    *,
    account: str = "primary",
    writer: Any | None = None,
    model_call: Callable[
        ...,
        Awaitable[WorkerExecutionResult],
    ] = run_claude_detailed,
    tool_executor: Callable[
        ...,
        Awaitable[Any],
    ] = execute_tool,
    output_root: Path = OUTPUT_ROOT,
    limits: ResearchLoopLimits
        | None = None,
) -> dict[str, Any]:

    if limits is None:
        limits = ResearchLoopLimits(
            max_steps=10,
            max_search_calls=4,
            max_fetch_calls=6,
            max_protocol_errors=3,
            search_results_per_call=5,
            max_prompt_bytes=70_000,
            max_source_chars_per_prompt=
                12_000,
            max_total_source_chars_in_prompt=
                42_000,
            model_timeout_seconds=180,
        )

    if writer is None:
        writer = MeasurementWriter(
            required=True
        )

    git_sha = _git_sha()

    case_ok = writer.ensure_case(
        case_id=CASE_ID,
        case_version=CASE_VERSION,
        title=(
            "E4.5 Real External Web "
            "Direct Anchor"
        ),
        objective=topic,
        raw_case={
            "phase":
                "E4.5-C3",
            "worker_id":
                WORKER_ID,
            "tool_profile":
                "research-readonly",
            "claude_tool_profile":
                "reasoning",
        },
    )

    if not case_ok:
        raise DirectAnchorError(
            "Unable to ensure evaluation case"
        )

    run_id = writer.start_run(
        case_id=CASE_ID,
        case_version=CASE_VERSION,
        run_type=
            "real_external_web_direct_anchor",
        git_sha=git_sha,
        orchestration=
            "standalone_research_tool_loop",
        raw_metadata={
            "phase":
                "E4.5-C3",
            "account":
                account,
            "native_claude_tools":
                0,
            "research_tool_profile":
                "research-readonly",
        },
    )

    if run_id is None:
        raise DirectAnchorError(
            "Unable to start evaluation run"
        )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_dir = (
        output_root
        / str(run_id)
    )

    run_dir.mkdir(
        parents=False,
        exist_ok=False,
    )

    latest_path = (
        output_root
        / "latest_run_id.txt"
    )

    latest_path.write_text(
        str(run_id) + "\n",
        encoding="utf-8",
    )

    bridge = MeasurementBridge(
        writer=writer,
        run_id=run_id,
        worker_id=WORKER_ID,
    )

    async def measured_model_runner(
        prompt: str,
    ):

        result = await model_call(
            prompt,
            run_dir,
            timeout=
                limits.model_timeout_seconds,
            max_turns=1,
            tool_profile="reasoning",
            system_prompt=
                RESEARCH_SYSTEM_PROMPT,
            json_schema=
                RESEARCH_ACTION_SCHEMA,
            account=account,
        )

        if not isinstance(
            result,
            WorkerExecutionResult,
        ):
            raise DirectAnchorError(
                "Claude returned unexpected "
                "detailed result type"
            )

        bridge.record_worker_result(
            result
        )

        return result

    try:
        result = (
            await run_research_tool_loop(
                topic,
                cwd=run_dir,
                worker_id=WORKER_ID,
                account=account,
                limits=limits,
                model_runner=
                    measured_model_runner,
                tool_executor=
                    tool_executor,
                measurement_writer=
                    bridge,
                run_id=run_id,
                worker_invocation_id=None,
            )
        )

        worker_result = (
            result.worker_result
        )

        validate_worker_result(
            worker_result,
            expected_worker_id=
                WORKER_ID,
        )

        if (
            worker_result[
                "status"
            ]
            != "success"
        ):
            raise DirectAnchorError(
                "Direct Anchor did not "
                "complete with success status"
            )

        if result.search_calls < 1:
            raise DirectAnchorError(
                "Direct Anchor used no "
                "real search calls"
            )

        if result.fetch_calls < 1:
            raise DirectAnchorError(
                "Direct Anchor used no "
                "real fetch calls"
            )

        if (
            result.sources_retrieved
            < 1
        ):
            raise DirectAnchorError(
                "Direct Anchor retrieved "
                "no authoritative sources"
            )

        if not worker_result[
            "evidence"
        ]:
            raise DirectAnchorError(
                "Direct Anchor produced "
                "no evidence links"
            )

        result_path = (
            run_dir
            / "worker_result.json"
        )

        _write_json(
            result_path,
            worker_result,
        )

        summary = {
            "phase":
                "E4.5-C3",

            "run_id":
                str(run_id),

            "git_sha":
                git_sha,

            "case_id":
                CASE_ID,

            "case_version":
                CASE_VERSION,

            "worker_id":
                WORKER_ID,

            "account":
                account,

            "worker_status":
                worker_result[
                    "status"
                ],

            "steps":
                result.steps,

            "model_calls":
                result.model_calls,

            "search_calls":
                result.search_calls,

            "fetch_calls":
                result.fetch_calls,

            "sources_retrieved":
                result.sources_retrieved,

            "claims":
                len(
                    worker_result[
                        "claims"
                    ]
                ),

            "evidence":
                len(
                    worker_result[
                        "evidence"
                    ]
                ),

            "worker_invocation_ids":
                bridge
                .worker_invocation_ids,

            "worker_result_path":
                str(
                    result_path
                ),
        }

        summary_path = (
            run_dir
            / "summary.json"
        )

        _write_json(
            summary_path,
            summary,
        )

        if not writer.finish_run(
            run_id=run_id,
            status="success",
        ):
            raise DirectAnchorError(
                "Unable to finish "
                "measurement run"
            )

        return summary

    except Exception as exc:

        try:
            _write_json(
                run_dir
                / "failure.json",
                {
                    "run_id":
                        str(run_id),
                    "error_type":
                        type(exc).__name__,
                    "error":
                        str(exc),
                },
            )

        except Exception:
            pass

        try:
            writer.finish_run(
                run_id=run_id,
                status="failed",
            )

        except Exception:
            pass

        raise


def _parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Run E4.5 real external-web "
            "Direct Anchor."
        )
    )

    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
    )

    parser.add_argument(
        "--account",
        default=(
            os.getenv(
                "CLAUDE_RESEARCH_ACCOUNT"
            )
            or "primary"
        ),
        choices=[
            "primary",
            "secondary",
        ],
    )

    return parser.parse_args()


async def _main():

    args = _parse_args()

    _ensure_brave_key()

    summary = await run_direct_anchor(
        args.topic,
        account=args.account,
    )

    print()
    print(
        "REAL_CLAUDE_MODEL_OK"
    )

    print(
        "REAL_BRAVE_SEARCH_OK"
    )

    print(
        "REAL_GUARDED_FETCH_OK"
    )

    print(
        "REAL_CANONICAL_WORKER_RESULT_OK"
    )

    print(
        "REAL_SOURCE_PROVENANCE_OK"
    )

    print(
        "REAL_EVIDENCE_LINKS_OK"
    )

    print(
        "REAL_TOOL_TELEMETRY_REQUESTED_OK"
    )

    print()
    print(
        "DIRECT_ANCHOR_RUN_ID="
        + summary[
            "run_id"
        ]
    )

    print(
        "DIRECT_ANCHOR_RESULT="
        + summary[
            "worker_result_path"
        ]
    )

    print()
    print(
        "REAL_DIRECT_ANCHOR_RUNTIME_OK"
    )


if __name__ == "__main__":
    asyncio.run(
        _main()
    )
