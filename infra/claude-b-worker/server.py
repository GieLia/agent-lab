import asyncio
import json
import os
import signal
import time
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path


SOCKET_PATH = Path(
    os.getenv(
        "CLAUDE_B_SOCKET_PATH",
        "/run/claude-b-worker/worker.sock",
    )
)

CLAUDE_BIN = os.getenv(
    "CLAUDE_B_BIN",
    "/home/claude-b/.local/bin/claude",
)

CLAUDE_CWD = os.getenv(
    "CLAUDE_B_CWD",
    "/home/claude-b",
)

MAX_REQUEST_BYTES = int(
    os.getenv(
        "CLAUDE_B_MAX_REQUEST_BYTES",
        str(2 * 1024 * 1024),
    )
)

MAX_RESPONSE_BYTES = int(
    os.getenv(
        "CLAUDE_B_MAX_RESPONSE_BYTES",
        str(2 * 1024 * 1024),
    )
)

STREAM_LIMIT = MAX_REQUEST_BYTES + 1

TERMINATE_GRACE_SECONDS = 5.0
ERROR_TEXT_LIMIT = 6000


class ClientDisconnected(RuntimeError):
    pass


def _now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def _log(
    event,
    request_id,
    **fields,
):
    print(
        json.dumps(
            {
                "time": _now(),
                "event": event,
                "request_id": request_id,
                **fields,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        flush=True,
    )


def _truncate(
    text,
    limit=ERROR_TEXT_LIMIT,
):
    if len(text) <= limit:
        return text

    return (
        text[:limit]
        + "\n...<truncated>"
    )


def _request_id(value):
    if (
        isinstance(value, str)
        and 1 <= len(value) <= 128
    ):
        return value

    return str(uuid.uuid4())


def _validated(request):
    if not isinstance(request, dict):
        raise ValueError(
            "request must be a JSON object"
        )

    prompt = request.get("prompt")

    if not isinstance(prompt, str):
        raise ValueError(
            "prompt must be a string"
        )

    timeout = int(
        request.get(
            "timeout",
            1200,
        )
    )

    if not 1 <= timeout <= 7200:
        raise ValueError(
            "timeout must be 1..7200 seconds"
        )

    max_turns = int(
        request.get(
            "max_turns",
            8,
        )
    )

    if not 1 <= max_turns <= 100:
        raise ValueError(
            "max_turns must be 1..100"
        )

    tool_profile = request.get(
        "tool_profile",
        "reasoning",
    )

    if tool_profile != "reasoning":
        raise ValueError(
            "claude-b supports only "
            "tool_profile=reasoning"
        )

    system_prompt = request.get(
        "system_prompt"
    )

    if (
        system_prompt is not None
        and not isinstance(
            system_prompt,
            str,
        )
    ):
        raise ValueError(
            "system_prompt must be "
            "string or null"
        )

    json_schema = request.get(
        "json_schema"
    )

    if (
        json_schema is not None
        and not isinstance(
            json_schema,
            dict,
        )
    ):
        raise ValueError(
            "json_schema must be "
            "object or null"
        )

    return (
        prompt,
        timeout,
        max_turns,
        system_prompt,
        json_schema,
    )


async def _stop_process(
    process,
    request_id,
    reason,
):
    if process.returncode is not None:
        return

    _log(
        "process_stop_requested",
        request_id,
        pid=process.pid,
        reason=reason,
    )

    try:
        os.killpg(
            process.pid,
            signal.SIGTERM,
        )
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=TERMINATE_GRACE_SECONDS,
        )
        return

    except asyncio.TimeoutError:
        pass

    _log(
        "process_kill_requested",
        request_id,
        pid=process.pid,
        reason=reason,
    )

    with suppress(
        ProcessLookupError
    ):
        os.killpg(
            process.pid,
            signal.SIGKILL,
        )

    await process.wait()


async def execute(
    request,
    request_id,
    disconnect_task=None,
    include_telemetry=False,
):
    (
        prompt,
        timeout,
        max_turns,
        system_prompt,
        json_schema,
    ) = _validated(request)

    command = [
        CLAUDE_BIN,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        "--strict-mcp-config",
        "--safe-mode",
    ]

    if system_prompt:
        command.extend(
            [
                "--system-prompt",
                system_prompt,
            ]
        )

    if json_schema is not None:
        command.extend(
            [
                "--json-schema",
                json.dumps(
                    json_schema,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ]
        )

    started = time.monotonic()

    process = (
        await asyncio.create_subprocess_exec(
            *command,
            cwd=CLAUDE_CWD,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    )

    _log(
        "process_started",
        request_id,
        pid=process.pid,
        timeout=timeout,
        max_turns=max_turns,
        structured=(
            json_schema is not None
        ),
    )

    communicate_task = (
        asyncio.create_task(
            process.communicate()
        )
    )

    wait_set = {
        communicate_task
    }

    if disconnect_task is not None:
        wait_set.add(
            disconnect_task
        )

    done, _ = await asyncio.wait(
        wait_set,
        timeout=timeout,
        return_when=(
            asyncio.FIRST_COMPLETED
        ),
    )

    if communicate_task in done:
        stdout, stderr = (
            communicate_task.result()
        )

    elif (
        disconnect_task is not None
        and disconnect_task in done
    ):
        await _stop_process(
            process,
            request_id,
            "client_disconnected",
        )

        with suppress(
            asyncio.TimeoutError
        ):
            await asyncio.wait_for(
                communicate_task,
                timeout=2,
            )

        if not communicate_task.done():
            communicate_task.cancel()

        raise ClientDisconnected(
            "client disconnected"
        )

    else:
        await _stop_process(
            process,
            request_id,
            "timeout",
        )

        with suppress(
            asyncio.TimeoutError
        ):
            await asyncio.wait_for(
                communicate_task,
                timeout=2,
            )

        if not communicate_task.done():
            communicate_task.cancel()

        raise RuntimeError(
            f"Claude B timeout after "
            f"{timeout}s"
        )

    duration_ms = int(
        (
            time.monotonic()
            - started
        )
        * 1000
    )

    stdout_text = stdout.decode(
        "utf-8",
        errors="replace",
    ).strip()

    stderr_text = stderr.decode(
        "utf-8",
        errors="replace",
    ).strip()

    _log(
        "process_finished",
        request_id,
        pid=process.pid,
        return_code=process.returncode,
        duration_ms=duration_ms,
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
    )

    if process.returncode != 0:
        raise RuntimeError(
            "Claude B failed with exit code "
            f"{process.returncode}\n\n"
            "----- STDOUT -----\n"
            f"{_truncate(stdout_text) or '<empty>'}"
            "\n\n----- STDERR -----\n"
            f"{_truncate(stderr_text) or '<empty>'}"
        )

    if not stdout_text:
        raise RuntimeError(
            "Claude B returned empty stdout"
        )

    try:
        data = json.loads(
            stdout_text
        )

    except json.JSONDecodeError:
        if include_telemetry:
            return {
                "result":
                    stdout_text,
                "telemetry": {
                    "worker_duration_ms":
                        duration_ms,
                },
            }

        return stdout_text

    if isinstance(data, dict):

        if data.get("is_error"):
            raise RuntimeError(
                "Claude B returned an error:\n"
                + _truncate(
                    json.dumps(
                        data,
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            )

        if json_schema is not None:

            structured = data.get(
                "structured_output"
            )

            if structured is None:
                raise RuntimeError(
                    "Claude B returned no "
                    "structured_output:\n"
                    + _truncate(
                        json.dumps(
                            data,
                            indent=2,
                            ensure_ascii=False,
                        )
                    )
                )

            result_text = json.dumps(
                structured,
                ensure_ascii=False,
            )

            if include_telemetry:
                telemetry = {
                    key: value
                    for key, value
                    in data.items()
                    if key not in {
                        "result",
                        "structured_output",
                    }
                }

                telemetry[
                    "worker_duration_ms"
                ] = duration_ms

                return {
                    "result":
                        result_text,
                    "telemetry":
                        telemetry,
                }

            return result_text

        result = data.get(
            "result"
        )

        if not result:
            raise RuntimeError(
                "Claude B returned an "
                "empty result"
            )

        result_text = str(
            result
        )

        if include_telemetry:
            telemetry = {
                key: value
                for key, value
                in data.items()
                if key not in {
                    "result",
                    "structured_output",
                }
            }

            telemetry[
                "worker_duration_ms"
            ] = duration_ms

            return {
                "result":
                    result_text,
                "telemetry":
                    telemetry,
            }

        return result_text

    if include_telemetry:
        return {
            "result":
                stdout_text,
            "telemetry": {
                "worker_duration_ms":
                    duration_ms,
            },
        }

    return stdout_text


async def _close_writer(writer):

    writer.close()

    with suppress(
        ConnectionResetError,
        BrokenPipeError,
    ):
        await writer.wait_closed()


async def handle_client(
    reader,
    writer,
):
    request_id = str(
        uuid.uuid4()
    )

    try:
        response = None

        try:
            line = await reader.readline()

            if not line:
                return

            request_bytes = len(line)

            if (
                request_bytes
                > MAX_REQUEST_BYTES
            ):
                raise ValueError(
                    "request exceeds "
                    f"{MAX_REQUEST_BYTES} bytes"
                )

            request = json.loads(
                line.decode("utf-8")
            )

            if isinstance(
                request,
                dict,
            ):
                request_id = (
                    _request_id(
                        request.get(
                            "request_id"
                        )
                    )
                )

            _log(
                "request_received",
                request_id,
                request_bytes=(
                    request_bytes
                ),
            )

            disconnect_task = (
                asyncio.create_task(
                    reader.read()
                )
            )

            try:
                execution = await execute(
                    request,
                    request_id,
                    disconnect_task=(
                        disconnect_task
                    ),
                    include_telemetry=True,
                )

            finally:
                if (
                    not disconnect_task.done()
                ):
                    disconnect_task.cancel()

                    with suppress(
                        asyncio.CancelledError
                    ):
                        await disconnect_task

            response = {
                "ok": True,
                "protocol_version": 3,
                "request_id":
                    request_id,
                "result":
                    execution["result"],
                "telemetry":
                    execution.get(
                        "telemetry",
                        {},
                    ),
            }

        except ClientDisconnected:

            _log(
                "client_disconnected",
                request_id,
            )

            return

        except Exception as exc:

            _log(
                "request_failed",
                request_id,
                error_type=(
                    type(exc).__name__
                ),
                error=_truncate(
                    str(exc),
                    limit=1000,
                ),
            )

            response = {
                "ok": False,
                "protocol_version": 3,
                "request_id": request_id,
                "error": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

        encoded = (
            json.dumps(
                response,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")

        if (
            len(encoded)
            > MAX_RESPONSE_BYTES
        ):
            response = {
                "ok": False,
                "protocol_version": 3,
                "request_id": request_id,
                "error": (
                    "response exceeds "
                    f"{MAX_RESPONSE_BYTES} bytes"
                ),
            }

            encoded = (
                json.dumps(
                    response,
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")

        try:
            writer.write(
                encoded
            )

            await writer.drain()

            _log(
                "response_sent",
                request_id,
                response_bytes=(
                    len(encoded)
                ),
                ok=response["ok"],
            )

        except (
            ConnectionResetError,
            BrokenPipeError,
        ):
            _log(
                "response_connection_lost",
                request_id,
                response_bytes=(
                    len(encoded)
                ),
            )

    finally:
        await _close_writer(
            writer
        )


async def main():

    SOCKET_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()

    server = (
        await asyncio.start_unix_server(
            handle_client,
            path=str(SOCKET_PATH),
            limit=STREAM_LIMIT,
        )
    )

    os.chmod(
        SOCKET_PATH,
        0o660,
    )

    print(
        "claude-b worker listening: "
        f"{SOCKET_PATH} "
        "protocol=3 "
        "max_request_bytes="
        f"{MAX_REQUEST_BYTES} "
        "max_response_bytes="
        f"{MAX_RESPONSE_BYTES}",
        flush=True,
    )

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
