import asyncio
import socket

from unittest.mock import patch

import httpx

from app.tools.network_guard import (
    NetworkGuardError,
)
from app.tools.web_fetch import (
    WebFetchError,
    fetch_web,
)
from app.tools.web_search import (
    search_web,
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


async def test_fetch():

    async def handler(
        request,
    ):

        if (
            request.url.path
            == "/start"
        ):
            return httpx.Response(
                302,
                headers={
                    "location":
                        "/final",
                },
                request=request,
            )

        return httpx.Response(
            200,
            headers={
                "content-type":
                    "text/html; charset=utf-8",
            },
            text="""
<html>
<head>
<title>Test Document</title>
<style>SECRET_STYLE</style>
<script>SECRET_SCRIPT</script>
</head>
<body>
<h1>Evidence</h1>
<p>Useful research content.</p>
</body>
</html>
""",
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
        result = await fetch_web(
            "https://example.com/start",
            _transport=transport,
        )

    assert (
        result[
            "final_url"
        ]
        == "https://example.com/final"
    )

    assert (
        result[
            "title"
        ]
        == "Test Document"
    )

    assert (
        "Useful research content."
        in result[
            "text"
        ]
    )

    assert (
        "SECRET_SCRIPT"
        not in result[
            "text"
        ]
    )

    assert (
        "SECRET_STYLE"
        not in result[
            "text"
        ]
    )

    assert (
        len(
            result[
                "text_sha256"
            ]
        )
        == 64
    )

    assert (
        result[
            "truncated"
        ]
        is False
    )

    print(
        "WEB_FETCH_NORMALIZATION_OK"
    )


async def test_private_redirect():

    async def handler(
        request,
    ):
        return httpx.Response(
            302,
            headers={
                "location":
                    "http://127.0.0.1/secret",
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
        try:
            await fetch_web(
                "https://example.com/start",
                _transport=transport,
            )

        except NetworkGuardError:
            pass

        else:
            raise AssertionError(
                "Redirect to private IP "
                "was not rejected"
            )

    print(
        "PRIVATE_REDIRECT_REJECTED_OK"
    )


async def test_oversized():

    async def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type":
                    "text/plain",
            },
            content=b"x" * 2048,
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
        try:
            await fetch_web(
                "https://example.com/large",
                max_bytes=100,
                _transport=transport,
            )

        except WebFetchError:
            pass

        else:
            raise AssertionError(
                "Oversized response "
                "was accepted"
            )

    print(
        "OVERSIZED_RESPONSE_REJECTED_OK"
    )


async def test_search():

    async def handler(
        request,
    ):

        assert (
            request.headers.get(
                "x-subscription-token"
            )
            == "unit-test-key"
        )

        assert (
            request.url.params.get(
                "q"
            )
            == "agent research"
        )

        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title":
                                "Result One",
                            "url":
                                "https://example.com/one",
                            "description":
                                "First result.",
                        },
                        {
                            "title":
                                "Result Two",
                            "url":
                                "https://example.org/two",
                            "description":
                                "Second result.",
                        },
                        {
                            "title":
                                "Unsafe",
                            "url":
                                "http://127.0.0.1/private",
                            "description":
                                "Must be dropped.",
                        },
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
        result = await search_web(
            "agent research",
            count=5,
            api_key="unit-test-key",  # pragma: allowlist secret
            _transport=transport,
        )

    assert (
        result[
            "provider"
        ]
        == "brave"
    )

    assert (
        result[
            "result_count"
        ]
        == 2
    )

    assert (
        result[
            "results"
        ][0][
            "rank"
        ]
        == 1
    )

    assert (
        result[
            "results"
        ][1][
            "rank"
        ]
        == 2
    )

    print(
        "WEB_SEARCH_CONTRACT_OK"
    )


async def main():

    await test_fetch()
    await test_private_redirect()
    await test_oversized()
    await test_search()

    print()
    print(
        "WEB_TOOL_CONTRACTS_OK"
    )




async def test_declared_oversized():

    async def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type":
                    "text/plain",
                "content-length":
                    "5000",
            },
            content=b"tiny",
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
        try:
            await fetch_web(
                "https://example.com/declared-large",
                max_bytes=100,
                _transport=transport,
            )

        except WebFetchError:
            pass

        else:
            raise AssertionError(
                "Oversized Content-Length "
                "was accepted"
            )

    print(
        "CONTENT_LENGTH_LIMIT_OK"
    )


async def test_unsupported_content_type():

    async def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type":
                    "application/octet-stream",
            },
            content=b"binary",
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
        try:
            await fetch_web(
                "https://example.com/binary",
                _transport=transport,
            )

        except WebFetchError:
            pass

        else:
            raise AssertionError(
                "Unsupported content type "
                "was accepted"
            )

    print(
        "UNSUPPORTED_CONTENT_TYPE_REJECTED_OK"
    )


async def test_redirect_limit():

    async def handler(
        request,
    ):
        return httpx.Response(
            302,
            headers={
                "location":
                    "/again",
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
        try:
            await fetch_web(
                "https://example.com/start",
                max_redirects=1,
                _transport=transport,
            )

        except WebFetchError:
            pass

        else:
            raise AssertionError(
                "Redirect limit "
                "was not enforced"
            )

    print(
        "REDIRECT_LIMIT_OK"
    )



async def final_main():

    await test_fetch()
    await test_private_redirect()
    await test_oversized()
    await test_search()

    await test_declared_oversized()
    await test_unsupported_content_type()
    await test_redirect_limit()

    print()
    print(
        "WEB_TOOL_HARDENING_CONTRACTS_OK"
    )


asyncio.run(
    final_main()
)
