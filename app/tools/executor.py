import importlib
import inspect
import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PORTABLE = (
    ROOT
    / "portable"
)

TOOL_PROFILES_ROOT = (
    PORTABLE
    / "tool-profiles"
)

CAPABILITY_REGISTRY_PATH = (
    PORTABLE
    / "capabilities"
    / "registry.json"
)

BINDING_REGISTRY_PATH = (
    ROOT
    / "integrations"
    / "tool-bindings"
    / "registry.json"
)


PROFILE_ID_RE = re.compile(
    r"^[a-z][a-z0-9_-]*$"
)

APPROVAL_ORDER = {
    "none": 0,
    "runtime": 1,
    "human": 2,
}


class ToolAuthorizationError(
    RuntimeError
):
    pass


class ToolExecutionError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True
)
class AuthorizedTool:
    tool_name: str
    capability_id: str
    binding_id: str
    tool_kind: str
    callable_ref: str
    approval: str


@dataclass(
    frozen=True
)
class ToolExecutionResult:
    tool_name: str
    capability_id: str
    binding_id: str
    duration_ms: int
    value: Any


def _load_json(
    path: Path,
) -> dict[str, Any]:

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise ToolAuthorizationError(
            f"Unable to load runtime contract: "
            f"{path.name}"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise ToolAuthorizationError(
            f"Runtime contract is not an object: "
            f"{path.name}"
        )

    return data


def _safe_profile_path(
    profile_id: str,
) -> Path:

    if (
        not isinstance(
            profile_id,
            str,
        )
        or not PROFILE_ID_RE.fullmatch(
            profile_id
        )
    ):
        raise ToolAuthorizationError(
            "Invalid ToolProfile identifier"
        )

    root = TOOL_PROFILES_ROOT.resolve()

    path = (
        TOOL_PROFILES_ROOT
        / profile_id
        / "profile.json"
    ).resolve()

    try:
        path.relative_to(
            root
        )

    except ValueError as exc:
        raise ToolAuthorizationError(
            "ToolProfile path escaped "
            "portable root"
        ) from exc

    if not path.is_file():
        raise ToolAuthorizationError(
            "Unknown ToolProfile: "
            f"{profile_id}"
        )

    return path


def _load_profile(
    profile_id: str,
    *,
    allow_experimental: bool,
) -> dict[str, Any]:

    profile = _load_json(
        _safe_profile_path(
            profile_id
        )
    )

    if (
        profile.get(
            "profile_id"
        )
        != profile_id
    ):
        raise ToolAuthorizationError(
            "ToolProfile identity mismatch"
        )

    status = profile.get(
        "status"
    )

    if status == "active":
        pass

    elif (
        status == "experimental"
        and allow_experimental
    ):
        pass

    else:
        raise ToolAuthorizationError(
            "ToolProfile is not executable "
            f"in this runtime: {status}"
        )

    if (
        profile.get(
            "default_deny"
        )
        is not True
    ):
        raise ToolAuthorizationError(
            "ToolProfile must be default-deny"
        )

    allowed = profile.get(
        "allowed_capabilities"
    )

    if not isinstance(
        allowed,
        list,
    ):
        raise ToolAuthorizationError(
            "Invalid ToolProfile "
            "allowed_capabilities"
        )

    max_tools = profile.get(
        "max_tools_exposed"
    )

    if (
        not isinstance(
            max_tools,
            int,
        )
        or max_tools < 0
    ):
        raise ToolAuthorizationError(
            "Invalid max_tools_exposed"
        )

    return profile


def _load_capabilities() -> dict[
    str,
    dict[str, Any],
]:

    registry = _load_json(
        CAPABILITY_REGISTRY_PATH
    )

    raw = registry.get(
        "capabilities"
    )

    if not isinstance(
        raw,
        list,
    ):
        raise ToolAuthorizationError(
            "Invalid capability registry"
        )

    result = {}

    for capability in raw:

        if not isinstance(
            capability,
            dict,
        ):
            raise ToolAuthorizationError(
                "Invalid capability entry"
            )

        capability_id = (
            capability.get(
                "capability_id"
            )
        )

        if (
            not isinstance(
                capability_id,
                str,
            )
            or capability_id in result
        ):
            raise ToolAuthorizationError(
                "Invalid or duplicate "
                "capability_id"
            )

        result[
            capability_id
        ] = capability

    return result


def _load_bindings() -> list[
    dict[str, Any]
]:

    registry = _load_json(
        BINDING_REGISTRY_PATH
    )

    bindings = registry.get(
        "bindings"
    )

    if not isinstance(
        bindings,
        list,
    ):
        raise ToolAuthorizationError(
            "Invalid tool binding registry"
        )

    return bindings


def _binding_is_enabled(
    binding: dict[str, Any],
    *,
    allow_experimental: bool,
) -> bool:

    status = binding.get(
        "status"
    )

    if status == "active":
        return True

    if (
        status == "experimental"
        and allow_experimental
    ):
        return True

    return False


def _validate_approval(
    *,
    binding: dict[str, Any],
    capability: dict[str, Any],
):

    binding_approval = (
        binding.get(
            "approval"
        )
    )

    capability_approval = (
        capability.get(
            "default_approval"
        )
    )

    if (
        binding_approval
        not in APPROVAL_ORDER
        or capability_approval
        not in APPROVAL_ORDER
    ):
        raise ToolAuthorizationError(
            "Unknown approval class"
        )

    if (
        APPROVAL_ORDER[
            binding_approval
        ]
        <
        APPROVAL_ORDER[
            capability_approval
        ]
    ):
        raise ToolAuthorizationError(
            "Tool binding weakens "
            "capability approval floor"
        )

    # E4.5 executor v1 has no runtime/human
    # approval workflow yet.
    if binding_approval != "none":
        raise ToolAuthorizationError(
            "Tool requires an unsupported "
            "approval workflow"
        )


def _validate_python_binding(
    binding: dict[str, Any],
) -> str:

    if (
        binding.get(
            "tool_kind"
        )
        != "python"
    ):
        raise ToolAuthorizationError(
            "E4.5 executor v1 supports "
            "only Python tool bindings"
        )

    implementation = binding.get(
        "implementation"
    )

    if not isinstance(
        implementation,
        dict,
    ):
        raise ToolAuthorizationError(
            "Invalid binding implementation"
        )

    reference = implementation.get(
        "callable"
    )

    if (
        not isinstance(
            reference,
            str,
        )
        or reference.count(":") != 1
    ):
        raise ToolAuthorizationError(
            "Invalid Python callable reference"
        )

    module_name, function_name = (
        reference.split(
            ":",
            1,
        )
    )

    if not module_name.startswith(
        "app.tools."
    ):
        raise ToolAuthorizationError(
            "Python tool callable is outside "
            "the app.tools namespace"
        )

    if module_name == "app.tools.executor":
        raise ToolAuthorizationError(
            "Executor cannot bind itself"
        )

    if (
        not function_name
        or function_name.startswith(
            "_"
        )
    ):
        raise ToolAuthorizationError(
            "Invalid Python tool function"
        )

    return reference


def list_authorized_tools(
    profile_id: str,
    *,
    allow_experimental: bool = False,
) -> tuple[
    AuthorizedTool,
    ...,
]:

    profile = _load_profile(
        profile_id,
        allow_experimental=
            allow_experimental,
    )

    capabilities = (
        _load_capabilities()
    )

    bindings = (
        _load_bindings()
    )

    allowed_capabilities = set(
        profile[
            "allowed_capabilities"
        ]
    )

    authorized = []
    tool_names = set()

    for binding in bindings:

        if not isinstance(
            binding,
            dict,
        ):
            raise ToolAuthorizationError(
                "Invalid tool binding entry"
            )

        if not _binding_is_enabled(
            binding,
            allow_experimental=
                allow_experimental,
        ):
            continue

        capability_id = (
            binding.get(
                "capability_id"
            )
        )

        if (
            not isinstance(
                capability_id,
                str,
            )
            or not capability_id
        ):
            raise ToolAuthorizationError(
                "Invalid binding capability_id"
            )

        capability = (
            capabilities.get(
                capability_id
            )
        )

        # Enabled bindings may never reference
        # an unknown capability, even when the
        # selected ToolProfile would not authorize it.
        if capability is None:
            raise ToolAuthorizationError(
                "Binding references unknown "
                f"capability: {capability_id}"
            )

        # Binding existence never grants capability.
        if (
            capability_id
            not in allowed_capabilities
        ):
            continue

        _validate_approval(
            binding=binding,
            capability=capability,
        )

        callable_ref = (
            _validate_python_binding(
                binding
            )
        )

        tool_name = binding.get(
            "tool_name"
        )

        binding_id = binding.get(
            "binding_id"
        )

        if (
            not isinstance(
                tool_name,
                str,
            )
            or not tool_name
        ):
            raise ToolAuthorizationError(
                "Invalid tool_name"
            )

        # E4.5 v1 uses one canonical public tool
        # name per capability. This prevents a
        # registry mutation from relabelling one
        # authorized capability as another tool.
        if tool_name != capability_id:
            raise ToolAuthorizationError(
                "tool_name/capability_id "
                "identity mismatch"
            )

        if (
            not isinstance(
                binding_id,
                str,
            )
            or not binding_id
        ):
            raise ToolAuthorizationError(
                "Invalid binding_id"
            )

        if tool_name in tool_names:
            raise ToolAuthorizationError(
                "Duplicate authorized tool_name: "
                f"{tool_name}"
            )

        tool_names.add(
            tool_name
        )

        authorized.append(
            AuthorizedTool(
                tool_name=tool_name,
                capability_id=
                    capability_id,
                binding_id=
                    binding_id,
                tool_kind="python",
                callable_ref=
                    callable_ref,
                approval=
                    binding[
                        "approval"
                    ],
            )
        )

    max_tools = profile[
        "max_tools_exposed"
    ]

    if (
        len(authorized)
        > max_tools
    ):
        raise ToolAuthorizationError(
            "Authorized tool count exceeds "
            "ToolProfile max_tools_exposed"
        )

    return tuple(
        sorted(
            authorized,
            key=lambda item:
                item.tool_name,
        )
    )


def authorize_tool(
    profile_id: str,
    tool_name: str,
    *,
    allow_experimental: bool = False,
) -> AuthorizedTool:

    if (
        not isinstance(
            tool_name,
            str,
        )
        or not tool_name
    ):
        raise ToolAuthorizationError(
            "Invalid requested tool name"
        )

    tools = list_authorized_tools(
        profile_id,
        allow_experimental=
            allow_experimental,
    )

    for tool in tools:

        if (
            tool.tool_name
            == tool_name
        ):
            return tool

    raise ToolAuthorizationError(
        "Tool is not authorized by "
        f"ToolProfile '{profile_id}': "
        f"{tool_name}"
    )


def _resolve_callable(
    reference: str,
):

    module_name, function_name = (
        reference.split(
            ":",
            1,
        )
    )

    try:
        module = importlib.import_module(
            module_name
        )

    except Exception as exc:
        raise ToolAuthorizationError(
            "Unable to import authorized "
            "tool module"
        ) from exc

    function = getattr(
        module,
        function_name,
        None,
    )

    if not callable(
        function
    ):
        raise ToolAuthorizationError(
            "Authorized tool callable "
            "does not exist"
        )

    if not inspect.iscoroutinefunction(
        function
    ):
        raise ToolAuthorizationError(
            "Authorized tool callable "
            "must be async"
        )

    return function


async def execute_tool(
    profile_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    allow_experimental: bool = False,
) -> ToolExecutionResult:

    if not isinstance(
        arguments,
        dict,
    ):
        raise ToolExecutionError(
            "Tool arguments must "
            "be an object"
        )

    tool = authorize_tool(
        profile_id,
        tool_name,
        allow_experimental=
            allow_experimental,
    )

    function = _resolve_callable(
        tool.callable_ref
    )

    started = time.monotonic()

    try:
        value = await function(
            **arguments
        )

    except Exception as exc:
        raise ToolExecutionError(
            "Authorized tool execution failed: "
            f"{tool_name}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    duration_ms = max(
        0,
        int(
            (
                time.monotonic()
                - started
            )
            * 1000
        ),
    )

    return ToolExecutionResult(
        tool_name=
            tool.tool_name,
        capability_id=
            tool.capability_id,
        binding_id=
            tool.binding_id,
        duration_ms=
            duration_ms,
        value=value,
    )
