from decimal import Decimal
from typing import Any

from .result import WorkerExecutionResult


def _integer(
    value: Any,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        result = int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if result < 0:
        return None

    return result


def _decimal(
    value: Any,
) -> Decimal | None:
    if value is None:
        return None

    try:
        result = Decimal(
            str(value)
        )
    except Exception:
        return None

    if result < 0:
        return None

    return result


def _claude_model(
    payload: dict[str, Any],
) -> str | None:
    direct = payload.get(
        "model"
    )

    if (
        isinstance(direct, str)
        and direct.strip()
    ):
        return direct.strip()

    model_usage = payload.get(
        "modelUsage"
    )

    if not isinstance(
        model_usage,
        dict,
    ):
        return None

    models = sorted(
        str(name)
        for name in model_usage
        if str(name).strip()
    )

    if len(models) == 1:
        return models[0]

    return None


def parse_claude_payload(
    *,
    payload: dict[str, Any],
    text: str,
    account: str | None,
    request_id: str | None = None,
    duration_ms: int | None = None,
) -> WorkerExecutionResult:
    usage = payload.get(
        "usage"
    )

    if not isinstance(
        usage,
        dict,
    ):
        usage = {}

    output_details = usage.get(
        "output_tokens_details"
    )

    if not isinstance(
        output_details,
        dict,
    ):
        output_details = {}

    reported_cost = _decimal(
        payload.get(
            "total_cost_usd"
        )
    )

    provider_duration = _integer(
        payload.get(
            "duration_ms"
        )
    )

    metadata = {
        key: value
        for key, value in payload.items()
        if key not in {
            "result",
            "structured_output",
        }
    }

    session_id = payload.get(
        "session_id"
    )

    if not isinstance(
        session_id,
        str,
    ):
        session_id = None

    return WorkerExecutionResult(
        text=text,
        provider="claude",
        account=account,
        model=_claude_model(
            payload
        ),
        request_id=request_id,
        session_id=session_id,
        status="success",
        duration_ms=(
            provider_duration
            if provider_duration is not None
            else duration_ms
        ),
        input_tokens=_integer(
            usage.get(
                "input_tokens"
            )
        ),
        output_tokens=_integer(
            usage.get(
                "output_tokens"
            )
        ),
        cache_read_tokens=_integer(
            usage.get(
                "cache_read_input_tokens"
            )
        ),
        cache_write_tokens=_integer(
            usage.get(
                "cache_creation_input_tokens"
            )
        ),
        reasoning_output_tokens=_integer(
            output_details.get(
                "thinking_tokens"
            )
        ),
        reported_cost_usd=reported_cost,
        cost_source=(
            "claude_cli_reported"
            if reported_cost is not None
            else None
        ),
        raw_metadata=metadata,
    )


def parse_codex_events(
    *,
    events: list[dict[str, Any]],
    text: str,
    account: str | None = None,
    requested_model: str | None = None,
    duration_ms: int | None = None,
) -> WorkerExecutionResult:
    thread_id = None
    usage: dict[str, Any] = {}
    event_types: list[str] = []

    for event in events:
        event_type = event.get(
            "type"
        )

        if isinstance(
            event_type,
            str,
        ):
            event_types.append(
                event_type
            )

        if event_type == "thread.started":
            candidate = event.get(
                "thread_id"
            )

            if isinstance(
                candidate,
                str,
            ):
                thread_id = candidate

        if (
            event_type == "turn.completed"
            and isinstance(
                event.get(
                    "usage"
                ),
                dict,
            )
        ):
            usage = event[
                "usage"
            ]

    raw_metadata = {
        "thread_id": thread_id,
        "usage": usage,
        "event_types": event_types,
    }

    return WorkerExecutionResult(
        text=text,
        provider="codex",
        account=account,
        model=(
            requested_model
            if requested_model
            else None
        ),
        request_id=None,
        session_id=thread_id,
        status="success",
        duration_ms=duration_ms,
        input_tokens=_integer(
            usage.get(
                "input_tokens"
            )
        ),
        output_tokens=_integer(
            usage.get(
                "output_tokens"
            )
        ),
        cache_read_tokens=_integer(
            usage.get(
                "cached_input_tokens"
            )
        ),
        cache_write_tokens=_integer(
            usage.get(
                "cache_write_input_tokens"
            )
        ),
        reasoning_output_tokens=_integer(
            usage.get(
                "reasoning_output_tokens"
            )
        ),
        reported_cost_usd=None,
        cost_source=None,
        raw_metadata=raw_metadata,
    )
