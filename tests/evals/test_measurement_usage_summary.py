import uuid

from decimal import Decimal


from app.measurements import (
    MeasurementWriter,
)

from app.research.graph_measurement import (
    GraphMeasurementBridge,
)


class FakeCursor:

    description = None


    def execute(
        self,
        query,
        params,
    ):
        assert (
            "measurement.worker_invocation"
            in query
        )

        assert len(
            params
        ) == 1


    def fetchone(
        self,
    ):
        return (
            8,
            24,
            8551,
            19327,
            30425,
            1315,
            Decimal(
                "0.23336840"
            ),
            0,
            0,
        )


    def __enter__(
        self,
    ):
        return self


    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


class FakeConnection:

    def cursor(
        self,
    ):
        return FakeCursor()


    def __enter__(
        self,
    ):
        return self


    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


def main():

    writer = MeasurementWriter(
        required=True
    )

    writer._connect = (
        lambda:
        FakeConnection()
    )

    run_id = uuid.uuid4()

    usage = (
        writer
        .summarize_worker_invocations(
            run_id=
                run_id,
        )
    )

    assert usage == {
        "worker_invocations":
            8,

        "input_tokens":
            24,

        "output_tokens":
            8551,

        "cache_read_tokens":
            19327,

        "cache_write_tokens":
            30425,

        "reasoning_output_tokens":
            1315,

        "reported_cost_usd":
            "0.23336840",

        "transport_failure_invocations":
            0,

        "missing_reported_cost_invocations":
            0,

        "cost_complete":
            True,
    }

    bridge = GraphMeasurementBridge(
        writer=writer,
        run_id=run_id,
    )

    snapshot = bridge.snapshot()

    assert (
        snapshot[
            "usage"
        ]
        == usage
    )

    print(
        "MEASUREMENT_USAGE_TOTALS_OK"
    )

    print(
        "MEASUREMENT_COST_COMPLETE_OK"
    )

    print(
        "MEASUREMENT_USAGE_JSON_SAFE_OK"
    )

    print()
    print(
        "MEASUREMENT_USAGE_SUMMARY_V1_OK"
    )


if __name__ == "__main__":
    main()
