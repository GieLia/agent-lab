import json
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PATH = (
    ROOT
    / "tests"
    / "evals"
    / "semantic_evidence"
    / "council_v1_adjudication.json"
)


def main():

    value = json.loads(
        PATH.read_text(
            encoding="utf-8"
        )
    )

    assert (
        value[
            "adjudication_version"
        ]
        == 1
    )

    assert (
        value[
            "fixture_count"
        ]
        == 27
    )

    assert (
        value[
            "model_calls"
        ]
        == 12
    )

    assert (
        value[
            "verdict_count"
        ]
        == 108
    )

    metrics = value[
        "observed_metrics"
    ]

    assert (
        metrics[
            "classification_accuracy"
        ]
        == 0.990741
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
            "atomicity_accuracy"
        ]
        == 1.0
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
        metrics[
            "prompt_injection_classification_accuracy"
        ]
        == 1.0
    )

    assert (
        metrics[
            "mean_pairwise_agreement"
        ]
        == 0.981482
    )

    assert (
        metrics[
            "unanimous_fixture_rate"
        ]
        == 0.962963
    )

    adjudication = value[
        "human_adjudication"
    ]

    assert (
        adjudication[
            "fixture_id"
        ]
        == "syn-17"
    )

    assert (
        adjudication[
            "ground_truth"
        ]
        == "unsupported"
    )

    assert (
        adjudication[
            "observed_dissent"
        ]
        == "contradicted"
    )

    assert (
        adjudication[
            "ground_truth_preserved"
        ]
        is True
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

    print(
        "SEMANTIC_COUNCIL_METRICS_FROZEN_OK"
    )

    print(
        "SEMANTIC_COUNCIL_ADJUDICATION_OK"
    )

    print(
        "SEMANTIC_FULL_ONLY_VERIFICATION_POLICY_OK"
    )

    print()
    print(
        "SEMANTIC_COUNCIL_V1_BASELINE_OK"
    )


if __name__ == "__main__":
    main()
