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

from workers.claude_worker import run_claude
from workers.codex_worker import run_codex


faulthandler.enable()

RUN_ROOT = Path("/opt/agent-lab/runs")

QUALITY_THRESHOLD = float(
    os.getenv("QUALITY_THRESHOLD", "0.80")
)

MAX_ITERATIONS = int(
    os.getenv("MAX_ITERATIONS", "2")
)


class ResearchState(TypedDict, total=False):
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
    return datetime.now(timezone.utc).isoformat()


def get_run_dir(run_id: str) -> Path:
    run_dir = RUN_ROOT / run_id
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
        "topic": state["topic"],
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


def extract_json(text: str) -> dict:
    """
    Recover JSON even if the model wraps it
    in Markdown code fences.
    """

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

    if start >= 0 and end > start:
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
        f"Research iteration {iteration}"
    )

    state_for_status = {
        **state,
        "iteration": iteration,
    }

    write_status(
        state_for_status,
        "research",
    )

    previous_feedback = ""

    if state.get("critique"):
        previous_feedback = f"""
THIS IS A RESEARCH RETRY.

Previous critic feedback:

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

Improve specifically on these weaknesses.
Do not simply repeat the previous report.
"""

    claude_prompt = f"""
You are Researcher A.

Research independently:

{state["topic"]}

{previous_feedback}

Requirements:

1. Identify central questions.
2. Prefer evidence over intuition.
3. Separate facts, assumptions and speculation.
4. Explicitly identify uncertainty.
5. Look for contradictory evidence.
6. Preserve source URLs/references when available.
7. Identify evidence that is still missing.
8. Produce a structured Markdown report.
"""

    codex_prompt = f"""
You are Researcher B.

Critically research:

{state["topic"]}

{previous_feedback}

Requirements:

1. Challenge assumptions.
2. Prefer independently verifiable evidence.
3. Identify contradictions.
4. Identify factual gaps.
5. Preserve source URLs/references when available.
6. Do not agree with Researcher A by default.
7. Produce a structured Markdown report.
"""

    start = time.time()

    claude_task = run_claude(
        claude_prompt,
        run_dir,
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

    claude_result, codex_result = results

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

    if errors:
        error_file = (
            run_dir
            / f"errors_iteration_{iteration}.json"
        )

        error_file.write_text(
            json.dumps(
                errors,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(
            f"[{now()}] "
            f"Research worker failure"
        )

        for worker, error in errors.items():
            print()
            print(
                f"--- "
                f"{worker.upper()} "
                f"ERROR ---"
            )
            print(error)

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
        / f"claude_iteration_{iteration}.md"
    ).write_text(
        claude_result,
        encoding="utf-8",
    )

    (
        run_dir
        / f"codex_iteration_{iteration}.md"
    ).write_text(
        codex_result,
        encoding="utf-8",
    )

    return {
        "iteration": iteration,
        "claude_result": claude_result,
        "codex_result": codex_result,
        "status": "researched",
    }


async def critic_node(
    state: ResearchState,
) -> dict:
    run_dir = get_run_dir(
        state["run_id"]
    )

    print(
        f"[{now()}] Starting critic..."
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


Evaluate the combined research.

Score quality from 0.00 to 1.00.

Evaluate:

- factual support;
- source quality;
- source coverage;
- contradictions;
- unsupported claims;
- important unanswered questions;
- whether more research would materially improve the result.

Return ONLY valid JSON in exactly this structure:

{{
  "quality_score": 0.00,
  "critique": "detailed explanation",
  "missing_evidence": [
    "item 1",
    "item 2"
  ]
}}

Do not use Markdown fences.
"""

    raw = await run_claude(
        prompt,
        run_dir,
    )

    data = extract_json(
        raw
    )

    score = float(
        data["quality_score"]
    )

    score = max(
        0.0,
        min(
            score,
            1.0,
        ),
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
            for item in missing_raw
        ]

    else:
        missing = [
            str(missing_raw)
        ]

    iteration = state[
        "iteration"
    ]

    critic_file = (
        run_dir
        / f"critic_iteration_{iteration}.json"
    )

    critic_file.write_text(
        json.dumps(
            {
                "quality_score": score,
                "critique": critique,
                "missing_evidence": missing,
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
        "quality_score": score,
        "critique": critique,
        "missing_evidence": missing,
        "status": "critic_complete",
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

    if iteration >= max_iterations:
        print(
            f"[{now()}] "
            f"STOP: "
            f"max iterations reached "
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
    )

    (
        run_dir / "final.md"
    ).write_text(
        result,
        encoding="utf-8",
    )

    write_status(
        {
            **state,
            "final_result": result,
        },
        "finished",
        {
            "finished": True,
        },
    )

    print(
        f"[{now()}] "
        f"Synthesis finished"
    )

    return {
        "final_result": result,
        "status": "finished",
    }


def build_graph():
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
            "research": "research",
            "synthesis": "synthesis",
        },
    )

    builder.add_edge(
        "synthesis",
        END,
    )

    return builder.compile()


graph = build_graph()


async def main():
    topic = os.getenv(
        "TOPIC",
        (
            "Kokie praktiniai principai "
            "svarbiausi kuriant patikimą "
            "autonominę LLM tyrimų sistemą?"
        ),
    )

    run_id = str(
        uuid.uuid4()
    )

    run_dir = get_run_dir(
        run_id
    )

    initial_state: ResearchState = {
        "topic": topic,
        "run_id": run_id,
        "iteration": 0,
        "max_iterations": MAX_ITERATIONS,
        "quality_threshold":
            QUALITY_THRESHOLD,
        "status": "starting",
    }

    (
        run_dir / "metadata.json"
    ).write_text(
        json.dumps(
            {
                "run_id": run_id,
                "topic": topic,
                "created": now(),
                "max_iterations":
                    MAX_ITERATIONS,
                "quality_threshold":
                    QUALITY_THRESHOLD,
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

    print()
    print("=" * 70)
    print(
        "AI AGENT LAB — LOOP V2"
    )
    print("=" * 70)
    print(
        f"RUN ID: {run_id}"
    )
    print(
        f"MAX ITERATIONS: "
        f"{MAX_ITERATIONS}"
    )
    print(
        f"QUALITY THRESHOLD: "
        f"{QUALITY_THRESHOLD}"
    )
    print()

    try:
        result = await graph.ainvoke(
            initial_state
        )

    except Exception as exc:
        write_status(
            initial_state,
            "failed",
            {
                "error": str(exc),
            },
        )

        print()
        print("=" * 70)
        print("FAILED")
        print("=" * 70)
        print(str(exc))

        raise

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print(
        f"RUN: {run_dir}"
    )

    print(
        f"ITERATIONS: "
        f"{result['iteration']}"
    )

    print(
        f"QUALITY: "
        f"{result['quality_score']:.2f}"
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
