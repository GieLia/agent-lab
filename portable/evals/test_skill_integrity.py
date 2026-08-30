from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills"

EXPECTED = {
    "web-research",
    "source-verification",
    "synthesis",
    "knowledge-update",
}

REQUIRED_SECTIONS = [
    "## Purpose",
    "## Inputs",
    "## Outputs",
    "## Procedure",
    "## Retry Conditions",
    "## Stop Conditions",
    "## Prohibited Behavior",
    "## Required Policies",
]


def read(name):
    return (
        SKILL_DIR
        / name
        / "skill.md"
    ).read_text(
        encoding="utf-8"
    )


def check_files():
    actual = {
        path.parent.name
        for path in SKILL_DIR.glob(
            "*/skill.md"
        )
    }

    assert actual == EXPECTED, (
        f"skill set mismatch: {actual}"
    )

    print(
        "SKILL_FILES_OK"
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
        "SKILL_STRUCTURE_OK"
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
        "SKILL_POLICY_BINDING_OK"
    )


def check_research_contract():
    text = read(
        "web-research"
    ).lower()

    required = [
        "targeted follow-up",
        "granular claims",
        "create evidence links",
        "detect contradictions",
        "search snippets alone",
    ]

    for value in required:
        assert value in text, value

    print(
        "WEB_RESEARCH_CONTRACT_OK"
    )


def check_verification_contract():
    text = read(
        "source-verification"
    ).lower()

    required = [
        "independent verification",
        "source independence",
        "partially_verified",
        "contradicted",
        "disputed",
        "read-only",
    ]

    for value in required:
        assert value in text, value

    print(
        "SOURCE_VERIFICATION_CONTRACT_OK"
    )


def check_synthesis_contract():
    text = read(
        "synthesis"
    ).lower()

    required = [
        "do not independently browse",
        "deduplicate claims",
        "preserve verification state",
        "handle contradictions",
        "verify traceability",
    ]

    for value in required:
        assert value in text, value

    print(
        "SYNTHESIS_CONTRACT_OK"
    )


def check_knowledge_contract():
    text = read(
        "knowledge-update"
    ).lower()

    required = [
        "durable knowledge",
        "supersedes",
        "verification state",
        "silently overwriting",
        "store secrets or credentials",
        "no-update",
    ]

    for value in required:
        assert value in text, value

    print(
        "KNOWLEDGE_UPDATE_CONTRACT_OK"
    )


def check_portability():
    forbidden = [
        "/home/agent",
        "/home/claude-b",
        "/opt/agent-lab",
        "claude-b",
        "account=\"secondary\"",
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
        "SKILL_PORTABILITY_OK"
    )


def main():
    check_files()
    check_structure()
    check_policy_binding()
    check_research_contract()
    check_verification_contract()
    check_synthesis_contract()
    check_knowledge_contract()
    check_portability()

    print()
    print(
        "PORTABLE_SKILL_INTEGRITY_OK"
    )


if __name__ == "__main__":
    main()
