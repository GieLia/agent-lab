import asyncio
import faulthandler
import json
import os
import re
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from workers.claude_worker import run_claude
from workers.codex_worker import run_codex


faulthandler.enable()


RUN_ROOT = Path(
    "/opt/agent-lab/runs"
)

STATE_ROOT = Path(
    "/opt/agent-lab/state"
)

CHECKPOINT_DB = (
    STATE_ROOT / "checkpoints.sqlite"
)


QUALITY_THRESHOLD = float(
    os.getenv(
        "QUALITY_THRESHOLD",
        "0.80",
    )
)

MAX_ITERATIONS = int(
    os.getenv(
        "MAX_ITERATIONS",
        "2",
    )
)


class ResearchState(
    TypedDict,
    total=False,
):
    topic: str
    run_id: str

    iteration: int
    max_iterations: int
    quality_threshold: float

    claude_result: str
    codex_result: str

    critique: str
    missing_evidence: list[str]
    quality_score: float

    final_result: str
    status: str


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def get_run_dir(
    run_id: str,
) -> Path:

    run_dir = (
        RUN_ROOT / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return run_dir


def write_status(
    state: ResearchState,
    phase: str,
    extra: dict | None = None,
) -> None:

    run_dir = get_run_dir(
        state["run_id"]
    )

    data = {
        "time": now(),
        "phase": phase,
        "run_id": state["run_id"],
        "topic": state.get(
            "topic",
            "",
        ),
        "iteration": state.get(
            "iteration",
            0,
        ),
        "max_iterations": state.get(
            "max_iterations",
            MAX_ITERATIONS,
        ),
        "quality_score": state.get(
            "quality_score"
        ),
        "quality_threshold": state.get(
            "quality_threshold",
            QUALITY_THRESHOLD,
        ),
    }

    if extra:
        data.update(extra)

    (
        run_dir / "status.json"
    ).write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def extract_json(
    text: str,
) -> dict:

    text = text.strip()

    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.I,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if (
        start >= 0
        and end > start
    ):
        return json.loads(
            text[start:end + 1]
        )

    raise ValueError(
        "Critic returned no valid JSON"
    )


async def research_node(
    state: ResearchState,
) -> dict:

    run_dir = get_run_dir(
        state["run_id"]
    )

    iteration = (
        state.get(
            "iteration",
            0,
        )
        + 1
    )

    print()
    print(
        f"[{now()}] "
        f"Research iteration "
        f"{iteration}"
    )

    write_status(
        {
            **state,
            "iteration": iteration,
        },
        "research",
    )

    claude_revision = ""
    codex_revision = ""

    if state.get("critique"):

        critique = str(
            state["critique"]
        )

        missing_evidence = json.dumps(
            state.get(
                "missing_evidence",
                [],
            ),
            ensure_ascii=False,
            indent=2,
        )

        previous_quality = state.get(
            "quality_score"
        )

        previous_claude = str(
            state.get(
                "claude_result",
                "",
            )
        ).strip()

        previous_codex = str(
            state.get(
                "codex_result",
                "",
            )
        ).strip()

        claude_revision = f"""
THIS IS A REVISION, NOT A NEW REPORT.

Previous quality score:

{previous_quality}

YOUR PREVIOUS REPORT:

{previous_claude}

CRITIC FEEDBACK:

{critique}

MISSING EVIDENCE:

{missing_evidence}

Revise YOUR previous report.

Rules:

1. Preserve material that is correct and was not criticized.
2. Fix specifically the weaknesses identified by the critic.
3. Address missing evidence where possible.
4. Do not regenerate the report from scratch.
5. Do not silently remove useful prior findings.
6. Return the complete revised Markdown report.
"""

        codex_revision = f"""
THIS IS A REVISION, NOT A NEW REPORT.

Previous quality score:

{previous_quality}

YOUR PREVIOUS REPORT:

{previous_codex}

CRITIC FEEDBACK:

{critique}

MISSING EVIDENCE:

{missing_evidence}

Revise YOUR previous report.

Rules:

1. Preserve material that is correct and was not criticized.
2. Fix specifically the weaknesses identified by the critic.
3. Address missing evidence where possible.
4. Do not regenerate the report from scratch.
5. Do not silently remove useful prior findings.
6. Return the complete revised Markdown report.
"""

    claude_prompt = f"""
You are Researcher A.

Research independently:

{state["topic"]}

{claude_revision}

Requirements:

1. Identify central questions.
2. Prefer evidence over intuition.
3. Separate facts, assumptions and speculation.
4. Explicitly identify uncertainty.
5. Look for contradictory evidence.
6. Preserve source URLs/references when available.
7. Identify evidence still missing.
8. Produce a structured Markdown report.
"""

    codex_prompt = f"""
You are Researcher B.

Critically research:

{state["topic"]}

{codex_revision}

Requirements:

1. Challenge assumptions.
2. Prefer independently verifiable evidence.
3. Identify contradictions.
4. Identify factual gaps.
5. Preserve source URLs/references when available.
6. Do not agree with Researcher A by default.
7. Produce a structured Markdown report.
"""

    trace_dir = (
        run_dir / "trace"
    )

    trace_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        trace_dir
        / f"iter{iteration}_claude_prompt.txt"
    ).write_text(
        claude_prompt,
        encoding="utf-8",
    )

    (
        trace_dir
        / f"iter{iteration}_codex_prompt.txt"
    ).write_text(
        codex_prompt,
        encoding="utf-8",
    )

    start = time.time()

    claude_task = run_claude(
        claude_prompt,
        run_dir,
        tool_profile="reasoning",
    )

    codex_task = run_codex(
        codex_prompt,
        run_dir,
    )

    results = await asyncio.gather(
        claude_task,
        codex_task,
        return_exceptions=True,
    )

    claude_result = results[0]
    codex_result = results[1]

    errors = {}

    if isinstance(
        claude_result,
        BaseException,
    ):
        errors["claude"] = str(
            claude_result
        )

    if isinstance(
        codex_result,
        BaseException,
    ):
        errors["codex"] = str(
            codex_result
        )

    if (
        not isinstance(
            claude_result,
            BaseException,
        )
        and not str(
            claude_result
        ).strip()
    ):
        errors["claude"] = (
            "Claude returned an empty result"
        )

    if (
        not isinstance(
            codex_result,
            BaseException,
        )
        and not str(
            codex_result
        ).strip()
    ):
        errors["codex"] = (
            "Codex returned an empty result"
        )

    if errors:

        (
            run_dir
            / f"errors_iteration_"
              f"{iteration}.json"
        ).write_text(
            json.dumps(
                errors,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        write_status(
            {
                **state,
                "iteration": iteration,
            },
            "research_failed",
            {
                "errors": errors,
            },
        )

        print()
        print(
            f"[{now()}] "
            f"Research worker failure"
        )

        for (
            worker,
            error,
        ) in errors.items():

            print()
            print(
                f"--- "
                f"{worker.upper()} "
                f"ERROR ---"
            )

            print(error)

        raise RuntimeError(
            f"Research iteration "
            f"{iteration} failed: "
            f"{', '.join(errors.keys())}"
        )

    claude_result = str(
        claude_result
    )

    codex_result = str(
        codex_result
    )

    elapsed = round(
        time.time() - start,
        1,
    )

    print(
        f"[{now()}] "
        f"Research iteration "
        f"{iteration} finished "
        f"in {elapsed}s"
    )

    (
        run_dir
        / f"claude_iteration_"
          f"{iteration}.md"
    ).write_text(
        claude_result,
        encoding="utf-8",
    )

    (
        run_dir
        / f"codex_iteration_"
          f"{iteration}.md"
    ).write_text(
        codex_result,
        encoding="utf-8",
    )

    (
        trace_dir
        / f"iter{iteration}_claude_draft.md"
    ).write_text(
        claude_result,
        encoding="utf-8",
    )

    (
        trace_dir
        / f"iter{iteration}_codex_draft.md"
    ).write_text(
        codex_result,
        encoding="utf-8",
    )

    return {
        "iteration": iteration,
        "claude_result":
            claude_result,
        "codex_result":
            codex_result,
        "status":
            "researched",
    }


async def critic_node(
    state: ResearchState,
) -> dict:

    run_dir = get_run_dir(
        state["run_id"]
    )

    print(
        f"[{now()}] "
        f"Starting critic..."
    )

    write_status(
        state,
        "critic",
    )

    prompt = f"""
You are an independent research quality controller.

TOPIC:

{state["topic"]}


CLAUDE REPORT:

{state["claude_result"]}


CODEX REPORT:

{state["codex_result"]}


Evaluate the supplied research only.

Score EACH dimension independently from 0 to 4.

General anchors:

0 = absent, fundamentally wrong, or unsupported
1 = major deficiencies
2 = partial or mixed quality
3 = strong with minor material gaps
4 = consistently strong and well supported

Dimensions:

factual_support:
Are important factual claims supported by the supplied material?

source_quality:
Are sources appropriate, credible and relevant?

source_coverage:
Does the research cover the evidence needed for the task?

contradiction_handling:
Are disagreements, conflicting evidence and alternative explanations handled?

uncertainty_hygiene:
Are unknowns, assumptions, speculation and evidence gaps clearly separated?

task_completion:
Does the research actually answer the requested task?

Rules:

- Score each dimension independently.
- Do not calculate an overall score.
- Do not infer evidence that is not supplied.
- Do not reward length by itself.
- Do not use external tools.
- Explain each dimension score briefly.
- Identify remaining missing evidence.
- Return only the requested structured result.
"""

    rubric_dimensions = (
        "factual_support",
        "source_quality",
        "source_coverage",
        "contradiction_handling",
        "uncertainty_hygiene",
        "task_completion",
    )

    rubric_item_schema = {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 4,
            },
            "reason": {
                "type": "string",
                "minLength": 1,
            },
        },
        "required": [
            "score",
            "reason",
        ],
        "additionalProperties": False,
    }

    critic_schema = {
        "type": "object",
        "properties": {
            "rubric": {
                "type": "object",
                "properties": {
                    dimension:
                        rubric_item_schema
                    for dimension
                    in rubric_dimensions
                },
                "required":
                    list(rubric_dimensions),
                "additionalProperties":
                    False,
            },
            "critique": {
                "type": "string",
            },
            "missing_evidence": {
                "type": "array",
                "items": {
                    "type": "string",
                },
            },
        },
        "required": [
            "rubric",
            "critique",
            "missing_evidence",
        ],
        "additionalProperties": False,
    }

    raw = await run_claude(
        prompt,
        run_dir,
        max_turns=5,
        tool_profile="reasoning",
        system_prompt=(
            "You are an independent research "
            "quality evaluator in an unattended "
            "software pipeline. Do not use tools. "
            "Evaluate only the material provided "
            "in the user prompt."
        ),
        json_schema=critic_schema,
    )

    trace_dir = (
        run_dir / "trace"
    )

    trace_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        trace_dir
        / (
            f"critic_iteration_"
            f"{state['iteration']}_raw.txt"
        )
    ).write_text(
        raw,
        encoding="utf-8",
    )

    data = extract_json(
        raw
    )

    rubric = data.get(
        "rubric"
    )

    if not isinstance(
        rubric,
        dict,
    ):
        raise ValueError(
            "Critic returned no valid rubric"
        )

    rubric_scores = {}

    for dimension in rubric_dimensions:

        item = rubric.get(
            dimension
        )

        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Missing rubric dimension: "
                f"{dimension}"
            )

        raw_score = item.get(
            "score"
        )

        if (
            isinstance(raw_score, bool)
            or not isinstance(
                raw_score,
                int,
            )
            or not 0 <= raw_score <= 4
        ):
            raise ValueError(
                "Invalid rubric score for "
                f"{dimension}: "
                f"{raw_score!r}"
            )

        reason = str(
            item.get(
                "reason",
                "",
            )
        ).strip()

        if not reason:
            raise ValueError(
                "Missing rubric reason for "
                f"{dimension}"
            )

        rubric_scores[
            dimension
        ] = raw_score

    score = round(
        sum(
            rubric_scores.values()
        )
        / (
            4
            * len(
                rubric_dimensions
            )
        ),
        6,
    )

    critique = str(
        data.get(
            "critique",
            "",
        )
    )

    missing_raw = data.get(
        "missing_evidence",
        [],
    )

    if isinstance(
        missing_raw,
        list,
    ):
        missing = [
            str(item)
            for item
            in missing_raw
        ]

    else:
        missing = [
            str(missing_raw)
        ]

    iteration = state[
        "iteration"
    ]

    (
        run_dir
        / f"critic_iteration_"
          f"{iteration}.json"
    ).write_text(
        json.dumps(
            {
                "quality_score":
                    score,
                "rubric":
                    rubric,
                "dimension_scores":
                    rubric_scores,
                "critique":
                    critique,
                "missing_evidence":
                    missing,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"[{now()}] "
        f"Quality score = "
        f"{score:.2f}"
    )

    return {
        "quality_score":
            score,
        "critique":
            critique,
        "missing_evidence":
            missing,
        "status":
            "critic_complete",
    }


def route_after_critic(
    state: ResearchState,
) -> str:

    score = state[
        "quality_score"
    ]

    iteration = state[
        "iteration"
    ]

    threshold = state[
        "quality_threshold"
    ]

    max_iterations = state[
        "max_iterations"
    ]

    if score >= threshold:

        print(
            f"[{now()}] "
            f"PASS: "
            f"{score:.2f} "
            f">= "
            f"{threshold:.2f}"
        )

        return "synthesis"

    if (
        iteration
        >= max_iterations
    ):

        print(
            f"[{now()}] "
            f"STOP: max iterations "
            f"reached "
            f"({iteration}/"
            f"{max_iterations})"
        )

        return "synthesis"

    print(
        f"[{now()}] "
        f"RETRY: "
        f"{score:.2f} "
        f"< "
        f"{threshold:.2f}"
    )

    return "research"


async def synthesis_node(
    state: ResearchState,
) -> dict:

    run_dir = get_run_dir(
        state["run_id"]
    )

    print(
        f"[{now()}] "
        f"Starting synthesis..."
    )

    write_status(
        state,
        "synthesis",
    )

    prompt = f"""
You are the senior research editor.

TOPIC:

{state["topic"]}


CLAUDE REPORT:

{state["claude_result"]}


CODEX REPORT:

{state["codex_result"]}


CRITIC ASSESSMENT:

Quality score:

{state["quality_score"]}


Critique:

{state["critique"]}


Missing evidence:

{json.dumps(
    state.get(
        "missing_evidence",
        [],
    ),
    ensure_ascii=False,
    indent=2,
)}


Produce the final Markdown report.

Requirements:

1. Merge only defensible findings.
2. Explicitly identify agreement.
3. Explicitly identify disagreement.
4. Reject unsupported claims.
5. Separate:
   - verified facts;
   - interpretation;
   - speculation.
6. Preserve useful source references.
7. State remaining evidence gaps.
8. Give confidence levels.
9. Recommend the next research question.
"""

    result = await run_claude(
        prompt,
        run_dir,
        tool_profile="reasoning",
        system_prompt=(
            "You are a senior research editor "
            "working in an unattended pipeline. "
            "Use only the material supplied in "
            "the user prompt. Do not use tools."
        ),
    )

    (
        run_dir / "final.md"
    ).write_text(
        result,
        encoding="utf-8",
    )

    print(
        f"[{now()}] "
        f"Synthesis finished"
    )

    return {
        "final_result":
            result,
        "status":
            "finished",
    }


def build_graph(
    checkpointer,
):

    builder = StateGraph(
        ResearchState
    )

    builder.add_node(
        "research",
        research_node,
    )

    builder.add_node(
        "critic",
        critic_node,
    )

    builder.add_node(
        "synthesis",
        synthesis_node,
    )

    builder.add_edge(
        START,
        "research",
    )

    builder.add_edge(
        "research",
        "critic",
    )

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "research":
                "research",
            "synthesis":
                "synthesis",
        },
    )

    builder.add_edge(
        "synthesis",
        END,
    )

    return builder.compile(
        checkpointer=checkpointer
    )


async def new_run(
    graph,
):

    topic = os.getenv(
        "TOPIC",
        (
            "Kokie praktiniai principai "
            "svarbiausi kuriant patikimą "
            "autonominę LLM tyrimų sistemą?"
        ),
    )

    run_id = os.getenv(
        "RUN_ID"
    )

    if not run_id:
        run_id = str(
            uuid.uuid4()
        )

    run_dir = get_run_dir(
        run_id
    )

    initial_state: ResearchState = {
        "topic":
            topic,
        "run_id":
            run_id,
        "iteration":
            0,
        "max_iterations":
            MAX_ITERATIONS,
        "quality_threshold":
            QUALITY_THRESHOLD,
        "status":
            "starting",
    }

    (
        run_dir / "metadata.json"
    ).write_text(
        json.dumps(
            {
                "run_id":
                    run_id,
                "topic":
                    topic,
                "created":
                    now(),
                "max_iterations":
                    MAX_ITERATIONS,
                "quality_threshold":
                    QUALITY_THRESHOLD,
                "checkpoint_db":
                    str(
                        CHECKPOINT_DB
                    ),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_status(
        initial_state,
        "starting",
    )

    config = {
        "configurable": {
            "thread_id":
                run_id
        }
    }

    print()
    print("=" * 70)
    print(
        "AI AGENT LAB "
        "— LOOP V3 PERSISTENT"
    )
    print("=" * 70)

    print(
        f"RUN ID: "
        f"{run_id}"
    )

    print(
        f"THREAD ID: "
        f"{run_id}"
    )

    print(
        f"MAX ITERATIONS: "
        f"{MAX_ITERATIONS}"
    )

    print(
        f"QUALITY THRESHOLD: "
        f"{QUALITY_THRESHOLD}"
    )

    print(
        f"CHECKPOINT DB: "
        f"{CHECKPOINT_DB}"
    )

    print()

    try:

        result = await graph.ainvoke(
            initial_state,
            config=config,
        )

    except Exception as exc:

        snapshot = await graph.aget_state(
            config
        )

        write_status(
            {
                **initial_state,
                **snapshot.values,
            },
            "failed",
            {
                "error":
                    str(exc),
            },
        )

        print()
        print("=" * 70)
        print("FAILED")
        print("=" * 70)

        print(
            f"RUN ID: "
            f"{run_id}"
        )

        print(
            f"CHECKPOINT SAVED: "
            f"YES"
        )

        print(
            f"ERROR: "
            f"{exc}"
        )

        print()
        print(
            "Use the same RUN_ID "
            "for diagnostics/resume."
        )

        raise

    write_status(
        result,
        "finished",
        {
            "finished":
                True,
        },
    )

    snapshot = await graph.aget_state(
        config
    )

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print(
        f"RUN: "
        f"{run_dir}"
    )

    print(
        f"THREAD: "
        f"{run_id}"
    )

    print(
        f"ITERATIONS: "
        f"{result['iteration']}"
    )

    print(
        f"QUALITY: "
        f"{result['quality_score']:.2f}"
    )

    print(
        f"CHECKPOINT STATE: "
        f"{snapshot.values.get('status')}"
    )


async def show_state(
    graph,
    run_id: str,
):

    config = {
        "configurable": {
            "thread_id":
                run_id
        }
    }

    snapshot = await graph.aget_state(
        config
    )

    if not snapshot.values:

        print(
            "No checkpoint found "
            f"for RUN_ID={run_id}"
        )

        return

    print()
    print("=" * 70)
    print("CHECKPOINT STATE")
    print("=" * 70)

    print(
        "RUN ID:",
        snapshot.values.get(
            "run_id"
        ),
    )

    print(
        "TOPIC:",
        snapshot.values.get(
            "topic"
        ),
    )

    print(
        "ITERATION:",
        snapshot.values.get(
            "iteration"
        ),
    )

    print(
        "QUALITY:",
        snapshot.values.get(
            "quality_score"
        ),
    )

    print(
        "STATUS:",
        snapshot.values.get(
            "status"
        ),
    )

    print(
        "NEXT:",
        snapshot.next,
    )


async def main():

    STATE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    async with (
        AsyncSqliteSaver
        .from_conn_string(
            str(CHECKPOINT_DB)
        )
    ) as checkpointer:

        graph = build_graph(
            checkpointer
        )

        inspect_run = os.getenv(
            "INSPECT_RUN"
        )

        if inspect_run:

            await show_state(
                graph,
                inspect_run,
            )

            return

        await new_run(
            graph
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
