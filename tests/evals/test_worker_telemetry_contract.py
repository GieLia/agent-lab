from decimal import Decimal
from pathlib import Path

from app.workers.telemetry import (
    parse_claude_payload,
    parse_codex_events,
)


ROOT = Path(
    "/opt/agent-lab"
)


def test_claude():
    payload = {
        "session_id":
            "00000000-0000-0000-0000-000000000001",
        "duration_ms":
            2283,
        "total_cost_usd":
            0.0089728,
        "usage": {
            "input_tokens":
                2,
            "cache_creation_input_tokens":
                1779,
            "cache_read_input_tokens":
                3289,
            "output_tokens":
                20,
            "output_tokens_details": {
                "thinking_tokens":
                    0,
            },
        },
        "modelUsage": {
            "claude-model-a": {},
            "claude-model-b": {},
        },
    }

    result = parse_claude_payload(
        payload=payload,
        text="CLAUDE_OK",
        account="primary",
    )

    assert result.text == "CLAUDE_OK"
    assert result.provider == "claude"
    assert result.account == "primary"

    assert result.model is None

    assert result.input_tokens == 2
    assert result.output_tokens == 20
    assert result.cache_read_tokens == 3289
    assert result.cache_write_tokens == 1779
    assert result.reasoning_output_tokens == 0

    assert (
        result.reported_cost_usd
        == Decimal("0.0089728")
    )

    assert (
        result.cost_source
        == "claude_cli_reported"
    )

    print(
        "CLAUDE_TELEMETRY_OK"
    )


def test_codex():
    events = [
        {
            "type":
                "thread.started",
            "thread_id":
                "00000000-0000-0000-0000-000000000002",
        },
        {
            "type":
                "turn.started",
        },
        {
            "type":
                "turn.completed",
            "usage": {
                "input_tokens":
                    14700,
                "cached_input_tokens":
                    11008,
                "cache_write_input_tokens":
                    0,
                "output_tokens":
                    11,
                "reasoning_output_tokens":
                    0,
            },
        },
    ]

    result = parse_codex_events(
        events=events,
        text="CODEX_OK",
        account="primary",
    )

    assert result.text == "CODEX_OK"
    assert result.provider == "codex"

    assert result.model is None

    assert (
        result.session_id
        == "00000000-0000-0000-0000-000000000002"
    )

    assert result.input_tokens == 14700
    assert result.output_tokens == 11
    assert result.cache_read_tokens == 11008
    assert result.cache_write_tokens == 0
    assert result.reasoning_output_tokens == 0

    assert result.reported_cost_usd is None

    print(
        "CODEX_TELEMETRY_OK"
    )


def test_migration():
    sql = (
        ROOT
        / "infra"
        / "postgres"
        / "migrations"
        / "002_worker_usage_fields.sql"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "reasoning_output_tokens"
        in sql
    )

    print(
        "WORKER_USAGE_MIGRATION_OK"
    )


def main():
    test_claude()
    test_codex()
    test_migration()

    print()
    print(
        "WORKER_TELEMETRY_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
