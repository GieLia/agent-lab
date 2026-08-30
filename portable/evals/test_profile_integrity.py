from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "profiles"

EXPECTED = {
    "research-lead",
    "researcher",
    "critic",
    "evidence-verifier",
    "synthesizer",
}

REQUIRED_SECTIONS = [
    "## Purpose",
    "## Responsibilities",
    "## Inputs",
    "## Outputs",
    "## Allowed Skills",
    "## Allowed Tools",
    "## Prohibited Actions",
    "## Required Policies",
    "## Completion Criteria",
]


def read(name):
    return (
        PROFILE_DIR
        / name
        / "profile.md"
    ).read_text(
        encoding="utf-8"
    )


def check_files():
    actual = {
        path.parent.name
        for path in PROFILE_DIR.glob(
            "*/profile.md"
        )
    }

    assert actual == EXPECTED, (
        f"profile set mismatch: {actual}"
    )

    print(
        "PROFILE_FILES_OK"
    )


def check_structure():
    for name in EXPECTED:
        text = read(name)

        assert "Version: 1" in text
        assert "Status: active" in text

        for section in REQUIRED_SECTIONS:
            assert section in text, (
                f"{name}: missing {section}"
            )

    print(
        "PROFILE_STRUCTURE_OK"
    )


def check_policy_binding():
    for name in EXPECTED:
        text = read(name).lower()

        for policy in [
            "research-policy.md",
            "evidence-policy.md",
            "security-policy.md",
        ]:
            assert policy in text, (
                f"{name}: missing {policy}"
            )

    print(
        "PROFILE_POLICY_BINDING_OK"
    )


def check_role_boundaries():
    critic = read(
        "critic"
    ).lower()

    verifier = read(
        "evidence-verifier"
    ).lower()

    synthesizer = read(
        "synthesizer"
    ).lower()

    lead = read(
        "research-lead"
    ).lower()

    assert (
        "no external research tools"
        in critic
    )

    assert (
        "read-only source discovery"
        in verifier
    )

    assert (
        "no independent external research tools"
        in synthesizer
    )

    assert (
        "does not automatically inherit"
        in lead
    )

    print(
        "PROFILE_ROLE_BOUNDARIES_OK"
    )


def check_portability():
    forbidden = [
        "/home/agent",
        "/home/claude-b",
        "/opt/agent-lab",
        'account="primary"',
        'account="secondary"',
    ]

    for name in EXPECTED:
        text = read(name).lower()

        for value in forbidden:
            assert (
                value.lower()
                not in text
            ), (
                f"{name}: runtime-specific "
                f"value found: {value}"
            )

    print(
        "PROFILE_PORTABILITY_OK"
    )


def main():
    check_files()
    check_structure()
    check_policy_binding()
    check_role_boundaries()
    check_portability()

    print()
    print(
        "PORTABLE_PROFILE_INTEGRITY_OK"
    )


if __name__ == "__main__":
    main()
