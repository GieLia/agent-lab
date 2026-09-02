import asyncio
import socket

from unittest.mock import patch

import httpx

from app.tools.executor import (
    ToolAuthorizationError,
    authorize_tool,
    execute_tool,
    list_authorized_tools,
)


def fake_public_dns(
    host,
    port,
    family,
    socktype,
    proto,
):

    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (
                "8.8.8.8",
                port,
            ),
        )
    ]


def expect_authorization_rejected(
    fn,
    *args,
    **kwargs,
):

    try:
        fn(
            *args,
            **kwargs,
        )

    except ToolAuthorizationError:
        return

    raise AssertionError(
        "Expected authorization rejection"
    )


def check_reasoning_zero_tools():

    tools = list_authorized_tools(
        "reasoning"
    )

    assert tools == ()

    expect_authorization_rejected(
        authorize_tool,
        "reasoning",
        "web.search",
    )

    expect_authorization_rejected(
        authorize_tool,
        "reasoning",
        "web.fetch",
    )

    print(
        "REASONING_EXECUTOR_ZERO_TOOLS_OK"
    )


def check_experimental_opt_in():

    expect_authorization_rejected(
        list_authorized_tools,
        "research-readonly",
    )

    tools = list_authorized_tools(
        "research-readonly",
        allow_experimental=True,
    )

    assert (
        len(tools)
        == 2
    )

    names = {
        tool.tool_name
        for tool
        in tools
    }

    assert names == {
        "web.search",
        "web.fetch",
    }

    print(
        "EXPERIMENTAL_OPT_IN_REQUIRED_OK"
    )


def check_binding_identity():

    search = authorize_tool(
        "research-readonly",
        "web.search",
        allow_experimental=True,
    )

    fetch = authorize_tool(
        "research-readonly",
        "web.fetch",
        allow_experimental=True,
    )

    assert (
        search.capability_id
        == "web.search"
    )

    assert (
        search.binding_id
        == "web.search.brave"
    )

    assert (
        search.callable_ref
        == "app.tools.web_search:search_web"
    )

    assert (
        fetch.capability_id
        == "web.fetch"
    )

    assert (
        fetch.binding_id
        == "web.fetch.guarded"
    )

    assert (
        fetch.callable_ref
        == "app.tools.web_fetch:fetch_web"
    )

    print(
        "EXECUTOR_BINDING_IDENTITY_OK"
    )


def check_unknown_tool():

    expect_authorization_rejected(
        authorize_tool,
        "research-readonly",
        "process.execute",
        allow_experimental=True,
    )

    expect_authorization_rejected(
        authorize_tool,
        "research-readonly",
        "system.shell",
        allow_experimental=True,
    )

    print(
        "UNBOUND_TOOLS_REJECTED_OK"
    )


def check_unknown_profile():

    expect_authorization_rejected(
        list_authorized_tools,
        "does-not-exist",
        allow_experimental=True,
    )

    expect_authorization_rejected(
        list_authorized_tools,
        "../reasoning",
        allow_experimental=True,
    )

    print(
        "UNKNOWN_PROFILE_REJECTED_OK"
    )


async def check_execution():

    async def handler(
        request,
    ):

        assert (
            request.headers.get(
                "x-subscription-token"
            )
            == "executor-test-key"
        )

        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title":
                                "Executor Result",
                            "url":
                                "https://example.com/result",
                            "description":
                                "Controlled result.",
                        }
                    ]
                }
            },
            request=request,
        )

    transport = httpx.MockTransport(
        handler
    )

    with patch(
        "app.tools.network_guard."
        "socket.getaddrinfo",
        side_effect=fake_public_dns,
    ):

        result = await execute_tool(
            "research-readonly",
            "web.search",
            {
                "query":
                    "executor contract",
                "count":
                    1,
                "api_key":
                    "executor-test-key",  # pragma: allowlist secret
                "_transport":
                    transport,
            },
            allow_experimental=True,
        )

    assert (
        result.tool_name
        == "web.search"
    )

    assert (
        result.capability_id
        == "web.search"
    )

    assert (
        result.binding_id
        == "web.search.brave"
    )

    assert (
        result.duration_ms
        >= 0
    )

    assert (
        result.value[
            "result_count"
        ]
        == 1
    )

    print(
        "AUTHORIZED_EXECUTION_OK"
    )


async def main():

    check_reasoning_zero_tools()
    check_experimental_opt_in()
    check_binding_identity()
    check_unknown_tool()
    check_unknown_profile()

    await check_execution()

    print()
    print(
        "TOOL_EXECUTOR_CONTRACT_OK"
    )


asyncio.run(
    main()
)
