import asyncio
import json
import time
import uuid

from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from workers.claude_worker import run_claude
from workers.codex_worker import run_codex


RUN_ROOT = Path("/opt/agent-lab/runs")


class ResearchState(TypedDict, total=False):
    topic: str
    run_id: str

    claude_result: str
    codex_result: str

    final_result: str


def get_run_dir(run_id: str) -> Path:

    run_dir = RUN_ROOT / run_id

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return run_dir


async def parallel_research(
    state: ResearchState,
):

    run_dir = get_run_dir(
        state["run_id"]
    )

    topic = state["topic"]

    claude_prompt = f"""
You are Researcher A.

Independently analyze this topic:

{topic}

Requirements:

1. Identify the central questions.
2. Build evidence-based conclusions.
3. Separate facts from assumptions.
4. Explicitly identify uncertainty.
5. Search for contradictory arguments.
6. Preserve useful source references when available.
7. Suggest follow-up research questions.

Return a structured Markdown report.
"""

    codex_prompt = f"""
You are Researcher B.

Independently and critically analyze:

{topic}

Requirements:

1. Identify the key technical and factual questions.
2. Challenge assumptions.
3. Prefer verifiable conclusions.
4. Identify missing evidence.
5. Highlight contradictions and weaknesses.
6. Preserve useful source references when available.
7. Suggest further investigations.

Return a structured Markdown report.
"""

    print("Starting Claude and Codex in parallel...")

    start = time.time()

    claude_task = run_claude(
        claude_prompt,
        run_dir,
    )

    codex_task = run_codex(
        codex_prompt,
        run_dir,
    )

    claude_result, codex_result = (
        await asyncio.gather(
            claude_task,
            codex_task,
        )
    )

    elapsed = round(
        time.time() - start,
        1,
    )

    print(
        f"Parallel research finished "
        f"in {elapsed}s"
    )

    (
        run_dir / "claude.md"
    ).write_text(
        claude_result,
        encoding="utf-8",
    )

    (
        run_dir / "codex.md"
    ).write_text(
        codex_result,
        encoding="utf-8",
    )

    return {
        "claude_result": claude_result,
        "codex_result": codex_result,
    }


async def synthesis(
    state: ResearchState,
):

    run_dir = get_run_dir(
        state["run_id"]
    )

    prompt = f"""
You are the senior research reviewer.

ORIGINAL TOPIC:

{state["topic"]}


================================
RESEARCHER A — CLAUDE
================================

{state["claude_result"]}


================================
RESEARCHER B — CODEX
================================

{state["codex_result"]}


Produce a single high-quality final report.

Requirements:

1. Identify conclusions supported by both researchers.
2. Identify disagreements.
3. Reject unsupported claims.
4. Separate:
   - verified facts
   - interpretation
   - speculation
5. Preserve useful source references.
6. Assign confidence:
   - HIGH
   - MEDIUM
   - LOW
7. List unresolved questions.
8. Propose the next research loop.

Return Markdown only.
"""

    print("Starting synthesis...")

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

    return {
        "final_result": result
    }


def build_graph():

    builder = StateGraph(
        ResearchState
    )

    builder.add_node(
        "parallel_research",
        parallel_research,
    )

    builder.add_node(
        "synthesis",
        synthesis,
    )

    builder.add_edge(
        START,
        "parallel_research",
    )

    builder.add_edge(
        "parallel_research",
        "synthesis",
    )

    builder.add_edge(
        "synthesis",
        END,
    )

    return builder.compile()


graph = build_graph()


async def main():

    topic = (
        "Kokie yra svarbiausi praktiniai "
        "Loop Engineering ir Graph Engineering "
        "principai kuriant autonominę "
        "LLM tyrimų sistemą?"
    )

    run_id = str(
        uuid.uuid4()
    )

    run_dir = get_run_dir(
        run_id
    )

    metadata = {
        "run_id": run_id,
        "topic": topic,
    }

    (
        run_dir / "metadata.json"
    ).write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("AI AGENT LAB")
    print("=" * 70)

    print(
        f"RUN ID: {run_id}"
    )

    print(
        f"TOPIC: {topic}"
    )

    result = await graph.ainvoke(
        {
            "topic": topic,
            "run_id": run_id,
        }
    )

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print(
        f"Results:"
        f" {run_dir}"
    )

    print()
    print(result["final_result"])


if __name__ == "__main__":
    asyncio.run(main())
