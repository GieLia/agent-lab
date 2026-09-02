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

        if raw_iteration > 0:

            if state.get(
                "retry_required"
            ) is True:
                _fail(
                    "targeted research retry "
                    "requires WorkerResult merge "
                    "semantics and is not enabled "
                    "in E5-C3"
                )

            _fail(
                "research node cannot overwrite "
                "an existing research iteration"
            )

        topic = _require_state_string(
            state,
            "topic",
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

        worker_result = (
            copy.deepcopy(
                result.worker_result
            )
        )

        try:
            validate_worker_result(
                worker_result,
                expected_worker_id=
                    dependencies
                    .research_worker_id,
            )

        except ResearchProtocolError as exc:
            raise GraphNodeAdapterError(
                "research runner produced "
                "invalid canonical WorkerResult"
            ) from exc

        return {
            "iteration":
                1,

            "research_result":
                worker_result,

            "research_metrics": {
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
            },

            # Clear any stale derived authority.
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

            "acceptance_gate":
                {},

            "synthesis_input":
                {},

            "retry_required":
                False,

            "retry_claim_ids":
                [],

            "status":
                "researched",
        }

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

        return {
            "semantic_records":
                records,

            "status":
                "semantically_evaluated",
        }

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
