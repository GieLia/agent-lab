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
