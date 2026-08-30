def validate_gate(gate):
    accepted_workers = set(
        gate["accepted_worker_ids"]
    )
    rejected_workers = set(
        gate["rejected_worker_ids"]
    )

    accepted_claims = set(
        gate["accepted_claim_ids"]
    )
    rejected_claims = set(
        gate["rejected_claim_ids"]
    )

    assert not (
        accepted_workers
        & rejected_workers
    ), "worker appears in accepted and rejected sets"

    assert not (
        accepted_claims
        & rejected_claims
    ), "claim appears in accepted and rejected sets"

    decision = gate["decision"]

    accepted_count = (
        len(accepted_workers)
        + len(accepted_claims)
    )

    rejected_count = (
        len(rejected_workers)
        + len(rejected_claims)
    )

    if decision == "accepted":
        assert accepted_count > 0
        assert rejected_count == 0

    elif decision == "partial":
        assert accepted_count > 0
        assert rejected_count > 0

    elif decision == "rejected":
        assert accepted_count == 0
        assert rejected_count > 0

    else:
        raise AssertionError(
            f"invalid decision: {decision}"
        )


def check_valid_cases():
    cases = [
        {
            "decision": "accepted",
            "accepted_worker_ids": ["w-1"],
            "accepted_claim_ids": [],
            "rejected_worker_ids": [],
            "rejected_claim_ids": [],
        },
        {
            "decision": "partial",
            "accepted_worker_ids": ["w-1"],
            "accepted_claim_ids": ["c-1"],
            "rejected_worker_ids": ["w-2"],
            "rejected_claim_ids": ["c-2"],
        },
        {
            "decision": "rejected",
            "accepted_worker_ids": [],
            "accepted_claim_ids": [],
            "rejected_worker_ids": ["w-1"],
            "rejected_claim_ids": [],
        },
    ]

    for gate in cases:
        validate_gate(gate)

    print(
        "ACCEPTANCE_GATE_VALID_CASES_OK"
    )


def check_overlap_rejected():
    broken = {
        "decision": "partial",
        "accepted_worker_ids": ["w-1"],
        "accepted_claim_ids": ["c-1"],
        "rejected_worker_ids": ["w-1"],
        "rejected_claim_ids": ["c-2"],
    }

    try:
        validate_gate(broken)

    except AssertionError:
        print(
            "ACCEPTANCE_GATE_OVERLAP_REJECTED_OK"
        )
        return

    raise AssertionError(
        "overlapping gate was accepted"
    )


def main():
    check_valid_cases()
    check_overlap_rejected()

    print()
    print(
        "ACCEPTANCE_GATE_SEMANTICS_OK"
    )


if __name__ == "__main__":
    main()
