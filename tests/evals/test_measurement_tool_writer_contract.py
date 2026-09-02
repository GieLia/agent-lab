import uuid

from app.measurements import (
    MeasurementWriter,
)


class FakeCursor:
    def __init__(
        self,
        captured,
    ):
        self.captured = captured

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

    def execute(
        self,
        query,
        params,
    ):
        self.captured[
            "query"
        ] = query

        self.captured[
            "params"
        ] = params


class FakeConnection:
    def __init__(
        self,
        captured,
    ):
        self.captured = captured

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

    def cursor(
        self,
    ):
        return FakeCursor(
            self.captured
        )


class RecordingWriter(
    MeasurementWriter
):
    def __init__(
        self,
        captured,
        *,
        required=False,
    ):
        super().__init__(
            required=required
        )

        self.captured = captured

    def _connect(
        self,
    ):
        return FakeConnection(
            self.captured
        )


class FailingWriter(
    MeasurementWriter
):
    def _connect(
        self,
    ):
        raise RuntimeError(
            "synthetic database failure"
        )


def check_insert_contract():

    captured = {}

    writer = RecordingWriter(
        captured
    )

    run_id = uuid.uuid4()

    invocation_id = (
        writer.record_tool_invocation(
            run_id=run_id,
            worker_invocation_id=
                "worker-invocation-test",
            capability="web.search",
            tool_name="web.search",
            tool_kind="python",
            tool_profile=
                "research-readonly",
            duration_ms=123,
            status="success",
            metadata={
                "binding_id":
                    "web.search.brave",
                "result_count":
                    5,
            },
        )
    )

    assert isinstance(
        invocation_id,
        str,
    )

    assert invocation_id

    query = captured[
        "query"
    ]

    params = captured[
        "params"
    ]

    assert (
        "measurement.tool_invocation"
        in query
    )

    assert (
        params[0]
        == invocation_id
    )

    assert (
        params[1]
        == run_id
    )

    assert (
        params[2]
        == "worker-invocation-test"
    )

    assert (
        params[3]
        == "web.search"
    )

    assert (
        params[4]
        == "web.search"
    )

    assert (
        params[5]
        == "python"
    )

    assert (
        params[6]
        == "research-readonly"
    )

    assert (
        params[11]
        == 123
    )

    assert (
        params[12]
        == "success"
    )

    assert (
        params[14]
        is False
    )

    assert (
        params[15]
        is None
    )

    print(
        "TOOL_INVOCATION_INSERT_CONTRACT_OK"
    )


def check_fail_open():

    writer = FailingWriter(
        required=False
    )

    result = (
        writer.record_tool_invocation(
            run_id=uuid.uuid4(),
            capability="web.fetch",
            tool_name="web.fetch",
            tool_kind="python",
            tool_profile=
                "research-readonly",
            status="failed",
            error_code=
                "synthetic_failure",
        )
    )

    assert result is None

    print(
        "TOOL_INVOCATION_FAIL_OPEN_OK"
    )


def check_required_mode():

    writer = FailingWriter(
        required=True
    )

    try:
        writer.record_tool_invocation(
            run_id=uuid.uuid4(),
            capability="web.fetch",
            tool_name="web.fetch",
            tool_kind="python",
            status="failed",
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "required measurement "
            "failure was swallowed"
        )

    print(
        "TOOL_INVOCATION_REQUIRED_MODE_OK"
    )


def check_local_validation():

    writer = RecordingWriter(
        {}
    )

    try:
        writer.record_tool_invocation(
            run_id=uuid.uuid4(),
            capability="web.search",
            tool_name="web.search",
            tool_kind="python",
            status="success",
            duration_ms=-1,
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "negative duration accepted"
        )

    try:
        writer.record_tool_invocation(
            run_id=uuid.uuid4(),
            capability="web.search",
            tool_name="web.search",
            tool_kind="python",
            status="success",
            human_approval_required=False,
            human_approval_granted=True,
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "invalid approval state accepted"
        )

    print(
        "TOOL_INVOCATION_LOCAL_VALIDATION_OK"
    )


def main():

    check_insert_contract()
    check_fail_open()
    check_required_mode()
    check_local_validation()

    print()
    print(
        "MEASUREMENT_TOOL_WRITER_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
