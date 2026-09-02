from __future__ import annotations

from collections import defaultdict
from typing import Any


from app.research.protocol import (
    ResearchProtocolError,
    validate_worker_result,
)

from app.research.semantic_evaluator import (
    validate_semantic_evaluation,
)


class VerificationPolicyError(
    RuntimeError
):
    pass


POLICY_VERSION = 1

FACT_STATUS_VALUES = frozenset(
    {
        "verified",
        "partially_verified",
        "unverified",
        "contradicted",
        "disputed",
    }
)


def _fail(
    message: str,
) -> None:
    raise VerificationPolicyError(
        message
    )


def _require_string(
    value: Any,
    label: str,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        _fail(
            f"{label} must be a "
            "non-empty string"
        )

    return value.strip()


def _validate_pair_record(
    value: Any,
) -> dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):
        _fail(
            "semantic verification record "
            "must be an object"
        )

    expected = {
        "claim_id",
        "evidence_id",
        "evaluation",
    }

    if set(value) != expected:
        _fail(
            "semantic verification record "
            "has invalid fields"
        )

    claim_id = _require_string(
        value["claim_id"],
        "claim_id",
    )

    evidence_id = _require_string(
        value["evidence_id"],
        "evidence_id",
    )

    evaluation = value[
        "evaluation"
    ]

    try:
        validated = (
            validate_semantic_evaluation(
                evaluation
            )
        )

    except Exception as exc:
        raise VerificationPolicyError(
            "invalid semantic evaluation"
        ) from exc

    return {
        "claim_id":
            claim_id,
        "evidence_id":
            evidence_id,
        "evaluation":
            validated,
    }


def _fact_status(
    verdicts: list[
        dict[str, Any]
    ],
) -> str:

    entailments = {
        item[
            "evaluation"
        ][
            "entailment"
        ]
        for item
        in verdicts
    }

    has_full = (
        "full"
        in entailments
    )

    has_contradiction = (
        "contradicted"
        in entailments
    )

    has_partial = (
        "partial"
        in entailments
    )

    if (
        has_full
        and has_contradiction
    ):
        return "disputed"

    if has_contradiction:
        return "contradicted"

    if has_full:
        return "verified"

    if has_partial:
        return "partially_verified"

    return "unverified"


def build_verification_summary(
    worker_result: dict[str, Any],
    semantic_records: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    try:
        validate_worker_result(
            worker_result
        )

    except ResearchProtocolError as exc:
        raise VerificationPolicyError(
            "WorkerResult failed "
            "canonical validation"
        ) from exc

    if not isinstance(
        semantic_records,
        list,
    ):
        _fail(
            "semantic_records must "
            "be a list"
        )

    claims = {
        item["claim_id"]:
            item
        for item
        in worker_result[
            "claims"
        ]
    }

    evidence = {
        item["evidence_id"]:
            item
        for item
        in worker_result[
            "evidence"
        ]
    }

    factual_evidence_ids = {
        item["evidence_id"]
        for item
        in worker_result[
            "evidence"
        ]
        if (
            claims[
                item["claim_id"]
            ][
                "claim_type"
            ]
            == "fact"
        )
    }

    validated_records = []

    seen_evidence_ids = set()

    for raw in semantic_records:

        record = (
            _validate_pair_record(
                raw
            )
        )

        evidence_id = record[
            "evidence_id"
        ]

        claim_id = record[
            "claim_id"
        ]

        if evidence_id in seen_evidence_ids:
            _fail(
                "duplicate semantic evaluation "
                f"for evidence_id={evidence_id}"
            )

        seen_evidence_ids.add(
            evidence_id
        )

        if evidence_id not in evidence:
            _fail(
                "semantic evaluation references "
                "unknown evidence_id="
                f"{evidence_id}"
            )

        authoritative_claim_id = (
            evidence[
                evidence_id
            ][
                "claim_id"
            ]
        )

        if (
            claim_id
            != authoritative_claim_id
        ):
            _fail(
                "semantic evaluation claim_id "
                "does not match authoritative "
                "Evidence.claim_id"
            )

        claim = claims.get(
            claim_id
        )

        if claim is None:
            _fail(
                "semantic evaluation references "
                "unknown claim_id="
                f"{claim_id}"
            )

        if (
            claim[
                "claim_type"
            ]
            != "fact"
        ):
            _fail(
                "semantic evaluator v1 accepts "
                "only factual claims"
            )

        validated_records.append(
            record
        )

    supplied = {
        item[
            "evidence_id"
        ]
        for item
        in validated_records
    }

    if (
        supplied
        != factual_evidence_ids
    ):
        missing = sorted(
            factual_evidence_ids
            - supplied
        )

        extra = sorted(
            supplied
            - factual_evidence_ids
        )

        _fail(
            "semantic evaluation coverage "
            "must exactly match factual "
            "evidence; "
            f"missing={missing}, "
            f"extra={extra}"
        )

    by_claim = defaultdict(
        list
    )

    for record in validated_records:
        by_claim[
            record["claim_id"]
        ].append(
            record
        )

    claim_results = []

    verified_claim_ids = []
    partially_verified_claim_ids = []
    unverified_claim_ids = []
    contradicted_claim_ids = []
    disputed_claim_ids = []
    non_fact_claim_ids = []

    for claim in worker_result[
        "claims"
    ]:

        claim_id = claim[
            "claim_id"
        ]

        claim_type = claim[
            "claim_type"
        ]

        researcher_status = (
            claim.get(
                "verification_status",
                "unverified",
            )
        )

        verdicts = sorted(
            by_claim.get(
                claim_id,
                [],
            ),
            key=lambda item:
                item[
                    "evidence_id"
                ],
        )

        if claim_type != "fact":

            runtime_status = (
                "unverified"
            )

            eligible = False

            non_fact_claim_ids.append(
                claim_id
            )

        else:

            runtime_status = (
                _fact_status(
                    verdicts
                )
            )

            eligible = (
                runtime_status
                == "verified"
            )

            if runtime_status not in (
                FACT_STATUS_VALUES
            ):
                _fail(
                    "internal verification "
                    "status error"
                )

            target = {
                "verified":
                    verified_claim_ids,
                "partially_verified":
                    partially_verified_claim_ids,
                "unverified":
                    unverified_claim_ids,
                "contradicted":
                    contradicted_claim_ids,
                "disputed":
                    disputed_claim_ids,
            }[
                runtime_status
            ]

            target.append(
                claim_id
            )

        full_evidence_ids = [
            item[
                "evidence_id"
            ]
            for item
            in verdicts
            if (
                item[
                    "evaluation"
                ][
                    "entailment"
                ]
                == "full"
            )
        ]

        contradicted_evidence_ids = [
            item[
                "evidence_id"
            ]
            for item
            in verdicts
            if (
                item[
                    "evaluation"
                ][
                    "entailment"
                ]
                == "contradicted"
            )
        ]

        claim_results.append(
            {
                "claim_id":
                    claim_id,

                "claim_type":
                    claim_type,

                "researcher_verification_status":
                    researcher_status,

                "runtime_verification_status":
                    runtime_status,

                "verification_eligible":
                    eligible,

                "full_evidence_ids":
                    full_evidence_ids,

                "contradicted_evidence_ids":
                    contradicted_evidence_ids,

                "semantic_verdicts":
                    verdicts,
            }
        )

    return {
        "policy_version":
            POLICY_VERSION,

        "worker_id":
            worker_result[
                "worker_id"
            ],

        "structural_integrity":
            "pass",

        "claim_results":
            claim_results,

        "verified_claim_ids":
            verified_claim_ids,

        "partially_verified_claim_ids":
            partially_verified_claim_ids,

        "unverified_claim_ids":
            unverified_claim_ids,

        "contradicted_claim_ids":
            contradicted_claim_ids,

        "disputed_claim_ids":
            disputed_claim_ids,

        "non_fact_claim_ids":
            non_fact_claim_ids,
    }
