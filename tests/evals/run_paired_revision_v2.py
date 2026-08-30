import argparse
import asyncio
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.workers.claude_worker import run_claude


RUNS_DIR = ROOT / "runs"
RESULTS_DIR = ROOT / "tests" / "evals" / "results"

DIMENSIONS = (
    "factual_support",
    "source_quality",
    "source_coverage",
    "contradiction_handling",
    "uncertainty_hygiene",
    "task_completion",
)

CHOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {
            "type": "string",
            "enum": [
                "A",
                "B",
                "tie",
            ],
        },
        "reason": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "winner",
        "reason",
    ],
    "additionalProperties": False,
}

PAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "dimensions": {
            "type": "object",
            "properties": {
                dimension: CHOICE_SCHEMA
                for dimension in DIMENSIONS
            },
            "required": list(DIMENSIONS),
            "additionalProperties": False,
        },
        "overall": CHOICE_SCHEMA,
    },
    "required": [
        "dimensions",
        "overall",
    ],
    "additionalProperties": False,
}


def load_iteration(
    run_dir: Path,
    iteration: int,
):
    claude = (
        run_dir
        / f"claude_iteration_{iteration}.md"
    ).read_text(
        encoding="utf-8"
    )

    codex = (
        run_dir
        / f"codex_iteration_{iteration}.md"
    ).read_text(
        encoding="utf-8"
    )

    if not claude.strip():
        raise RuntimeError(
            f"Claude iteration {iteration} empty"
        )

    if not codex.strip():
        raise RuntimeError(
            f"Codex iteration {iteration} empty"
        )

    return {
        "claude": claude,
        "codex": codex,
    }


def candidate_text(reports):
    return f"""
CLAUDE REPORT:

{reports["claude"]}


CODEX REPORT:

{reports["codex"]}
"""


def build_prompt(
    topic,
    candidate_a,
    candidate_b,
):
    return f"""
You are an independent comparative research evaluator.

Both candidates answer the SAME task.

TOPIC:

{topic}


============================================================
CANDIDATE A
============================================================

{candidate_text(candidate_a)}


============================================================
CANDIDATE B
============================================================

{candidate_text(candidate_b)}


Compare A and B directly.

For EACH dimension choose exactly:

A
B
tie

Dimensions:

factual_support
source_quality
source_coverage
contradiction_handling
uncertainty_hygiene
task_completion

Rules:

- Judge only material differences.
- Use only supplied content.
- Do not use external tools.
- Do not assume either candidate is newer.
- Do not infer which candidate is a revision.
- Do not reward length, verbosity, formatting, or repetition.
- More text is not better unless it adds materially useful evidence or reasoning.
- Prefer tie when differences are marginal or stylistic.
- Evaluate each dimension independently.
- Then choose an overall winner: A, B, or tie.
- Explain each decision briefly.
- Return only the requested structured result.
"""


def resolve_claude_account() -> str:

    value = (
        os.getenv(
            "CLAUDE_EVAL_ACCOUNT"
        )
        or os.getenv(
            "CLAUDE_ACCOUNT"
        )
        or "primary"
    )

    value = value.strip().lower()

    aliases = {
        "a": "primary",
        "primary": "primary",
        "b": "secondary",
        "secondary": "secondary",
    }

    return aliases.get(
        value,
        value,
    )


async def evaluate_once(
    prompt,
    run_dir,
):
    raw = await run_claude(
        prompt=prompt,
        cwd=run_dir,
        timeout=300,
        max_turns=5,
        tool_profile="reasoning",
        account=resolve_claude_account(),
        system_prompt=(
            "You are a comparative research evaluator. "
            "Do not use tools. Ignore verbosity and "
            "presentation differences. Judge only "
            "material quality differences."
        ),
        json_schema=PAIR_SCHEMA,
    )

    return json.loads(raw)


def map_winner(
    winner,
    *,
    after_is_a,
    before_iteration,
    after_iteration,
):
    if winner == "tie":
        return "tie"

    if after_is_a:
        return (
            after_iteration
            if winner == "A"
            else before_iteration
        )

    return (
        before_iteration
        if winner == "A"
        else after_iteration
    )


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-id",
        required=True,
    )

    parser.add_argument(
        "--before",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--after",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=6,
    )

    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id

    metadata = json.loads(
        (run_dir / "metadata.json").read_text(
            encoding="utf-8"
        )
    )

    before_reports = load_iteration(
        run_dir,
        args.before,
    )

    after_reports = load_iteration(
        run_dir,
        args.after,
    )

    results = []
    errors = []

    for repeat in range(
        1,
        args.repeats + 1,
    ):
        after_is_a = repeat % 2 == 0

        if after_is_a:
            candidate_a = after_reports
            candidate_b = before_reports
            a_iteration = args.after
            b_iteration = args.before
        else:
            candidate_a = before_reports
            candidate_b = after_reports
            a_iteration = args.before
            b_iteration = args.after

        print(
            f"[{repeat}/{args.repeats}] "
            f"A=iter{a_iteration} "
            f"B=iter{b_iteration}",
            flush=True,
        )

        prompt = build_prompt(
            metadata["topic"],
            candidate_a,
            candidate_b,
        )

        try:
            data = await evaluate_once(
                prompt,
                run_dir,
            )

        except Exception as exc:
            errors.append(
                {
                    "repeat": repeat,
                    "error": str(exc),
                }
            )

            first_line = next(
                (
                    line.strip()
                    for line
                    in str(exc).splitlines()
                    if line.strip()
                ),
                type(exc).__name__,
            )

            print(
                f"  ERROR: {first_line}",
                flush=True,
            )

            continue

        overall = map_winner(
            data["overall"]["winner"],
            after_is_a=after_is_a,
            before_iteration=args.before,
            after_iteration=args.after,
        )

        dimension_winners = {}

        for dimension in DIMENSIONS:
            dimension_winners[
                dimension
            ] = map_winner(
                data[
                    "dimensions"
                ][dimension]["winner"],
                after_is_a=after_is_a,
                before_iteration=args.before,
                after_iteration=args.after,
            )

        results.append(
            {
                "repeat": repeat,
                "candidate_a_iteration":
                    a_iteration,
                "candidate_b_iteration":
                    b_iteration,
                "overall_winner":
                    overall,
                "dimension_winners":
                    dimension_winners,
                "raw_result":
                    data,
            }
        )

        print(
            "  overall=",
            overall,
            flush=True,
        )

        print(
            "  dimensions=",
            dimension_winners,
            flush=True,
        )

    if not results:
        raise RuntimeError(
            "No successful evaluations"
        )

    after_wins = sum(
        item["overall_winner"]
        == args.after
        for item in results
    )

    before_wins = sum(
        item["overall_winner"]
        == args.before
        for item in results
    )

    ties = sum(
        item["overall_winner"]
        == "tie"
        for item in results
    )

    dimension_summary = {}

    for dimension in DIMENSIONS:
        values = [
            item[
                "dimension_winners"
            ][dimension]
            for item in results
        ]

        dimension_summary[
            dimension
        ] = {
            "after": sum(
                value == args.after
                for value in values
            ),
            "before": sum(
                value == args.before
                for value in values
            ),
            "tie": sum(
                value == "tie"
                for value in values
            ),
            "values": values,
        }

    payload = {
        "source_run_id":
            args.run_id,
        "before_iteration":
            args.before,
        "after_iteration":
            args.after,
        "method":
            "paired_comparative_v2",
        "evaluator": {
            "provider":
                "claude",
            "account":
                resolve_claude_account(),
        },
        "position_balancing":
            "alternating_A_B",
        "requested_repeats":
            args.repeats,
        "successful_repeats":
            len(results),
        "failed_repeats":
            len(errors),
        "after_wins":
            after_wins,
        "before_wins":
            before_wins,
        "ties":
            ties,
        "dimension_summary":
            dimension_summary,
        "errors":
            errors,
        "results":
            results,
    }

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    output = (
        RESULTS_DIR
        / f"paired_revision_v2_{stamp}.json"
    )

    output.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 64)
    print("PAIRED COMPARATIVE V2 SUMMARY")
    print("=" * 64)

    print(
        "success:",
        f"{len(results)}/{args.repeats}",
    )

    print(
        "overall:",
        f"after={after_wins}",
        f"before={before_wins}",
        f"tie={ties}",
    )

    print()
    print("DIMENSIONS")

    for dimension in DIMENSIONS:
        stats = dimension_summary[
            dimension
        ]

        print(
            f"{dimension:25} "
            f"after={stats['after']} "
            f"before={stats['before']} "
            f"tie={stats['tie']}"
        )

    print()
    print("result:", output)


if __name__ == "__main__":
    asyncio.run(main())
