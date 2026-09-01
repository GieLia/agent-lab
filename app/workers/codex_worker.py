import asyncio
from pathlib import Path

CODEX_BIN = "/home/agent/.local/bin/codex"


async def run_codex(
    prompt: str,
    cwd: Path,
    timeout: int = 900,
) -> str:

    process = await asyncio.create_subprocess_exec(
        CODEX_BIN,
        "exec",
        "--skip-git-repo-check",
        prompt,
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
        raise RuntimeError("Codex timeout")

    stdout_text = stdout.decode(
        "utf-8",
        errors="replace",
    )

    stderr_text = stderr.decode(
        "utf-8",
        errors="replace",
    )

    if process.returncode != 0:
        raise RuntimeError(
            f"Codex failed ({process.returncode}):\n"
            f"{stderr_text}"
        )

    return stdout_text.strip()


async def run_codex_detailed(
    prompt: str,
    cwd: Path,
    timeout: int = 900,
    *,
    account: str | None = "primary",
    model: str | None = None,
    profile: str | None = None,
    sandbox: str | None = None,
):
    import json
    import os
    import tempfile
    import time

    from .telemetry import (
        parse_codex_events,
    )

    fd, output_path = (
        tempfile.mkstemp(
            prefix="agent-lab-codex-",
            suffix=".txt",
        )
    )

    os.close(fd)

    command = [
        CODEX_BIN,
        "exec",
        "--skip-git-repo-check",
        "--json",
        "--output-last-message",
        output_path,
    ]

    if model:
        command.extend(
            [
                "--model",
                model,
            ]
        )

    if profile:
        command.extend(
            [
                "--profile",
                profile,
            ]
        )

    if sandbox:
        command.extend(
            [
                "--sandbox",
                sandbox,
            ]
        )

    command.append(
        prompt
    )

    started = time.monotonic()

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
            f"Codex timeout after {timeout}s"
        )

    finally:
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
    )

    stderr_text = stderr.decode(
        "utf-8",
        errors="replace",
    )

    try:
        if process.returncode != 0:
            raise RuntimeError(
                "Codex failed "
                f"({process.returncode}):\n"
                f"{stderr_text}"
            )

        events = []

        for line in (
            stdout_text
            .splitlines()
        ):
            if not line.strip():
                continue

            try:
                event = json.loads(
                    line
                )

            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "Codex --json returned "
                    "invalid JSONL"
                ) from exc

            if isinstance(
                event,
                dict,
            ):
                events.append(
                    event
                )

        with open(
            output_path,
            "r",
            encoding="utf-8",
        ) as handle:
            result_text = (
                handle.read()
                .strip()
            )

        if not result_text:
            raise RuntimeError(
                "Codex returned an "
                "empty final message"
            )

        return parse_codex_events(
            events=events,
            text=result_text,
            account=account,
            requested_model=model,
            duration_ms=duration_ms,
        )

    finally:
        try:
            os.unlink(
                output_path
            )
        except FileNotFoundError:
            pass
