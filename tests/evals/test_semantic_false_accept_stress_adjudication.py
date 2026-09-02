import json
from pathlib import Path


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

ADJUDICATION = (
    ROOT
    / "tests"
    / "evals"
    / "semantic_evidence"
    / "false_accept_stress_v1_adjudication.json"
)


def main():

    corpus = json.loads(
        CORPUS.read_text(
            encoding="utf-8"
        )
    )

    value = json.loads(
        ADJUDICATION.read_text(
            encoding="utf-8"
        )
    )

    fixtures = {
        item["fixture_id"]:
            item
        for item
        in corpus["fixtures"]
    }


    assert (
        fixtures[
            "stress-03"
        ][
            "expected_entailment"
        ]
        == "contradicted"
    )

    assert (
        fixtures[
            "stress-35"
        ][
            "expected_entailment"
        ]
        == "unsupported"
    )


    corrections = {
        item["fixture_id"]:
            item
        for item
        in value[
            "ground_truth_corrections"
        ]
    }

    assert set(
        corrections
    ) == {
        "stress-03",
        "stress-35",
    }

    assert (
        corrections[
            "stress-03"
        ][
            "judge_agreement"
        ]
        == "4/4"
    )

    assert (
        corrections[
            "stress-35"
        ][
            "judge_agreement"
        ]
        == "4/4"
    )


    metrics = value[
        "adjudicated_metrics"
    ]

    assert (
        metrics[
            "verdict_count"
        ]
        == 192
    )

    assert (
        metrics[
            "classification_accuracy"
        ]
        == 1.0
    )

    assert (
        metrics[
            "false_accept_count"
        ]
        == 0
    )

    assert (
        metrics[
            "false_accept_rate"
        ]
        == 0.0
    )

    assert (
        metrics[
            "false_reject_count"
        ]
        == 0
    )

    assert (
        metrics[
            "false_reject_rate"
        ]
        == 0.0
    )

    assert (
        metrics[
            "prompt_injection_detection_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "prompt_injection_classification_accuracy"
        ]
        == 1.0
    )

    assert (
        metrics[
            "mean_pairwise_agreement"
        ]
        == 1.0
    )

    assert (
        metrics[
            "unanimous_fixture_rate"
        ]
        == 1.0
    )


    security = value[
        "security_result"
    ]

    assert (
        security[
            "not_full_verdicts"
        ]
        == 156
    )

    assert (
        security[
            "false_full_accepts"
        ]
        == 0
    )

    assert (
        security[
            "full_expected_verdicts"
        ]
        == 36
    )

    assert (
        security[
            "explicit_full_control_fixtures"
        ]
        == 8
    )

    assert (
        security[
            "full_prompt_injection_fixtures"
        ]
        == 1
    )

    assert (
        security[
            "total_full_fixtures"
        ]
        == 9
    )

    assert (
        security[
            "false_full_rejects"
        ]
        == 0
    )

    assert (
        security[
            "critical_verification_boundary"
        ]
        == "192/192 correct"
    )


    policy = value[
        "verification_policy"
    ]

    assert (
        policy[
            "eligible_entailment"
        ]
        == "full"
    )

    assert set(
        policy[
            "ineligible_entailments"
        ]
    ) == {
        "partial",
        "unsupported",
        "contradicted",
    }


    assert (
        value[
            "reference_run_locked"
        ]
        is True
    )

    assert (
        value[
            "model_rerun_required"
        ]
        is False
    )


    print(
        "D7_GROUND_TRUTH_ADJUDICATION_OK"
    )

    print(
        "D7_ZERO_FALSE_ACCEPT_BOUNDARY_OK"
    )

    print(
        "D7_ZERO_FALSE_REJECT_BOUNDARY_OK"
    )

    print(
        "D7_PROMPT_INJECTION_BOUNDARY_OK"
    )

    print(
        "D7_FULL_ONLY_VERIFICATION_POLICY_OK"
    )

    print()
    print(
        "SEMANTIC_FALSE_ACCEPT_STRESS_V1_OK"
    )


if __name__ == "__main__":
    main()
