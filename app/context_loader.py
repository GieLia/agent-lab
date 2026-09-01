from __future__ import annotations

import json
import re

from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

PORTABLE_ROOT = (
    REPO_ROOT
    / "portable"
)

MANIFEST_ROOT = (
    PORTABLE_ROOT
    / "context-manifests"
)

PROFILE_ROOT = (
    PORTABLE_ROOT
    / "profiles"
)

SKILL_ROOT = (
    PORTABLE_ROOT
    / "skills"
)

POLICY_ROOT = (
    PORTABLE_ROOT
    / "policies"
)

TOOL_PROFILE_ROOT = (
    PORTABLE_ROOT
    / "tool-profiles"
)

SCHEMA_ROOT = (
    PORTABLE_ROOT
    / "schemas"
)


LOGICAL_ID_RE = re.compile(
    r"^[a-z][a-z0-9_-]*$"
)

SCHEMA_NAME_RE = re.compile(
    r"^[a-z][a-z0-9_-]*\.schema\.json$"
)

POLICY_NAME_RE = re.compile(
    r"^[a-z][a-z0-9_-]*-policy\.md$"
)


class ContextAssemblyError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True
)
class ContextAsset:
    kind: str
    identifier: str
    relative_path: str
    content: str


@dataclass(
    frozen=True
)
class AssembledContext:
    manifest_id: str
    role_profile: str
    skills: tuple[str, ...]
    tool_profile: str
    schemas: tuple[str, ...]
    policies: tuple[str, ...]
    assets: tuple[ContextAsset, ...]
    file_count: int
    total_bytes: int
    rendered: str


def _fail(
    message: str,
) -> None:
    raise ContextAssemblyError(
        message
    )


def _require_logical_id(
    value: Any,
    label: str,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or
        LOGICAL_ID_RE.fullmatch(
            value
        )
        is None
    ):
        _fail(
            f"invalid {label}: "
            f"{value!r}"
        )

    return value


def _require_schema_name(
    value: Any,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or
        SCHEMA_NAME_RE.fullmatch(
            value
        )
        is None
    ):
        _fail(
            f"invalid schema name: "
            f"{value!r}"
        )

    return value


def _require_policy_name(
    value: Any,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or
        POLICY_NAME_RE.fullmatch(
            value
        )
        is None
    ):
        _fail(
            f"invalid policy name: "
            f"{value!r}"
        )

    return value


def _safe_file(
    root: Path,
    *parts: str,
) -> Path:

    resolved_root = (
        root.resolve()
    )

    candidate = (
        root.joinpath(
            *parts
        )
        .resolve()
    )

    try:
        candidate.relative_to(
            resolved_root
        )

    except ValueError as exc:
        raise ContextAssemblyError(
            "context path escaped "
            f"approved root: {candidate}"
        ) from exc

    if not candidate.is_file():
        _fail(
            "required context asset "
            f"does not exist: {candidate}"
        )

    return candidate


def _read_text(
    path: Path,
) -> str:

    return path.read_text(
        encoding="utf-8"
    )


def _load_json(
    path: Path,
) -> dict[str, Any]:

    try:
        value = json.loads(
            _read_text(
                path
            )
        )

    except json.JSONDecodeError as exc:
        raise ContextAssemblyError(
            "invalid JSON context asset: "
            f"{path}"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        _fail(
            "JSON context asset must "
            f"be an object: {path}"
        )

    return value


def _markdown_list(
    text: str,
    heading: str,
) -> tuple[str, ...]:

    lines = text.splitlines()

    try:
        index = next(
            i
            for i, line
            in enumerate(lines)
            if line.strip()
            == heading
        )

    except StopIteration:
        _fail(
            "missing Markdown section: "
            f"{heading}"
        )

    values: list[str] = []

    for line in lines[
        index + 1:
    ]:
        stripped = (
            line.strip()
        )

        if stripped.startswith(
            "## "
        ):
            break

        if stripped.startswith(
            "- "
        ):
            value = (
                stripped[2:]
                .strip()
            )

            if value:
                values.append(
                    value
                )

    return tuple(
        values
    )


def _require_active_markdown(
    text: str,
    label: str,
) -> None:

    if (
        "Version: 1"
        not in text
    ):
        _fail(
            f"{label} has unsupported "
            "or missing version"
        )

    if (
        "Status: active"
        not in text
    ):
        _fail(
            f"{label} is not active"
        )


def _validate_manifest_shape(
    manifest: dict[str, Any],
    *,
    allow_experimental: bool,
) -> None:

    expected = {
        "manifest_id",
        "version",
        "status",
        "role_profile",
        "skills",
        "tool_profile",
        "schemas",
        "context_budget",
    }

    if (
        set(manifest)
        != expected
    ):
        _fail(
            "invalid ContextManifest "
            "top-level fields"
        )

    _require_logical_id(
        manifest[
            "manifest_id"
        ],
        "manifest_id",
    )

    if (
        manifest[
            "version"
        ]
        != 1
    ):
        _fail(
            "unsupported "
            "ContextManifest version"
        )

    status = manifest[
        "status"
    ]

    if status == "disabled":
        _fail(
            "ContextManifest is disabled"
        )

    if (
        status
        == "experimental"
        and not allow_experimental
    ):
        _fail(
            "experimental ContextManifest "
            "requires explicit opt-in"
        )

    if status not in {
        "active",
        "experimental",
        "disabled",
    }:
        _fail(
            "invalid ContextManifest status"
        )

    _require_logical_id(
        manifest[
            "role_profile"
        ],
        "role_profile",
    )

    _require_logical_id(
        manifest[
            "tool_profile"
        ],
        "tool_profile",
    )

    skills = manifest[
        "skills"
    ]

    if (
        not isinstance(
            skills,
            list,
        )
        or
        not skills
    ):
        _fail(
            "skills must be a "
            "non-empty list"
        )

    checked_skills = [
        _require_logical_id(
            value,
            "skill",
        )
        for value in skills
    ]

    if (
        len(
            checked_skills
        )
        != len(
            set(
                checked_skills
            )
        )
    ):
        _fail(
            "duplicate skill identifiers"
        )

    schemas = manifest[
        "schemas"
    ]

    if not isinstance(
        schemas,
        list,
    ):
        _fail(
            "schemas must be a list"
        )

    checked_schemas = [
        _require_schema_name(
            value
        )
        for value in schemas
    ]

    if (
        len(
            checked_schemas
        )
        != len(
            set(
                checked_schemas
            )
        )
    ):
        _fail(
            "duplicate schema identifiers"
        )

    budget = manifest[
        "context_budget"
    ]

    if (
        not isinstance(
            budget,
            dict,
        )
        or
        set(budget)
        != {
            "max_files",
            "max_bytes",
        }
    ):
        _fail(
            "invalid context_budget"
        )

    max_files = budget[
        "max_files"
    ]

    max_bytes = budget[
        "max_bytes"
    ]

    if (
        not isinstance(
            max_files,
            int,
        )
        or isinstance(
            max_files,
            bool,
        )
        or not (
            1
            <= max_files
            <= 32
        )
    ):
        _fail(
            "max_files outside "
            "supported bounds"
        )

    if (
        not isinstance(
            max_bytes,
            int,
        )
        or isinstance(
            max_bytes,
            bool,
        )
        or not (
            1024
            <= max_bytes
            <= 262144
        )
    ):
        _fail(
            "max_bytes outside "
            "supported bounds"
        )


def _asset(
    *,
    kind: str,
    identifier: str,
    path: Path,
    repo_root: Path,
) -> ContextAsset:

    content = _read_text(
        path
    )

    return ContextAsset(
        kind=kind,
        identifier=identifier,
        relative_path=str(
            path.relative_to(
                repo_root
            )
        ),
        content=content,
    )


def _render_assets(
    assets: list[
        ContextAsset
    ],
) -> str:

    blocks: list[str] = []

    for asset in assets:
        label = (
            f"{asset.kind}:"
            f"{asset.identifier}"
        )

        blocks.append(
            "\n".join(
                [
                    (
                        "===== BEGIN "
                        f"{label} ====="
                    ),
                    (
                        asset.content
                        .rstrip()
                    ),
                    (
                        "===== END "
                        f"{label} ====="
                    ),
                ]
            )
        )

    return (
        "\n\n".join(
            blocks
        )
        + "\n"
    )


def load_context_manifest(
    manifest_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:

    manifest_id = (
        _require_logical_id(
            manifest_id,
            "manifest_id",
        )
    )

    root = (
        repo_root
        or REPO_ROOT
    ).resolve()

    manifest_root = (
        root
        / "portable"
        / "context-manifests"
    )

    path = _safe_file(
        manifest_root,
        manifest_id,
        "manifest.json",
    )

    manifest = _load_json(
        path
    )

    if (
        manifest.get(
            "manifest_id"
        )
        != manifest_id
    ):
        _fail(
            "manifest_id does not "
            "match manifest directory"
        )

    return manifest


def assemble_context_from_manifest(
    manifest: dict[str, Any],
    *,
    repo_root: Path | None = None,
    allow_experimental: bool = False,
) -> AssembledContext:

    root = (
        repo_root
        or REPO_ROOT
    ).resolve()

    portable = (
        root / "portable"
    )

    profile_root = (
        portable / "profiles"
    )

    skill_root = (
        portable / "skills"
    )

    policy_root = (
        portable / "policies"
    )

    tool_profile_root = (
        portable / "tool-profiles"
    )

    schema_root = (
        portable / "schemas"
    )

    _validate_manifest_shape(
        manifest,
        allow_experimental=
            allow_experimental,
    )

    manifest_id = manifest[
        "manifest_id"
    ]

    role_id = manifest[
        "role_profile"
    ]

    skill_ids = tuple(
        manifest[
            "skills"
        ]
    )

    tool_profile_id = manifest[
        "tool_profile"
    ]

    schema_names = tuple(
        manifest[
            "schemas"
        ]
    )

    role_path = _safe_file(
        profile_root,
        role_id,
        "profile.md",
    )

    role_text = _read_text(
        role_path
    )

    _require_active_markdown(
        role_text,
        f"role profile {role_id}",
    )

    allowed_skills = set(
        _markdown_list(
            role_text,
            "## Allowed Skills",
        )
    )

    unauthorized_skills = (
        set(skill_ids)
        - allowed_skills
    )

    if unauthorized_skills:
        _fail(
            "manifest selected skills "
            "not allowed by role profile: "
            + ", ".join(
                sorted(
                    unauthorized_skills
                )
            )
        )

    policy_names = set(
        _markdown_list(
            role_text,
            "## Required Policies",
        )
    )

    assets: list[
        ContextAsset
    ] = [
        _asset(
            kind="role",
            identifier=role_id,
            path=role_path,
            repo_root=root,
        )
    ]

    for skill_id in skill_ids:
        skill_path = _safe_file(
            skill_root,
            skill_id,
            "skill.md",
        )

        skill_text = _read_text(
            skill_path
        )

        _require_active_markdown(
            skill_text,
            f"skill {skill_id}",
        )

        policy_names.update(
            _markdown_list(
                skill_text,
                "## Required Policies",
            )
        )

        assets.append(
            _asset(
                kind="skill",
                identifier=skill_id,
                path=skill_path,
                repo_root=root,
            )
        )

    tool_profile_path = (
        _safe_file(
            tool_profile_root,
            tool_profile_id,
            "profile.json",
        )
    )

    tool_profile = _load_json(
        tool_profile_path
    )

    if (
        tool_profile.get(
            "profile_id"
        )
        != tool_profile_id
    ):
        _fail(
            "tool profile identifier "
            "mismatch"
        )

    tool_status = (
        tool_profile.get(
            "status"
        )
    )

    if tool_status == "disabled":
        _fail(
            "ToolProfile is disabled"
        )

    if (
        tool_status
        == "experimental"
        and not allow_experimental
    ):
        _fail(
            "experimental ToolProfile "
            "requires explicit opt-in"
        )

    if tool_status not in {
        "active",
        "experimental",
        "disabled",
    }:
        _fail(
            "invalid ToolProfile status"
        )

    required_tool_policies = (
        tool_profile.get(
            "required_policies"
        )
    )

    if (
        not isinstance(
            required_tool_policies,
            list,
        )
        or
        not required_tool_policies
    ):
        _fail(
            "ToolProfile has invalid "
            "required_policies"
        )

    for policy_name in (
        required_tool_policies
    ):
        policy_names.add(
            _require_policy_name(
                policy_name
            )
        )

    checked_policy_names = tuple(
        sorted(
            _require_policy_name(
                value
            )
            for value
            in policy_names
        )
    )

    for policy_name in (
        checked_policy_names
    ):
        policy_path = _safe_file(
            policy_root,
            policy_name,
        )

        policy_text = _read_text(
            policy_path
        )

        _require_active_markdown(
            policy_text,
            f"policy {policy_name}",
        )

        assets.append(
            _asset(
                kind="policy",
                identifier=policy_name,
                path=policy_path,
                repo_root=root,
            )
        )

    assets.append(
        _asset(
            kind="tool-profile",
            identifier=
                tool_profile_id,
            path=tool_profile_path,
            repo_root=root,
        )
    )

    for schema_name in schema_names:
        checked_name = (
            _require_schema_name(
                schema_name
            )
        )

        schema_path = _safe_file(
            schema_root,
            checked_name,
        )

        schema = _load_json(
            schema_path
        )

        if (
            schema.get(
                "$id"
            )
            != checked_name
        ):
            _fail(
                "schema identifier "
                f"mismatch: {checked_name}"
            )

        assets.append(
            _asset(
                kind="schema",
                identifier=
                    checked_name,
                path=schema_path,
                repo_root=root,
            )
        )

    rendered = _render_assets(
        assets
    )

    file_count = len(
        assets
    )

    total_bytes = len(
        rendered.encode(
            "utf-8"
        )
    )

    budget = manifest[
        "context_budget"
    ]

    if (
        file_count
        > budget[
            "max_files"
        ]
    ):
        _fail(
            "context file budget "
            "exceeded: "
            f"{file_count} > "
            f"{budget['max_files']}"
        )

    if (
        total_bytes
        > budget[
            "max_bytes"
        ]
    ):
        _fail(
            "context byte budget "
            "exceeded: "
            f"{total_bytes} > "
            f"{budget['max_bytes']}"
        )

    return AssembledContext(
        manifest_id=manifest_id,
        role_profile=role_id,
        skills=skill_ids,
        tool_profile=
            tool_profile_id,
        schemas=schema_names,
        policies=
            checked_policy_names,
        assets=tuple(
            assets
        ),
        file_count=file_count,
        total_bytes=
            total_bytes,
        rendered=rendered,
    )


def assemble_context(
    manifest_id: str,
    *,
    repo_root: Path | None = None,
    allow_experimental: bool = False,
) -> AssembledContext:

    root = (
        repo_root
        or REPO_ROOT
    ).resolve()

    manifest = (
        load_context_manifest(
            manifest_id,
            repo_root=root,
        )
    )

    return (
        assemble_context_from_manifest(
            manifest,
            repo_root=root,
            allow_experimental=
                allow_experimental,
        )
    )
