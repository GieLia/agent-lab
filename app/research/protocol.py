import copy
import json

from pathlib import Path
from typing import Any

from jsonschema import (
    Draft202012Validator,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SCHEMAS_ROOT = (
    ROOT
    / "portable"
    / "schemas"
)


class ResearchProtocolError(
    RuntimeError
):
    pass


RESEARCH_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "search",
                "fetch",
                "finish",
            ],
        },
        "query": {
            "type": [
                "string",
                "null",
            ],
        },
        "url": {
            "type": [
                "string",
                "null",
            ],
        },
        "reason": {
            "type": [
                "string",
                "null",
            ],
        },
        "result": {
            "type": [
                "object",
                "null",
            ],
        },
    },
    "required": [
        "action",
        "query",
        "url",
        "reason",
        "result",
    ],
    "additionalProperties":
        False,
}


def _load_json(
    path: Path,
) -> dict[str, Any]:

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise ResearchProtocolError(
            "Unable to load canonical schema: "
            f"{path.name}"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ResearchProtocolError(
            "Canonical schema is not an object: "
            f"{path.name}"
        )

    return value


def _inline_external_refs(
    value: Any,
) -> Any:

    if isinstance(
        value,
        list,
    ):
        return [
            _inline_external_refs(
                item
            )
            for item
            in value
        ]

    if not isinstance(
        value,
        dict,
    ):
        return value

    reference = value.get(
        "$ref"
    )

    if isinstance(
        reference,
        str,
    ):

        if reference.startswith(
            "#"
        ):
            # No external substitution needed.
            return {
                key:
                    _inline_external_refs(
                        item
                    )
                for key, item
                in value.items()
            }

        if (
            "/" in reference
            or "\\"
            in reference
            or not reference.endswith(
                ".schema.json"
            )
        ):
            raise ResearchProtocolError(
                "Unsafe external schema reference: "
                f"{reference}"
            )

        referenced_path = (
            SCHEMAS_ROOT
            / reference
        ).resolve()

        schemas_root = (
            SCHEMAS_ROOT.resolve()
        )

        try:
            referenced_path.relative_to(
                schemas_root
            )

        except ValueError as exc:
            raise ResearchProtocolError(
                "Schema reference escaped "
                "canonical root"
            ) from exc

        referenced = _load_json(
            referenced_path
        )

        return _inline_external_refs(
            referenced
        )

    return {
        key:
            _inline_external_refs(
                item
            )
        for key, item
        in value.items()
    }


def build_worker_result_schema(
) -> dict[str, Any]:

    schema = _load_json(
        SCHEMAS_ROOT
        / "worker-result.schema.json"
    )

    inlined = _inline_external_refs(
        schema
    )

    Draft202012Validator.check_schema(
        inlined
    )

    return inlined


WORKER_RESULT_SCHEMA = (
    build_worker_result_schema()
)


def parse_action(
    value: str | dict[str, Any],
) -> dict[str, Any]:

    if isinstance(
        value,
        str,
    ):
        try:
            action = json.loads(
                value
            )

        except json.JSONDecodeError as exc:
            raise ResearchProtocolError(
                "Research action is not valid JSON"
            ) from exc

    elif isinstance(
        value,
        dict,
    ):
        action = copy.deepcopy(
            value
        )

    else:
        raise ResearchProtocolError(
            "Research action must be "
            "JSON text or object"
        )

    try:
        Draft202012Validator(
            RESEARCH_ACTION_SCHEMA
        ).validate(
            action
        )

    except Exception as exc:
        raise ResearchProtocolError(
            "Research action does not match "
            "protocol schema"
        ) from exc

    action_name = action[
        "action"
    ]

    query = action[
        "query"
    ]

    url = action[
        "url"
    ]

    result = action[
        "result"
    ]

    if action_name == "search":

        if (
            not isinstance(
                query,
                str,
            )
            or not query.strip()
        ):
            raise ResearchProtocolError(
                "search action requires query"
            )

        if url is not None:
            raise ResearchProtocolError(
                "search action must not "
                "contain url"
            )

        if result is not None:
            raise ResearchProtocolError(
                "search action must not "
                "contain result"
            )

        action[
            "query"
        ] = query.strip()

    elif action_name == "fetch":

        if (
            not isinstance(
                url,
                str,
            )
            or not url.strip()
        ):
            raise ResearchProtocolError(
                "fetch action requires url"
            )

        if query is not None:
            raise ResearchProtocolError(
                "fetch action must not "
                "contain query"
            )

        if result is not None:
            raise ResearchProtocolError(
                "fetch action must not "
                "contain result"
            )

        action[
            "url"
        ] = url.strip()

    elif action_name == "finish":

        if (
            query is not None
            or url is not None
        ):
            raise ResearchProtocolError(
                "finish action cannot contain "
                "query or url"
            )

        if not isinstance(
            result,
            dict,
        ):
            raise ResearchProtocolError(
                "finish action requires "
                "WorkerResult object"
            )

    return action


def validate_worker_result(
    value: dict[str, Any],
    *,
    expected_worker_id: str | None = None,
) -> None:

    if not isinstance(
        value,
        dict,
    ):
        raise ResearchProtocolError(
            "WorkerResult must be an object"
        )

    try:
        Draft202012Validator(
            WORKER_RESULT_SCHEMA
        ).validate(
            value
        )

    except Exception as exc:
        raise ResearchProtocolError(
            "WorkerResult does not match "
            "canonical schema"
        ) from exc

    if (
        value[
            "role"
        ]
        != "researcher"
    ):
        raise ResearchProtocolError(
            "Standalone web research result "
            "must have role=researcher"
        )

    if (
        expected_worker_id
        is not None
        and value[
            "worker_id"
        ]
        != expected_worker_id
    ):
        raise ResearchProtocolError(
            "WorkerResult worker_id mismatch"
        )

    claim_ids = [
        claim[
            "claim_id"
        ]
        for claim
        in value[
            "claims"
        ]
    ]

    source_ids = [
        source[
            "source_id"
        ]
        for source
        in value[
            "sources"
        ]
    ]

    evidence_ids = [
        evidence[
            "evidence_id"
        ]
        for evidence
        in value[
            "evidence"
        ]
    ]

    if (
        len(claim_ids)
        != len(
            set(claim_ids)
        )
    ):
        raise ResearchProtocolError(
            "Duplicate claim_id"
        )

    if (
        len(source_ids)
        != len(
            set(source_ids)
        )
    ):
        raise ResearchProtocolError(
            "Duplicate source_id"
        )

    if (
        len(evidence_ids)
        != len(
            set(evidence_ids)
        )
    ):
        raise ResearchProtocolError(
            "Duplicate evidence_id"
        )

    claim_id_set = set(
        claim_ids
    )

    source_id_set = set(
        source_ids
    )

    for evidence in value[
        "evidence"
    ]:

        if (
            evidence[
                "claim_id"
            ]
            not in claim_id_set
        ):
            raise ResearchProtocolError(
                "Evidence references "
                "unknown claim_id"
            )

        if (
            evidence[
                "source_id"
            ]
            not in source_id_set
        ):
            raise ResearchProtocolError(
                "Evidence references "
                "unknown source_id"
            )

    if (
        value[
            "status"
        ]
        == "success"
        and not value[
            "claims"
        ]
    ):
        raise ResearchProtocolError(
            "Successful Researcher result "
            "cannot contain zero claims"
        )


def normalize_worker_result(
    value: dict[str, Any],
    *,
    worker_id: str,
    provider: str | None,
    account: str | None,
    model: str | None,
) -> dict[str, Any]:

    result = copy.deepcopy(
        value
    )

    # Runtime provenance is authoritative.
    result[
        "worker_id"
    ] = worker_id

    result[
        "role"
    ] = "researcher"

    result[
        "provider"
    ] = provider

    result[
        "account"
    ] = account

    result[
        "model"
    ] = model

    result.setdefault(
        "gaps",
        [],
    )

    result.setdefault(
        "notes",
        None,
    )

    validate_worker_result(
        result,
        expected_worker_id=
            worker_id,
    )

    return result
