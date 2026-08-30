import asyncio
import json
import os
import uuid

from pathlib import Path


CLAUDE_BIN = "/home/agent/.local/bin/claude"

CLAUDE_SECONDARY_SOCKET = (
    "/run/claude-b-worker/worker.sock"
)

CLAUDE_SECONDARY_MAX_REQUEST_BYTES = int(
    os.getenv(
        "CLAUDE_SECONDARY_MAX_REQUEST_BYTES",
        str(2 * 1024 * 1024),
    )
)

CLAUDE_SECONDARY_MAX_RESPONSE_BYTES = int(
    os.getenv(
        "CLAUDE_SECONDARY_MAX_RESPONSE_BYTES",
        str(2 * 1024 * 1024),
    )
)


def _resolve_account(
    account: str | None,
) -> str:

    if account is None:
        account = os.getenv(
            "CLAUDE_ACCOUNT",
            "primary",
        )

    account = (
        account
        .strip()
        .lower()
    )

    aliases = {
        "a": "primary",
        "primary": "primary",
        "b": "secondary",
        "secondary": "secondary",
    }

    resolved = aliases.get(
        account
    )

    if resolved is None:
        raise ValueError(
            "Unknown Claude account: "
            f"{account}"
        )

    return resolved


def _resolve_tool_profile(
    tool_profile: str | None,
) -> str:

    if tool_profile is None:
        tool_profile = os.getenv(
            "CLAUDE_TOOL_PROFILE",
            "default",
        )

    tool_profile = (
        tool_profile
        .strip()
        .lower()
    )

    if tool_profile not in {
        "default",
        "reasoning",
    }:
        raise ValueError(
            "Unknown CLAUDE_TOOL_PROFILE: "
            f"{tool_profile}"
        )

    return tool_profile


async def _run_primary(
    *,
    prompt: str,
    cwd: Path,
    timeout: int,
    max_turns: int,
    tool_profile: str,
    system_prompt: str | None,
    json_schema: dict | None,
) -> str:

    command = [
        CLAUDE_BIN,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
    ]

    if tool_profile == "reasoning":
        command.extend(
            [
                "--tools",
                "",
                "--permission-mode",
                "dontAsk",
                "--strict-mcp-config",
                "--safe-mode",
            ]
        )

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

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )

    except asyncio.TimeoutError:
        process.kill()
        await process.wait()

        raise RuntimeError(
            f"Claude timeout after {timeout}s"
        )

    stdout_text = stdout.decode(
        "utf-8",
        errors="replace",
    ).strip()

    stderr_text = stderr.decode(
        "utf-8",
        errors="replace",
    ).strip()

    if process.returncode != 0:
        raise RuntimeError(
            "\n"
            f"Claude failed with exit code "
            f"{process.returncode}\n"
            "\n"
            "----- STDOUT -----\n"
            f"{stdout_text or '<empty>'}\n"
            "\n"
            "----- STDERR -----\n"
            f"{stderr_text or '<empty>'}\n"
        )

    if not stdout_text:
        raise RuntimeError(
            "Claude returned empty stdout"
        )

    try:
        data = json.loads(
            stdout_text
        )

    except json.JSONDecodeError:
        return stdout_text

    if isinstance(data, dict):

        if data.get("is_error"):
            raise RuntimeError(
                "Claude returned an error:\n"
                + json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                )
            )

        if json_schema is not None:
            structured = data.get(
                "structured_output"
            )

            if structured is None:
                raise RuntimeError(
                    "Claude returned no "
                    "structured_output:\n"
                    + json.dumps(
                        data,
                        indent=2,
                        ensure_ascii=False,
                    )
                )

            return json.dumps(
                structured,
                ensure_ascii=False,
            )

        result = data.get(
            "result"
        )

        if not result:
            raise RuntimeError(
                "Claude returned an empty result"
            )

        return str(result)

    return stdout_text


async def _run_secondary(
    *,
    prompt: str,
    timeout: int,
    max_turns: int,
    tool_profile: str,
    system_prompt: str | None,
    json_schema: dict | None,
) -> str:

    if tool_profile != "reasoning":
        raise ValueError(
            "Secondary Claude account currently "
            "supports only "
            "tool_profile='reasoning'"
        )

    request_id = str(
        uuid.uuid4()
    )

    request = {
        "request_id":
            request_id,

        "prompt":
            prompt,

        "timeout":
            timeout,

        "max_turns":
            max_turns,

        "tool_profile":
            tool_profile,

        "system_prompt":
            system_prompt,

        "json_schema":
            json_schema,
    }

    encoded_request = (
        json.dumps(
            request,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    if (
        len(encoded_request)
        > CLAUDE_SECONDARY_MAX_REQUEST_BYTES
    ):
        raise RuntimeError(
            "Secondary Claude request "
            f"{request_id} exceeds "
            f"{CLAUDE_SECONDARY_MAX_REQUEST_BYTES} "
            "bytes"
        )

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(
                CLAUDE_SECONDARY_SOCKET,
                limit=(
                    CLAUDE_SECONDARY_MAX_RESPONSE_BYTES
                    + 1
                ),
            ),
            timeout=10,
        )

    except Exception as exc:
        raise RuntimeError(
            "Unable to connect to secondary "
            "Claude worker at "
            f"{CLAUDE_SECONDARY_SOCKET}: "
            f"{exc}"
        ) from exc

    try:
        writer.write(
            encoded_request
        )

        await writer.drain()

        try:
            line = await asyncio.wait_for(
                reader.readline(),
                timeout=timeout + 30,
            )

        except ValueError as exc:
            raise RuntimeError(
                "Secondary Claude response "
                f"{request_id} exceeded "
                f"{CLAUDE_SECONDARY_MAX_RESPONSE_BYTES} "
                "bytes"
            ) from exc

        if not line:
            raise RuntimeError(
                "Secondary Claude worker "
                f"returned no response "
                f"(request_id={request_id})"
            )

        if (
            len(line)
            > CLAUDE_SECONDARY_MAX_RESPONSE_BYTES
        ):
            raise RuntimeError(
                "Secondary Claude response "
                f"{request_id} exceeds "
                f"{CLAUDE_SECONDARY_MAX_RESPONSE_BYTES} "
                "bytes"
            )

        try:
            response = json.loads(
                line.decode(
                    "utf-8",
                    errors="replace",
                )
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Secondary Claude worker "
                "returned invalid JSON "
                f"(request_id={request_id})"
            ) from exc

        response_request_id = (
            response.get(
                "request_id"
            )
        )

        # Backward compatible with protocol v1
        # during rolling deployment.
        if (
            response_request_id is not None
            and response_request_id
            != request_id
        ):
            raise RuntimeError(
                "Secondary Claude worker "
                "request_id mismatch: "
                f"sent={request_id} "
                f"received={response_request_id}"
            )

        if not response.get("ok"):
            raise RuntimeError(
                "Secondary Claude worker "
                "failed "
                f"(request_id={request_id}):\n"
                + str(
                    response.get(
                        "error",
                        "Unknown error",
                    )
                )
            )

        result = response.get(
            "result"
        )

        if not result:
            raise RuntimeError(
                "Secondary Claude worker "
                "returned an empty result "
                f"(request_id={request_id})"
            )

        return str(result)

    finally:
        writer.close()

        try:
            await writer.wait_closed()
        except Exception:
            pass


async def run_claude(
    prompt: str,
    cwd: Path,
    timeout: int = 1200,
    max_turns: int = 8,
    tool_profile: str | None = None,
    system_prompt: str | None = None,
    json_schema: dict | None = None,
    account: str | None = None,
) -> str:

    resolved_account = _resolve_account(
        account
    )

    resolved_profile = (
        _resolve_tool_profile(
            tool_profile
        )
    )

    if resolved_account == "primary":
        return await _run_primary(
            prompt=prompt,
            cwd=cwd,
            timeout=timeout,
            max_turns=max_turns,
            tool_profile=
                resolved_profile,
            system_prompt=
                system_prompt,
            json_schema=
                json_schema,
        )

    return await _run_secondary(
        prompt=prompt,
        timeout=timeout,
        max_turns=max_turns,
        tool_profile=
            resolved_profile,
        system_prompt=
            system_prompt,
        json_schema=
            json_schema,
    )
