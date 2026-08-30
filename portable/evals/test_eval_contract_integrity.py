from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals"

EXPECTED = {
    "evidence-integrity.md",
    "role-boundary.md",
    "acceptance-integrity.md",
    "synthesis-traceability.md",
    "knowledge-durability.md",
    "revision-quality.md",
}

REQUIRED_SECTIONS = [
    "## Purpose",
    "## Subject",
    "## Inputs",
    "## Pass Criteria",
    "## Fail Conditions",
    "## Measurements",
    "## Prohibited Shortcuts",
]


def read(name):
    return (
        EVAL_DIR / name
    ).read_text(
        encoding="utf-8"
    )


def check_files():
    actual = {
        path.name
        for path in EVAL_DIR.glob(
            "*.md"
        )
        if path.name != "README.md"
    }

    assert actual == EXPECTED, (
        f"eval set mismatch: {actual}"
    )

    print(
        "EVAL_CONTRACT_FILES_OK"
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
        "EVAL_CONTRACT_STRUCTURE_OK"
    )


def check_evidence_contract():
    text = read(
        "evidence-integrity.md"
    ).lower()

    required = [
        "claim -> evidence -> source",
        "orphan evidence",
        "identifier collision",
        "contradictory evidence",
        "deterministic",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVAL_EVIDENCE_CONTRACT_OK"
    )


def check_role_contract():
    text = read(
        "role-boundary.md"
    ).lower()

    required = [
        "research lead",
        "critic external research",
        "synthesizer external research",
        "independent-verification bypass",
        "capability inheritance",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVAL_ROLE_CONTRACT_OK"
    )


def check_acceptance_contract():
    text = read(
        "acceptance-integrity.md"
    ).lower()

    required = [
        "disjoint",
        "partial decision",
        "rejected material enters synthesis",
        "eligible for synthesis",
        "equivalent",
        "factual verification",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVAL_ACCEPTANCE_CONTRACT_OK"
    )


def check_synthesis_contract():
    text = read(
        "synthesis-traceability.md"
    ).lower()

    required = [
        "gate-authorized",
        "evidence traceability",
        "verification states",
        "contradictions",
        "unsupported factual certainty",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVAL_SYNTHESIS_CONTRACT_OK"
    )


def check_knowledge_contract():
    text = read(
        "knowledge-durability.md"
    ).lower()

    required = [
        "research run is unavailable",
        "orphaned",
        "supersedes",
        "superseded_by",
        "retraction",
        "secrets",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVAL_KNOWLEDGE_CONTRACT_OK"
    )


def check_revision_contract():
    text = read(
        "revision-quality.md"
    ).lower()

    required = [
        "before-versus-after",
        "factual support",
        "source quality",
        "source coverage",
        "contradiction handling",
        "uncertainty hygiene",
        "task completion",
        "allow tie outcomes",
        "null control",
        "absolute quality scores",
        "not sufficient",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVAL_REVISION_CONTRACT_OK"
    )


def check_portability():
    forbidden = [
        "/home/agent",
        "/home/claude-b",
        "/opt/agent-lab",
        "claude_e1",
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
        "EVAL_CONTRACT_PORTABILITY_OK"
    )


def main():
    check_files()
    check_structure()
    check_evidence_contract()
    check_role_contract()
    check_acceptance_contract()
    check_synthesis_contract()
    check_knowledge_contract()
    check_revision_contract()
    check_portability()

    print()
    print(
        "PORTABLE_EVAL_CONTRACT_INTEGRITY_OK"
    )


if __name__ == "__main__":
    main()
