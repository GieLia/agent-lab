from copy import deepcopy


from app.research.retry_merge import (
    RetryMergeError,
    merge_retry_worker_result,
)


def base_result():

    return {
        "worker_id":
            "research-graph-v1-researcher",

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
                    "claim-good",

                "text":
                    "API listens on port 8000.",

                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-target",

                "text":
                    "VM has four CPUs.",

                "claim_type":
                    "fact",
            },
            {
                "claim_id":
                    "claim-rec",

                "text":
                    "Prefer PostgreSQL.",

                "claim_type":
                    "recommendation",
            },
        ],

        "sources": [
            {
                "source_id":
                    "source-001",

                "source_type":
                    "internal",

                "title":
                    "Original source",
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-good",

                "claim_id":
                    "claim-good",

                "source_id":
                    "source-001",

                "relationship":
                    "supports",

                "excerpt":
                    "API listens on port 8000.",
            }
        ],

        "gaps": [
            "CPU evidence missing."
        ],

        "notes":
            None,
    }


def retry_result():

    return {
        "worker_id":
            "research-graph-v1-researcher",

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
                    "claim-target",

                "text":
                    "VM has four CPUs.",

                "claim_type":
                    "fact",
            }
        ],

        # Deliberately collides with first run.
        "sources": [
            {
                "source_id":
                    "source-001",

                "source_type":
                    "web",

                "title":
                    "Retry source",
            }
        ],

        "evidence": [
            {
                "evidence_id":
                    "ev-001",

                "claim_id":
                    "claim-target",

                "source_id":
                    "source-001",

                "relationship":
                    "supports",

                "excerpt":
                    "The VM is configured with four CPUs.",
            }
        ],

        "gaps":
            [],

        "notes":
            None,
    }


def reject(
    fn,
    label,
):

    try:
        fn()

    except RetryMergeError:
        print(
            f"{label}_OK"
        )

    else:
        raise AssertionError(
            f"{label} was accepted"
        )


def main():

    base = base_result()
    retry = retry_result()

    merged = merge_retry_worker_result(
        base_result=
            base,

        retry_result=
            retry,

        retry_claim_ids=[
            "claim-target",
        ],

        iteration=2,
    )


    assert [
        item["claim_id"]
        for item
        in merged["claims"]
    ] == [
        "claim-good",
        "claim-target",
        "claim-rec",
    ]


    assert [
        item["source_id"]
        for item
        in merged["sources"]
    ] == [
        "source-001",
        "retry-2-source-001",
    ]


    assert [
        item["evidence_id"]
        for item
        in merged["evidence"]
    ] == [
        "ev-good",
        "retry-2-ev-001",
    ]


    retry_evidence = (
        merged[
            "evidence"
        ][1]
    )

    assert (
        retry_evidence[
            "claim_id"
        ]
        == "claim-target"
    )

    assert (
        retry_evidence[
            "source_id"
        ]
        == "retry-2-source-001"
    )


    assert (
        merged[
            "claims"
        ][0]
        == base[
            "claims"
        ][0]
    )

    assert (
        merged[
            "evidence"
        ][0]
        == base[
            "evidence"
        ][0]
    )

    assert (
        merged[
            "status"
        ]
        == "partial"
    )

    print(
        "RETRY_EXISTING_GOOD_MATERIAL_PRESERVED_OK"
    )

    print(
        "RETRY_TARGET_EVIDENCE_APPENDED_OK"
    )

    print(
        "RETRY_SOURCE_IDS_NAMESPACED_OK"
    )

    print(
        "RETRY_EVIDENCE_IDS_NAMESPACED_OK"
    )


    scope = retry_result()

    scope[
        "claims"
    ].append(
        {
            "claim_id":
                "claim-new",

            "text":
                "New unrelated claim.",

            "claim_type":
                "fact",
        }
    )

    reject(
        lambda:
            merge_retry_worker_result(
                base_result=
                    base_result(),

                retry_result=
                    scope,

                retry_claim_ids=[
                    "claim-target",
                ],

                iteration=2,
            ),
        "RETRY_SCOPE_EXPANSION_REJECTED",
    )


    drift = retry_result()

    drift[
        "claims"
    ][0][
        "text"
    ] = (
        "VM has at least four CPUs."
    )

    reject(
        lambda:
            merge_retry_worker_result(
                base_result=
                    base_result(),

                retry_result=
                    drift,

                retry_claim_ids=[
                    "claim-target",
                ],

                iteration=2,
            ),
        "RETRY_CLAIM_DRIFT_REJECTED",
    )


    reject(
        lambda:
            merge_retry_worker_result(
                base_result=
                    base_result(),

                retry_result=
                    retry_result(),

                retry_claim_ids=[
                    "claim-rec",
                ],

                iteration=2,
            ),
        "RETRY_NONFACT_TARGET_REJECTED",
    )


    new_base = base_result()

    new_base[
        "sources"
    ].append(
        {
            "source_id":
                "retry-2-source-001",

            "source_type":
                "internal",

            "title":
                "Collision",
        }
    )

    reject(
        lambda:
            merge_retry_worker_result(
                base_result=
                    new_base,

                retry_result=
                    retry_result(),

                retry_claim_ids=[
                    "claim-target",
                ],

                iteration=2,
            ),
        "RETRY_NAMESPACED_COLLISION_REJECTED",
    )


    print()
    print(
        "RESEARCH_RETRY_MERGE_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
