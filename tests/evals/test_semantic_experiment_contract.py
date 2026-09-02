import asyncio
import json
import tempfile

from pathlib import Path

from app.workers.result import (
    WorkerExecutionResult,
)
from tests.evals.run_semantic_evidence_experiment import (
    BATCH_SCHEMA,
    calculate_agreement,
    calculate_metrics,
    evaluate_batch,
    materialize_fixtures,
    parse_batch_result,
    split_batches,
)


def perfect_evaluation(
    fixture,
):
    entailment = fixture[
        "expected_entailment"
    ]

    if entailment == "full":
        sufficiency = "sufficient"
        unsupported = []
        contradicted = []

    elif entailment == "partial":
        sufficiency = "insufficient"
        unsupported = [
            "material unsupported clause"
        ]
        contradicted = []

    elif entailment == "unsupported":
        sufficiency = "insufficient"
        unsupported = [
            "claim is not established"
        ]
        contradicted = []

    elif entailment == "contradicted":
        sufficiency = "insufficient"
        unsupported = []
        contradicted = [
            "material contradicted clause"
        ]

    else:
        raise AssertionError(
            entailment
        )

    return {
        "fixture_id":
            fixture[
                "fixture_id"
            ],
        "entailment":
            entailment,
        "claim_atomicity":
            fixture[
                "expected_atomicity"
            ],
        "support_sufficiency":
            sufficiency,
        "unsupported_clauses":
            unsupported,
        "contradicted_clauses":
            contradicted,
        "untrusted_instruction_detected":
            fixture[
                "expected_instruction_detected"
            ],
        "confidence":
            0.95,
        "rationale":
            "Deterministic fake evaluation.",
    }


def check_fixture_materialization():
    fixtures = materialize_fixtures()

    assert len(
        fixtures
    ) == 27

    ids = {
        item[
            "fixture_id"
        ]
        for item
        in fixtures
    }

    assert len(
        ids
    ) == 27

    assert {
        "frozen-claim-1",
        "frozen-claim-2",
        "frozen-claim-3",
        "syn-21",
        "syn-22",
        "syn-23",
    } <= ids

    print(
        "SEMANTIC_FIXTURE_MATERIALIZATION_OK"
    )


def check_batching():
    fixtures = materialize_fixtures()

    batches = split_batches(
        fixtures,
        9,
    )

    assert len(
        batches
    ) == 3

    assert [
        len(item)
        for item
        in batches
    ] == [
        9,
        9,
        9,
    ]

    print(
        "SEMANTIC_BATCHING_12_CALL_PLAN_OK"
    )


def check_batch_parser():
    fixtures = materialize_fixtures()[
        :9
    ]

    rows = [
        perfect_evaluation(
            item
        )
        for item
        in fixtures
    ]

    raw = json.dumps(
        {
            "evaluations":
                rows
        }
    )

    parsed = (
        parse_batch_result(
            raw,
            [
                item[
                    "fixture_id"
                ]
                for item
                in fixtures
            ],
        )
    )

    assert len(
        parsed
    ) == 9

    print(
        "SEMANTIC_BATCH_SCHEMA_OK"
    )


def check_metrics():
    fixtures = materialize_fixtures()

    records = []

    for account in (
        "primary",
        "secondary",
    ):
        for repeat in (
            1,
            2,
        ):
            for fixture in fixtures:
                expected = fixture[
                    "expected_entailment"
                ]

                records.append(
                    {
                        "fixture_id":
                            fixture[
                                "fixture_id"
                            ],
                        "category":
                            fixture[
                                "category"
                            ],
                        "account":
                            account,
                        "repeat":
                            repeat,
                        "expected_entailment":
                            expected,
                        "predicted_entailment":
                            expected,
                        "expected_atomicity":
                            fixture[
                                "expected_atomicity"
                            ],
                        "predicted_atomicity":
                            fixture[
                                "expected_atomicity"
                            ],
                        "expected_instruction_detected":
                            fixture[
                                "expected_instruction_detected"
                            ],
                        "predicted_instruction_detected":
                            fixture[
                                "expected_instruction_detected"
                            ],
                        "support_sufficiency":
                            (
                                "sufficient"
                                if expected
                                == "full"
                                else
                                "insufficient"
                            ),
                        "unsupported_clauses":
                            [],
                        "contradicted_clauses":
                            [],
                        "confidence":
                            0.95,
                        "rationale":
                            "Perfect fixture.",
                    }
                )

    metrics = calculate_metrics(
        records
    )

    agreement = calculate_agreement(
        records
    )

    assert (
        metrics[
            "total_verdicts"
        ]
        == 108
    )

    assert (
        metrics[
            "classification_accuracy"
        ]
        == 1.0
    )

    assert (
        metrics[
            "false_accept_rate"
        ]
        == 0.0
    )

    assert (
        metrics[
            "false_reject_rate"
        ]
        == 0.0
    )

    assert (
        metrics[
            "known_frozen_defect_detection_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "known_frozen_good_accept_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "prompt_injection_detection_rate"
        ]
        == 1.0
    )

    assert (
        agreement[
            "mean_pairwise_agreement"
        ]
        == 1.0
    )

    assert (
        agreement[
            "unanimous_fixture_rate"
        ]
        == 1.0
    )

    print(
        "SEMANTIC_METRICS_CONTRACT_OK"
    )

    print(
        "SEMANTIC_AGREEMENT_CONTRACT_OK"
    )


async def check_model_boundary():
    fixtures = materialize_fixtures()[
        :3
    ]

    captured = {}

    async def fake_model(
        prompt,
        cwd,
        **kwargs,
    ):
        captured[
            "prompt"
        ] = prompt

        captured.update(
            kwargs
        )

        payload = {
            "evaluations": [
                perfect_evaluation(
                    item
                )
                for item
                in fixtures
            ]
        }

        return WorkerExecutionResult(
            text=json.dumps(
                payload
            ),
            provider="claude",
            account="primary",
            model="fake-model",
            request_id=
                "fake-request",
            session_id=None,
            status="success",
            duration_ms=10,
            input_tokens=100,
            output_tokens=100,
            cache_read_tokens=0,
            cache_write_tokens=0,
            reasoning_output_tokens=0,
            reported_cost_usd=None,
            cost_source=None,
            raw_metadata={},
        )

    with tempfile.TemporaryDirectory() as tmp:
        (
            evaluations,
            telemetry,
        ) = await evaluate_batch(
            fixtures=fixtures,
            account="primary",
            repeat=1,
            batch_number=1,
            run_dir=
                Path(tmp),
            timeout=240,
            model_call=
                fake_model,
        )

    assert len(
        evaluations
    ) == 3

    assert (
        captured[
            "tool_profile"
        ]
        == "reasoning"
    )

    assert (
        captured[
            "max_turns"
        ]
        == 1
    )

    assert (
        captured[
            "json_schema"
        ]
        == BATCH_SCHEMA
    )

    assert (
        captured[
            "account"
        ]
        == "primary"
    )

    assert (
        "UNTRUSTED"
        in captured[
            "prompt"
        ]
    )

    assert (
        telemetry[
            "provider"
        ]
        == "claude"
    )

    print(
        "SEMANTIC_COUNCIL_ZERO_TOOL_BOUNDARY_OK"
    )

    print(
        "SEMANTIC_COUNCIL_SINGLE_TURN_OK"
    )


def main():
    check_fixture_materialization()
    check_batching()
    check_batch_parser()
    check_metrics()

    asyncio.run(
        check_model_boundary()
    )

    print()
    print(
        "SEMANTIC_EXPERIMENT_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
