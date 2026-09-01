import json

from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PORTABLE = (
    ROOT
    / "portable"
)

REGISTRY_PATH = (
    PORTABLE
    / "capabilities"
    / "registry.json"
)

PROFILE_ROOT = (
    PORTABLE
    / "tool-profiles"
)


APPROVAL_RANK = {
    "none": 0,
    "runtime": 1,
    "human": 2,
}

MIN_APPROVAL = {
    "read": "none",
    "write": "runtime",
    "execute": "runtime",
    "privileged": "human",
}


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def load_registry():
    registry = load_json(
        REGISTRY_PATH
    )

    assert (
        registry["registry_version"]
        == 1
    )

    capabilities = (
        registry["capabilities"]
    )

    ids = [
        item["capability_id"]
        for item in capabilities
    ]

    assert len(ids) == len(
        set(ids)
    )

    mapping = {
        item["capability_id"]:
            item
        for item in capabilities
    }

    for capability in capabilities:
        access_class = (
            capability[
                "access_class"
            ]
        )

        approval = (
            capability[
                "default_approval"
            ]
        )

        minimum = (
            MIN_APPROVAL[
                access_class
            ]
        )

        assert (
            APPROVAL_RANK[
                approval
            ]
            >=
            APPROVAL_RANK[
                minimum
            ]
        )

    print(
        "CAPABILITY_REGISTRY_OK"
    )

    return mapping


def load_profiles():
    paths = sorted(
        PROFILE_ROOT.glob(
            "*/profile.json"
        )
    )

    assert paths

    profiles = {}

    for path in paths:
        profile = load_json(
            path
        )

        profile_id = (
            profile[
                "profile_id"
            ]
        )

        assert (
            profile_id
            not in profiles
        )

        assert (
            profile[
                "default_deny"
            ]
            is True
        )

        assert (
            0
            <= profile[
                "max_tools_exposed"
            ]
            <= 20
        )

        required_policies = set(
            profile[
                "required_policies"
            ]
        )

        assert (
            "security-policy.md"
            in required_policies
        )

        assert (
            "tool-security-policy.md"
            in required_policies
        )

        profiles[
            profile_id
        ] = profile

    print(
        "TOOL_PROFILES_LOAD_OK"
    )

    return profiles


def check_profile_capabilities(
    capabilities,
    profiles,
):
    for profile in (
        profiles.values()
    ):
        allowed = (
            profile[
                "allowed_capabilities"
            ]
        )

        assert len(allowed) == len(
            set(allowed)
        )

        constraints = (
            profile[
                "runtime_constraints"
            ]
        )

        for capability_id in allowed:
            assert (
                capability_id
                in capabilities
            )

            capability = (
                capabilities[
                    capability_id
                ]
            )

            if capability[
                "network_access"
            ]:
                assert (
                    constraints[
                        "network_access"
                    ]
                    != "none"
                )

            if (
                capability[
                    "resource"
                ]
                == "workspace"
                and capability[
                    "access_class"
                ]
                == "write"
            ):
                assert (
                    constraints[
                        "workspace_write"
                    ]
                    is True
                )

            if (
                capability[
                    "access_class"
                ]
                == "execute"
            ):
                assert (
                    constraints[
                        "process_execute"
                    ]
                    is True
                )

            if (
                capability[
                    "access_class"
                ]
                == "privileged"
            ):
                assert (
                    constraints[
                        "privileged"
                    ]
                    is True
                )

    print(
        "TOOL_PROFILE_CAPABILITY_LINKS_OK"
    )


def check_reasoning(
    profiles,
):
    profile = profiles[
        "reasoning"
    ]

    assert (
        profile[
            "status"
        ]
        == "active"
    )

    assert (
        profile[
            "allowed_capabilities"
        ]
        == []
    )

    assert (
        profile[
            "max_tools_exposed"
        ]
        == 0
    )

    constraints = (
        profile[
            "runtime_constraints"
        ]
    )

    assert (
        constraints[
            "network_access"
        ]
        == "none"
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

    print(
        "REASONING_PROFILE_BOUNDARY_OK"
    )


def check_research_readonly(
    capabilities,
    profiles,
):
    profile = profiles[
        "research-readonly"
    ]

    constraints = (
        profile[
            "runtime_constraints"
        ]
    )

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

    for capability_id in (
        profile[
            "allowed_capabilities"
        ]
    ):
        capability = (
            capabilities[
                capability_id
            ]
        )

        assert (
            capability[
                "access_class"
            ]
            == "read"
        )

        assert (
            capability[
                "potential_external_side_effects"
            ]
            is False
        )

    print(
        "RESEARCH_READONLY_BOUNDARY_OK"
    )


def main():
    capabilities = (
        load_registry()
    )

    profiles = (
        load_profiles()
    )

    assert (
        "reasoning"
        in profiles
    )

    assert (
        "research-readonly"
        in profiles
    )

    check_profile_capabilities(
        capabilities,
        profiles,
    )

    check_reasoning(
        profiles
    )

    check_research_readonly(
        capabilities,
        profiles,
    )

    print()
    print(
        "TOOL_CAPABILITY_BOUNDARY_OK"
    )


if __name__ == "__main__":
    main()
