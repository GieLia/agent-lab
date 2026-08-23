import os

os.environ.setdefault(
    "LANGGRAPH_STRICT_MSGPACK",
    "true",
)

import asyncio
import uuid
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from db import get_db_uri


class TestState(TypedDict):
    value: int


async def increment(state: TestState) -> dict:
    return {
        "value": state["value"] + 1
    }


async def main():
    db_uri = get_db_uri()

    print("Connecting to PostgreSQL...")

    async with AsyncPostgresSaver.from_conn_string(
        db_uri
    ) as checkpointer:

        print("Running checkpointer setup...")

        await checkpointer.setup()

        print("CHECKPOINTER_SETUP_OK")

        builder = StateGraph(TestState)

        builder.add_node(
            "increment",
            increment,
        )

        builder.add_edge(
            START,
            "increment",
        )

        builder.add_edge(
            "increment",
            END,
        )

        graph = builder.compile(
            checkpointer=checkpointer
        )

        thread_id = (
            "checkpoint-test-"
            + str(uuid.uuid4())
        )

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        print(
            "THREAD_ID:",
            thread_id,
        )

        result = await graph.ainvoke(
            {
                "value": 41
            },
            config=config,
        )

        print(
            "GRAPH_RESULT:",
            result,
        )

        snapshot = await graph.aget_state(
            config
        )

        print(
            "CHECKPOINT_STATE:",
            snapshot.values,
        )

        if result["value"] != 42:
            raise RuntimeError(
                "Unexpected graph result"
            )

        if snapshot.values.get("value") != 42:
            raise RuntimeError(
                "Checkpoint state mismatch"
            )

        print("POSTGRES_CHECKPOINT_OK")


if __name__ == "__main__":
    asyncio.run(main())
