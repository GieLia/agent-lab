import importlib
import inspect
import json

from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

BINDINGS_PATH = (
    ROOT
    / "integrations"
    / "tool-bindings"
    / "registry.json"
)

PROFILE_PATH = (
    ROOT
    / "portable"
    / "tool-profiles"
    / "research-readonly"
    / "profile.json"
)

CAPABILITIES_PATH = (
    ROOT
    / "portable"
    / "capabilities"
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


def resolve_python_callable(
    reference: str,
):

    if (
        not isinstance(
            reference,
            str,
        )
        or reference.count(":") != 1
    ):
        raise AssertionError(
            "Invalid Python callable reference"
        )

    module_name, function_name = (
        reference.split(
            ":",
            1,
        )
    )

    module = importlib.import_module(
        module_name
    )

    function = getattr(
        module,
        function_name,
        None,
    )

    assert callable(
        function
    )

    assert inspect.iscoroutinefunction(
        function
    )

    return function


def main():

    registry = load_json(
        BINDINGS_PATH
    )

    profile = load_json(
        PROFILE_PATH
    )

    capabilities = load_json(
        CAPABILITIES_PATH
    )

    assert (
        registry[
            "registry_version"
        ]
        == 1
    )

    bindings = registry[
        "bindings"
    ]

    assert (
        len(bindings)
        == 2
    )

    binding_ids = [
        binding[
            "binding_id"
        ]
        for binding
        in bindings
    ]

    assert (
        len(binding_ids)
        == len(
            set(binding_ids)
        )
    )

    by_capability = {
        binding[
            "capability_id"
        ]:
        binding
        for binding
        in bindings
    }

    assert (
        set(
            by_capability
        )
        == {
            "web.search",
            "web.fetch",
        }
    )

    known_capabilities = {
        item[
            "capability_id"
        ]
        for item
        in capabilities[
            "capabilities"
        ]
    }

    allowed_capabilities = set(
        profile[
            "allowed_capabilities"
        ]
    )

    expected = {
        "web.search": {
            "binding_id":
                "web.search.brave",
            "tool_name":
                "web.search",
            "callable":
                "app.tools.web_search:search_web",
        },
        "web.fetch": {
            "binding_id":
                "web.fetch.guarded",
            "tool_name":
                "web.fetch",
            "callable":
                "app.tools.web_fetch:fetch_web",
        },
    }

    for (
        capability_id,
        expected_values,
    ) in expected.items():

        assert (
            capability_id
            in known_capabilities
        )

        assert (
            capability_id
            in allowed_capabilities
        )

        binding = by_capability[
            capability_id
        ]

        assert (
            binding[
                "binding_id"
            ]
            == expected_values[
                "binding_id"
            ]
        )

        assert (
            binding[
                "version"
            ]
            == 1
        )

        assert (
            binding[
                "status"
            ]
            == "experimental"
        )

        assert (
            binding[
                "tool_kind"
            ]
            == "python"
        )

        assert (
            binding[
                "tool_name"
            ]
            == expected_values[
                "tool_name"
            ]
        )

        assert (
            binding[
                "approval"
            ]
            == "none"
        )

        callable_ref = (
            binding[
                "implementation"
            ][
                "callable"
            ]
        )

        assert (
            callable_ref
            == expected_values[
                "callable"
            ]
        )

        resolve_python_callable(
            callable_ref
        )

    constraints = profile[
        "runtime_constraints"
    ]

    assert (
        constraints[
            "network_access"
        ]
        == "read_only"
    )

    assert (
        constraints[
            "workspace_write"
        ]
        is False
    )

    assert (
        constraints[
            "process_execute"
        ]
        is False
    )

    assert (
        constraints[
            "privileged"
        ]
        is False
    )

    assert (
        profile[
            "default_deny"
        ]
        is True
    )

    print(
        "WEB_BINDING_CAPABILITIES_OK"
    )

    print(
        "WEB_BINDING_CALLABLES_OK"
    )

    print(
        "WEB_BINDING_READONLY_BOUNDARY_OK"
    )

    print()
    print(
        "WEB_TOOL_BINDING_CONTRACT_OK"
    )


if __name__ == "__main__":
    main()
