import asyncio
import socket

from unittest.mock import patch

from app.tools.network_guard import (
    NetworkGuardError,
    resolve_public_url,
    validate_ip_address,
    validate_url_syntax,
)


def expect_rejected(
    fn,
    *args,
):

    try:
        fn(
            *args
        )

    except NetworkGuardError:
        return

    raise AssertionError(
        f"Expected rejection: "
        f"{args}"
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


def fake_mixed_dns(
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
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (
                "192.168.1.100",
                port,
            ),
        ),
    ]


async def main():

    assert (
        validate_ip_address(
            "8.8.8.8"
        )
        == "8.8.8.8"
    )

    blocked_ips = [
        "127.0.0.1",
        "0.0.0.0",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.100",
        "169.254.169.254",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fc00::1",
    ]

    for address in blocked_ips:
        expect_rejected(
            validate_ip_address,
            address,
        )

    print(
        "PRIVATE_SPECIAL_IPS_REJECTED_OK"
    )

    valid = validate_url_syntax(
        "https://example.com/path?q=1"
    )

    assert (
        valid[0]
        == "https"
    )

    assert (
        valid[1]
        == "example.com"
    )

    assert (
        valid[2]
        == 443
    )

    blocked_urls = [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "gopher://example.com/",
        "data:text/plain,test",
        "javascript:alert(1)",
        "http://localhost/",
        "http://server/",
        "http://example.local/",
        "http://example.internal/",
        "http://127.0.0.1/",
        "http://192.168.1.100/",
        "http://169.254.169.254/",
        "https://user:pass@example.com/",  # pragma: allowlist secret
        "https://example.com:8443/",
        "http://example.com:8080/",
    ]

    for url in blocked_urls:
        expect_rejected(
            validate_url_syntax,
            url,
        )

    print(
        "UNSAFE_URLS_REJECTED_OK"
    )

    with patch(
        "app.tools.network_guard."
        "socket.getaddrinfo",
        side_effect=fake_public_dns,
    ):
        target = await resolve_public_url(
            "https://example.com/test"
        )

        assert (
            target.resolved_ips
            == (
                "8.8.8.8",
            )
        )

    print(
        "PUBLIC_DNS_ACCEPTED_OK"
    )

    with patch(
        "app.tools.network_guard."
        "socket.getaddrinfo",
        side_effect=fake_mixed_dns,
    ):
        try:
            await resolve_public_url(
                "https://example.com/test"
            )

        except NetworkGuardError:
            pass

        else:
            raise AssertionError(
                "Mixed public/private DNS "
                "answer was accepted"
            )

    print(
        "DNS_PRIVATE_MIX_REJECTED_OK"
    )

    print()
    print(
        "WEB_NETWORK_GUARD_OK"
    )


asyncio.run(
    main()
)
