import asyncio
import tempfile

from pathlib import Path

from langgraph.checkpoint.sqlite.aio import (
    AsyncSqliteSaver,
)

from app.graph_v4 import (
    ResearchGraphNodes,
    build_graph,
    build_initial_state,
)


async def main_async():

    calls = {
        "research": 0,
        "integrity": 0,
        "semantic": 0,
        "runtime": 0,
        "critic": 0,
        "gate": 0,
        "synthesis_input": 0,
        "synthesis": 0,
    }


    async def research(
        state,
    ):

        calls[
            "research"
        ] += 1

        return {
            "iteration":
                state.get(
                    "iteration",
                    0,
                )
                + 1,

            "research_result": {
                "worker_id":
                    "checkpoint-worker",
                "claims": [
                    {
                        "claim_id":
                            "claim-1",
                    }
                ],
            },

            "status":
                "researched",
        }


    async def integrity(
        state,
    ):

        calls[
            "integrity"
        ] += 1

        assert (
            state[
                "research_result"
            ][
                "worker_id"
            ]
            == "checkpoint-worker"
        )

        return {
            "structural_integrity":
                "pass",

            "structural_errors":
                [],

            "status":
                "integrity_checked",
        }


    async def semantic(
        state,
    ):

        calls[
            "semantic"
        ] += 1

        return {
            "semantic_records": [
                {
                    "claim_id":
                        "claim-1",

                    "evidence_id":
                        "ev-1",

                    "evaluation": {
                        "entailment":
                            "full",
                    },
                }
            ],

            "status":
                "semantically_evaluated",
        }


    async def runtime_verification(
        state,
    ):

        calls[
            "runtime"
        ] += 1

        assert (
            state[
                "semantic_records"
            ][0][
                "claim_id"
            ]
            == "claim-1"
        )

        return {
            "verification_summary": {
                "worker_id":
                    "checkpoint-worker",

                "verified_claim_ids": [
                    "claim-1",
                ],
            },

            "verified_claim_ids": [
                "claim-1",
            ],

            "rejected_claim_ids":
                [],

            "status":
                "runtime_verified",
        }


    async def critic(
        state,
    ):

        calls[
            "critic"
        ] += 1

        assert (
            state[
                "verified_claim_ids"
            ]
            == [
                "claim-1",
            ]
        )

        if (
            calls[
                "critic"
            ]
            == 1
        ):
            raise RuntimeError(
                "synthetic checkpoint interruption"
            )

        return {
            "critic_result": {
                "finding":
                    "resume succeeded",
            },

            "retry_required":
                False,

            "retry_claim_ids":
                [],

            "status":
                "critic_complete",
        }


    async def gate(
        state,
    ):

        calls[
            "gate"
        ] += 1

        return {
            "acceptance_gate": {
                "decision":
                    "accepted",

                "accepted_claim_ids": [
                    "claim-1",
                ],

                "rejected_claim_ids":
                    [],
            },

            "status":
                "accepted",
        }


    async def synthesis_input(
        state,
    ):

        calls[
            "synthesis_input"
        ] += 1

        assert (
            state[
                "acceptance_gate"
            ][
                "accepted_claim_ids"
            ]
            == [
                "claim-1",
            ]
        )

        return {
            "synthesis_input": {
                "accepted_claim_ids": [
                    "claim-1",
                ],
            },

            "status":
                "synthesis_ready",
        }


    async def synthesis(
        state,
    ):

        calls[
            "synthesis"
        ] += 1

        return {
            "final_result":
                "Checkpoint resume result.",

            "status":
                "finished",
        }


    with tempfile.TemporaryDirectory() as tmp:

        db_path = (
            Path(tmp)
            / "research-graph-v1.sqlite"
        )

        async with (
            AsyncSqliteSaver
            .from_conn_string(
                str(
                    db_path
                )
            )
        ) as checkpointer:

            graph = build_graph(
                nodes=ResearchGraphNodes(
                    research=
                        research,

                    evidence_integrity=
                        integrity,

                    semantic_verification=
                        semantic,

                    runtime_verification=
                        runtime_verification,

                    critic=
                        critic,

                    acceptance_gate=
                        gate,

                    synthesis_input=
                        synthesis_input,

                    synthesis=
                        synthesis,
                ),

                checkpointer=
                    checkpointer,
            )

            config = {
                "configurable": {
                    "thread_id":
                        "e5-checkpoint-test",
                }
            }

            initial_state = (
                build_initial_state(
                    topic=
                        "Checkpoint test",

                    run_id=
                        "run-checkpoint-test",

                    mission_id=
                        "mission-checkpoint-test",

                    max_iterations=2,
                )
            )


            try:

                await graph.ainvoke(
                    initial_state,
                    config=config,
                )

            except RuntimeError as exc:

                assert (
                    "synthetic checkpoint interruption"
                    in str(exc)
                )

            else:
                raise AssertionError(
                    "synthetic interruption "
                    "did not occur"
                )


            snapshot = await graph.aget_state(
                config
            )

            assert snapshot.values

            assert (
                snapshot.values[
                    "iteration"
                ]
                == 1
            )

            assert (
                snapshot.values[
                    "research_result"
                ][
                    "worker_id"
                ]
                == "checkpoint-worker"
            )

            assert (
                snapshot.values[
                    "structural_integrity"
                ]
                == "pass"
            )

            assert (
                snapshot.values[
                    "verified_claim_ids"
                ]
                == [
                    "claim-1",
                ]
            )

            assert (
                snapshot.values[
                    "status"
                ]
                == "runtime_verified"
            )

            assert (
                "critic"
                in snapshot.next
            )

            print(
                "GRAPH_V4_CHECKPOINT_AFTER_FAILURE_OK"
            )


            resumed = await graph.ainvoke(
                None,
                config=config,
            )


            assert (
                resumed[
                    "final_result"
                ]
                == "Checkpoint resume result."
            )

            assert (
                resumed[
                    "status"
                ]
                == "finished"
            )


            final_snapshot = (
                await graph.aget_state(
                    config
                )
            )

            assert (
                not final_snapshot.next
            )

            assert (
                final_snapshot.values[
                    "final_result"
                ]
                == "Checkpoint resume result."
            )


            assert (
                calls[
                    "research"
                ]
                == 1
            )

            assert (
                calls[
                    "integrity"
                ]
                == 1
            )

            assert (
                calls[
                    "semantic"
                ]
                == 1
            )

            assert (
                calls[
                    "runtime"
                ]
                == 1
            )

            assert (
                calls[
                    "critic"
                ]
                == 2
            )

            assert (
                calls[
                    "gate"
                ]
                == 1
            )

            assert (
                calls[
                    "synthesis_input"
                ]
                == 1
            )

            assert (
                calls[
                    "synthesis"
                ]
                == 1
            )

            assert db_path.exists()

            print(
                "GRAPH_V4_RESUME_FROM_FAILED_NODE_OK"
            )

            print(
                "GRAPH_V4_PREVIOUS_NODES_NOT_REEXECUTED_OK"
            )

            print(
                "GRAPH_V4_SQLITE_CHECKPOINTER_OK"
            )


    print()
    print(
        "RESEARCH_GRAPH_V1_CHECKPOINT_CONTRACT_OK"
    )


def main():

    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()
