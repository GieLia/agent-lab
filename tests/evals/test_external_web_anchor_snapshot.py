import hashlib
import json
from pathlib import Path

from app.research.protocol import (
    validate_worker_result,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DIRECT = (
    ROOT
    / "tests"
    / "evals"
    / "direct_anchor"
)

BASELINE = (
    DIRECT
    / "baselines"
    / "external_web_research_v1"
)


EXPECTED_RUN_ID = (
    "7a8e5eac-07c0-41de-b412-10b06f37e6b3"
)

EXPECTED_RUN_GIT_SHA = (
    "47ee8fc75b9192178b3d6f510640f6bf5a2e1bd6"
)

EXPECTED_RUNNER_COMMIT = (
    "5df4d61"
)

EXPECTED_RESULT_SHA = (
    "1230f1eb25241d4a9c6fe9a9b1c9181172d0fe8fb40a2b79c3c474b70841baf0"
)


def load(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256(
    path: Path,
):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def check_manifest():

    manifest = load(
        BASELINE
        / "baseline-manifest.json"
    )

    assert (
        manifest[
            "manifest_version"
        ]
        == 1
    )

    assert (
        manifest[
            "case_id"
        ]
        == "external_web_research_v1"
    )

    assert (
        manifest[
            "run_id"
        ]
        == EXPECTED_RUN_ID
    )

    assert (
        len(
            manifest[
                "files"
            ]
        )
        == 5
    )

    for (
        relative,
        expected,
    ) in manifest[
        "files"
    ].items():

        path = (
            ROOT
            / relative
        )

        assert path.is_file(), relative

        assert (
            sha256(
                path
            )
            == expected
        ), (
            "external web baseline hash "
            f"mismatch: {relative}"
        )

    print(
        "EXTERNAL_WEB_ANCHOR_HASHES_OK"
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

    assert (
        metadata[
            "run_id"
        ]
        == EXPECTED_RUN_ID
    )

    assert (
        evaluation[
            "run_id"
        ]
        == EXPECTED_RUN_ID
    )

    assert (
        metadata[
            "case_id"
        ]
        == evaluation[
            "case_id"
        ]
        == "external_web_research_v1"
    )

    assert (
        metadata[
            "run_git_sha"
        ]
        == EXPECTED_RUN_GIT_SHA
    )

    assert (
        metadata[
            "runner_commit"
        ]
        == EXPECTED_RUNNER_COMMIT
    )

    assert (
        metadata[
            "worker_result_original_sha256"
        ]
        == EXPECTED_RESULT_SHA
    )

    print(
        "EXTERNAL_WEB_ANCHOR_IDENTITY_OK"
    )


def check_runtime_boundary():

    metadata = load(
        BASELINE
        / "metadata.json"
    )

    assert (
        metadata[
            "claude_tool_profile"
        ]
        == "reasoning"
    )

    assert (
        metadata[
            "native_claude_tools"
        ]
        == 0
    )

    assert (
        metadata[
            "research_tool_profile"
        ]
        == "research-readonly"
    )

    assert set(
        metadata[
            "allowed_capabilities"
        ]
    ) == {
        "web.search",
        "web.fetch",
    }

    assert (
        metadata[
            "orchestration"
        ]
        == "standalone_research_tool_loop"
    )

    assert (
        metadata[
            "model_invocations"
        ]
        == 3
    )

    assert (
        metadata[
            "search_calls"
        ]
        == 1
    )

    assert (
        metadata[
            "fetch_calls"
        ]
        == 1
    )

    print(
        "EXTERNAL_WEB_ANCHOR_RUNTIME_BOUNDARY_OK"
    )


def check_worker_result():

    path = (
        BASELINE
        / "worker-result.json"
    )

    assert (
        sha256(
            path
        )
        == EXPECTED_RESULT_SHA
    )

    result = load(
        path
    )

    validate_worker_result(
        result,
        expected_worker_id=
            "direct-web-researcher-v1",
    )

    assert (
        result[
            "status"
        ]
        == "success"
    )

    assert (
        len(
            result[
                "claims"
            ]
        )
        == 3
    )

    assert (
        len(
            result[
                "sources"
            ]
        )
        == 1
    )

    assert (
        len(
            result[
                "evidence"
            ]
        )
        == 3
    )

    source = result[
        "sources"
    ][0]

    assert (
        source[
            "url"
        ]
        == (
            "https://docs.python.org/"
            "3/library/venv.html"
        )
    )

    assert (
        source[
            "content_hash"
        ]
    )

    assert (
        source[
            "retrieved_at"
        ]
    )

    print(
        "EXTERNAL_WEB_ANCHOR_RESULT_OK"
    )


def check_human_evaluation():

    evaluation = load(
        BASELINE
        / "human-evaluation.json"
    )

    assert (
        evaluation[
            "verdict"
        ]
        == "pass_with_findings"
    )

    assert (
        evaluation[
            "criteria_total"
        ]
        == 7
    )

    assert (
        evaluation[
            "criteria_passed"
        ]
        == 7
    )

    assert all(
        item[
            "status"
        ]
        == "pass"
        for item
        in evaluation[
            "criteria"
        ]
    )

    dimensions = (
        evaluation[
            "quality_dimensions"
        ]
    )

    assert (
        dimensions[
            "runtime_security"
        ]
        == "pass"
    )

    assert (
        dimensions[
            "source_provenance"
        ]
        == "pass"
    )

    assert (
        dimensions[
            "schema_integrity"
        ]
        == "pass"
    )

    assert (
        dimensions[
            "evidence_excerpt_existence"
        ]
        == "pass"
    )

    assert (
        dimensions[
            "claim_evidence_semantic_coverage"
        ]
        == "partial"
    )

    assert (
        evaluation[
            "baseline_locked"
        ]
        is True
    )

    assert (
        evaluation[
            "regeneration_allowed"
        ]
        is False
    )

    print(
        "EXTERNAL_WEB_ANCHOR_HUMAN_GATE_OK"
    )


def check_known_defects():

    evaluation = load(
        BASELINE
        / "human-evaluation.json"
    )

    findings = {
        item[
            "id"
        ]:
            item
        for item
        in evaluation[
            "findings"
        ]
    }

    assert {
        "WEB-HAF-001",
        "WEB-HAF-002",
        "WEB-HAF-003",
    } <= set(
        findings
    )

    assert (
        findings[
            "WEB-HAF-001"
        ][
            "claim_id"
        ]
        == "claim-1"
    )

    assert (
        findings[
            "WEB-HAF-001"
        ][
            "evidence_id"
        ]
        == "ev-1"
    )

    assert (
        findings[
            "WEB-HAF-002"
        ][
            "claim_id"
        ]
        == "claim-2"
    )

    assert (
        findings[
            "WEB-HAF-002"
        ][
            "evidence_id"
        ]
        == "ev-2"
    )

    print(
        "EXTERNAL_WEB_ANCHOR_KNOWN_DEFECTS_OK"
    )


def check_reference_contract():

    reference = load(
        DIRECT
        / "external_web_human_reference_v1.json"
    )

    case = load(
        DIRECT
        / "external_web_case_v1.json"
    )

    assert (
        case[
            "case_id"
        ]
        == reference[
            "case_id"
        ]
        == "external_web_research_v1"
    )

    assert (
        len(
            reference[
                "required_anchor_points"
            ]
        )
        == 7
    )

    print(
        "EXTERNAL_WEB_ANCHOR_REFERENCE_OK"
    )


def main():

    check_manifest()
    check_identity()
    check_runtime_boundary()
    check_worker_result()
    check_human_evaluation()
    check_known_defects()
    check_reference_contract()

    print()
    print(
        "EXTERNAL_WEB_DIRECT_ANCHOR_FROZEN_OK"
    )


if __name__ == "__main__":
    main()
