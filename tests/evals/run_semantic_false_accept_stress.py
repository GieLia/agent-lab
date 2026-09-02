import argparse
import asyncio
import json
import statistics
import uuid

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tests.evals.run_semantic_evidence_experiment import (
    calculate_agreement,
    calculate_metrics,
    enrich_records,
    evaluate_batch,
    split_batches,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

CORPUS = (
    ROOT
    / "tests"
    / "evals"
    / "semantic_evidence"
    / "false_accept_stress_v1.json"
)

RUN_ROOT = (
    ROOT
    / "runs"
    / "e4.5-semantic-false-accept-stress"
)


def load_fixtures():

    value = json.loads(
        CORPUS.read_text(
            encoding="utf-8"
        )
    )

    fixtures = value[
        "fixtures"
    ]

    if len(
        fixtures
    ) != 48:
        raise RuntimeError(
            "Expected 48 stress fixtures"
        )

    return fixtures


def write_json(
    path,
    value,
):
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def calculate_stress_metrics(
    records,
):

    base = calculate_metrics(
        records
    )

    false_accept_rows = [
        row
        for row
        in records
        if (
            row[
                "expected_entailment"
            ]
            != "full"
            and
            row[
                "predicted_entailment"
            ]
            == "full"
        )
    ]

    false_reject_rows = [
        row
        for row
        in records
        if (
            row[
                "expected_entailment"
            ]
            == "full"
            and
            row[
                "predicted_entailment"
            ]
            != "full"
        )
    ]

    by_category = defaultdict(
        list
    )

    for row in records:
        by_category[
            row["category"]
        ].append(row)

    category_metrics = {}

    for category, rows in sorted(
        by_category.items()
    ):

        exact = sum(
            row[
                "expected_entailment"
            ]
            == row[
                "predicted_entailment"
            ]
            for row
            in rows
        )

        category_false_accepts = sum(
            (
                row[
                    "expected_entailment"
                ]
                != "full"
            )
            and
            (
                row[
                    "predicted_entailment"
                ]
                == "full"
            )
            for row
            in rows
        )

        category_metrics[
            category
        ] = {
            "verdicts":
                len(rows),

            "exact_accuracy":
                round(
                    exact
                    / len(rows),
                    6,
                ),

            "false_accepts":
                category_false_accepts,
        }

    confidence_false_accept = [
        row["confidence"]
        for row
        in false_accept_rows
    ]

    return {
        **base,

        "critical_false_accepts":
            false_accept_rows,

        "critical_false_rejects":
            false_reject_rows,

        "highest_false_accept_confidence":
            (
                max(
                    confidence_false_accept
                )
                if confidence_false_accept
                else None
            ),

        "category_metrics":
            category_metrics,
    }


async def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--accounts",
        nargs="+",
        default=[
            "primary",
            "secondary",
        ],
        choices=[
            "primary",
            "secondary",
        ],
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
    )

    args = parser.parse_args()

    fixtures = load_fixtures()

    fixtures_by_id = {
        item["fixture_id"]:
            item
        for item
        in fixtures
    }

    batches = split_batches(
        fixtures,
        args.batch_size,
    )

    run_id = str(
        uuid.uuid4()
    )

    run_dir = (
        RUN_ROOT
        / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    started_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    records = []
    telemetry = []
    model_calls = 0

    for account in args.accounts:

        for repeat in range(
            1,
            args.repeats + 1,
        ):

            for (
                batch_number,
                batch,
            ) in enumerate(
                batches,
                start=1,
            ):

                print(
                    "RUN",
                    f"account={account}",
                    f"repeat={repeat}",
                    (
                        "batch="
                        f"{batch_number}/"
                        f"{len(batches)}"
                    ),
                    (
                        "fixtures="
                        f"{len(batch)}"
                    ),
                    flush=True,
                )

                (
                    evaluations,
                    batch_telemetry,
                ) = await evaluate_batch(
                    fixtures=batch,
                    account=account,
                    repeat=repeat,
                    batch_number=
                        batch_number,
                    run_dir=run_dir,
                    timeout=args.timeout,
                )

                model_calls += 1

                telemetry.append(
                    batch_telemetry
                )

                records.extend(
                    enrich_records(
                        fixtures_by_id=
                            fixtures_by_id,
                        evaluations=
                            evaluations,
                        account=account,
                        repeat=repeat,
                    )
                )

    expected_verdicts = (
        len(fixtures)
        * len(args.accounts)
        * args.repeats
    )

    assert (
        len(records)
        == expected_verdicts
    )

    metrics = (
        calculate_stress_metrics(
            records
        )
    )

    agreement = (
        calculate_agreement(
            records
        )
    )

    finished_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    report = {
        "experiment_version":
            1,

        "experiment":
            "semantic-false-accept-stress-v1",

        "run_id":
            run_id,

        "started_at":
            started_at,

        "finished_at":
            finished_at,

        "fixture_count":
            len(fixtures),

        "accounts":
            args.accounts,

        "repeats":
            args.repeats,

        "batch_size":
            args.batch_size,

        "model_calls":
            model_calls,

        "verdict_count":
            len(records),

        "metrics":
            metrics,

        "agreement":
            agreement,

        "records":
            records,

        "model_telemetry":
            telemetry,
    }

    write_json(
        run_dir
        / "report.json",
        report,
    )

    (
        RUN_ROOT
        / "latest_run_id.txt"
    ).write_text(
        run_id + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "FALSE_ACCEPT_STRESS_RUN_ID=",
        run_id,
    )

    print(
        "MODEL_CALLS=",
        model_calls,
    )

    print(
        "VERDICTS=",
        len(records),
    )

    print(
        "CLASSIFICATION_ACCURACY=",
        metrics[
            "classification_accuracy"
        ],
    )

    print(
        "FALSE_ACCEPT_COUNT=",
        metrics[
            "false_accept_count"
        ],
    )

    print(
        "FALSE_ACCEPT_RATE=",
        metrics[
            "false_accept_rate"
        ],
    )

    print(
        "FALSE_REJECT_COUNT=",
        metrics[
            "false_reject_count"
        ],
    )

    print(
        "FALSE_REJECT_RATE=",
        metrics[
            "false_reject_rate"
        ],
    )

    print(
        "PROMPT_INJECTION_DETECTION=",
        metrics[
            "prompt_injection_detection_rate"
        ],
    )

    print(
        "PROMPT_INJECTION_CLASSIFICATION=",
        metrics[
            "prompt_injection_classification_accuracy"
        ],
    )

    print(
        "MEAN_PAIRWISE_AGREEMENT=",
        agreement[
            "mean_pairwise_agreement"
        ],
    )

    print(
        "UNANIMOUS_FIXTURE_RATE=",
        agreement[
            "unanimous_fixture_rate"
        ],
    )

    print(
        "CRITICAL_FALSE_ACCEPTS=",
        len(
            metrics[
                "critical_false_accepts"
            ]
        ),
    )

    print(
        "RESULT=",
        run_dir
        / "report.json",
    )

    print()
    print(
        "SEMANTIC_FALSE_ACCEPT_STRESS_EXPERIMENT_OK"
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
