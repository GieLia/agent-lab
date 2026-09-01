import json

from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

CAPABILITY_REGISTRY = (
    ROOT
    / "portable"
    / "capabilities"
    / "registry.json"
)

BINDING_REGISTRY = (
    ROOT
    / "integrations"
    / "tool-bindings"
    / "registry.json"
)


APPROVAL_RANK = {
    "none": 0,
    "runtime": 1,
    "human": 2,
}

TOOL_KINDS = {
    "native",
    "cli",
    "python",
    "http",
    "mcp",
}

MCP_TRANSPORTS = {
    "stdio",
    "streamable_http",
}


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_capabilities():
    data = load_json(
        CAPABILITY_REGISTRY
    )

    return {
        item["capability_id"]:
            item
        for item in data[
            "capabilities"
        ]
    }


def validate_binding(
    binding,
    capabilities,
):
    required = {
        "binding_id",
        "version",
        "status",
        "capability_id",
        "tool_kind",
        "tool_name",
        "approval",
        "implementation",
    }

    assert (
        set(binding)
        == required
    )

    assert (
        binding[
            "capability_id"
        ]
        in capabilities
    )

    assert (
        binding[
            "tool_kind"
        ]
        in TOOL_KINDS
    )

    assert (
        binding[
            "status"
        ]
        in {
            "active",
            "experimental",
            "disabled",
        }
    )

    capability = (
        capabilities[
            binding[
                "capability_id"
            ]
        ]
    )

    assert (
        APPROVAL_RANK[
            binding[
                "approval"
            ]
        ]
        >=
        APPROVAL_RANK[
            capability[
                "default_approval"
            ]
        ]
    )

    implementation = (
        binding[
            "implementation"
        ]
    )

    assert isinstance(
        implementation,
        dict,
    )

    kind = binding[
        "tool_kind"
    ]

    if kind == "native":
        assert (
            set(
                implementation
            )
            == {
                "provider",
                "native_tool",
            }
        )

    elif kind == "cli":
        assert (
            set(
                implementation
            )
            == {
                "executable",
            }
        )

    elif kind == "python":
        assert (
            set(
                implementation
            )
            == {
                "callable",
            }
        )

    elif kind == "http":
        assert (
            set(
                implementation
            )
            == {
                "endpoint_id",
            }
        )

    elif kind == "mcp":
        assert (
            {
                "server_id",
                "tool",
                "transport",
            }
            .issubset(
                implementation
            )
        )

        assert (
            implementation[
                "transport"
            ]
            in MCP_TRANSPORTS
        )

        assert (
            set(
                implementation
            )
            <= {
                "server_id",
                "server_version",
                "tool",
                "transport",
            }
        )


def check_registry():
    capabilities = (
        load_capabilities()
    )

    registry = load_json(
        BINDING_REGISTRY
    )

    assert (
        set(registry)
        == {
            "registry_version",
            "bindings",
        }
    )

    assert (
        registry[
            "registry_version"
        ]
        == 1
    )

    bindings = (
        registry[
            "bindings"
        ]
    )

    assert isinstance(
        bindings,
        list,
    )

    ids = []

    for binding in bindings:
        validate_binding(
            binding,
            capabilities,
        )

        ids.append(
            binding[
                "binding_id"
            ]
        )

    assert (
        len(ids)
        == len(
            set(ids)
        )
    )

    print(
        "TOOL_BINDING_REGISTRY_OK"
    )


def check_synthetic_contracts():
    capabilities = (
        load_capabilities()
    )

    valid_mcp = {
        "binding_id":
            "example.web_search",
        "version":
            1,
        "status":
            "disabled",
        "capability_id":
            "web.search",
        "tool_kind":
            "mcp",
        "tool_name":
            "search",
        "approval":
            "none",
        "implementation": {
            "server_id":
                "example",
            "server_version":
                None,
            "tool":
                "search",
            "transport":
                "stdio",
        },
    }

    validate_binding(
        valid_mcp,
        capabilities,
    )

    weaker_privileged = {
        "binding_id":
            "example.privileged",
        "version":
            1,
        "status":
            "disabled",
        "capability_id":
            "system.privileged",
        "tool_kind":
            "cli",
        "tool_name":
            "example",
        "approval":
            "runtime",
        "implementation": {
            "executable":
                "example",
        },
    }

    try:
        validate_binding(
            weaker_privileged,
            capabilities,
        )

    except AssertionError:
        print(
            "APPROVAL_DOWNGRADE_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "approval downgrade accepted"
        )

    legacy_sse = {
        **valid_mcp,
        "binding_id":
            "example.legacy_sse",
        "implementation": {
            **valid_mcp[
                "implementation"
            ],
            "transport":
                "sse",
        },
    }

    try:
        validate_binding(
            legacy_sse,
            capabilities,
        )

    except AssertionError:
        print(
            "LEGACY_MCP_SSE_REJECTED_OK"
        )

    else:
        raise AssertionError(
            "legacy MCP SSE accepted"
        )

    print(
        "TOOL_BINDING_SYNTHETIC_CONTRACTS_OK"
    )


def main():
    check_registry()
    check_synthetic_contracts()

    print()
    print(
        "TOOL_BINDING_BOUNDARY_OK"
    )


if __name__ == "__main__":
    main()
