from __future__ import annotations

import copy

from typing import Any

from jsonschema import (
    Draft202012Validator,
)


class CriticContractError(
    RuntimeError
):
    pass


CRITIC_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "retry_required": {
            "type": "boolean",
        },
        "retry_claim_ids": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "minLength": 1,
            },
        },
        "missing_evidence": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
            },
        },
        "retry_topic": {
            "type": [
                "string",
                "null",
            ],
        },
        "critique": {
            "type": "string",
        },
    },
    "required": [
        "retry_required",
        "retry_claim_ids",
        "missing_evidence",
        "retry_topic",
        "critique",
    ],
    "additionalProperties":
        False,
}


Draft202012Validator.check_schema(
    CRITIC_RESULT_SCHEMA
)


def _fail(
    message: str,
) -> None:

    raise CriticContractError(
        message
    )


def validate_critic_result(
    value: dict[str, Any],
    *,
    candidate_retry_claim_ids:
        list[str],
    structural_integrity: str,
) -> dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):
        _fail(
            "CriticResult must "
            "be an object"
        )

    result = copy.deepcopy(
        value
    )

    try:
        Draft202012Validator(
            CRITIC_RESULT_SCHEMA
        ).validate(
            result
        )

    except Exception as exc:
        raise CriticContractError(
            "CriticResult failed schema"
        ) from exc


    if (
        structural_integrity
        not in {
            "pass",
            "fail",
        }
    ):
        _fail(
            "structural_integrity must "
            "be pass or fail"
        )


    allowed = set(
        candidate_retry_claim_ids
    )

    requested = set(
        result[
            "retry_claim_ids"
        ]
    )

    if not (
        requested
        <= allowed
    ):
        _fail(
            "Critic attempted to retry "
            "a claim outside runtime "
            "rejection set"
        )


    if (
        structural_integrity
        == "fail"
    ):

        if result[
            "retry_required"
        ]:
            _fail(
                "structurally invalid "
                "WorkerResult cannot enter "
                "claim-level retry in E5-C4"
            )

        if result[
            "retry_claim_ids"
        ]:
            _fail(
                "structural failure cannot "
                "contain retry_claim_ids "
                "in E5-C4"
            )

        if (
            result[
                "retry_topic"
            ]
            is not None
        ):
            _fail(
                "structural failure cannot "
                "contain retry_topic "
                "in E5-C4"
            )

        return result


    if result[
        "retry_required"
    ]:

        if not result[
            "retry_claim_ids"
        ]:
            _fail(
                "retry_required requires "
                "retry_claim_ids"
            )

        retry_topic = result[
            "retry_topic"
        ]

        if (
            not isinstance(
                retry_topic,
                str,
            )
            or not retry_topic.strip()
        ):
            _fail(
                "retry_required requires "
                "non-empty retry_topic"
            )

        if not result[
            "missing_evidence"
        ]:
            _fail(
                "retry_required requires "
                "missing_evidence"
            )

        result[
            "retry_topic"
        ] = retry_topic.strip()

    else:

        if result[
            "retry_claim_ids"
        ]:
            _fail(
                "retry_required=false "
                "requires empty "
                "retry_claim_ids"
            )

        if (
            result[
                "retry_topic"
            ]
            is not None
        ):
            _fail(
                "retry_required=false "
                "requires retry_topic=null"
            )


    return result
