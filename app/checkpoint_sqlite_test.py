import asyncio
import uuid
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


DB_FILE = Path(
    "/opt/agent-lab/state/checkpoints.sqlite"
)


class TestState(TypedDict):
    value: int


async def increment(
    state: TestState,
) -> dict:
    return {
        "value": state["value"] + 1
    }


async def main():
    print(
        "CHECKPOINT_DB:",
        DB_FILE,
    )

    async with AsyncSqliteSaver.from_conn_string(
        str(DB_FILE)
    ) as checkpointer:

        builder = StateGraph(
            TestState
        )

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
            "sqlite-test-"
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

        if (
            snapshot.values.get("value")
            != 42
        ):
            raise RuntimeError(
                "Checkpoint state mismatch"
            )

        print(
            "SQLITE_CHECKPOINT_OK"
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
