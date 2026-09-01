from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "policies"

EXPECTED = {
    "research-policy.md",
    "evidence-policy.md",
    "security-policy.md",
    "tool-security-policy.md",
}


def read(name):
    return (
        POLICY_DIR / name
    ).read_text(
        encoding="utf-8"
    )


def check_files():
    actual = {
        path.name
        for path in POLICY_DIR.glob(
            "*-policy.md"
        )
    }

    assert actual == EXPECTED, (
        f"policy set mismatch: {actual}"
    )

    print(
        "POLICY_FILES_OK"
    )


def check_common_structure():
    for name in EXPECTED:
        text = read(name)

        assert "Version: 1" in text
        assert "Status: active" in text
        assert "## Purpose" in text

    print(
        "POLICY_STRUCTURE_OK"
    )


def check_research_policy():
    text = read(
        "research-policy.md"
    ).lower()

    required = [
        "contradictory evidence",
        "targeted follow-up",
        "empty successful results are invalid",
        "critic:",
        "evidence verifier:",
        "synthesizer:",
        "research lead:",
    ]

    for value in required:
        assert value in text, value

    print(
        "RESEARCH_POLICY_CONTRACT_OK"
    )


def check_evidence_policy():
    text = read(
        "evidence-policy.md"
    ).lower()

    required = [
        "claim <- evidence -> source",
        "unverified:",
        "partially_verified:",
        "verified:",
        "contradicted:",
        "disputed:",
        "orphan evidence is invalid",
        "do not invent numeric confidence",
    ]

    for value in required:
        assert value in text, value

    print(
        "EVIDENCE_POLICY_CONTRACT_OK"
    )


def check_security_policy():
    text = read(
        "security-policy.md"
    ).lower()

    required = [
        "denied unless explicitly allowed",
        "critic:",
        "must not use external research tools",
        "evidence verifier:",
        "read-only source verification tools",
        "synthesizer:",
        "must not independently browse",
        "production project tree",
        "untrusted data",
        "human gates",
        "least privilege",
    ]

    for value in required:
        assert value in text, value

    print(
        "SECURITY_POLICY_CONTRACT_OK"
    )


def check_tool_security_policy():
    text = read(
        "tool-security-policy.md"
    ).lower()

    required = [
        "default deny",
        "a model must not grant itself additional capabilities",
        "concrete tools are implementation details",
        "mcp is an implementation kind, not a capability class",
        "dynamic tool discovery must not automatically authorize",
        "privileged operations require explicit human approval",
        "measurement does not replace enforcement",
        "the stricter security boundary wins",
    ]

    for value in required:
        assert value in text, value

    print(
        "TOOL_SECURITY_POLICY_CONTRACT_OK"
    )


def check_role_separation():
    security = read(
        "security-policy.md"
    ).lower()

    assert (
        "critic:\n"
        "must not use external research tools"
        in security
    )

    assert (
        "evidence verifier:\n"
        "may use explicitly allowed read-only "
        "source verification tools"
        in security
    )

    assert (
        "synthesizer:\n"
        "must not independently browse"
        in security
    )

    print(
        "ROLE_SECURITY_SEPARATION_OK"
    )


def main():
    check_files()
    check_common_structure()
    check_research_policy()
    check_evidence_policy()
    check_security_policy()
    check_tool_security_policy()
    check_role_separation()

    print()
    print(
        "PORTABLE_POLICY_INTEGRITY_OK"
    )


if __name__ == "__main__":
    main()
