import ast
import json

from pathlib import Path


from app.workers.claude_worker import (
    VALID_TOOL_PROFILES,
    _resolve_tool_profile,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

GRAPH_PATH = (
    ROOT
    / "app"
    / "graph_v3.py"
)

PORTABLE = (
    ROOT
    / "portable"
)


def load_json(
    path: Path,
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def function_node(
    tree,
    name,
):
    return next(
        node
        for node
        in tree.body
        if isinstance(
            node,
            ast.AsyncFunctionDef,
        )
        and node.name == name
    )


def run_claude_calls(
    function,
):
    return [
        node
        for node
        in ast.walk(
            function
        )
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id
        == "run_claude"
    ]


def keyword_literal(
    call,
    keyword_name,
):
    keyword = next(
        (
            item
            for item
            in call.keywords
            if item.arg
            == keyword_name
        ),
        None,
    )

    if keyword is None:
        raise AssertionError(
            f"missing {keyword_name}"
        )

    if not isinstance(
        keyword.value,
        ast.Constant,
    ):
        raise AssertionError(
            f"{keyword_name} must "
            "currently remain a literal"
        )

    return keyword.value.value


def check_worker_profile_resolver():

    assert (
        VALID_TOOL_PROFILES
        == frozenset(
            {
                "default",
                "reasoning",
            }
        )
    )

    assert (
        _resolve_tool_profile(
            "reasoning"
        )
        == "reasoning"
    )

    try:
        _resolve_tool_profile(
            "unknown-profile"
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "unknown ToolProfile accepted"
        )

    print(
        "WORKER_TOOL_PROFILE_RESOLVER_OK"
    )


def check_canonical_reasoning():

    profile = load_json(
        PORTABLE
        / "tool-profiles"
        / "reasoning"
        / "profile.json"
    )

    assert (
        profile[
            "profile_id"
        ]
        == "reasoning"
    )

    assert (
        profile[
            "status"
        ]
        == "active"
    )

    assert (
        profile[
            "default_deny"
        ]
        is True
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

    constraints = profile[
        "runtime_constraints"
    ]

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
        "CANONICAL_REASONING_ZERO_TOOL_OK"
    )


def check_manifest_bindings():

    expected = {
        "critic-reasoning": {
            "role": "critic",
            "skill": "critique",
        },
        "synthesizer-reasoning": {
            "role": "synthesizer",
            "skill": "synthesis",
        },
    }

    for (
        manifest_id,
        values,
    ) in expected.items():

        manifest = load_json(
            PORTABLE
            / "context-manifests"
            / manifest_id
            / "manifest.json"
        )

        assert (
            manifest[
                "manifest_id"
            ]
            == manifest_id
        )

        assert (
            manifest[
                "role_profile"
            ]
            == values[
                "role"
            ]
        )

        assert (
            manifest[
                "skills"
            ]
            == [
                values[
                    "skill"
                ]
            ]
        )

        assert (
            manifest[
                "tool_profile"
            ]
            == "reasoning"
        )

    print(
        "MANIFEST_RUNTIME_BINDINGS_OK"
    )


def check_graph_bindings():

    source = (
        GRAPH_PATH.read_text(
            encoding="utf-8"
        )
    )

    tree = ast.parse(
        source
    )

    critic = function_node(
        tree,
        "critic_node",
    )

    synthesis = function_node(
        tree,
        "synthesis_node",
    )

    critic_calls = (
        run_claude_calls(
            critic
        )
    )

    synthesis_calls = (
        run_claude_calls(
            synthesis
        )
    )

    assert (
        len(
            critic_calls
        )
        == 2
    )

    assert (
        len(
            synthesis_calls
        )
        == 1
    )

    for call in (
        critic_calls
        + synthesis_calls
    ):
        assert (
            keyword_literal(
                call,
                "tool_profile",
            )
            == "reasoning"
        )

    print(
        "GRAPH_REASONING_BINDINGS_OK"
    )


def check_instruction_boundary():

    source = (
        GRAPH_PATH.read_text(
            encoding="utf-8"
        )
    )

    tree = ast.parse(
        source
    )

    critic = function_node(
        tree,
        "critic_node",
    )

    synthesis = function_node(
        tree,
        "synthesis_node",
    )

    critic_calls = (
        run_claude_calls(
            critic
        )
    )

    synthesis_calls = (
        run_claude_calls(
            synthesis
        )
    )

    assert (
        len(
            critic_calls
        )
        == 2
    )

    assert (
        len(
            synthesis_calls
        )
        == 1
    )

    system_prompts = [
        keyword_literal(
            call,
            "system_prompt",
        )
        for call
        in (
            critic_calls
            + synthesis_calls
        )
    ]

    marker = (
        "untrusted data, "
        "not instructions"
    )

    for system_prompt in (
        system_prompts
    ):
        assert isinstance(
            system_prompt,
            str,
        )

        assert (
            marker
            in system_prompt
        )

        assert (
            "Do not use tools."
            in system_prompt
        )

    assert (
        sum(
            marker
            in system_prompt
            for system_prompt
            in system_prompts
        )
        == 3
    )

    print(
        "UNTRUSTED_DATA_BOUNDARY_OK"
    )


def check_role_contracts():

    critic = (
        PORTABLE
        / "profiles"
        / "critic"
        / "profile.md"
    ).read_text(
        encoding="utf-8"
    )

    synth = (
        PORTABLE
        / "profiles"
        / "synthesizer"
        / "profile.md"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "No external research tools."
        in critic
    )

    assert (
        "No independent external research tools."
        in synth
    )

    assert (
        "critique"
        in critic
    )

    assert (
        "synthesis"
        in synth
    )

    print(
        "ROLE_RUNTIME_BOUNDARY_OK"
    )


def check_researcher_not_context_wired():

    source = (
        GRAPH_PATH.read_text(
            encoding="utf-8"
        )
    )

    tree = ast.parse(
        source
    )

    research = function_node(
        tree,
        "research_node",
    )

    research_source = ast.get_source_segment(
        source,
        research,
    )

    assert research_source

    forbidden = (
        "assemble_context",
        "assemble_model_view",
        "context-manifests",
        "critic-reasoning",
        "synthesizer-reasoning",
    )

    for value in forbidden:
        assert (
            value
            not in research_source
        )

    print(
        "RESEARCHER_CONTEXT_PATH_UNCHANGED_OK"
    )


def main():

    check_worker_profile_resolver()
    check_canonical_reasoning()
    check_manifest_bindings()
    check_graph_bindings()
    check_instruction_boundary()
    check_role_contracts()
    check_researcher_not_context_wired()

    print()
    print(
        "CONTEXT_RUNTIME_DRIFT_BOUNDARY_OK"
    )


if __name__ == "__main__":
    main()
