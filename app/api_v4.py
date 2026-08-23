import asyncio
import json
import os
import signal
import sys
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel, Field


APP_ROOT = Path("/opt/agent-lab/app")
RUN_ROOT = Path("/opt/agent-lab/runs")
GRAPH_FILE = APP_ROOT / "graph_v3.py"
DASHBOARD_FILE = APP_ROOT / "static" / "index.html"

PYTHON_BIN = Path(sys.executable)


app = FastAPI(
    title="AI Agent Lab",
    version="4.0",
    description=(
        "Control API for Claude + Codex + "
        "LangGraph research workflows."
    ),
)


processes: dict[str, asyncio.subprocess.Process] = {}


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class RunRequest(BaseModel):
    topic: str = Field(
        min_length=3,
        max_length=10000,
    )

    max_iterations: int = Field(
        default=2,
        ge=1,
        le=10,
    )

    quality_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
    )


def get_run_dir(
    run_id: str,
) -> Path:
    return RUN_ROOT / run_id


def read_json(
    path: Path,
) -> dict[str, Any] | None:

    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return None


def get_process_state(
    run_id: str,
) -> str:

    process = processes.get(
        run_id
    )

    if process is None:
        return "not_managed"

    if process.returncode is None:
        return "running"

    if process.returncode == 0:
        return "completed"

    return "failed"


def build_run_info(
    run_id: str,
) -> dict[str, Any]:

    run_dir = get_run_dir(
        run_id
    )

    if not run_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Run not found",
        )

    metadata = read_json(
        run_dir / "metadata.json"
    ) or {}

    status = read_json(
        run_dir / "status.json"
    ) or {}

    final_file = (
        run_dir / "final.md"
    )

    return {
        "run_id": run_id,
        "topic": (
            status.get("topic")
            or metadata.get("topic")
        ),
        "phase": status.get(
            "phase",
            "unknown",
        ),
        "iteration": status.get(
            "iteration"
        ),
        "max_iterations": (
            status.get(
                "max_iterations"
            )
        ),
        "quality_score": (
            status.get(
                "quality_score"
            )
        ),
        "quality_threshold": (
            status.get(
                "quality_threshold"
            )
        ),
        "process_state":
            get_process_state(
                run_id
            ),
        "result_available":
            final_file.exists(),
        "directory":
            str(run_dir),
    }


async def wait_for_process(
    run_id: str,
    process: asyncio.subprocess.Process,
    log_handle,
) -> None:

    try:
        await process.wait()

    finally:
        try:
            log_handle.flush()
            log_handle.close()

        except Exception:
            pass


@app.get("/")
async def root():
    return FileResponse(
        DASHBOARD_FILE
    )

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "time": now(),
        "python": str(
            PYTHON_BIN
        ),
        "graph": str(
            GRAPH_FILE
        ),
        "graph_exists":
            GRAPH_FILE.exists(),
    }


@app.post("/runs")
async def start_run(
    request: RunRequest,
):

    run_id = str(
        uuid.uuid4()
    )

    run_dir = get_run_dir(
        run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = (
        run_dir / "process.log"
    )

    log_handle = open(
        log_file,
        "ab",
        buffering=0,
    )

    env = os.environ.copy()

    env.update(
        {
            "RUN_ID":
                run_id,
            "TOPIC":
                request.topic,
            "MAX_ITERATIONS":
                str(
                    request.max_iterations
                ),
            "QUALITY_THRESHOLD":
                str(
                    request.quality_threshold
                ),
            "PYTHONUNBUFFERED":
                "1",
        }
    )

    try:
        process = (
            await asyncio.create_subprocess_exec(
                str(PYTHON_BIN),
                "-X",
                "faulthandler",
                str(GRAPH_FILE),
                cwd=str(APP_ROOT),
                env=env,
                stdout=log_handle,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
        )

    except Exception:
        log_handle.close()
        raise

    processes[run_id] = process

    asyncio.create_task(
        wait_for_process(
            run_id,
            process,
            log_handle,
        )
    )

    return {
        "run_id": run_id,
        "pid": process.pid,
        "status": "started",
        "topic": request.topic,
        "max_iterations":
            request.max_iterations,
        "quality_threshold":
            request.quality_threshold,
    }


@app.get("/runs")
async def list_runs():

    result = []

    if not RUN_ROOT.exists():
        return result

    directories = sorted(
        (
            path
            for path in RUN_ROOT.iterdir()
            if path.is_dir()
        ),
        key=lambda path:
            path.stat().st_mtime,
        reverse=True,
    )

    for directory in directories[:100]:

        try:
            result.append(
                build_run_info(
                    directory.name
                )
            )

        except Exception:
            continue

    return result


@app.get("/runs/{run_id}")
async def get_run(
    run_id: str,
):
    return build_run_info(
        run_id
    )


@app.get(
    "/runs/{run_id}/result",
    response_class=PlainTextResponse,
)
async def get_result(
    run_id: str,
):

    result_file = (
        get_run_dir(run_id)
        / "final.md"
    )

    if not result_file.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Final result "
                "not available"
            ),
        )

    return result_file.read_text(
        encoding="utf-8"
    )


@app.get(
    "/runs/{run_id}/log",
    response_class=PlainTextResponse,
)
async def get_log(
    run_id: str,
):

    log_file = (
        get_run_dir(run_id)
        / "process.log"
    )

    if not log_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Log not available",
        )

    return log_file.read_text(
        encoding="utf-8",
        errors="replace",
    )


@app.post("/runs/{run_id}/stop")
async def stop_run(
    run_id: str,
):

    process = processes.get(
        run_id
    )

    if process is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Run is not controlled "
                "by this API process"
            ),
        )

    if process.returncode is not None:
        return {
            "run_id": run_id,
            "status":
                "already_finished",
            "returncode":
                process.returncode,
        }

    try:
        os.killpg(
            process.pid,
            signal.SIGTERM,
        )

    except ProcessLookupError:
        pass

    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=10,
        )

    except asyncio.TimeoutError:

        try:
            os.killpg(
                process.pid,
                signal.SIGKILL,
            )

        except ProcessLookupError:
            pass

        await process.wait()

    return {
        "run_id": run_id,
        "status": "stopped",
        "returncode":
            process.returncode,
    }
