import hashlib
import sys
import uuid

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

import psycopg

from psycopg.types.json import Jsonb

from app.db import get_db_uri
from app.workers.result import (
    WorkerExecutionResult,
)


class MeasurementWriter:
    def __init__(
        self,
        *,
        required: bool = False,
        db_uri: str | None = None,
    ):
        self.required = required
        self.db_uri = db_uri

    def _connect(self):
        uri = (
            self.db_uri
            if self.db_uri is not None
            else get_db_uri()
        )

        return psycopg.connect(
            uri
        )

    def _failure(
        self,
        action: str,
        exc: Exception,
    ):
        print(
            "MEASUREMENT_WARNING "
            f"action={action} "
            f"error_type="
            f"{type(exc).__name__}",
            file=sys.stderr,
        )

        if self.required:
            raise RuntimeError(
                "Measurement operation failed: "
                f"{action}"
            ) from exc

    def ensure_case(
        self,
        *,
        case_id: str,
        case_version: int,
        case_sha256: str | None = None,
        title: str | None = None,
        objective: str | None = None,
        raw_case: dict[str, Any] | None = None,
    ) -> bool:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO
                            measurement.evaluation_case (
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
                            case_id,
                            case_version,
                            case_sha256,
                            title,
                            objective,
                            (
                                Jsonb(raw_case)
                                if raw_case
                                is not None
                                else None
                            ),
                        ),
                    )

            return True

        except Exception as exc:
            self._failure(
                "ensure_case",
                exc,
            )

            return False

    def start_run(
        self,
        *,
        case_id: str,
        case_version: int,
        run_type: str,
        git_sha: str | None,
        orchestration: str | None = None,
        config_hash: str | None = None,
        raw_metadata: dict[str, Any] | None = None,
        run_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        if run_id is None:
            run_id = uuid.uuid4()

        started_at = datetime.now(
            timezone.utc
        )

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO
                            measurement.evaluation_run (
                                run_id,
                                case_id,
                                case_version,
                                run_type,
                                git_sha,
                                config_hash,
                                orchestration,
                                started_at,
                                status,
                                raw_metadata
                            )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            run_id,
                            case_id,
                            case_version,
                            run_type,
                            git_sha,
                            config_hash,
                            orchestration,
                            started_at,
                            "running",
                            (
                                Jsonb(
                                    raw_metadata
                                )
                                if raw_metadata
                                is not None
                                else None
                            ),
                        ),
                    )

            return run_id

        except Exception as exc:
            self._failure(
                "start_run",
                exc,
            )

            return None

    def record_worker_invocation(
        self,
        *,
        run_id: uuid.UUID,
        worker_id: str,
        role: str,
        result: WorkerExecutionResult,
        tool_profile: str | None = None,
        tools_exposed_count: int | None = None,
        skill_ids: list[str] | None = None,
        invocation_id: str | None = None,
    ) -> str | None:
        if invocation_id is None:
            invocation_id = str(
                uuid.uuid4()
            )

        finished_at = datetime.now(
            timezone.utc
        )

        if result.duration_ms is not None:
            started_at = (
                finished_at
                - timedelta(
                    milliseconds=
                        result.duration_ms
                )
            )
        else:
            started_at = finished_at

        text_bytes = result.text.encode(
            "utf-8"
        )

        raw_result = {
            "text_sha256":
                hashlib.sha256(
                    text_bytes
                ).hexdigest(),

            "text_bytes":
                len(text_bytes),

            "raw_metadata":
                result.raw_metadata,
        }

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO
                            measurement.worker_invocation (
                                invocation_id,
                                run_id,
                                worker_id,
                                role,
                                provider,
                                account,
                                model,
                                request_id,
                                session_id,
                                skill_ids,
                                tool_profile,
                                tools_exposed_count,
                                started_at,
                                finished_at,
                                duration_ms,
                                status,
                                input_tokens,
                                output_tokens,
                                cache_read_tokens,
                                cache_write_tokens,
                                reasoning_output_tokens,
                                reported_cost_usd,
                                cost_source,
                                raw_result
                            )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        (
                            invocation_id,
                            run_id,
                            worker_id,
                            role,
                            result.provider,
                            result.account,
                            result.model,
                            result.request_id,
                            result.session_id,
                            (
                                skill_ids
                                if skill_ids
                                is not None
                                else []
                            ),
                            tool_profile,
                            tools_exposed_count,
                            started_at,
                            finished_at,
                            result.duration_ms,
                            result.status,
                            result.input_tokens,
                            result.output_tokens,
                            result.cache_read_tokens,
                            result.cache_write_tokens,
                            result.reasoning_output_tokens,
                            result.reported_cost_usd,
                            result.cost_source,
                            Jsonb(
                                raw_result
                            ),
                        ),
                    )

            return invocation_id

        except Exception as exc:
            self._failure(
                "record_worker_invocation",
                exc,
            )

            return None

    def record_worker_transport_failure(
        self,
        *,
        run_id: uuid.UUID,
        worker_id: str,
        role: str,
        provider: str,
        account: str | None,
        error: Exception,
        tool_profile: str | None = None,
        tools_exposed_count: int | None = None,
        duration_ms: int | None = None,
        invocation_id: str | None = None,
    ) -> str | None:

        if invocation_id is None:
            invocation_id = str(
                uuid.uuid4()
            )

        finished_at = datetime.now(
            timezone.utc
        )

        if duration_ms is not None:
            started_at = (
                finished_at
                - timedelta(
                    milliseconds=
                        duration_ms
                )
            )
        else:
            started_at = finished_at

        error_text = str(
            error
        )

        error_bytes = error_text.encode(
            "utf-8"
        )

        raw_result = {
            "failure_stage":
                "transport",

            "error_type":
                type(
                    error
                ).__name__,

            "error_sha256":
                hashlib.sha256(
                    error_bytes
                ).hexdigest(),

            "error_bytes":
                len(
                    error_bytes
                ),
        }

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        INSERT INTO
                            measurement.worker_invocation (
                                invocation_id,
                                run_id,
                                worker_id,
                                role,
                                provider,
                                account,
                                skill_ids,
                                tool_profile,
                                tools_exposed_count,
                                started_at,
                                finished_at,
                                duration_ms,
                                status,
                                raw_result
                            )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        (
                            invocation_id,
                            run_id,
                            worker_id,
                            role,
                            provider,
                            account,
                            [],
                            tool_profile,
                            tools_exposed_count,
                            started_at,
                            finished_at,
                            duration_ms,
                            "failed",
                            Jsonb(
                                raw_result
                            ),
                        ),
                    )

            return invocation_id

        except Exception as exc:
            self._failure(
                "record_worker_transport_failure",
                exc,
            )

            return None


    def record_tool_invocation(
        self,
        *,
        run_id: uuid.UUID,
        capability: str,
        tool_name: str,
        tool_kind: str,
        status: str,
        tool_profile: str | None = None,
        worker_invocation_id: str | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
        human_approval_required: bool = False,
        human_approval_granted: bool | None = None,
        metadata: dict[str, Any] | None = None,
        tool_invocation_id: str | None = None,
    ) -> str | None:

        if tool_invocation_id is None:
            tool_invocation_id = str(
                uuid.uuid4()
            )

        if (
            duration_ms is not None
            and duration_ms < 0
        ):
            raise ValueError(
                "duration_ms must be nonnegative"
            )

        if (
            human_approval_granted
            is not None
            and not human_approval_required
        ):
            raise ValueError(
                "human_approval_granted requires "
                "human_approval_required=True"
            )

        finished_at = datetime.now(
            timezone.utc
        )

        if duration_ms is not None:
            started_at = (
                finished_at
                - timedelta(
                    milliseconds=
                        duration_ms
                )
            )

        else:
            started_at = finished_at

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO
                            measurement.tool_invocation (
                                tool_invocation_id,
                                run_id,
                                worker_invocation_id,
                                capability,
                                tool_name,
                                tool_kind,
                                tool_profile,
                                mcp_server,
                                mcp_server_version,
                                started_at,
                                finished_at,
                                duration_ms,
                                status,
                                error_code,
                                human_approval_required,
                                human_approval_granted,
                                metadata
                            )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s
                        )
                        """,
                        (
                            tool_invocation_id,
                            run_id,
                            worker_invocation_id,
                            capability,
                            tool_name,
                            tool_kind,
                            tool_profile,
                            None,
                            None,
                            started_at,
                            finished_at,
                            duration_ms,
                            status,
                            error_code,
                            human_approval_required,
                            human_approval_granted,
                            (
                                Jsonb(metadata)
                                if metadata
                                is not None
                                else None
                            ),
                        ),
                    )

            return tool_invocation_id

        except Exception as exc:
            self._failure(
                "record_tool_invocation",
                exc,
            )

            return None

    def summarize_worker_invocations(
        self,
        *,
        run_id: uuid.UUID,
    ) -> dict[str, Any] | None:

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT
                            COUNT(*),

                            COALESCE(
                                SUM(input_tokens),
                                0
                            ),

                            COALESCE(
                                SUM(output_tokens),
                                0
                            ),

                            COALESCE(
                                SUM(cache_read_tokens),
                                0
                            ),

                            COALESCE(
                                SUM(cache_write_tokens),
                                0
                            ),

                            COALESCE(
                                SUM(
                                    reasoning_output_tokens
                                ),
                                0
                            ),

                            COALESCE(
                                SUM(reported_cost_usd),
                                0
                            ),

                            COUNT(*) FILTER (
                                WHERE
                                    raw_result
                                    ->> 'failure_stage'
                                    = 'transport'
                            ),

                            COUNT(*) FILTER (
                                WHERE
                                    reported_cost_usd
                                    IS NULL
                                    AND (
                                        raw_result
                                        ->> 'failure_stage'
                                        IS DISTINCT FROM
                                        'transport'
                                    )
                            )
                        FROM
                            measurement.worker_invocation
                        WHERE
                            run_id = %s
                        """,
                        (
                            run_id,
                        ),
                    )

                    row = cursor.fetchone()

            if row is None:
                raise RuntimeError(
                    "worker usage aggregation "
                    "returned no row"
                )

            transport_failures = int(
                row[7]
            )

            missing_costs = int(
                row[8]
            )

            return {
                "worker_invocations":
                    int(
                        row[0]
                    ),

                "input_tokens":
                    int(
                        row[1]
                    ),

                "output_tokens":
                    int(
                        row[2]
                    ),

                "cache_read_tokens":
                    int(
                        row[3]
                    ),

                "cache_write_tokens":
                    int(
                        row[4]
                    ),

                "reasoning_output_tokens":
                    int(
                        row[5]
                    ),

                "reported_cost_usd":
                    str(
                        row[6]
                    ),

                "transport_failure_invocations":
                    transport_failures,

                "missing_reported_cost_invocations":
                    missing_costs,

                "cost_complete": (
                    transport_failures == 0
                    and missing_costs == 0
                ),
            }

        except Exception as exc:
            self._failure(
                "summarize_worker_invocations",
                exc,
            )

            return None


    def finish_run(
        self,
        *,
        run_id: uuid.UUID,
        status: str,
    ) -> bool:
        finished_at = datetime.now(
            timezone.utc
        )

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE
                            measurement.evaluation_run
                        SET
                            status = %s,
                            finished_at = %s
                        WHERE
                            run_id = %s
                        """,
                        (
                            status,
                            finished_at,
                            run_id,
                        ),
                    )

            return True

        except Exception as exc:
            self._failure(
                "finish_run",
                exc,
            )

            return False
