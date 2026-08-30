import asyncio
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path


SERVER_PATH = Path(
    "infra/claude-b-worker/server.py"
)


def load_server():

    spec = (
        importlib.util.spec_from_file_location(
            "claude_b_worker_server",
            SERVER_PATH,
        )
    )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


async def large_request_test(
    module,
    root,
):
    socket_path = (
        root / "large.sock"
    )

    original_execute = (
        module.execute
    )

    async def fake_execute(
        request,
        request_id,
        disconnect_task=None,
    ):
        assert (
            len(
                request[
                    "prompt"
                ].encode("utf-8")
            )
            > 100_000
        )

        return "LARGE_OK"

    module.execute = fake_execute

    try:
        server = (
            await asyncio.start_unix_server(
                module.handle_client,
                path=str(socket_path),
                limit=module.STREAM_LIMIT,
            )
        )

        async with server:

            reader, writer = (
                await asyncio.open_unix_connection(
                    str(socket_path),
                    limit=(
                        module.MAX_RESPONSE_BYTES
                        + 1
                    ),
                )
            )

            request_id = (
                "offline-large"
            )

            request = {
                "request_id":
                    request_id,

                "prompt":
                    "X" * 150_000,

                "timeout":
                    10,

                "max_turns":
                    1,

                "tool_profile":
                    "reasoning",
            }

            encoded = (
                json.dumps(request)
                + "\n"
            ).encode("utf-8")

            assert (
                len(encoded)
                > 65_536
            )

            assert (
                len(encoded)
                < module.MAX_REQUEST_BYTES
            )

            writer.write(
                encoded
            )

            await writer.drain()

            response = json.loads(
                (
                    await reader.readline()
                ).decode("utf-8")
            )

            writer.close()
            await writer.wait_closed()

            assert (
                response["ok"]
                is True
            )

            assert (
                response[
                    "request_id"
                ]
                == request_id
            )

            assert (
                response["result"]
                == "LARGE_OK"
            )

    finally:
        module.execute = (
            original_execute
        )

    print(
        "LARGE_REQUEST_OFFLINE_OK"
    )


async def disconnect_test(
    module,
    root,
):
    socket_path = (
        root / "disconnect.sock"
    )

    fake_bin = (
        root / "fake-claude"
    )

    pid_file = (
        root / "fake.pid"
    )

    fake_bin.write_text(
        """#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

Path(
    os.environ["FAKE_PID_FILE"]
).write_text(
    str(os.getpid())
)

time.sleep(30)

print(
    json.dumps(
        {
            "is_error": False,
            "result": "SHOULD_NOT_FINISH",
        }
    )
)
""",
        encoding="utf-8",
    )

    fake_bin.chmod(
        fake_bin.stat().st_mode
        | stat.S_IXUSR
    )

    old_bin = module.CLAUDE_BIN
    old_cwd = module.CLAUDE_CWD

    module.CLAUDE_BIN = str(
        fake_bin
    )

    module.CLAUDE_CWD = str(
        root
    )

    os.environ[
        "FAKE_PID_FILE"
    ] = str(pid_file)

    try:
        server = (
            await asyncio.start_unix_server(
                module.handle_client,
                path=str(socket_path),
                limit=module.STREAM_LIMIT,
            )
        )

        async with server:

            _, writer = (
                await asyncio.open_unix_connection(
                    str(socket_path)
                )
            )

            request = {
                "request_id":
                    "offline-disconnect",

                "prompt":
                    "sleep",

                "timeout":
                    60,

                "max_turns":
                    1,

                "tool_profile":
                    "reasoning",
            }

            writer.write(
                (
                    json.dumps(request)
                    + "\n"
                ).encode("utf-8")
            )

            await writer.drain()

            for _ in range(50):

                if pid_file.exists():
                    break

                await asyncio.sleep(
                    0.05
                )

            assert pid_file.exists()

            pid = int(
                pid_file.read_text().strip()
            )

            writer.close()
            await writer.wait_closed()

            await asyncio.sleep(
                1.0
            )

            try:
                os.kill(
                    pid,
                    0,
                )

            except ProcessLookupError:
                pass

            else:
                raise AssertionError(
                    "orphan fake Claude "
                    "process still alive: "
                    f"{pid}"
                )

    finally:
        module.CLAUDE_BIN = (
            old_bin
        )

        module.CLAUDE_CWD = (
            old_cwd
        )

        os.environ.pop(
            "FAKE_PID_FILE",
            None,
        )

    print(
        "CLIENT_DISCONNECT_CANCEL_OK"
    )


async def main():

    module = load_server()

    with tempfile.TemporaryDirectory(
        prefix=(
            "claude-b-worker-test-"
        )
    ) as temp:

        root = Path(temp)

        await large_request_test(
            module,
            root,
        )

        await disconnect_test(
            module,
            root,
        )

    print(
        "CLAUDE_B_WORKER_OFFLINE_OK"
    )


asyncio.run(main())
