import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "tests" / "evals"
RESULTS_DIR = EVAL_DIR / "results"
CASES_FILE = EVAL_DIR / "cases.yaml"

RUN_EVAL = EVAL_DIR / "run_eval.py"
RUN_PAIRED = (
    EVAL_DIR
    / "run_paired_revision_v2.py"
)

DIMENSIONS = (
    "factual_support",
    "source_quality",
    "source_coverage",
    "contradiction_handling",
    "uncertainty_hygiene",
    "task_completion",
)


def load_cases():
    data = yaml.safe_load(
        CASES_FILE.read_text(
            encoding="utf-8"
        )
    )

    return data["cases"]


def newest_matching(pattern, before):
    files = set(
        RESULTS_DIR.glob(pattern)
    )

    created = files - before

    if len(created) != 1:
        raise RuntimeError(
            f"Expected exactly one new {pattern} "
            f"result, found {len(created)}"
        )

    return created.pop()


def run_pipeline_case(
    case_id,
    *,
    max_iterations,
    timeout,
):
    before = set(
        RESULTS_DIR.glob(
            "baseline_v3_*.json"
        )
    )

    command = [
        sys.executable,
        str(RUN_EVAL),
        "--case",
        case_id,
        "--max-iterations",
        str(max_iterations),
        "--force-iterations",
        "--timeout",
        str(timeout),
    ]

    print()
    print("=" * 70)
    print(
        f"PIPELINE CASE: {case_id}"
    )
    print("=" * 70)

    process = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
    )

    if process.returncode != 0:
        raise RuntimeError(
            f"run_eval failed for {case_id} "
            f"with rc={process.returncode}"
        )

    result_file = newest_matching(
        "baseline_v3_*.json",
        before,
    )

    payload = json.loads(
        result_file.read_text(
            encoding="utf-8"
        )
    )

    cases = payload.get(
        "cases",
        []
    )

    if len(cases) != 1:
        raise RuntimeError(
            "Unexpected baseline case count "
            f"for {case_id}: {len(cases)}"
        )

    result = cases[0]

    if result.get("case_id") != case_id:
        raise RuntimeError(
            "Result case mismatch: "
            f"{result.get('case_id')} "
            f"!= {case_id}"
        )

    if (
        result.get("iterations_scored")
        != max_iterations
    ):
        raise RuntimeError(
            f"{case_id}: expected "
            f"{max_iterations} scored iterations, "
            "got "
            f"{result.get('iterations_scored')}"
        )

    run_id = result.get(
        "run_id"
    )

    if not run_id:
        raise RuntimeError(
            f"{case_id}: missing run_id"
        )

    return result_file, result


def run_paired(
    *,
    run_id,
    before_iteration,
    after_iteration,
    repeats,
):
    before = set(
        RESULTS_DIR.glob(
            "paired_revision_v2_*.json"
        )
    )

    command = [
        sys.executable,
        str(RUN_PAIRED),
        "--run-id",
        run_id,
        "--before",
        str(before_iteration),
        "--after",
        str(after_iteration),
        "--repeats",
        str(repeats),
    ]

    process = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
    )

    if process.returncode != 0:
        raise RuntimeError(
            "paired comparative evaluator "
            f"failed for run_id={run_id}, "
            f"rc={process.returncode}"
        )

    result_file = newest_matching(
        "paired_revision_v2_*.json",
        before,
    )

    payload = json.loads(
        result_file.read_text(
            encoding="utf-8"
        )
    )

    if (
        payload.get("source_run_id")
        != run_id
    ):
        raise RuntimeError(
            "Paired result run_id mismatch: "
            f"{payload.get('source_run_id')} "
            f"!= {run_id}"
        )

    successful = payload.get(
        "successful_repeats"
    )

    failed = payload.get(
        "failed_repeats"
    )

    if successful != repeats:
        raise RuntimeError(
            "Incomplete paired evaluation for "
            f"run_id={run_id}: "
            f"successful={successful}/{repeats}"
        )

    if failed != 0:
        raise RuntimeError(
            "Paired evaluator reported failures "
            f"for run_id={run_id}: "
            f"failed_repeats={failed}"
        )

    return result_file, payload


def case_preference(
    *,
    after_wins,
    before_wins,
):
    if after_wins > before_wins:
        return "after"

    if before_wins > after_wins:
        return "before"

    return "tie"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help=(
            "Case ID. May be supplied multiple "
            "times. Without --case all cases "
            "are used."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--paired-repeats",
        type=int,
        default=6,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
    )

    args = parser.parse_args()

    if args.max_iterations != 2:
        raise SystemExit(
            "Current cross-case evaluator "
            "expects --max-iterations 2"
        )

    if args.paired_repeats < 1:
        raise SystemExit(
            "--paired-repeats must be >= 1"
        )

    all_cases = load_cases()

    selected = all_cases

    if args.cases:
        wanted = set(
            args.cases
        )

        selected = [
            case
            for case in all_cases
            if case["id"] in wanted
        ]

        found = {
            case["id"]
            for case in selected
        }

        missing = (
            wanted - found
        )

        if missing:
            raise SystemExit(
                "Unknown cases: "
                + ", ".join(
                    sorted(missing)
                )
            )

    if args.limit is not None:
        selected = selected[
            :args.limit
        ]

    if not selected:
        raise SystemExit(
            "No cases selected"
        )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []
    errors = []

    for index, case in enumerate(
        selected,
        start=1,
    ):
        case_id = case["id"]

        print()
        print(
            f"[{index}/{len(selected)}] "
            f"{case_id}"
        )

        try:
            (
                baseline_file,
                pipeline,
            ) = run_pipeline_case(
                case_id,
                max_iterations=
                    args.max_iterations,
                timeout=
                    args.timeout,
            )

            (
                paired_file,
                paired,
            ) = run_paired(
                run_id=
                    pipeline["run_id"],
                before_iteration=1,
                after_iteration=2,
                repeats=
                    args.paired_repeats,
            )

            after_wins = paired[
                "after_wins"
            ]

            before_wins = paired[
                "before_wins"
            ]

            ties = paired[
                "ties"
            ]

            preference = case_preference(
                after_wins=after_wins,
                before_wins=before_wins,
            )

            item = {
                "case_id":
                    case_id,

                "category":
                    case.get(
                        "category"
                    ),

                "run_id":
                    pipeline["run_id"],

                # Diagnostic only.
                "pipeline_quality_scores":
                    pipeline[
                        "quality_scores"
                    ],

                # Diagnostic only. Not used to
                # decide revision improvement.
                "pipeline_absolute_improvement":
                    pipeline[
                        "improvement"
                    ],

                "pipeline_duration_s":
                    pipeline[
                        "duration_s"
                    ],

                "paired_method":
                    paired.get(
                        "method"
                    ),

                "successful_repeats":
                    paired[
                        "successful_repeats"
                    ],

                "after_wins":
                    after_wins,

                "before_wins":
                    before_wins,

                "ties":
                    ties,

                "case_preference":
                    preference,

                "dimension_summary":
                    paired[
                        "dimension_summary"
                    ],

                "baseline_result":
                    str(
                        baseline_file.relative_to(
                            ROOT
                        )
                    ),

                "paired_result":
                    str(
                        paired_file.relative_to(
                            ROOT
                        )
                    ),
            }

            results.append(
                item
            )

            print()
            print(
                "CASE SUMMARY:",
                case_id,
            )

            print(
                "  preference:",
                preference,
            )

            print(
                "  votes:",
                f"after={after_wins}",
                f"before={before_wins}",
                f"tie={ties}",
            )

        except Exception as exc:
            errors.append(
                {
                    "case_id":
                        case_id,
                    "error":
                        str(exc),
                }
            )

            print()
            print(
                "CASE ERROR:",
                case_id,
            )

            print(
                str(exc)
            )

    stamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    output = (
        RESULTS_DIR
        / (
            "cross_case_revision_v2_"
            f"{stamp}.json"
        )
    )

    total_after_wins = sum(
        item["after_wins"]
        for item in results
    )

    total_before_wins = sum(
        item["before_wins"]
        for item in results
    )

    total_ties = sum(
        item["ties"]
        for item in results
    )

    cases_after_majority = sum(
        item["case_preference"]
        == "after"
        for item in results
    )

    cases_before_majority = sum(
        item["case_preference"]
        == "before"
        for item in results
    )

    cases_tied = sum(
        item["case_preference"]
        == "tie"
        for item in results
    )

    aggregate_dimensions = {}

    for dimension in DIMENSIONS:
        aggregate_dimensions[
            dimension
        ] = {
            "after": sum(
                item[
                    "dimension_summary"
                ][dimension]["after"]
                for item in results
            ),

            "before": sum(
                item[
                    "dimension_summary"
                ][dimension]["before"]
                for item in results
            ),

            "tie": sum(
                item[
                    "dimension_summary"
                ][dimension]["tie"]
                for item in results
            ),
        }

    total_decisions = (
        total_after_wins
        + total_before_wins
        + total_ties
    )

    payload = {
        "created_at":
            stamp,

        "method":
            "cross_case_paired_comparative_v2",

        "max_iterations":
            args.max_iterations,

        "paired_repeats":
            args.paired_repeats,

        "requested_cases":
            len(selected),

        "successful_cases":
            len(results),

        "failed_cases":
            len(errors),

        "cases_after_majority":
            cases_after_majority,

        "cases_before_majority":
            cases_before_majority,

        "cases_tied":
            cases_tied,

        "total_after_wins":
            total_after_wins,

        "total_before_wins":
            total_before_wins,

        "total_ties":
            total_ties,

        "total_overall_decisions":
            total_decisions,

        "aggregate_dimension_summary":
            aggregate_dimensions,

        "results":
            results,

        "errors":
            errors,
    }

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
    print("=" * 70)
    print(
        "CROSS-CASE COMPARATIVE V2 SUMMARY"
    )
    print("=" * 70)

    for item in results:
        print(
            f"{item['case_id']:24} "
            f"preference="
            f"{item['case_preference']:6} "
            f"after={item['after_wins']} "
            f"before={item['before_wins']} "
            f"tie={item['ties']}"
        )

    print()
    print(
        "case majority:",
        f"after={cases_after_majority}",
        f"before={cases_before_majority}",
        f"tie={cases_tied}",
    )

    print(
        "overall votes:",
        f"after={total_after_wins}",
        f"before={total_before_wins}",
        f"tie={total_ties}",
    )

    print()
    print("DIMENSION VOTES")

    for dimension in DIMENSIONS:
        stats = aggregate_dimensions[
            dimension
        ]

        print(
            f"{dimension:25} "
            f"after={stats['after']} "
            f"before={stats['before']} "
            f"tie={stats['tie']}"
        )

    print()
    print(
        "failed cases:",
        len(errors),
    )

    print(
        "result:",
        output,
    )

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
