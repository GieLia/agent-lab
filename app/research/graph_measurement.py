from __future__ import annotations

import uuid

from dataclasses import (
    dataclass,
    field,
)
from typing import Any


from app.workers.result import (
    WorkerExecutionResult,
)


class GraphMeasurementError(
    RuntimeError
):
    pass


@dataclass(
    slots=True,
)
class GraphMeasurementBridge:

    writer: Any
    run_id: uuid.UUID

    research_worker_id: str = (
        "research-graph-v1-researcher"
    )

    semantic_worker_id: str = (
        "research-graph-v1-evidence-verifier"
    )

    critic_worker_id: str = (
        "research-graph-v1-critic"
    )

    synthesis_worker_id: str = (
        "research-graph-v1-synthesizer"
    )

    worker_invocation_ids: list[str] = field(
        default_factory=list
    )

    research_worker_invocation_ids: list[str] = field(
        default_factory=list
    )

    semantic_worker_invocation_ids: list[str] = field(
        default_factory=list
    )

    critic_worker_invocation_ids: list[str] = field(
        default_factory=list
    )

    synthesis_worker_invocation_ids: list[str] = field(
        default_factory=list
    )

    tool_invocation_ids: list[str] = field(
        default_factory=list
    )

    latest_research_worker_invocation_id: (
        str | None
    ) = None


    def _record_worker(
        self,
        *,
        worker_id: str,
        role: str,
        result: WorkerExecutionResult,
    ) -> str:

        if not isinstance(
            result,
            WorkerExecutionResult,
        ):
            raise GraphMeasurementError(
                "measurement requires "
                "WorkerExecutionResult"
            )

        invocation_id = (
            self.writer
            .record_worker_invocation(
                run_id=
                    self.run_id,

                worker_id=
                    worker_id,

                role=
                    role,

                result=
                    result,

                tool_profile=
                    "reasoning",

                tools_exposed_count=
                    0,

                skill_ids=
                    None,
            )
        )

        if (
            not isinstance(
                invocation_id,
                str,
            )
            or not invocation_id
        ):
            raise GraphMeasurementError(
                "worker invocation telemetry "
                "was not persisted"
            )

        self.worker_invocation_ids.append(
            invocation_id
        )

        return invocation_id


    def record_research_model_result(
        self,
        result: WorkerExecutionResult,
    ) -> None:

        invocation_id = (
            self._record_worker(
                worker_id=
                    self.research_worker_id,

                role=
                    "researcher",

                result=
                    result,
            )
        )

        self.latest_research_worker_invocation_id = (
            invocation_id
        )

        self.research_worker_invocation_ids.append(
            invocation_id
        )


    def record_semantic_model_result(
        self,
        result: WorkerExecutionResult,
    ) -> None:

        invocation_id = (
            self._record_worker(
                worker_id=
                    self.semantic_worker_id,

                role=
                    "evidence-verifier",

                result=
                    result,
            )
        )

        self.semantic_worker_invocation_ids.append(
            invocation_id
        )


    def record_critic_model_result(
        self,
        result: WorkerExecutionResult,
    ) -> None:

        invocation_id = (
            self._record_worker(
                worker_id=
                    self.critic_worker_id,

                role=
                    "critic",

                result=
                    result,
            )
        )

        self.critic_worker_invocation_ids.append(
            invocation_id
        )


    def record_synthesis_model_result(
        self,
        result: WorkerExecutionResult,
    ) -> None:

        invocation_id = (
            self._record_worker(
                worker_id=
                    self.synthesis_worker_id,

                role=
                    "synthesizer",

                result=
                    result,
            )
        )

        self.synthesis_worker_invocation_ids.append(
            invocation_id
        )


    def record_tool_invocation(
        self,
        **kwargs: Any,
    ) -> str:

        values = dict(
            kwargs
        )

        supplied_run_id = values.pop(
            "run_id",
            None,
        )

        if (
            supplied_run_id
            is not None
            and supplied_run_id
            != self.run_id
        ):
            raise GraphMeasurementError(
                "tool telemetry run_id mismatch"
            )

        worker_invocation_id = values.get(
            "worker_invocation_id"
        )

        if worker_invocation_id is None:

            worker_invocation_id = (
                self
                .latest_research_worker_invocation_id
            )

            if worker_invocation_id is None:
                raise GraphMeasurementError(
                    "tool invocation has no "
                    "preceding Researcher "
                    "model invocation"
                )

            values[
                "worker_invocation_id"
            ] = worker_invocation_id

        invocation_id = (
            self.writer
            .record_tool_invocation(
                run_id=
                    self.run_id,

                **values,
            )
        )

        if (
            not isinstance(
                invocation_id,
                str,
            )
            or not invocation_id
        ):
            raise GraphMeasurementError(
                "tool invocation telemetry "
                "was not persisted"
            )

        self.tool_invocation_ids.append(
            invocation_id
        )

        return invocation_id


    def snapshot(
        self,
    ) -> dict[str, Any]:

        return {
            "run_id":
                str(
                    self.run_id
                ),

            "worker_invocation_ids":
                list(
                    self.worker_invocation_ids
                ),

            "research_worker_invocation_ids":
                list(
                    self
                    .research_worker_invocation_ids
                ),

            "semantic_worker_invocation_ids":
                list(
                    self
                    .semantic_worker_invocation_ids
                ),

            "critic_worker_invocation_ids":
                list(
                    self
                    .critic_worker_invocation_ids
                ),

            "synthesis_worker_invocation_ids":
                list(
                    self
                    .synthesis_worker_invocation_ids
                ),

            "tool_invocation_ids":
                list(
                    self.tool_invocation_ids
                ),

            "worker_invocation_count":
                len(
                    self.worker_invocation_ids
                ),

            "research_worker_invocation_count":
                len(
                    self
                    .research_worker_invocation_ids
                ),

            "semantic_worker_invocation_count":
                len(
                    self
                    .semantic_worker_invocation_ids
                ),

            "critic_worker_invocation_count":
                len(
                    self
                    .critic_worker_invocation_ids
                ),

            "synthesis_worker_invocation_count":
                len(
                    self
                    .synthesis_worker_invocation_ids
                ),

            "tool_invocation_count":
                len(
                    self.tool_invocation_ids
                ),
        }
