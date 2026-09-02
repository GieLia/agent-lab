import copy

from app.research.protocol import (
    RESEARCH_ACTION_SCHEMA,
    WORKER_RESULT_SCHEMA,
    ResearchProtocolError,
    normalize_worker_result,
    parse_action,
    validate_worker_result,
)


def expect_rejected(
    fn,
    *args,
    **kwargs,
):

    try:
        fn(
            *args,
            **kwargs,
        )

    except ResearchProtocolError:
        return

    raise AssertionError(
        "Expected ResearchProtocolError"
    )


def valid_worker_result():

    return {
        "worker_id":
            "researcher-test-v1",

        "role":
            "researcher",

        "provider":
            "claude",

        "account":
            "primary",

        "model":
            None,

        "status":
            "success",

        "claims": [
            {
                "claim_id":
                    "claim-1",
                "text":
                    "Example factual claim.",
                "claim_type":
                    "fact",
                "importance":
                    "high",
                "verification_status":
                    "verified",
            }
        ],

        "sources": [
            {
                "source_id":
                    "source-1",
                "source_type":
                    "web",
                "title":
                    "Example Source",
                "url":
                    "https://example.com/",
                "publisher":
                    None,
                "published_at":
                    None,
                "retrieved_at":
                    None,
                "content_hash":
                    None,
                "metadata": {},
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "evidence-1",
                "claim_id":
                    "claim-1",
                "source_id":
                    "source-1",
                "relationship":
                    "supports",
                "excerpt":
                    "Example evidence.",
                "location":
                    None,
                "strength":
                    "strong",
                "notes":
                    None,
            }
        ],

        "gaps": [],
        "notes":
            None,
    }


def check_action_protocol():

    search = parse_action(
        {
            "action":
                "search",
            "query":
                " test query ",
            "url":
                None,
            "reason":
                "Find candidate sources.",
            "result":
                None,
        }
    )

    assert (
        search[
            "query"
        ]
        == "test query"
    )

    fetch = parse_action(
        {
            "action":
                "fetch",
            "query":
                None,
            "url":
                " https://example.com/ ",
            "reason":
                "Retrieve evidence.",
            "result":
                None,
        }
    )

    assert (
        fetch[
            "url"
        ]
        == "https://example.com/"
    )

    finish = parse_action(
        {
            "action":
                "finish",
            "query":
                None,
            "url":
                None,
            "reason":
                "Coverage sufficient.",
            "result":
                valid_worker_result(),
        }
    )

    assert (
        finish[
            "action"
        ]
        == "finish"
    )

    print(
        "RESEARCH_ACTION_PROTOCOL_OK"
    )


def check_action_rejections():

    expect_rejected(
        parse_action,
        {
            "action":
                "search",
            "query":
                "",
            "url":
                None,
            "reason":
                None,
            "result":
                None,
        },
    )

    expect_rejected(
        parse_action,
        {
            "action":
                "search",
            "query":
                "query",
            "url":
                "https://example.com/",
            "reason":
                None,
            "result":
                None,
        },
    )

    expect_rejected(
        parse_action,
        {
            "action":
                "fetch",
            "query":
                None,
            "url":
                None,
            "reason":
                None,
            "result":
                None,
        },
    )

    expect_rejected(
        parse_action,
        {
            "action":
                "finish",
            "query":
                "forbidden",
            "url":
                None,
            "reason":
                None,
            "result":
                None,
        },
    )

    expect_rejected(
        parse_action,
        {
            "action":
                "shell",
            "query":
                None,
            "url":
                None,
            "reason":
                None,
            "result":
                None,
        },
    )

    print(
        "RESEARCH_ACTION_REJECTIONS_OK"
    )


def check_schema_inlining():

    def collect_refs(
        value,
    ):

        refs = []

        if isinstance(
            value,
            list,
        ):
            for item in value:
                refs.extend(
                    collect_refs(
                        item
                    )
                )

            return refs

        if not isinstance(
            value,
            dict,
        ):
            return refs

        reference = value.get(
            "$ref"
        )

        if isinstance(
            reference,
            str,
        ):
            refs.append(
                reference
            )

        for item in value.values():
            refs.extend(
                collect_refs(
                    item
                )
            )

        return refs

    refs = collect_refs(
        WORKER_RESULT_SCHEMA
    )

    external_refs = [
        reference
        for reference
        in refs
        if not reference.startswith(
            "#"
        )
    ]

    assert (
        external_refs
        == []
    )

    # Embedded canonical schemas may retain
    # their own $id values. That is expected.
    serialized = str(
        WORKER_RESULT_SCHEMA
    )

    assert (
        "'title': 'Claim'"
        in serialized
    )

    assert (
        "'title': 'Source'"
        in serialized
    )

    assert (
        "'title': 'Evidence'"
        in serialized
    )

    assert (
        RESEARCH_ACTION_SCHEMA[
            "additionalProperties"
        ]
        is False
    )

    print(
        "WORKER_RESULT_SCHEMA_INLINED_OK"
    )


def check_worker_result():

    result = valid_worker_result()

    validate_worker_result(
        result,
        expected_worker_id=
            "researcher-test-v1",
    )

    print(
        "CANONICAL_WORKER_RESULT_OK"
    )


def check_worker_result_integrity():

    orphan_claim = (
        valid_worker_result()
    )

    orphan_claim[
        "evidence"
    ][0][
        "claim_id"
    ] = "missing-claim"

    expect_rejected(
        validate_worker_result,
        orphan_claim,
    )

    orphan_source = (
        valid_worker_result()
    )

    orphan_source[
        "evidence"
    ][0][
        "source_id"
    ] = "missing-source"

    expect_rejected(
        validate_worker_result,
        orphan_source,
    )

    duplicate = (
        valid_worker_result()
    )

    duplicate[
        "claims"
    ].append(
        copy.deepcopy(
            duplicate[
                "claims"
            ][0]
        )
    )

    expect_rejected(
        validate_worker_result,
        duplicate,
    )

    empty_success = (
        valid_worker_result()
    )

    empty_success[
        "claims"
    ] = []

    empty_success[
        "evidence"
    ] = []

    expect_rejected(
        validate_worker_result,
        empty_success,
    )

    print(
        "WORKER_RESULT_REFERENCE_INTEGRITY_OK"
    )


def check_runtime_provenance():

    value = (
        valid_worker_result()
    )

    value[
        "worker_id"
    ] = "MODEL_FAKE_ID"

    value[
        "role"
    ] = "critic"

    value[
        "provider"
    ] = "MODEL_FAKE_PROVIDER"

    value[
        "account"
    ] = "MODEL_FAKE_ACCOUNT"

    value[
        "model"
    ] = "MODEL_FAKE_MODEL"

    normalized = (
        normalize_worker_result(
            value,
            worker_id=
                "runtime-researcher-v1",
            provider=
                "claude",
            account=
                "primary",
            model=
                None,
        )
    )

    assert (
        normalized[
            "worker_id"
        ]
        == "runtime-researcher-v1"
    )

    assert (
        normalized[
            "role"
        ]
        == "researcher"
    )

    assert (
        normalized[
            "provider"
        ]
        == "claude"
    )

    assert (
        normalized[
            "account"
        ]
        == "primary"
    )

    assert (
        normalized[
            "model"
        ]
        is None
    )

    print(
        "RUNTIME_PROVENANCE_AUTHORITY_OK"
    )


def main():

    check_action_protocol()
    check_action_rejections()
    check_schema_inlining()
    check_worker_result()
    check_worker_result_integrity()
    check_runtime_provenance()

    print()
    print(
        "RESEARCH_PROTOCOL_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
