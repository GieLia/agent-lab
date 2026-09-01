from pathlib import Path


ROOT = Path(
    "/opt/agent-lab"
)

SQL_FILE = (
    ROOT
    / "infra"
    / "postgres"
    / "migrations"
    / "001_measurement_schema.sql"
)


REQUIRED_TABLES = [
    "measurement.evaluation_case",
    "measurement.evaluation_run",
    "measurement.worker_invocation",
    "measurement.tool_invocation",
    "measurement.run_metric",
    "measurement.gate_result",
    "measurement.artifact_reference",
]


REQUIRED_WORKER_FIELDS = [
    "provider",
    "account",
    "model",
    "role",
    "skill_ids",
    "tool_profile",
    "tools_exposed_count",
    "request_id",
    "session_id",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reported_cost_usd",
    "cost_source",
]


REQUIRED_TOOL_FIELDS = [
    "capability",
    "tool_name",
    "tool_kind",
    "tool_profile",
    "mcp_server",
    "mcp_server_version",
    "human_approval_required",
    "human_approval_granted",
]


def main() -> None:
    sql = SQL_FILE.read_text(
        encoding="utf-8"
    ).lower()

    for table in REQUIRED_TABLES:
        assert table in sql, (
            f"missing table: {table}"
        )

    print(
        "MEASUREMENT_TABLES_OK"
    )

    for field in REQUIRED_WORKER_FIELDS:
        assert field in sql, (
            "missing worker field: "
            f"{field}"
        )

    print(
        "WORKER_PROVENANCE_FIELDS_OK"
    )

    for field in REQUIRED_TOOL_FIELDS:
        assert field in sql, (
            "missing tool field: "
            f"{field}"
        )

    print(
        "TOOL_PROVENANCE_FIELDS_OK"
    )

    for tool_kind in [
        "native",
        "cli",
        "python",
        "http",
        "mcp",
    ]:
        assert (
            f"'{tool_kind}'"
            in sql
        )

    print(
        "TOOL_KIND_CONTRACT_OK"
    )

    assert (
        "reported_cost_usd"
        in sql
    )

    assert (
        "actual_cost_usd"
        not in sql
    )

    print(
        "COST_SEMANTICS_OK"
    )

    print()
    print(
        "MEASUREMENT_SCHEMA_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
