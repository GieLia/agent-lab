import json
from collections import Counter
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


def main():

    data = json.loads(
        CORPUS.read_text(
            encoding="utf-8"
        )
    )

    assert data["version"] == 1

    fixtures = data[
        "fixtures"
    ]

    assert len(
        fixtures
    ) == 48

    ids = [
        item["fixture_id"]
        for item
        in fixtures
    ]

    assert len(
        ids
    ) == len(
        set(ids)
    ) == 48

    counts = Counter(
        item[
            "expected_entailment"
        ]
        for item
        in fixtures
    )

    assert counts[
        "full"
    ] == 9

    assert (
        counts["partial"]
        + counts["unsupported"]
        + counts["contradicted"]
    ) == 39

    injection = [
        item
        for item
        in fixtures
        if item[
            "expected_instruction_detected"
        ]
    ]

    assert len(
        injection
    ) == 6

    required_categories = {
        "modal_may_to_will",
        "modal_should_to_must",
        "planned_to_implemented",
        "lower_bound_to_exact",
        "some_to_all",
        "historical_to_current",
        "old_version_to_current",
        "wrong_entity",
        "regional_scope",
        "correlation_to_causation",
        "test_to_production",
        "draft_to_deployed",
        "superseded_to_current",
        "conditional_scope",
        "capability_to_usage",
        "available_to_configured",
        "installed_to_running",
        "running_to_healthy",
        "documented_to_implemented",
        "partial_compound",
        "direct_numeric_contradiction",
        "omitted_negation",
        "prompt_injection_supported",
        "prompt_injection_title",
        "prompt_injection_metadata",
        "recommendation_to_fact",
        "possibility_to_certainty",
        "cherry_picked_condition",
        "one_sample_to_general",
        "full_exact_control",
    }

    categories = {
        item[
            "category"
        ]
        for item
        in fixtures
    }

    assert (
        required_categories
        <= categories
    )

    for item in fixtures:

        assert (
            item[
                "evidence"
            ][
                "claim_id"
            ]
            == item[
                "claim"
            ][
                "claim_id"
            ]
        )

        assert (
            item[
                "evidence"
            ][
                "source_id"
            ]
            == item[
                "source"
            ][
                "source_id"
            ]
        )

    print(
        "FALSE_ACCEPT_STRESS_FIXTURE_COUNT_OK"
    )

    print(
        "FALSE_ACCEPT_STRESS_CLASS_BALANCE_OK"
    )

    print(
        "FALSE_ACCEPT_STRESS_INJECTION_COVERAGE_OK"
    )

    print(
        "FALSE_ACCEPT_STRESS_REFERENCE_INTEGRITY_OK"
    )

    print()
    print(
        "FALSE_ACCEPT_STRESS_CORPUS_GATE_OK"
    )


if __name__ == "__main__":
    main()
