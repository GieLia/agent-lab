import asyncio
import json
from pathlib import Path


CLAUDE_BIN = "/home/agent/.local/bin/claude"


async def run_claude(
    prompt: str,
    cwd: Path,
    timeout: int = 1200,
    max_turns: int = 8,
) -> str:

    process = await asyncio.create_subprocess_exec(
        CLAUDE_BIN,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
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

    try:
        data = json.loads(stdout_text)

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

        return str(
            data.get(
                "result",
                stdout_text,
            )
        )

    return stdout_text
