from __future__ import annotations

import copy

from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
)


from app.research.acceptance import (
    build_acceptance_gate,
    build_rejected_worker_gate,
)

from app.research.protocol import (
    ResearchProtocolError,
    validate_worker_result,
)

from app.research.semantic_evaluator import (
    evaluate_semantic_evidence,
    validate_semantic_evaluation,
)

from app.research.tool_loop import (
    ResearchLoopResult,
    run_research_tool_loop,
)

from app.research.verification import (
    build_verification_summary,
)

from app.research.retry_merge import (
    RetryMergeError,
    merge_retry_worker_result,
)

from app.research.graph_measurement import (
    GraphMeasurementBridge,
)


class GraphNodeAdapterError(
    RuntimeError
):
    pass


ResearchRunner = Callable[
    ...,
    Awaitable[ResearchLoopResult],
]

SemanticRunner = Callable[
    ...,
    Awaitable[
        tuple[
            dict[str, Any],
            Any,
        ]
    ],
]


@dataclass(
    frozen=True,
    slots=True,
)
class GraphNodeDependencies:

    cwd: Path

    research_worker_id: str = (
        "research-graph-v1-researcher"
    )

    research_account: str | None = None

    semantic_account: str = "primary"

    semantic_timeout: int = 180

    measurement_bridge: GraphMeasurementBridge | None = None

    research_runner: ResearchRunner = (
        run_research_tool_loop
    )

    semantic_runner: SemanticRunner = (
        evaluate_semantic_evidence
    )


def _fail(
    message: str,
) -> None:

    raise GraphNodeAdapterError(
        message
    )


def _require_state_string(
    state: dict[str, Any],
    key: str,
) -> str:

    value = state.get(
        key
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        _fail(
            f"{key} must be a "
            "non-empty string"
        )

    return value.strip()


def _accumulate_research_metrics(
    previous: Any,
    result: ResearchLoopResult,
) -> dict[str, int]:

    current = {
        "steps":
            result.steps,

        "model_calls":
            result.model_calls,

        "search_calls":
            result.search_calls,

        "fetch_calls":
            result.fetch_calls,

        "sources_retrieved":
            result.sources_retrieved,
    }

    if previous is None:
        return current

    if not isinstance(
        previous,
        dict,
    ):
        _fail(
            "research_metrics must "
            "be an object"
        )

    merged = {}

    for key, value in current.items():

        old = previous.get(
            key,
            0,
        )

        if (
            isinstance(
                old,
                bool,
            )
            or not isinstance(
                old,
                int,
            )
            or old < 0
        ):
            _fail(
                "invalid accumulated "
                f"research metric: {key}"
            )

        merged[
            key
        ] = old + value

    return merged


def build_research_node(
    dependencies: GraphNodeDependencies,
):

    async def research_node(
        state: dict[str, Any],
    ) -> dict[str, Any]:

        raw_iteration = state.get(
            "iteration",
            0,
        )

        if (
            isinstance(
                raw_iteration,
                bool,
            )
            or not isinstance(
                raw_iteration,
                int,
            )
            or raw_iteration < 0
        ):
            _fail(
                "iteration must be "
                "an integer >= 0"
            )


        raw_max_iterations = state.get(
            "max_iterations",
            1,
        )

        if (
            isinstance(
                raw_max_iterations,
                bool,
            )
            or not isinstance(
                raw_max_iterations,
                int,
            )
            or raw_max_iterations < 1
        ):
            _fail(
                "max_iterations must be "
                "an integer >= 1"
            )


        is_retry = (
            raw_iteration > 0
        )


        if is_retry:

            if (
                state.get(
                    "retry_required"
                )
                is not True
            ):
                _fail(
                    "research retry requires "
                    "retry_required=true"
                )

            if (
                raw_iteration
                >= raw_max_iterations
            ):
                _fail(
                    "research retry budget "
                    "is exhausted"
                )

            retry_claim_ids = state.get(
                "retry_claim_ids"
            )

            if (
                not isinstance(
                    retry_claim_ids,
                    list,
                )
                or not retry_claim_ids
                or any(
                    not isinstance(
                        item,
                        str,
                    )
                    or not item.strip()
                    for item
                    in retry_claim_ids
                )
            ):
                _fail(
                    "retry_claim_ids must "
                    "contain factual targets"
                )

            topic = (
                _require_state_string(
                    state,
                    "retry_topic",
                )
            )

            base_result = state.get(
                "research_result"
            )

            if not isinstance(
                base_result,
                dict,
            ):
                _fail(
                    "targeted retry requires "
                    "existing research_result"
                )

            try:
                validate_worker_result(
                    base_result,
                    expected_worker_id=
                        dependencies
                        .research_worker_id,
                )

            except ResearchProtocolError as exc:
                raise GraphNodeAdapterError(
                    "existing WorkerResult "
                    "failed retry validation"
                ) from exc

        else:

            topic = (
                _require_state_string(
                    state,
                    "topic",
                )
            )

            retry_claim_ids = []


        bridge = (
            dependencies
            .measurement_bridge
        )

        result = await (
            dependencies
            .research_runner(
                topic,
                cwd=
                    dependencies.cwd,
                worker_id=
                    dependencies
                    .research_worker_id,
                account=
                    dependencies
                    .research_account,

                model_result_observer=(
                    bridge
                    .record_research_model_result
                    if bridge is not None
                    else None
                ),

                measurement_writer=
                    bridge,

                run_id=(
                    bridge.run_id
                    if bridge is not None
                    else None
                ),

                worker_invocation_id=
                    None,
            )
        )


        if not isinstance(
            result,
            ResearchLoopResult,
        ):
            _fail(
                "research runner returned "
                "unexpected result type"
            )


        incoming_result = (
            copy.deepcopy(
                result.worker_result
            )
        )


        try:
            validate_worker_result(
                incoming_result,
                expected_worker_id=
                    dependencies
                    .research_worker_id,
            )

        except ResearchProtocolError as exc:
            raise GraphNodeAdapterError(
                "research runner produced "
                "invalid canonical WorkerResult"
            ) from exc


        next_iteration = (
            raw_iteration
            + 1
        )


        if is_retry:

            try:
                worker_result = (
                    merge_retry_worker_result(
                        base_result=
                            base_result,

                        retry_result=
                            incoming_result,

                        retry_claim_ids=
                            retry_claim_ids,

                        iteration=
                            next_iteration,
                    )
                )

            except RetryMergeError as exc:
                raise GraphNodeAdapterError(
                    "targeted retry merge "
                    "was rejected"
                ) from exc

        else:

            worker_result = (
                incoming_result
            )


        metrics = (
            _accumulate_research_metrics(
                state.get(
                    "research_metrics"
                ),
                result,
            )
        )


        node_result = {
            "iteration":
                next_iteration,

            "research_result":
                worker_result,

            "research_metrics":
                metrics,

            # Every research iteration invalidates
            # all downstream derived authority.
            "structural_integrity":
                "",

            "structural_errors":
                [],

            "semantic_records":
                [],

            "verification_summary":
                {},

            "verified_claim_ids":
                [],

            "rejected_claim_ids":
                [],

            "critic_result":
                {},

            "acceptance_gate":
                {},

            "synthesis_input":
                {},

            "retry_required":
                False,

            "retry_claim_ids":
                [],

            "retry_topic":
                "",

            "status":
                (
                    "research_retried"
                    if is_retry
                    else "researched"
                ),
        }

        if bridge is not None:
            node_result[
                "measurement_summary"
            ] = bridge.snapshot()

        return node_result

    return research_node


async def evidence_integrity_node(
    state: dict[str, Any],
) -> dict[str, Any]:

    result = state.get(
        "research_result"
    )

    if not isinstance(
        result,
        dict,
    ):
        return {
            "structural_integrity":
                "fail",

            "structural_errors": [
                (
                    "research_result is "
                    "missing or not an object"
                )
            ],

            "semantic_records":
                [],

            "verification_summary":
                {},

            "verified_claim_ids":
                [],

            "rejected_claim_ids":
                [],

            "status":
                "integrity_failed",
        }

    try:
        validate_worker_result(
            result
        )

    except ResearchProtocolError as exc:

        return {
            "structural_integrity":
                "fail",

            "structural_errors": [
                str(exc)
            ],

            "semantic_records":
                [],

            "verification_summary":
                {},

            "verified_claim_ids":
                [],

            "rejected_claim_ids":
                [],

            "status":
                "integrity_failed",
        }

    return {
        "structural_integrity":
            "pass",

        "structural_errors":
            [],

        "status":
            "integrity_passed",
    }


def build_semantic_verification_node(
    dependencies: GraphNodeDependencies,
):

    async def semantic_verification_node(
        state: dict[str, Any],
    ) -> dict[str, Any]:

        if (
            state.get(
                "structural_integrity"
            )
            != "pass"
        ):
            _fail(
                "semantic verification "
                "requires structural "
                "integrity pass"
            )

        worker_result = state.get(
            "research_result"
        )

        if not isinstance(
            worker_result,
            dict,
        ):
            _fail(
                "research_result must "
                "be an object"
            )

        try:
            validate_worker_result(
                worker_result
            )

        except ResearchProtocolError as exc:
            raise GraphNodeAdapterError(
                "research_result failed "
                "canonical validation"
            ) from exc

        claims = {
            item["claim_id"]:
                item
            for item
            in worker_result[
                "claims"
            ]
        }

        sources = {
            item["source_id"]:
                item
            for item
            in worker_result[
                "sources"
            ]
        }

        records = []

        for evidence in worker_result[
            "evidence"
        ]:

            claim_id = evidence[
                "claim_id"
            ]

            claim = claims[
                claim_id
            ]

            if (
                claim[
                    "claim_type"
                ]
                != "fact"
            ):
                continue

            source_id = evidence[
                "source_id"
            ]

            source = sources[
                source_id
            ]

            raw = await (
                dependencies
                .semantic_runner(
                    claim=
                        copy.deepcopy(
                            claim
                        ),

                    evidence=
                        copy.deepcopy(
                            evidence
                        ),

                    source=
                        copy.deepcopy(
                            source
                        ),

                    cwd=
                        dependencies.cwd,

                    account=
                        dependencies
                        .semantic_account,

                    timeout=
                        dependencies
                        .semantic_timeout,
                )
            )

            if (
                not isinstance(
                    raw,
                    tuple,
                )
                or len(raw) != 2
            ):
                _fail(
                    "semantic runner returned "
                    "unexpected result shape"
                )

            if (
                dependencies
                .measurement_bridge
                is not None
            ):
                (
                    dependencies
                    .measurement_bridge
                    .record_semantic_model_result(
                        raw[1]
                    )
                )

            evaluation = (
                validate_semantic_evaluation(
                    raw[0]
                )
            )

            records.append(
                {
                    "claim_id":
                        claim_id,

                    "evidence_id":
                        evidence[
                            "evidence_id"
                        ],

                    "evaluation":
                        evaluation,
                }
            )

        node_result = {
            "semantic_records":
                records,

            "status":
                "semantically_evaluated",
        }

        if (
            dependencies
            .measurement_bridge
            is not None
        ):
            node_result[
                "measurement_summary"
            ] = (
                dependencies
                .measurement_bridge
                .snapshot()
            )

        return node_result

    return semantic_verification_node


async def runtime_verification_node(
    state: dict[str, Any],
) -> dict[str, Any]:

    if (
        state.get(
            "structural_integrity"
        )
        != "pass"
    ):
        _fail(
            "runtime verification "
            "requires structural "
            "integrity pass"
        )

    worker_result = state.get(
        "research_result"
    )

    semantic_records = state.get(
        "semantic_records"
    )

    if not isinstance(
        worker_result,
        dict,
    ):
        _fail(
            "research_result must "
            "be an object"
        )

    if not isinstance(
        semantic_records,
        list,
    ):
        _fail(
            "semantic_records must "
            "be a list"
        )

    summary = (
        build_verification_summary(
            worker_result,
            semantic_records,
        )
    )

    all_claim_ids = [
        item[
            "claim_id"
        ]
        for item
        in worker_result[
            "claims"
        ]
    ]

    verified = list(
        summary[
            "verified_claim_ids"
        ]
    )

    verified_set = set(
        verified
    )

    rejected = [
        claim_id
        for claim_id
        in all_claim_ids
        if claim_id
        not in verified_set
    ]

    return {
        "verification_summary":
            summary,

        "verified_claim_ids":
            verified,

        "rejected_claim_ids":
            rejected,

        "status":
            "runtime_verified",
    }


def build_acceptance_gate_node(
    dependencies: GraphNodeDependencies,
):

    async def acceptance_gate_node(
        state: dict[str, Any],
    ) -> dict[str, Any]:

        mission_id = (
            _require_state_string(
                state,
                "mission_id",
            )
        )

        integrity = state.get(
            "structural_integrity"
        )

        if integrity == "fail":

            errors = state.get(
                "structural_errors",
                [],
            )

            rationale = (
                "WorkerResult rejected by "
                "runtime structural integrity "
                "boundary."
            )

            if isinstance(
                errors,
                list,
            ) and errors:

                rationale += (
                    " "
                    + "; ".join(
                        str(item)
                        for item
                        in errors
                    )
                )

            gate = (
                build_rejected_worker_gate(
                    mission_id=
                        mission_id,

                    worker_id=
                        dependencies
                        .research_worker_id,

                    rationale=
                        rationale,
                )
            )

        elif integrity == "pass":

            worker_result = state.get(
                "research_result"
            )

            verification = state.get(
                "verification_summary"
            )

            if not isinstance(
                worker_result,
                dict,
            ):
                _fail(
                    "research_result must "
                    "be an object"
                )

            if not isinstance(
                verification,
                dict,
            ):
                _fail(
                    "verification_summary must "
                    "be an object"
                )

            gate = build_acceptance_gate(
                mission_id=
                    mission_id,

                worker_result=
                    worker_result,

                verification_summary=
                    verification,
            )

        else:
            _fail(
                "AcceptanceGate requires "
                "explicit structural "
                "integrity result"
            )

        return {
            "acceptance_gate":
                gate,

            "status": (
                "accepted"
                if gate[
                    "decision"
                ]
                == "accepted"
                else (
                    "partially_accepted"
                    if gate[
                        "decision"
                    ]
                    == "partial"
                    else "rejected"
                )
            ),
        }

    return acceptance_gate_node


CriticRunner = Callable[
    ...,
    Awaitable[
        dict[str, Any]
    ],
]


def build_critic_node(
    *,
    critic_runner: CriticRunner,
):

    from app.research.critic_contract import (
        validate_critic_result,
    )

    async def critic_node(
        state: dict[str, Any],
    ) -> dict[str, Any]:

        integrity = state.get(
            "structural_integrity"
        )

        if integrity not in {
            "pass",
            "fail",
        }:
            _fail(
                "critic requires explicit "
                "structural integrity result"
            )


        rejected_claim_ids = state.get(
            "rejected_claim_ids",
            [],
        )

        if not isinstance(
            rejected_claim_ids,
            list,
        ):
            _fail(
                "rejected_claim_ids "
                "must be a list"
            )


        if integrity == "pass":

            worker_result = state.get(
                "research_result"
            )

            if not isinstance(
                worker_result,
                dict,
            ):
                _fail(
                    "critic requires "
                    "research_result"
                )

            factual_claim_ids = {
                item[
                    "claim_id"
                ]
                for item
                in worker_result.get(
                    "claims",
                    [],
                )
                if (
                    item.get(
                        "claim_type"
                    )
                    == "fact"
                )
            }

            candidate_retry_claim_ids = [
                claim_id
                for claim_id
                in rejected_claim_ids
                if (
                    claim_id
                    in factual_claim_ids
                )
            ]

        else:

            # Structural failure is terminal at
            # claim-level retry in E5-D2.
            candidate_retry_claim_ids = []


        raw = await critic_runner(
            topic=state.get(
                "topic"
            ),

            research_result=
                copy.deepcopy(
                    state.get(
                        "research_result"
                    )
                ),

            verification_summary=
                copy.deepcopy(
                    state.get(
                        "verification_summary"
                    )
                ),

            structural_integrity=
                integrity,

            structural_errors=
                copy.deepcopy(
                    state.get(
                        "structural_errors",
                        [],
                    )
                ),

            rejected_claim_ids=
                list(
                    rejected_claim_ids
                ),

            candidate_retry_claim_ids=
                list(
                    candidate_retry_claim_ids
                ),
        )


        result = validate_critic_result(
            raw,

            candidate_retry_claim_ids=
                candidate_retry_claim_ids,

            structural_integrity=
                integrity,
        )


        return {
            "critic_result":
                result,

            "retry_required":
                result[
                    "retry_required"
                ],

            "retry_claim_ids":
                list(
                    result[
                        "retry_claim_ids"
                    ]
                ),

            "retry_topic":
                (
                    result[
                        "retry_topic"
                    ]
                    or ""
                ),

            "status":
                "critic_complete",
        }

    return critic_node


async def synthesis_input_node(
    state: dict[str, Any],
) -> dict[str, Any]:

    from app.research.synthesis_input import (
        build_synthesis_input,
    )

    mission_id = (
        _require_state_string(
            state,
            "mission_id",
        )
    )

    worker_result = state.get(
        "research_result"
    )

    verification = state.get(
        "verification_summary"
    )

    gate = state.get(
        "acceptance_gate"
    )

    if not isinstance(
        worker_result,
        dict,
    ):
        _fail(
            "synthesis input requires "
            "research_result"
        )

    if not isinstance(
        verification,
        dict,
    ):
        _fail(
            "synthesis input requires "
            "verification_summary"
        )

    if not isinstance(
        gate,
        dict,
    ):
        _fail(
            "synthesis input requires "
            "acceptance_gate"
        )


    value = build_synthesis_input(
        mission_id=
            mission_id,

        worker_result=
            worker_result,

        verification_summary=
            verification,

        acceptance_gate=
            gate,
    )


    return {
        "synthesis_input":
            value,

        "status":
            "synthesis_ready",
    }
