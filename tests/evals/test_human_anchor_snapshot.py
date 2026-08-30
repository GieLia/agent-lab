import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

BASELINE = (
    ROOT
    / "tests"
    / "evals"
    / "direct_anchor"
    / "baselines"
    / "state_storage_boundary_v1"
)


def load(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def check_manifest():
    manifest = load(
        BASELINE
        / "baseline-manifest.json"
    )

    for relative, expected in (
        manifest["files"].items()
    ):
        path = ROOT / relative

        assert path.is_file(), relative

        assert sha256(path) == expected, (
            f"baseline hash mismatch: "
            f"{relative}"
        )

    print(
        "HUMAN_ANCHOR_HASHES_OK"
    )


def check_identity():
    metadata = load(
        BASELINE
        / "metadata.json"
    )

    evaluation = load(
        BASELINE
        / "human-evaluation.json"
    )

    assert metadata["run_id"] == (
        evaluation["run_id"]
    )

    assert metadata["case_id"] == (
        evaluation["case_id"]
    )

    assert metadata["model_invocations"] == 1
    assert metadata["orchestration"] == "none"
    assert metadata["external_tools"] is False
    assert metadata["critic"] is False
    assert metadata["evidence_verifier"] is False
    assert metadata["synthesizer"] is False

    print(
        "HUMAN_ANCHOR_IDENTITY_OK"
    )


def check_criteria():
    reference = load(
        ROOT
        / "tests"
        / "evals"
        / "direct_anchor"
        / "human_reference_v1.json"
    )

    evaluation = load(
        BASELINE
        / "human-evaluation.json"
    )

    assert len(
        reference[
            "required_anchor_points"
        ]
    ) == 7

    assert (
        evaluation["criteria_total"]
        == 7
    )

    assert (
        evaluation["criteria_passed"]
        == 7
    )

    assert all(
        item["status"] == "pass"
        for item in evaluation[
            "criteria"
        ]
    )

    assert (
        evaluation["verdict"]
        == "pass_with_findings"
    )

    assert (
        evaluation["baseline_locked"]
        is True
    )

    assert (
        evaluation[
            "regeneration_allowed"
        ]
        is False
    )

    print(
        "HUMAN_ANCHOR_CRITERIA_OK"
    )


def check_references():
    result = load(
        BASELINE
        / "worker-result.json"
    )

    evaluation = load(
        BASELINE
        / "human-evaluation.json"
    )

    claim_ids = {
        item["claim_id"]
        for item in result["claims"]
    }

    for criterion in evaluation[
        "criteria"
    ]:
        assert set(
            criterion["claim_refs"]
        ) <= claim_ids

    print(
        "HUMAN_ANCHOR_REFERENCES_OK"
    )


def check_known_baseline_defect():
    result = load(
        BASELINE
        / "worker-result.json"
    )

    claims = {
        item["claim_id"]: item
        for item in result["claims"]
    }

    evidence = {
        item["evidence_id"]: item
        for item in result["evidence"]
    }

    assert (
        claims["c12"][
            "verification_status"
        ]
        == "contradicted"
    )

    assert (
        evidence["e12"][
            "claim_id"
        ]
        == "c12"
    )

    assert (
        evidence["e12"][
            "relationship"
        ]
        == "contradicts"
    )

    print(
        "HUMAN_ANCHOR_KNOWN_DEFECT_OK"
    )


def main():
    check_manifest()
    check_identity()
    check_criteria()
    check_references()
    check_known_baseline_defect()

    print()
    print(
        "HUMAN_ANCHOR_GATE_OK"
    )


if __name__ == "__main__":
    main()
