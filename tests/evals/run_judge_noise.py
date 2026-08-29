import argparse
import asyncio
import json
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

RUBRIC_ITEM_SCHEMA = {
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

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "rubric": {
            "type": "object",
            "properties": {
                dimension: RUBRIC_ITEM_SCHEMA
                for dimension in DIMENSIONS
            },
            "required": list(DIMENSIONS),
            "additionalProperties": False,
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


def calculate_score(data: dict):
    scores = {}

    for dimension in DIMENSIONS:
        item = data["rubric"][dimension]
        score = item["score"]

        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or not 0 <= score <= 4
        ):
            raise ValueError(
                f"Invalid score for {dimension}: {score!r}"
            )

        if not str(item["reason"]).strip():
            raise ValueError(
                f"Missing reason for {dimension}"
            )

        scores[dimension] = score

    normalized = (
        sum(scores.values())
        / (4 * len(DIMENSIONS))
    )

    return round(normalized, 6), scores


def build_prompt(
    topic: str,
    claude_report: str,
    codex_report: str,
):
    return f"""
You are an independent research quality controller.

TOPIC:

{topic}


CLAUDE REPORT:

{claude_report}


CODEX REPORT:

{codex_report}


Evaluate only the supplied research.

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


async def evaluate_once(
    prompt: str,
    run_dir: Path,
):
    raw = await run_claude(
        prompt=prompt,
        cwd=run_dir,
        timeout=240,
        max_turns=5,
        tool_profile="reasoning",
        system_prompt=(
            "You are an independent research quality "
            "evaluator in an unattended software pipeline. "
            "Do not use tools. Evaluate only the material "
            "provided in the user prompt."
        ),
        json_schema=CRITIC_SCHEMA,
    )

    return json.loads(raw)


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-id",
        required=True,
    )

    parser.add_argument(
        "--iteration",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id

    metadata = json.loads(
        (run_dir / "metadata.json").read_text(
            encoding="utf-8"
        )
    )

    claude_report = (
        run_dir
        / f"claude_iteration_{args.iteration}.md"
    ).read_text(
        encoding="utf-8"
    )

    codex_report = (
        run_dir
        / f"codex_iteration_{args.iteration}.md"
    ).read_text(
        encoding="utf-8"
    )

    if not claude_report.strip():
        raise RuntimeError(
            "Claude fixed draft is empty"
        )

    if not codex_report.strip():
        raise RuntimeError(
            "Codex fixed draft is empty"
        )

    prompt = build_prompt(
        metadata["topic"],
        claude_report,
        codex_report,
    )

    results = []
    errors = []

    for index in range(
        1,
        args.repeats + 1,
    ):
        print(
            f"[{index}/{args.repeats}] critic",
            flush=True,
        )

        try:
            data = await evaluate_once(
                prompt,
                run_dir,
            )

            score, dimension_scores = (
                calculate_score(data)
            )

        except Exception as exc:
            errors.append(
                {
                    "repeat": index,
                    "error": str(exc),
                }
            )

            first_line = next(
                (
                    line.strip()
                    for line in str(exc).splitlines()
                    if line.strip()
                ),
                type(exc).__name__,
            )

            print(
                f"  ERROR: {first_line}",
                flush=True,
            )

            continue

        results.append(
            {
                "repeat": index,
                "quality_score": score,
                "dimension_scores":
                    dimension_scores,
                "rubric": data["rubric"],
                "critique": data["critique"],
                "missing_evidence":
                    data["missing_evidence"],
            }
        )

        print(
            f"  score={score:.4f}",
            dimension_scores,
            flush=True,
        )

    scores = [
        item["quality_score"]
        for item in results
    ]

    if not scores:
        raise RuntimeError(
            "No successful critic evaluations"
        )

    mean = statistics.mean(scores)

    stdev = (
        statistics.stdev(scores)
        if len(scores) >= 2
        else 0.0
    )

    dimension_stats = {}

    for dimension in DIMENSIONS:
        values = [
            item["dimension_scores"][dimension]
            for item in results
        ]

        dimension_stats[dimension] = {
            "values": values,
            "mean": round(
                statistics.mean(values),
                6,
            ),
            "stdev": round(
                statistics.stdev(values),
                6,
            )
            if len(values) >= 2
            else 0.0,
            "minimum": min(values),
            "maximum": max(values),
        }

    summary = {
        "source_run_id": args.run_id,
        "source_iteration": args.iteration,
        "scoring_method":
            "six_dimension_rubric_v1",
        "repeats": args.repeats,
        "successful_repeats": len(scores),
        "failed_repeats": len(errors),
        "scores": scores,
        "mean": round(mean, 6),
        "stdev": round(stdev, 6),
        "minimum": min(scores),
        "maximum": max(scores),
        "range": round(
            max(scores) - min(scores),
            6,
        ),
        "dimension_stats":
            dimension_stats,
        "errors": errors,
        "results": results,
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
        / f"judge_noise_rubric_{stamp}.json"
    )

    output.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("RUBRIC JUDGE NOISE SUMMARY")
    print("=" * 60)

    print("scores:", scores)
    print(
        "success:",
        f"{len(scores)}/{args.repeats}",
    )
    print("failed:", len(errors))
    print(f"mean:   {mean:.4f}")
    print(f"stdev:  {stdev:.4f}")
    print(
        "range:  "
        f"{min(scores):.4f}"
        " .. "
        f"{max(scores):.4f}"
    )
    print(
        "span:   "
        f"{max(scores) - min(scores):.4f}"
    )

    print()
    print("DIMENSION STATS")

    for dimension in DIMENSIONS:
        stats = dimension_stats[dimension]

        print(
            f"{dimension:25} "
            f"{stats['values']} "
            f"mean={stats['mean']:.3f} "
            f"sd={stats['stdev']:.3f}"
        )

    print()
    print("result:", output)


if __name__ == "__main__":
    asyncio.run(main())
