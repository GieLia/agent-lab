import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.db import get_db_uri


ROOT = Path("/opt/agent-lab")

DEFAULT_BASELINE = (
    ROOT
    / "tests"
    / "evals"
    / "direct_anchor"
    / "baselines"
    / "state_storage_boundary_v1"
)

CASE_FILE = (
    ROOT
    / "tests"
    / "evals"
    / "direct_anchor"
    / "case_v1.json"
)


def load_json(path: Path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def parse_time(value: str):
    return datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )


def ensure_case(
    cursor,
    metadata,
    case,
):
    cursor.execute(
        """
        INSERT INTO measurement.evaluation_case (
            case_id,
            case_version,
            case_sha256,
            title,
            objective,
            raw_case
        )
        VALUES (
            %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (
            case_id,
            case_version
        )
        DO NOTHING
        """,
        (
            metadata["case_id"],
            metadata["case_version"],
            metadata.get(
                "case_sha256"
            ),
            case.get(
                "title",
                metadata["case_id"],
            ),
            case.get(
                "objective"
            ),
            Jsonb(case),
        ),
    )

    cursor.execute(
        """
        SELECT case_sha256
        FROM measurement.evaluation_case
        WHERE
            case_id = %s
            AND case_version = %s
        """,
        (
            metadata["case_id"],
            metadata["case_version"],
        ),
    )

    stored_hash = cursor.fetchone()[0]

    if (
        metadata.get("case_sha256")
        and stored_hash
        != metadata["case_sha256"]
    ):
        raise RuntimeError(
            "Evaluation case hash mismatch"
        )


def ensure_run(
    cursor,
    metadata,
    result,
    git_sha,
):
    run_id = UUID(
        metadata["run_id"]
    )

    cursor.execute(
        """
        INSERT INTO measurement.evaluation_run (
            run_id,
            case_id,
            case_version,
            run_type,
            git_sha,
            orchestration,
            started_at,
            status,
            raw_metadata
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (run_id)
        DO NOTHING
        """,
        (
            run_id,
            metadata["case_id"],
            metadata["case_version"],
            "direct_anchor",
            git_sha,
            metadata.get(
                "orchestration"
            ),
            parse_time(
                metadata["created_at"]
            ),
            result["status"],
            Jsonb(metadata),
        ),
    )

    return run_id


def ensure_worker(
    cursor,
    run_id,
    metadata,
    result,
):
    invocation_id = (
        f"{run_id}:"
        f"{result['worker_id']}"
    )

    tools_exposed_count = None

    if (
        metadata.get(
            "external_tools"
        )
        is False
    ):
        tools_exposed_count = 0

    cursor.execute(
        """
        INSERT INTO measurement.worker_invocation (
            invocation_id,
            run_id,
            worker_id,
            role,
            provider,
            account,
            model,
            skill_ids,
            tool_profile,
            tools_exposed_count,
            started_at,
            status,
            raw_result
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (invocation_id)
        DO NOTHING
        """,
        (
            invocation_id,
            run_id,
            result["worker_id"],
            result["role"],
            result["provider"],
            result.get(
                "account"
            ),
            result.get(
                "model"
            ),
            [],
            metadata.get(
                "tool_profile"
            ),
            tools_exposed_count,
            parse_time(
                metadata["created_at"]
            ),
            result["status"],
            Jsonb(result),
        ),
    )

    return invocation_id


def ensure_metric(
    cursor,
    run_id,
    invocation_id,
    name,
    value,
    unit="count",
):
    cursor.execute(
        """
        SELECT 1
        FROM measurement.run_metric
        WHERE
            run_id = %s
            AND worker_invocation_id = %s
            AND metric_name = %s
        LIMIT 1
        """,
        (
            run_id,
            invocation_id,
            name,
        ),
    )

    if cursor.fetchone():
        return

    cursor.execute(
        """
        INSERT INTO measurement.run_metric (
            run_id,
            worker_invocation_id,
            metric_name,
            numeric_value,
            unit
        )
        VALUES (
            %s, %s, %s, %s, %s
        )
        """,
        (
            run_id,
            invocation_id,
            name,
            value,
            unit,
        ),
    )


def ensure_gate(
    cursor,
    run_id,
    evaluation,
):
    gate_name = "human_anchor_v1"

    cursor.execute(
        """
        SELECT 1
        FROM measurement.gate_result
        WHERE
            run_id = %s
            AND gate_name = %s
            AND evaluator_type = %s
        LIMIT 1
        """,
        (
            run_id,
            gate_name,
            evaluation[
                "evaluator_type"
            ],
        ),
    )

    if cursor.fetchone():
        return

    passed = (
        evaluation[
            "criteria_passed"
        ]
        == evaluation[
            "criteria_total"
        ]
    )

    payload = {
        "criteria":
            evaluation.get(
                "criteria",
                [],
            ),
        "findings":
            evaluation.get(
                "findings",
                [],
            ),
        "notes":
            evaluation.get(
                "notes",
            ),
    }

    cursor.execute(
        """
        INSERT INTO measurement.gate_result (
            run_id,
            gate_name,
            evaluator_type,
            verdict,
            passed,
            findings
        )
        VALUES (
            %s, %s, %s, %s, %s, %s
        )
        """,
        (
            run_id,
            gate_name,
            evaluation[
                "evaluator_type"
            ],
            evaluation[
                "verdict"
            ],
            passed,
            Jsonb(payload),
        ),
    )


def ensure_artifact(
    cursor,
    run_id,
    invocation_id,
    artifact_type,
    artifact_uri,
    digest,
    media_type,
):
    cursor.execute(
        """
        SELECT 1
        FROM measurement.artifact_reference
        WHERE
            run_id = %s
            AND artifact_uri = %s
        LIMIT 1
        """,
        (
            run_id,
            artifact_uri,
        ),
    )

    if cursor.fetchone():
        return

    cursor.execute(
        """
        INSERT INTO measurement.artifact_reference (
            run_id,
            worker_invocation_id,
            artifact_type,
            artifact_uri,
            sha256,
            media_type
        )
        VALUES (
            %s, %s, %s, %s, %s, %s
        )
        """,
        (
            run_id,
            invocation_id,
            artifact_type,
            artifact_uri,
            digest,
            media_type,
        ),
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--git-sha",
        required=True,
    )

    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=DEFAULT_BASELINE,
    )

    args = parser.parse_args()

    baseline = (
        args.baseline_dir.resolve()
    )

    metadata_file = (
        baseline / "metadata.json"
    )

    result_file = (
        baseline / "worker-result.json"
    )

    evaluation_file = (
        baseline
        / "human-evaluation.json"
    )

    manifest_file = (
        baseline
        / "baseline-manifest.json"
    )

    for path in [
        metadata_file,
        result_file,
        evaluation_file,
        manifest_file,
        CASE_FILE,
    ]:
        if not path.is_file():
            raise RuntimeError(
                f"Missing file: {path}"
            )

    metadata = load_json(
        metadata_file
    )

    result = load_json(
        result_file
    )

    evaluation = load_json(
        evaluation_file
    )

    manifest = load_json(
        manifest_file
    )

    case = load_json(
        CASE_FILE
    )

    if (
        metadata["run_id"]
        != evaluation["run_id"]
    ):
        raise RuntimeError(
            "Run identity mismatch"
        )

    if (
        metadata["run_id"]
        != manifest["run_id"]
    ):
        raise RuntimeError(
            "Manifest identity mismatch"
        )

    git_sha = args.git_sha.strip()

    if not git_sha:
        raise RuntimeError(
            "Empty git SHA"
        )

    with psycopg.connect(
        get_db_uri()
    ) as connection:

        with connection.cursor() as cursor:
            ensure_case(
                cursor,
                metadata,
                case,
            )

            run_id = ensure_run(
                cursor,
                metadata,
                result,
                git_sha,
            )

            invocation_id = (
                ensure_worker(
                    cursor,
                    run_id,
                    metadata,
                    result,
                )
            )

            metrics = {
                "claims_count":
                    len(
                        result.get(
                            "claims",
                            [],
                        )
                    ),
                "sources_count":
                    len(
                        result.get(
                            "sources",
                            [],
                        )
                    ),
                "evidence_count":
                    len(
                        result.get(
                            "evidence",
                            [],
                        )
                    ),
                "gaps_count":
                    len(
                        result.get(
                            "gaps",
                            [],
                        )
                    ),
                "model_invocations":
                    metadata.get(
                        "model_invocations",
                        1,
                    ),
                "human_criteria_total":
                    evaluation[
                        "criteria_total"
                    ],
                "human_criteria_passed":
                    evaluation[
                        "criteria_passed"
                    ],
            }

            for name, value in (
                metrics.items()
            ):
                ensure_metric(
                    cursor,
                    run_id,
                    invocation_id,
                    name,
                    value,
                )

            ensure_gate(
                cursor,
                run_id,
                evaluation,
            )

            artifact_types = {
                "metadata.json":
                    "run_metadata",
                "worker-result.json":
                    "worker_result",
                "human-evaluation.json":
                    "human_evaluation",
                "case_v1.json":
                    "evaluation_case",
                "human_reference_v1.json":
                    "human_reference",
            }

            for (
                relative,
                digest,
            ) in manifest[
                "files"
            ].items():

                artifact_path = (
                    ROOT / relative
                )

                artifact_name = (
                    artifact_path.name
                )

                worker_ref = None

                if (
                    artifact_name
                    == "worker-result.json"
                ):
                    worker_ref = (
                        invocation_id
                    )

                ensure_artifact(
                    cursor,
                    run_id,
                    worker_ref,
                    artifact_types.get(
                        artifact_name,
                        "eval_artifact",
                    ),
                    relative,
                    digest,
                    "application/json",
                )

            ensure_artifact(
                cursor,
                run_id,
                None,
                "baseline_manifest",
                str(
                    manifest_file.relative_to(
                        ROOT
                    )
                ),
                sha256(
                    manifest_file
                ),
                "application/json",
            )

    print(
        "DIRECT_ANCHOR_BASELINE_IMPORT_OK"
    )

    print(
        f"run_id={metadata['run_id']}"
    )

    print(
        f"worker_invocation_id="
        f"{metadata['run_id']}:"
        f"{result['worker_id']}"
    )


if __name__ == "__main__":
    main()
