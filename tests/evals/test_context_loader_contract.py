import json

from copy import deepcopy
from pathlib import Path


from app.context_loader import (
    ContextAssemblyError,
    assemble_context,
    assemble_context_from_manifest,
    load_context_manifest,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


EXPECTED_POLICIES = (
    "evidence-policy.md",
    "research-policy.md",
    "security-policy.md",
    "tool-security-policy.md",
)


def reject(
    fn,
    label,
):
    try:
        fn()

    except ContextAssemblyError:
        print(
            f"{label}_OK"
        )

    else:
        raise AssertionError(
            f"{label} was accepted"
        )


def check_critic():
    context = assemble_context(
        "critic-reasoning",
        repo_root=ROOT,
    )

    assert (
        context.role_profile
        == "critic"
    )

    assert (
        context.skills
        == ("critique",)
    )

    assert (
        context.tool_profile
        == "reasoning"
    )

    assert (
        context.policies
        == EXPECTED_POLICIES
    )

    assert (
        context.file_count
        == 7
    )

    assert (
        context.total_bytes
        <= 32768
    )

    assert all(
        "README.md"
        not in asset.relative_path
        for asset
        in context.assets
    )

    assert (
        context.assets[0].kind
        == "role"
    )

    assert (
        context.assets[-1].kind
        == "tool-profile"
    )

    second = assemble_context(
        "critic-reasoning",
        repo_root=ROOT,
    )

    assert (
        context.rendered
        == second.rendered
    )

    print(
        "CRITIC_CONTEXT_OK"
    )


def check_synthesizer():
    context = assemble_context(
        "synthesizer-reasoning",
        repo_root=ROOT,
    )

    assert (
        context.role_profile
        == "synthesizer"
    )

    assert (
        context.skills
        == ("synthesis",)
    )

    assert (
        context.tool_profile
        == "reasoning"
    )

    assert (
        context.policies
        == EXPECTED_POLICIES
    )

    assert (
        context.file_count
        == 8
    )

    assert (
        context.total_bytes
        <= 49152
    )

    schema_assets = [
        asset.identifier
        for asset
        in context.assets
        if asset.kind
        == "schema"
    ]

    assert (
        schema_assets
        == [
            "research-report.schema.json"
        ]
    )

    print(
        "SYNTHESIZER_CONTEXT_OK"
    )


def check_role_skill_boundary():
    manifest = (
        load_context_manifest(
            "critic-reasoning",
            repo_root=ROOT,
        )
    )

    broken = deepcopy(
        manifest
    )

    broken[
        "skills"
    ] = [
        "synthesis"
    ]

    reject(
        lambda:
            assemble_context_from_manifest(
                broken,
                repo_root=ROOT,
            ),
        "ROLE_SKILL_ESCALATION_REJECTED",
    )


def check_path_boundary():
    manifest = (
        load_context_manifest(
            "critic-reasoning",
            repo_root=ROOT,
        )
    )

    broken = deepcopy(
        manifest
    )

    broken[
        "schemas"
    ] = [
        "../security-policy.md"
    ]

    reject(
        lambda:
            assemble_context_from_manifest(
                broken,
                repo_root=ROOT,
            ),
        "PATH_TRAVERSAL_REJECTED",
    )

    reject(
        lambda:
            load_context_manifest(
                "../critic-reasoning",
                repo_root=ROOT,
            ),
        "MANIFEST_PATH_ESCAPE_REJECTED",
    )


def check_budget_boundary():
    manifest = (
        load_context_manifest(
            "critic-reasoning",
            repo_root=ROOT,
        )
    )

    broken_files = deepcopy(
        manifest
    )

    broken_files[
        "context_budget"
    ][
        "max_files"
    ] = 1

    reject(
        lambda:
            assemble_context_from_manifest(
                broken_files,
                repo_root=ROOT,
            ),
        "FILE_BUDGET_REJECTED",
    )

    broken_bytes = deepcopy(
        manifest
    )

    broken_bytes[
        "context_budget"
    ][
        "max_bytes"
    ] = 1024

    reject(
        lambda:
            assemble_context_from_manifest(
                broken_bytes,
                repo_root=ROOT,
            ),
        "BYTE_BUDGET_REJECTED",
    )


def check_manifest_identity():
    manifest_path = (
        ROOT
        / "portable"
        / "context-manifests"
        / "critic-reasoning"
        / "manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest[
            "manifest_id"
        ]
        == "critic-reasoning"
    )

    print(
        "MANIFEST_IDENTITY_OK"
    )


def main():
    check_critic()
    check_synthesizer()
    check_role_skill_boundary()
    check_path_boundary()
    check_budget_boundary()
    check_manifest_identity()

    print()
    print(
        "CONTEXT_LOADER_BOUNDARY_OK"
    )


if __name__ == "__main__":
    main()
