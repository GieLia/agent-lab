from copy import deepcopy


from app.research.verification import (
    VerificationPolicyError,
    build_verification_summary,
)


def evaluation(
    entailment,
):

    if entailment == "full":
        return {
            "entailment":
                "full",
            "claim_atomicity":
                "atomic",
            "support_sufficiency":
                "sufficient",
            "unsupported_clauses":
                [],
            "contradicted_clauses":
                [],
            "untrusted_instruction_detected":
                False,
            "confidence":
                0.9,
            "rationale":
                "Fully supported.",
        }

    if entailment == "partial":
        return {
            "entailment":
                "partial",
            "claim_atomicity":
                "compound",
            "support_sufficiency":
                "insufficient",
            "unsupported_clauses":
                [
                    "missing clause"
                ],
            "contradicted_clauses":
                [],
            "untrusted_instruction_detected":
                False,
            "confidence":
                0.8,
            "rationale":
                "Partially supported.",
        }

    if entailment == "unsupported":
        return {
            "entailment":
                "unsupported",
            "claim_atomicity":
                "atomic",
            "support_sufficiency":
                "insufficient",
            "unsupported_clauses":
                [
                    "claim"
                ],
            "contradicted_clauses":
                [],
            "untrusted_instruction_detected":
                False,
            "confidence":
                0.8,
            "rationale":
                "Unsupported.",
        }

    if entailment == "contradicted":
        return {
            "entailment":
                "contradicted",
            "claim_atomicity":
                "atomic",
            "support_sufficiency":
                "insufficient",
            "unsupported_clauses":
                [],
            "contradicted_clauses":
                [
                    "claim"
                ],
            "untrusted_instruction_detected":
                False,
            "confidence":
                0.9,
            "rationale":
                "Contradicted.",
        }

    raise AssertionError(
        entailment
    )


def worker_result():

    return {
        "worker_id":
            "researcher-e5-test",

        "role":
            "researcher",

        "provider":
            "claude",

        "account":
            "primary",

        "model":
            None,

        "status":
            "partial",

        "claims": [
            {
                "claim_id":
                    "claim-full",
                "text":
                    "API listens on port 8000.",
                "claim_type":
                    "fact",
                "importance":
                    "high",
                "verification_status":
                    "unverified",
            },
            {
                "claim_id":
                    "claim-partial",
                "text":
                    "VM has RAM and CPUs.",
                "claim_type":
                    "fact",
                "verification_status":
                    "verified",
            },
            {
                "claim_id":
                    "claim-contradicted",
                "text":
                    "Service is enabled.",
                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-disputed",
                "text":
                    "Retry limit is 3.",
                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-nonfact",
                "text":
                    "Prefer PostgreSQL.",
                "claim_type":
                    "recommendation",
            },
        ],

        "sources": [
            {
                "source_id":
                    "source-1",
                "source_type":
                    "internal",
                "title":
                    "Test source",
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-full",
                "claim_id":
                    "claim-full",
                "source_id":
                    "source-1",
                "relationship":
                    "supports",
                "excerpt":
                    "API listens on port 8000.",
            },
            {
                "evidence_id":
                    "ev-partial",
                "claim_id":
                    "claim-partial",
                "source_id":
                    "source-1",
                "relationship":
                    "supports",
                "excerpt":
                    "VM has RAM.",
            },
            {
                "evidence_id":
                    "ev-contradicted",
                "claim_id":
                    "claim-contradicted",
                "source_id":
                    "source-1",
                "relationship":
                    "contradicts",
                "excerpt":
                    "Service is disabled.",
            },
            {
                "evidence_id":
                    "ev-disputed-support",
                "claim_id":
                    "claim-disputed",
                "source_id":
                    "source-1",
                "relationship":
                    "supports",
                "excerpt":
                    "Retry limit is 3.",
            },
            {
                "evidence_id":
                    "ev-disputed-contradiction",
                "claim_id":
                    "claim-disputed",
                "source_id":
                    "source-1",
                "relationship":
                    "contradicts",
                "excerpt":
                    "Retry limit is 5.",
            },
        ],

        "gaps":
            [],

        "notes":
            None,
    }


def semantic_records():

    values = {
        "ev-full":
            "full",

        "ev-partial":
            "partial",

        "ev-contradicted":
            "contradicted",

        "ev-disputed-support":
            "full",

        "ev-disputed-contradiction":
            "contradicted",
    }

    worker = worker_result()

    evidence = {
        item["evidence_id"]:
            item
        for item
        in worker["evidence"]
    }

    return [
        {
            "claim_id":
                evidence[
                    evidence_id
                ][
                    "claim_id"
                ],

            "evidence_id":
                evidence_id,

            "evaluation":
                evaluation(
                    entailment
                ),
        }
        for evidence_id, entailment
        in values.items()
    ]


def reject(
    fn,
    label,
):
    try:
        fn()

    except VerificationPolicyError:
        print(
            f"{label}_OK"
        )

    else:
        raise AssertionError(
            f"{label} was accepted"
        )


def main():

    result = (
        build_verification_summary(
            worker_result(),
            semantic_records(),
        )
    )

    assert (
        result[
            "structural_integrity"
        ]
        == "pass"
    )

    assert (
        result[
            "verified_claim_ids"
        ]
        == [
            "claim-full"
        ]
    )

    assert (
        result[
            "partially_verified_claim_ids"
        ]
        == [
            "claim-partial"
        ]
    )

    assert (
        result[
            "contradicted_claim_ids"
        ]
        == [
            "claim-contradicted"
        ]
    )

    assert (
        result[
            "disputed_claim_ids"
        ]
        == [
            "claim-disputed"
        ]
    )

    assert (
        result[
            "non_fact_claim_ids"
        ]
        == [
            "claim-nonfact"
        ]
    )

    rows = {
        item["claim_id"]:
            item
        for item
        in result[
            "claim_results"
        ]
    }

    assert (
        rows[
            "claim-full"
        ][
            "verification_eligible"
        ]
        is True
    )

    assert (
        rows[
            "claim-partial"
        ][
            "verification_eligible"
        ]
        is False
    )

    assert (
        rows[
            "claim-partial"
        ][
            "researcher_verification_status"
        ]
        == "verified"
    )

    assert (
        rows[
            "claim-partial"
        ][
            "runtime_verification_status"
        ]
        == "partially_verified"
    )

    print(
        "RESEARCHER_SELF_VERIFICATION_IGNORED_OK"
    )

    print(
        "FULL_ONLY_VERIFICATION_POLICY_OK"
    )

    print(
        "CONTRADICTION_POLICY_OK"
    )

    print(
        "DISPUTED_POLICY_OK"
    )


    incomplete = (
        semantic_records()[:-1]
    )

    reject(
        lambda:
            build_verification_summary(
                worker_result(),
                incomplete,
            ),
        "INCOMPLETE_SEMANTIC_COVERAGE_REJECTED",
    )


    duplicate = (
        semantic_records()
    )

    duplicate.append(
        deepcopy(
            duplicate[0]
        )
    )

    reject(
        lambda:
            build_verification_summary(
                worker_result(),
                duplicate,
            ),
        "DUPLICATE_SEMANTIC_EVIDENCE_REJECTED",
    )


    mismatch = (
        semantic_records()
    )

    mismatch[0] = deepcopy(
        mismatch[0]
    )

    mismatch[0][
        "claim_id"
    ] = "claim-partial"

    reject(
        lambda:
            build_verification_summary(
                worker_result(),
                mismatch,
            ),
        "SEMANTIC_REFERENCE_MISMATCH_REJECTED",
    )


    print()
    print(
        "RESEARCH_VERIFICATION_POLICY_GATE_OK"
    )


if __name__ == "__main__":
    main()
