from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    TypedDict,
)

from langgraph.graph import (
    END,
    START,
    StateGraph,
)


GRAPH_VERSION = 1


class ResearchGraphContractError(
    RuntimeError
):
    pass


class ResearchGraphState(
    TypedDict,
    total=False,
):
    topic: str
    run_id: str
    mission_id: str

    iteration: int
    max_iterations: int

    research_result: dict[str, Any]

    structural_integrity: str
    structural_errors: list[str]

    semantic_records: list[
        dict[str, Any]
    ]

    verification_summary: dict[
        str,
        Any,
    ]

    verified_claim_ids: list[str]
    rejected_claim_ids: list[str]

    critic_result: dict[str, Any]

    retry_required: bool
    retry_claim_ids: list[str]
    retry_topic: str

    acceptance_gate: dict[
        str,
        Any,
    ]

    synthesis_input: dict[
        str,
        Any,
    ]

    final_result: str
    status: str


NodeResult = dict[str, Any]

NodeCallable = Callable[
    [ResearchGraphState],
    Awaitable[NodeResult]
    | NodeResult,
]


@dataclass(
    frozen=True,
    slots=True,
)
class ResearchGraphNodes:
    research: NodeCallable
    evidence_integrity: NodeCallable
    semantic_verification: NodeCallable
    runtime_verification: NodeCallable
    critic: NodeCallable
    acceptance_gate: NodeCallable
    synthesis_input: NodeCallable
    synthesis: NodeCallable


def _fail(
    message: str,
) -> None:
    raise ResearchGraphContractError(
        message
    )


def _require_string(
    value: Any,
    label: str,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        _fail(
            f"{label} must be "
            "a non-empty string"
        )

    return value.strip()


def _require_counter(
    value: Any,
    label: str,
    *,
    minimum: int,
) -> int:

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < minimum
    ):
        _fail(
            f"{label} must be an "
            f"integer >= {minimum}"
        )

    return value


def build_initial_state(
    *,
    topic: str,
    run_id: str,
    mission_id: str | None = None,
    max_iterations: int = 2,
) -> ResearchGraphState:

    topic = _require_string(
        topic,
        "topic",
    )

    run_id = _require_string(
        run_id,
        "run_id",
    )

    if mission_id is None:
        mission_id = run_id

    mission_id = _require_string(
        mission_id,
        "mission_id",
    )

    max_iterations = (
        _require_counter(
            max_iterations,
            "max_iterations",
            minimum=1,
        )
    )

    return {
        "topic":
            topic,

        "run_id":
            run_id,

        "mission_id":
            mission_id,

        "iteration":
            0,

        "max_iterations":
            max_iterations,

        "structural_errors":
            [],

        "semantic_records":
            [],

        "verified_claim_ids":
            [],

        "rejected_claim_ids":
            [],

        "retry_required":
            False,

        "retry_claim_ids":
            [],

        "status":
            "starting",
    }


def route_after_integrity(
    state: ResearchGraphState,
) -> str:

    value = state.get(
        "structural_integrity"
    )

    if value == "pass":
        return "semantic_verification"

    if value == "fail":
        return "critic"

    _fail(
        "structural_integrity must "
        "be 'pass' or 'fail'"
    )


def route_after_critic(
    state: ResearchGraphState,
) -> str:

    retry_required = state.get(
        "retry_required"
    )

    if not isinstance(
        retry_required,
        bool,
    ):
        _fail(
            "retry_required must "
            "be boolean"
        )

    iteration = _require_counter(
        state.get(
            "iteration"
        ),
        "iteration",
        minimum=0,
    )

    max_iterations = (
        _require_counter(
            state.get(
                "max_iterations"
            ),
            "max_iterations",
            minimum=1,
        )
    )

    if (
        retry_required
        and iteration
        < max_iterations
    ):

        retry_topic = (
            _require_string(
                state.get(
                    "retry_topic"
                ),
                "retry_topic",
            )
        )

        claim_ids = state.get(
            "retry_claim_ids"
        )

        if (
            not isinstance(
                claim_ids,
                list,
            )
            or not claim_ids
            or any(
                not isinstance(
                    item,
                    str,
                )
                or not item.strip()
                for item
                in claim_ids
            )
        ):
            _fail(
                "retry_claim_ids must "
                "contain at least one "
                "non-empty claim ID"
            )

        if not retry_topic:
            _fail(
                "retry_topic is required"
            )

        return "research"

    return "acceptance_gate"


def route_after_acceptance(
    state: ResearchGraphState,
) -> str:

    gate = state.get(
        "acceptance_gate"
    )

    if not isinstance(
        gate,
        dict,
    ):
        _fail(
            "acceptance_gate must "
            "be an object"
        )

    decision = gate.get(
        "decision"
    )

    if decision in {
        "accepted",
        "partial",
    }:

        accepted = gate.get(
            "accepted_claim_ids"
        )

        if (
            not isinstance(
                accepted,
                list,
            )
            or not accepted
        ):
            _fail(
                "accepted or partial gate "
                "must authorize at least "
                "one claim"
            )

        return "synthesis_input"

    if decision == "rejected":
        return "end"

    _fail(
        "invalid AcceptanceGate decision"
    )


def build_graph(
    *,
    nodes: ResearchGraphNodes,
    checkpointer: Any | None = None,
):

    builder = StateGraph(
        ResearchGraphState
    )

    builder.add_node(
        "research",
        nodes.research,
    )

    builder.add_node(
        "evidence_integrity",
        nodes.evidence_integrity,
    )

    builder.add_node(
        "semantic_verification",
        nodes.semantic_verification,
    )

    builder.add_node(
        "runtime_verification",
        nodes.runtime_verification,
    )

    builder.add_node(
        "critic",
        nodes.critic,
    )

    builder.add_node(
        "acceptance_gate",
        nodes.acceptance_gate,
    )

    builder.add_node(
        "synthesis_input",
        nodes.synthesis_input,
    )

    builder.add_node(
        "synthesis",
        nodes.synthesis,
    )


    builder.add_edge(
        START,
        "research",
    )

    builder.add_edge(
        "research",
        "evidence_integrity",
    )

    builder.add_conditional_edges(
        "evidence_integrity",
        route_after_integrity,
        {
            "semantic_verification":
                "semantic_verification",

            "critic":
                "critic",
        },
    )

    builder.add_edge(
        "semantic_verification",
        "runtime_verification",
    )

    builder.add_edge(
        "runtime_verification",
        "critic",
    )

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "research":
                "research",

            "acceptance_gate":
                "acceptance_gate",
        },
    )

    builder.add_conditional_edges(
        "acceptance_gate",
        route_after_acceptance,
        {
            "synthesis_input":
                "synthesis_input",

            "end":
                END,
        },
    )

    builder.add_edge(
        "synthesis_input",
        "synthesis",
    )

    builder.add_edge(
        "synthesis",
        END,
    )


    if checkpointer is None:
        return builder.compile()

    return builder.compile(
        checkpointer=checkpointer
    )
