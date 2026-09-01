from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class WorkerExecutionResult:
    text: str

    provider: str
    account: str | None
    model: str | None

    request_id: str | None
    session_id: str | None

    status: str
    duration_ms: int | None

    input_tokens: int | None
    output_tokens: int | None

    cache_read_tokens: int | None
    cache_write_tokens: int | None
    reasoning_output_tokens: int | None

    reported_cost_usd: Decimal | None
    cost_source: str | None

    raw_metadata: dict[str, Any] = field(
        default_factory=dict
    )
