from app.measurements import (
    MeasurementWriter,
)


BAD_URI = (
    "postgresql://"
    "invalid:invalid"
    "@127.0.0.1:1/"
    "invalid"
    "?connect_timeout=1"
)


def test_fail_open():
    writer = MeasurementWriter(
        required=False,
        db_uri=BAD_URI,
    )

    result = writer.ensure_case(
        case_id=(
            "measurement_fail_open_v1"
        ),
        case_version=1,
    )

    assert result is False

    print(
        "MEASUREMENT_FAIL_OPEN_OK"
    )


def test_required_mode():
    writer = MeasurementWriter(
        required=True,
        db_uri=BAD_URI,
    )

    try:
        writer.ensure_case(
            case_id=(
                "measurement_required_v1"
            ),
            case_version=1,
        )

    except RuntimeError:
        print(
            "MEASUREMENT_REQUIRED_MODE_OK"
        )

        return

    raise AssertionError(
        "required mode did not fail"
    )


def main():
    test_fail_open()
    test_required_mode()

    print()
    print(
        "MEASUREMENT_WRITER_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
