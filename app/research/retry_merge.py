from __future__ import annotations

import copy

from typing import Any


from app.research.protocol import (
    ResearchProtocolError,
    validate_worker_result,
)


class RetryMergeError(
    RuntimeError
):
    pass


def _fail(
    message: str,
) -> None:

    raise RetryMergeError(
        message
    )


def merge_retry_worker_result(
    *,
    base_result: dict[str, Any],
    retry_result: dict[str, Any],
    retry_claim_ids: list[str],
    iteration: int,
) -> dict[str, Any]:

    try:
        validate_worker_result(
            base_result
        )

        validate_worker_result(
            retry_result
        )

    except ResearchProtocolError as exc:
        raise RetryMergeError(
            "retry merge requires valid "
            "canonical WorkerResult objects"
        ) from exc


    if (
        isinstance(
            iteration,
            bool,
        )
        or not isinstance(
            iteration,
            int,
        )
        or iteration < 2
    ):
        _fail(
            "retry iteration must "
            "be an integer >= 2"
        )


    if (
        not isinstance(
            retry_claim_ids,
            list,
        )
        or not retry_claim_ids
    ):
        _fail(
            "retry_claim_ids must "
            "not be empty"
        )


    target_ids = set(
        retry_claim_ids
    )

    if (
        len(target_ids)
        != len(
            retry_claim_ids
        )
    ):
        _fail(
            "duplicate retry claim ID"
        )


    base_claims = {
        item["claim_id"]:
            item
        for item
        in base_result[
            "claims"
        ]
    }

    unknown_targets = (
        target_ids
        - set(
            base_claims
        )
    )

    if unknown_targets:
        _fail(
            "retry targets unknown "
            "base claim IDs"
        )


    for claim_id in target_ids:

        if (
            base_claims[
                claim_id
            ][
                "claim_type"
            ]
            != "fact"
        ):
            _fail(
                "targeted retry v1 "
                "accepts factual claims only"
            )


    incoming_claims = {
        item["claim_id"]:
            item
        for item
        in retry_result[
            "claims"
        ]
    }

    incoming_ids = set(
        incoming_claims
    )


    if not incoming_ids:
        _fail(
            "retry result contains "
            "no target claims"
        )


    if not (
        incoming_ids
        <= target_ids
    ):
        _fail(
            "retry result attempted "
            "claim scope expansion"
        )


    for claim_id in incoming_ids:

        original = base_claims[
            claim_id
        ]

        incoming = incoming_claims[
            claim_id
        ]

        if (
            incoming[
                "text"
            ]
            != original[
                "text"
            ]
        ):
            _fail(
                "retry result attempted "
                "claim text mutation"
            )

        if (
            incoming[
                "claim_type"
            ]
            != original[
                "claim_type"
            ]
        ):
            _fail(
                "retry result attempted "
                "claim type mutation"
            )


    prefix = (
        f"retry-{iteration}-"
    )


    source_id_map = {}

    existing_source_ids = {
        item["source_id"]
        for item
        in base_result[
            "sources"
        ]
    }

    retry_sources = []

    for source in retry_result[
        "sources"
    ]:

        old_id = source[
            "source_id"
        ]

        new_id = (
            prefix
            + old_id
        )

        if (
            new_id
            in existing_source_ids
        ):
            _fail(
                "retry source ID "
                "collision after namespacing"
            )

        source_id_map[
            old_id
        ] = new_id

        item = copy.deepcopy(
            source
        )

        item[
            "source_id"
        ] = new_id

        retry_sources.append(
            item
        )


    existing_evidence_ids = {
        item["evidence_id"]
        for item
        in base_result[
            "evidence"
        ]
    }

    retry_evidence = []

    for evidence in retry_result[
        "evidence"
    ]:

        claim_id = evidence[
            "claim_id"
        ]

        if (
            claim_id
            not in incoming_ids
        ):
            _fail(
                "retry evidence references "
                "claim outside retry result"
            )

        old_source_id = evidence[
            "source_id"
        ]

        if (
            old_source_id
            not in source_id_map
        ):
            _fail(
                "retry evidence source "
                "was not namespaced"
            )

        new_evidence_id = (
            prefix
            + evidence[
                "evidence_id"
            ]
        )

        if (
            new_evidence_id
            in existing_evidence_ids
        ):
            _fail(
                "retry evidence ID "
                "collision after namespacing"
            )

        item = copy.deepcopy(
            evidence
        )

        item[
            "evidence_id"
        ] = new_evidence_id

        item[
            "source_id"
        ] = source_id_map[
            old_source_id
        ]

        retry_evidence.append(
            item
        )


    merged = copy.deepcopy(
        base_result
    )

    merged[
        "sources"
    ].extend(
        retry_sources
    )

    merged[
        "evidence"
    ].extend(
        retry_evidence
    )


    merged_gaps = []

    for gap in (
        list(
            base_result.get(
                "gaps",
                []
            )
        )
        + list(
            retry_result.get(
                "gaps",
                []
            )
        )
    ):

        if (
            gap
            not in merged_gaps
        ):
            merged_gaps.append(
                gap
            )

    merged[
        "gaps"
    ] = merged_gaps


    # Merged runtime artifact remains conservative until
    # semantic verification is rerun.
    merged[
        "status"
    ] = "partial"


    try:
        validate_worker_result(
            merged
        )

    except ResearchProtocolError as exc:
        raise RetryMergeError(
            "merged WorkerResult failed "
            "canonical validation"
        ) from exc


    return merged
