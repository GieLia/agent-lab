import copy
import json
import tempfile

from pathlib import Path
from unittest.mock import patch

import app.tools.executor as executor

from app.tools.executor import (
    ToolAuthorizationError,
    list_authorized_tools,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

REAL_PROFILE = (
    ROOT
    / "portable"
    / "tool-profiles"
    / "research-readonly"
    / "profile.json"
)

REAL_CAPABILITIES = (
    ROOT
    / "portable"
    / "capabilities"
    / "registry.json"
)

REAL_BINDINGS = (
    ROOT
    / "integrations"
    / "tool-bindings"
    / "registry.json"
)


def load_json(
    path: Path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


BASE_PROFILE = load_json(
    REAL_PROFILE
)

BASE_CAPABILITIES = load_json(
    REAL_CAPABILITIES
)

BASE_BINDINGS = load_json(
    REAL_BINDINGS
)


def write_json(
    path: Path,
    value,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def expect_rejected(
    *,
    profile=None,
    capabilities=None,
    bindings=None,
):

    profile = copy.deepcopy(
        profile
        if profile is not None
        else BASE_PROFILE
    )

    capabilities = copy.deepcopy(
        capabilities
        if capabilities is not None
        else BASE_CAPABILITIES
    )

    bindings = copy.deepcopy(
        bindings
        if bindings is not None
        else BASE_BINDINGS
    )

    with tempfile.TemporaryDirectory() as tmp:

        root = Path(tmp)

        profile_root = (
            root
            / "tool-profiles"
        )

        profile_path = (
            profile_root
            / "research-readonly"
            / "profile.json"
        )

        capability_path = (
            root
            / "capabilities.json"
        )

        binding_path = (
            root
            / "bindings.json"
        )

        write_json(
            profile_path,
            profile,
        )

        write_json(
            capability_path,
            capabilities,
        )

        write_json(
            binding_path,
            bindings,
        )

        with (
            patch.object(
                executor,
                "TOOL_PROFILES_ROOT",
                profile_root,
            ),
            patch.object(
                executor,
                "CAPABILITY_REGISTRY_PATH",
                capability_path,
            ),
            patch.object(
                executor,
                "BINDING_REGISTRY_PATH",
                binding_path,
            ),
        ):

            try:
                list_authorized_tools(
                    "research-readonly",
                    allow_experimental=True,
                )

            except ToolAuthorizationError:
                return

            raise AssertionError(
                "Mutation unexpectedly authorized"
            )


def test_approval_downgrade():

    capabilities = copy.deepcopy(
        BASE_CAPABILITIES
    )

    for capability in capabilities[
        "capabilities"
    ]:
        if (
            capability[
                "capability_id"
            ]
            == "web.search"
        ):
            capability[
                "default_approval"
            ] = "runtime"

    expect_rejected(
        capabilities=capabilities,
    )

    print(
        "APPROVAL_DOWNGRADE_MUTATION_REJECTED_OK"
    )


def test_unknown_capability():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    bindings[
        "bindings"
    ][0][
        "capability_id"
    ] = "unknown.capability"

    expect_rejected(
        bindings=bindings,
    )

    print(
        "UNKNOWN_CAPABILITY_MUTATION_REJECTED_OK"
    )


def test_tool_capability_identity():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    bindings[
        "bindings"
    ][0][
        "tool_name"
    ] = "web.fetch"

    expect_rejected(
        bindings=bindings,
    )

    print(
        "TOOL_CAPABILITY_IDENTITY_MUTATION_REJECTED_OK"
    )


def test_duplicate_tool_name():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    bindings[
        "bindings"
    ][1][
        "capability_id"
    ] = "web.search"

    bindings[
        "bindings"
    ][1][
        "tool_name"
    ] = "web.search"

    expect_rejected(
        bindings=bindings,
    )

    print(
        "DUPLICATE_TOOL_NAME_MUTATION_REJECTED_OK"
    )


def test_max_tools_exposed():

    profile = copy.deepcopy(
        BASE_PROFILE
    )

    profile[
        "max_tools_exposed"
    ] = 1

    expect_rejected(
        profile=profile,
    )

    print(
        "MAX_TOOLS_EXPOSED_MUTATION_REJECTED_OK"
    )


def test_callable_namespace_escape():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    bindings[
        "bindings"
    ][0][
        "implementation"
    ][
        "callable"
    ] = "os:path"

    expect_rejected(
        bindings=bindings,
    )

    print(
        "CALLABLE_NAMESPACE_ESCAPE_REJECTED_OK"
    )


def test_private_function_binding():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    bindings[
        "bindings"
    ][0][
        "implementation"
    ][
        "callable"
    ] = (
        "app.tools.web_search:"
        "_validate_query"
    )

    expect_rejected(
        bindings=bindings,
    )

    print(
        "PRIVATE_CALLABLE_BINDING_REJECTED_OK"
    )


def test_invalid_binding_capability():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    bindings[
        "bindings"
    ][0][
        "capability_id"
    ] = None

    expect_rejected(
        bindings=bindings,
    )

    print(
        "INVALID_BINDING_CAPABILITY_REJECTED_OK"
    )


def test_default_deny_removed():

    profile = copy.deepcopy(
        BASE_PROFILE
    )

    profile[
        "default_deny"
    ] = False

    expect_rejected(
        profile=profile,
    )

    print(
        "DEFAULT_DENY_REMOVAL_REJECTED_OK"
    )


def test_disabled_bindings_are_not_exposed():

    bindings = copy.deepcopy(
        BASE_BINDINGS
    )

    for binding in bindings[
        "bindings"
    ]:
        binding[
            "status"
        ] = "disabled"

    with tempfile.TemporaryDirectory() as tmp:

        root = Path(tmp)

        profile_root = (
            root
            / "tool-profiles"
        )

        profile_path = (
            profile_root
            / "research-readonly"
            / "profile.json"
        )

        capability_path = (
            root
            / "capabilities.json"
        )

        binding_path = (
            root
            / "bindings.json"
        )

        write_json(
            profile_path,
            BASE_PROFILE,
        )

        write_json(
            capability_path,
            BASE_CAPABILITIES,
        )

        write_json(
            binding_path,
            bindings,
        )

        with (
            patch.object(
                executor,
                "TOOL_PROFILES_ROOT",
                profile_root,
            ),
            patch.object(
                executor,
                "CAPABILITY_REGISTRY_PATH",
                capability_path,
            ),
            patch.object(
                executor,
                "BINDING_REGISTRY_PATH",
                binding_path,
            ),
        ):

            tools = list_authorized_tools(
                "research-readonly",
                allow_experimental=True,
            )

            assert tools == ()

    print(
        "DISABLED_BINDINGS_NOT_EXPOSED_OK"
    )


def main():

    test_approval_downgrade()
    test_unknown_capability()
    test_tool_capability_identity()
    test_duplicate_tool_name()
    test_max_tools_exposed()
    test_callable_namespace_escape()
    test_private_function_binding()
    test_invalid_binding_capability()
    test_default_deny_removed()
    test_disabled_bindings_are_not_exposed()

    print()
    print(
        "TOOL_EXECUTOR_MUTATION_BOUNDARY_OK"
    )


if __name__ == "__main__":
    main()
