import argparse
import json
import os
import re
import subprocess
import sys
import time

from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
CASES_FILE = ROOT / "tests" / "evals" / "cases.yaml"
RESULTS_DIR = ROOT / "tests" / "evals" / "results"
RAW_DIR = RESULTS_DIR / "raw"

RUN_ID_RE = re.compile(r"RUN ID:\s*([0-9a-fA-F-]+)")
QUALITY_RE = re.compile(
    r"Quality score\s*=\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)


def load_cases():
    data = yaml.safe_load(
        CASES_FILE.read_text(encoding="utf-8")
    )
    return data["cases"]


def run_case(
    case,
    max_iterations,
    threshold,
    timeout,
    force_iterations=False,
):
    env = os.environ.copy()

    env["TOPIC"] = case["prompt"]
    env["MAX_ITERATIONS"] = str(max_iterations)
    env["QUALITY_THRESHOLD"] = str(threshold)
    env["FORCE_ITERATIONS"] = (
        "1"
        if force_iterations
        else "0"
    )
    env["PYTHONUNBUFFERED"] = "1"

    started = time.monotonic()

    try:
        process = subprocess.run(
            [
                sys.executable,
                "-X",
                "faulthandler",
                "graph_v3.py",
            ],
            cwd=APP_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        timed_out = False
        return_code = process.returncode

        log = (
            process.stdout
            + "\n--- STDERR ---\n"
            + process.stderr
        )

    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = None

        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")

        log = (
            stdout
            + "\n--- STDERR ---\n"
            + stderr
        )

    duration = round(
        time.monotonic() - started,
        2,
    )

    run_match = RUN_ID_RE.search(log)

    run_id = (
        run_match.group(1)
        if run_match
        else None
    )

    scores = [
        float(value)
        for value in QUALITY_RE.findall(log)
    ]

    improvement = None

    if len(scores) >= 2:
        improvement = round(
            scores[-1] - scores[0],
            4,
        )

    raw_file = RAW_DIR / f"{case['id']}.log"

    raw_file.write_text(
        log,
        encoding="utf-8",
    )

    return {
        "case_id": case["id"],
        "category": case["category"],
        "run_id": run_id,
        "return_code": return_code,
        "timed_out": timed_out,
        "duration_s": duration,
        "iterations_scored": len(scores),
        "quality_scores": scores,
        "first_score": scores[0] if scores else None,
        "last_score": scores[-1] if scores else None,
        "improvement": improvement,
        "improved": (
            improvement > 0
            if improvement is not None
            else None
        ),
        "required_points": case.get(
            "required_points",
            [],
        ),
        "raw_log": str(
            raw_file.relative_to(ROOT)
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--case")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.99,
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
    )
    parser.add_argument(
        "--force-iterations",
        action="store_true",
        help=(
            "Eval-only: ignore quality threshold "
            "until max iterations are completed."
        ),
    )

    args = parser.parse_args()

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cases = load_cases()

    if args.case:
        cases = [
            case
            for case in cases
            if case["id"] == args.case
        ]

        if not cases:
            raise SystemExit(
                f"Unknown case: {args.case}"
            )

    if args.limit is not None:
        cases = cases[:args.limit]

    results = []

    for index, case in enumerate(
        cases,
        start=1,
    ):
        print(
            f"[{index}/{len(cases)}] "
            f"{case['id']}"
        )

        result = run_case(
            case,
            args.max_iterations,
            args.threshold,
            args.timeout,
            args.force_iterations,
        )

        results.append(result)

        print("  run_id:", result["run_id"])
        print("  scores:", result["quality_scores"])
        print("  improvement:", result["improvement"])
        print("  duration_s:", result["duration_s"])
        print("  return_code:", result["return_code"])

    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    output_file = (
        RESULTS_DIR
        / f"baseline_v3_{stamp}.json"
    )

    payload = {
        "graph": "graph_v3.py",
        "created_at": stamp,
        "max_iterations": args.max_iterations,
        "quality_threshold": args.threshold,
        "force_iterations":
            args.force_iterations,
        "cases": results,
    }

    output_file.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    comparable = [
        result
        for result in results
        if result["improvement"] is not None
    ]

    improved = sum(
        result["improved"] is True
        for result in comparable
    )

    not_improved = sum(
        result["improved"] is False
        for result in comparable
    )

    print()
    print("=" * 60)
    print("V3 EVAL SUMMARY")
    print("=" * 60)
    print("Cases:", len(results))
    print("Comparable:", len(comparable))
    print("Improved:", improved)
    print("Not improved:", not_improved)
    print("RESULT:", output_file)

    failed_cases = [
        result
        for result in results
        if (
            result["timed_out"]
            or result["return_code"] != 0
            or result["iterations_scored"] == 0
        )
    ]

    if failed_cases:
        print(
            "FAILED CASES:",
            ", ".join(
                result["case_id"]
                for result in failed_cases
            ),
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
