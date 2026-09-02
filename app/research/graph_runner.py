from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import uuid

from pathlib import Path
from typing import Any


from langgraph.checkpoint.sqlite.aio import (
    AsyncSqliteSaver,
)


from app.graph_v4 import (
    GRAPH_VERSION,
    ResearchGraphNodes,
    build_graph,
    build_initial_state,
)

from app.measurements import (
    MeasurementWriter,
)

from app.research.graph_measurement import (
    GraphMeasurementBridge,
)

from app.research.graph_nodes import (
    GraphNodeDependencies,
    build_acceptance_gate_node,
    build_critic_node,
    build_research_node,
    build_semantic_verification_node,
    evidence_integrity_node,
    runtime_verification_node,
    synthesis_input_node,
)

from app.research.graph_reasoning import (
    build_measured_critic_runner,
    build_measured_synthesis_node,
)

from app.research.semantic_evaluator import (
    evaluate_semantic_evidence,
)

from app.research.tool_loop import (
    run_research_tool_loop,
)

from app.workers.claude_worker import (
    run_claude_detailed,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "runs"
    / "research-graph-v1"
)

CASE_ID = (
    "research-graph-v1"
)

CASE_VERSION = 1


class ResearchGraphRunnerError(
    RuntimeError
):
    pass


def _write_json(
    path: Path,
    value: Any,
) -> None:

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _git_sha() -> str:

    process = subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if process.returncode != 0:
        raise ResearchGraphRunnerError(
            "Unable to resolve git SHA"
        )

    value = process.stdout.strip()

    if not value:
        raise ResearchGraphRunnerError(
            "Empty git SHA"
        )

    return value


async def run_research_graph(
    topic: str,
    *,
    max_iterations: int = 2,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    writer: Any | None = None,
    research_account: str = "primary",
    semantic_account: str = "secondary",
    critic_account: str = "secondary",
    synthesis_account: str = "primary",
    research_runner: Any =
        run_research_tool_loop,
    semantic_runner: Any =
        evaluate_semantic_evidence,
    critic_model_call: Any =
        run_claude_detailed,
    synthesis_model_call: Any =
        run_claude_detailed,
) -> dict[str, Any]:

    if (
        not isinstance(
            topic,
            str,
        )
        or not topic.strip()
    ):
        raise ResearchGraphRunnerError(
            "topic must be a non-empty string"
        )

    if (
        isinstance(
            max_iterations,
            bool,
        )
        or not isinstance(
            max_iterations,
            int,
        )
        or max_iterations < 1
    ):
        raise ResearchGraphRunnerError(
            "max_iterations must be >= 1"
        )

    topic = topic.strip()

    if writer is None:
        writer = MeasurementWriter(
            required=True
        )

    git_sha = _git_sha()

    case_ok = writer.ensure_case(
        case_id=
            CASE_ID,

        case_version=
            CASE_VERSION,

        title=
            "Research Graph v1",

        objective=
            (
                "Execute the controlled "
                "research graph with runtime "
                "verification and gated synthesis."
            ),

        raw_case={
            "phase":
                "E5",

            "graph_version":
                GRAPH_VERSION,

            "research_tool_profile":
                "research-readonly",

            "reasoning_tool_profile":
                "reasoning",

            "native_model_tools":
                0,
        },
    )

    if not case_ok:
        raise ResearchGraphRunnerError(
            "Unable to ensure measurement case"
        )

    run_id = writer.start_run(
        case_id=
            CASE_ID,

        case_version=
            CASE_VERSION,

        run_type=
            "research_graph_v1",

        git_sha=
            git_sha,

        orchestration=
            "langgraph_research_graph_v1",

        raw_metadata={
            "phase":
                "E5",

            "graph_version":
                GRAPH_VERSION,

            "research_account":
                research_account,

            "semantic_account":
                semantic_account,

            "critic_account":
                critic_account,

            "synthesis_account":
                synthesis_account,

            "research_tool_profile":
                "research-readonly",

            "reasoning_tool_profile":
                "reasoning",

            "native_model_tools":
                0,

            "max_iterations":
                max_iterations,
        },
    )

    if not isinstance(
        run_id,
        uuid.UUID,
    ):
        raise ResearchGraphRunnerError(
            "Unable to start measurement run"
        )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_dir = (
        output_root
        / str(
            run_id
        )
    )

    try:

        run_dir.mkdir(
            parents=False,
            exist_ok=False,
        )

        (
            output_root
            / "latest_run_id.txt"
        ).write_text(
            str(
                run_id
            )
            + "\n",
            encoding="utf-8",
        )

        bridge = GraphMeasurementBridge(
            writer=
                writer,

            run_id=
                run_id,
        )

        dependencies = (
            GraphNodeDependencies(
                cwd=
                    run_dir,

                research_worker_id=
                    bridge
                    .research_worker_id,

                research_account=
                    research_account,

                semantic_account=
                    semantic_account,

                measurement_bridge=
                    bridge,

                research_runner=
                    research_runner,

                semantic_runner=
                    semantic_runner,
            )
        )

        critic_runner = (
            build_measured_critic_runner(
                cwd=
                    run_dir,

                account=
                    critic_account,

                measurement_bridge=
                    bridge,

                model_call=
                    critic_model_call,
            )
        )

        synthesis_node = (
            build_measured_synthesis_node(
                cwd=
                    run_dir,

                account=
                    synthesis_account,

                measurement_bridge=
                    bridge,

                model_call=
                    synthesis_model_call,
            )
        )

        nodes = ResearchGraphNodes(
            research=
                build_research_node(
                    dependencies
                ),

            evidence_integrity=
                evidence_integrity_node,

            semantic_verification=
                build_semantic_verification_node(
                    dependencies
                ),

            runtime_verification=
                runtime_verification_node,

            critic=
                build_critic_node(
                    critic_runner=
                        critic_runner
                ),

            acceptance_gate=
                build_acceptance_gate_node(
                    dependencies
                ),

            synthesis_input=
                synthesis_input_node,

            synthesis=
                synthesis_node,
        )

        checkpoint_path = (
            run_dir
            / "checkpoints.sqlite"
        )

        async with (
            AsyncSqliteSaver
            .from_conn_string(
                str(
                    checkpoint_path
                )
            )
        ) as checkpointer:

            graph = build_graph(
                nodes=
                    nodes,

                checkpointer=
                    checkpointer,
            )

            initial_state = (
                build_initial_state(
                    topic=
                        topic,

                    run_id=
                        str(
                            run_id
                        ),

                    mission_id=
                        str(
                            run_id
                        ),

                    max_iterations=
                        max_iterations,
                )
            )

            config = {
                "configurable": {
                    "thread_id":
                        str(
                            run_id
                        ),
                }
            }

            final_state = (
                await graph.ainvoke(
                    initial_state,
                    config=config,
                )
            )

            final_snapshot = (
                await graph.aget_state(
                    config
                )
            )

            if final_snapshot.next:
                raise ResearchGraphRunnerError(
                    "graph completed with "
                    "pending checkpoint nodes"
                )

        if not isinstance(
            final_state,
            dict,
        ):
            raise ResearchGraphRunnerError(
                "graph returned unexpected "
                "final state"
            )

        measurement_summary = (
            bridge.snapshot()
        )

        final_state[
            "measurement_summary"
        ] = measurement_summary

        _write_json(
            run_dir
            / "final_state.json",
            final_state,
        )

        artifact_map = {
            "research_result":
                "worker_result.json",

            "verification_summary":
                "verification_summary.json",

            "acceptance_gate":
                "acceptance_gate.json",

            "synthesis_input":
                "synthesis_input.json",

            "synthesis_result":
                "synthesis_result.json",
        }

        artifact_paths = {}

        for (
            state_key,
            filename,
        ) in artifact_map.items():

            value = final_state.get(
                state_key
            )

            if (
                isinstance(
                    value,
                    dict,
                )
                and value
            ):
                path = (
                    run_dir
                    / filename
                )

                _write_json(
                    path,
                    value,
                )

                artifact_paths[
                    state_key
                ] = str(
                    path
                )

        final_result = final_state.get(
            "final_result"
        )

        final_path = None

        if (
            isinstance(
                final_result,
                str,
            )
            and final_result.strip()
        ):
            final_path = (
                run_dir
                / "final.md"
            )

            final_path.write_text(
                final_result.strip()
                + "\n",
                encoding="utf-8",
            )

        gate = final_state.get(
            "acceptance_gate",
            {},
        )

        if isinstance(
            gate,
            dict,
        ):
            acceptance_decision = (
                gate.get(
                    "decision"
                )
            )
        else:
            acceptance_decision = None

        summary = {
            "phase":
                "E5",

            "graph_version":
                GRAPH_VERSION,

            "run_id":
                str(
                    run_id
                ),

            "git_sha":
                git_sha,

            "topic":
                topic,

            "status":
                final_state.get(
                    "status"
                ),

            "acceptance_decision":
                acceptance_decision,

            "iteration":
                final_state.get(
                    "iteration"
                ),

            "max_iterations":
                max_iterations,

            "verified_claim_ids":
                final_state.get(
                    "verified_claim_ids",
                    [],
                ),

            "rejected_claim_ids":
                final_state.get(
                    "rejected_claim_ids",
                    [],
                ),

            "research_metrics":
                final_state.get(
                    "research_metrics",
                    {},
                ),

            "measurement":
                measurement_summary,

            "run_dir":
                str(
                    run_dir
                ),

            "checkpoint_path":
                str(
                    checkpoint_path
                ),

            "final_state_path":
                str(
                    run_dir
                    / "final_state.json"
                ),

            "final_result_path": (
                str(
                    final_path
                )
                if final_path
                is not None
                else None
            ),

            "artifacts":
                artifact_paths,
        }

        _write_json(
            run_dir
            / "summary.json",
            summary,
        )

        if not writer.finish_run(
            run_id=
                run_id,

            status=
                "success",
        ):
            raise ResearchGraphRunnerError(
                "Unable to finish "
                "measurement run"
            )

        return summary

    except Exception as exc:

        try:

            if run_dir.exists():

                _write_json(
                    run_dir
                    / "failure.json",
                    {
                        "run_id":
                            str(
                                run_id
                            ),

                        "error_type":
                            type(
                                exc
                            ).__name__,

                        "error":
                            str(
                                exc
                            ),
                    },
                )

        except Exception:
            pass

        try:
            writer.finish_run(
                run_id=
                    run_id,

                status=
                    "failed",
            )

        except Exception:
            pass

        raise


def _parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Execute Research Graph v1."
        )
    )

    parser.add_argument(
        "topic",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--research-account",
        default="primary",
    )

    parser.add_argument(
        "--semantic-account",
        default="secondary",
    )

    parser.add_argument(
        "--critic-account",
        default="secondary",
    )

    parser.add_argument(
        "--synthesis-account",
        default="primary",
    )

    return parser.parse_args()


async def _main_async():

    args = _parse_args()

    summary = await run_research_graph(
        args.topic,

        max_iterations=
            args.max_iterations,

        research_account=
            args.research_account,

        semantic_account=
            args.semantic_account,

        critic_account=
            args.critic_account,

        synthesis_account=
            args.synthesis_account,
    )

    print(
        "RUN ID:",
        summary[
            "run_id"
        ],
    )

    print(
        "Status:",
        summary[
            "status"
        ],
    )

    print(
        "Acceptance:",
        summary[
            "acceptance_decision"
        ],
    )

    print(
        "Run directory:",
        summary[
            "run_dir"
        ],
    )


def main():

    asyncio.run(
        _main_async()
    )


if __name__ == "__main__":
    main()
