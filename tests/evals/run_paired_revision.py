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


CANDIDATE_SCHEMA = {
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
        "summary": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "rubric",
        "summary",
    ],
    "additionalProperties": False,
}


PAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_a": CANDIDATE_SCHEMA,
        "candidate_b": CANDIDATE_SCHEMA,
        "preferred": {
            "type": "string",
            "enum": [
                "A",
                "B",
                "tie",
            ],
        },
        "comparison_reason": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "candidate_a",
        "candidate_b",
        "preferred",
        "comparison_reason",
    ],
    "additionalProperties": False,
}


def calculate_score(candidate: dict):
    scores = {}

    for dimension in DIMENSIONS:
        item = candidate["rubric"][dimension]

        score = item["score"]

        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or not 0 <= score <= 4
        ):
            raise ValueError(
                f"Invalid score for {dimension}: {score!r}"
            )

        reason = str(
            item["reason"]
        ).strip()

        if not reason:
            raise ValueError(
                f"Missing reason for {dimension}"
            )

        scores[dimension] = score

    normalized = (
        sum(scores.values())
        / (4 * len(DIMENSIONS))
    )

    return round(normalized, 6), scores


def load_iteration(
    run_dir: Path,
    iteration: int,
):
    claude_report = (
        run_dir
        / f"claude_iteration_{iteration}.md"
    ).read_text(
        encoding="utf-8"
    )

    codex_report = (
        run_dir
        / f"codex_iteration_{iteration}.md"
    ).read_text(
        encoding="utf-8"
    )

    if not claude_report.strip():
        raise RuntimeError(
            f"Claude iteration {iteration} is empty"
        )

    if not codex_report.strip():
        raise RuntimeError(
            f"Codex iteration {iteration} is empty"
        )

    return {
        "claude": claude_report,
        "codex": codex_report,
    }


def candidate_text(reports: dict):
    return f"""
CLAUDE REPORT:

{reports["claude"]}


CODEX REPORT:

{reports["codex"]}
"""


def build_prompt(
    topic: str,
    candidate_a: dict,
    candidate_b: dict,
):
    return f"""
You are an independent research quality evaluator.

Evaluate two candidate research outputs for the SAME task.

Do not assume Candidate A or Candidate B is newer, revised, or preferred.
Judge only the supplied content.

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


Score EACH candidate independently on EACH dimension from 0 to 4.

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

- Evaluate A and B independently before comparing them.
- Use only supplied material.
- Do not use external tools.
- Do not infer missing evidence.
- Do not reward verbosity by itself.
- Do not calculate an overall numeric score.
- Explain every dimension score briefly.
- After scoring both candidates, select A, B, or tie.
- A tie is valid when differences are not materially meaningful.
- Return only the requested structured result.
"""


async def evaluate_once(
    prompt: str,
    run_dir: Path,
):
    raw = await run_claude(
        prompt=prompt,
        cwd=run_dir,
        timeout=300,
        max_turns=5,
        tool_profile="reasoning",
        system_prompt=(
            "You are an independent paired research "
            "quality evaluator in an unattended software "
            "pipeline. Do not use tools. Evaluate only "
            "the supplied candidates."
        ),
        json_schema=PAIR_SCHEMA,
    )

    return json.loads(raw)


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

    if args.repeats < 1:
        raise ValueError(
            "--repeats must be >= 1"
        )

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
        after_is_a = (
            repeat % 2 == 0
        )

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

            a_score, a_dimensions = (
                calculate_score(
                    data["candidate_a"]
                )
            )

            b_score, b_dimensions = (
                calculate_score(
                    data["candidate_b"]
                )
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

        if after_is_a:
            before_score = b_score
            after_score = a_score

            before_dimensions = (
                b_dimensions
            )

            after_dimensions = (
                a_dimensions
            )

            preferred_raw = (
                data["preferred"]
            )

            if preferred_raw == "A":
                preferred_iteration = (
                    args.after
                )
            elif preferred_raw == "B":
                preferred_iteration = (
                    args.before
                )
            else:
                preferred_iteration = (
                    "tie"
                )

        else:
            before_score = a_score
            after_score = b_score

            before_dimensions = (
                a_dimensions
            )

            after_dimensions = (
                b_dimensions
            )

            preferred_raw = (
                data["preferred"]
            )

            if preferred_raw == "A":
                preferred_iteration = (
                    args.before
                )
            elif preferred_raw == "B":
                preferred_iteration = (
                    args.after
                )
            else:
                preferred_iteration = (
                    "tie"
                )

        delta = round(
            after_score - before_score,
            6,
        )

        dimension_delta = {
            dimension:
                (
                    after_dimensions[
                        dimension
                    ]
                    - before_dimensions[
                        dimension
                    ]
                )
            for dimension in DIMENSIONS
        }

        results.append(
            {
                "repeat": repeat,
                "candidate_a_iteration":
                    a_iteration,
                "candidate_b_iteration":
                    b_iteration,
                "before_score":
                    before_score,
                "after_score":
                    after_score,
                "delta":
                    delta,
                "before_dimensions":
                    before_dimensions,
                "after_dimensions":
                    after_dimensions,
                "dimension_delta":
                    dimension_delta,
                "preferred_raw":
                    preferred_raw,
                "preferred_iteration":
                    preferred_iteration,
                "comparison_reason":
                    data[
                        "comparison_reason"
                    ],
                "raw_result":
                    data,
            }
        )

        print(
            f"  before={before_score:.4f} "
            f"after={after_score:.4f} "
            f"delta={delta:+.4f} "
            f"preferred="
            f"{preferred_iteration}",
            flush=True,
        )

        print(
            "  dimension_delta=",
            dimension_delta,
            flush=True,
        )

    if not results:
        raise RuntimeError(
            "No successful paired evaluations"
        )

    deltas = [
        item["delta"]
        for item in results
    ]

    mean_delta = statistics.mean(
        deltas
    )

    delta_stdev = (
        statistics.stdev(
            deltas
        )
        if len(deltas) >= 2
        else 0.0
    )

    after_wins = sum(
        item["preferred_iteration"]
        == args.after
        for item in results
    )

    before_wins = sum(
        item["preferred_iteration"]
        == args.before
        for item in results
    )

    ties = sum(
        item["preferred_iteration"]
        == "tie"
        for item in results
    )

    positive_delta = sum(
        item["delta"] > 0
        for item in results
    )

    zero_delta = sum(
        item["delta"] == 0
        for item in results
    )

    negative_delta = sum(
        item["delta"] < 0
        for item in results
    )

    dimension_summary = {}

    for dimension in DIMENSIONS:
        values = [
            item[
                "dimension_delta"
            ][dimension]
            for item in results
        ]

        dimension_summary[
            dimension
        ] = {
            "values": values,
            "mean_delta": round(
                statistics.mean(
                    values
                ),
                6,
            ),
            "positive": sum(
                value > 0
                for value in values
            ),
            "zero": sum(
                value == 0
                for value in values
            ),
            "negative": sum(
                value < 0
                for value in values
            ),
        }

    summary = {
        "source_run_id":
            args.run_id,
        "before_iteration":
            args.before,
        "after_iteration":
            args.after,
        "method":
            "paired_rubric_v1",
        "position_balancing":
            "alternating_A_B",
        "requested_repeats":
            args.repeats,
        "successful_repeats":
            len(results),
        "failed_repeats":
            len(errors),
        "deltas":
            deltas,
        "mean_delta":
            round(
                mean_delta,
                6,
            ),
        "delta_stdev":
            round(
                delta_stdev,
                6,
            ),
        "minimum_delta":
            min(deltas),
        "maximum_delta":
            max(deltas),
        "after_wins":
            after_wins,
        "before_wins":
            before_wins,
        "ties":
            ties,
        "positive_delta_count":
            positive_delta,
        "zero_delta_count":
            zero_delta,
        "negative_delta_count":
            negative_delta,
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
        / (
            "paired_revision_"
            f"{stamp}.json"
        )
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
    print("=" * 64)
    print("PAIRED REVISION SUMMARY")
    print("=" * 64)

    print(
        "deltas:",
        deltas,
    )

    print(
        "success:",
        f"{len(results)}/{args.repeats}",
    )

    print(
        "mean_delta:",
        f"{mean_delta:+.4f}",
    )

    print(
        "delta_stdev:",
        f"{delta_stdev:.4f}",
    )

    print(
        "delta_range:",
        f"{min(deltas):+.4f}",
        "..",
        f"{max(deltas):+.4f}",
    )

    print()

    print(
        "preference:",
        f"after={after_wins}",
        f"before={before_wins}",
        f"tie={ties}",
    )

    print(
        "numeric delta:",
        f"positive={positive_delta}",
        f"zero={zero_delta}",
        f"negative={negative_delta}",
    )

    print()
    print("DIMENSION DELTAS")

    for dimension in DIMENSIONS:
        stats = (
            dimension_summary[
                dimension
            ]
        )

        print(
            f"{dimension:25} "
            f"{stats['values']} "
            f"mean={stats['mean_delta']:+.3f} "
            f"+={stats['positive']} "
            f"0={stats['zero']} "
            f"-={stats['negative']}"
        )

    print()
    print(
        "result:",
        output,
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
