import asyncio
import ipaddress
import socket

from dataclasses import dataclass
from urllib.parse import urlsplit


ALLOWED_SCHEMES = frozenset(
    {
        "http",
        "https",
    }
)

BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".home.arpa",
)

MAX_URL_LENGTH = 8192


class NetworkGuardError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class ValidatedTarget:
    url: str
    scheme: str
    host: str
    port: int
    resolved_ips: tuple[str, ...]


def validate_ip_address(
    value: str,
) -> str:

    try:
        address = ipaddress.ip_address(
            value
        )

    except ValueError as exc:
        raise NetworkGuardError(
            f"Invalid IP address: {value}"
        ) from exc

    blocked = (
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )

    if blocked:
        raise NetworkGuardError(
            "Non-public network address "
            f"is not allowed: {address}"
        )

    return address.compressed


def validate_url_syntax(
    url: str,
) -> tuple[
    str,
    str,
    int,
]:

    if not isinstance(
        url,
        str,
    ):
        raise NetworkGuardError(
            "URL must be a string"
        )

    if not url:
        raise NetworkGuardError(
            "URL is empty"
        )

    if url != url.strip():
        raise NetworkGuardError(
            "URL contains leading or "
            "trailing whitespace"
        )

    if len(url) > MAX_URL_LENGTH:
        raise NetworkGuardError(
            "URL exceeds maximum length"
        )

    try:
        parts = urlsplit(
            url
        )

    except ValueError as exc:
        raise NetworkGuardError(
            "Malformed URL"
        ) from exc

    scheme = (
        parts.scheme
        .lower()
    )

    if (
        scheme
        not in ALLOWED_SCHEMES
    ):
        raise NetworkGuardError(
            "Only http and https "
            "URLs are allowed"
        )

    if (
        parts.username is not None
        or parts.password is not None
    ):
        raise NetworkGuardError(
            "Credentials in URLs "
            "are not allowed"
        )

    host = parts.hostname

    if not host:
        raise NetworkGuardError(
            "URL has no hostname"
        )

    host = (
        host
        .rstrip(".")
        .lower()
    )

    if (
        host == "localhost"
        or any(
            host.endswith(
                suffix
            )
            for suffix
            in BLOCKED_HOST_SUFFIXES
        )
    ):
        raise NetworkGuardError(
            "Local/internal hostname "
            "is not allowed"
        )

    # Single-label DNS names are treated as
    # potentially local/intranet names.
    if (
        "." not in host
        and ":" not in host
    ):
        try:
            ipaddress.ip_address(
                host
            )

        except ValueError:
            raise NetworkGuardError(
                "Single-label hostnames "
                "are not allowed"
            )

    try:
        port = parts.port

    except ValueError as exc:
        raise NetworkGuardError(
            "Invalid URL port"
        ) from exc

    default_port = (
        443
        if scheme == "https"
        else 80
    )

    if (
        port is not None
        and port != default_port
    ):
        raise NetworkGuardError(
            "Non-default network ports "
            "are not allowed"
        )

    port = (
        port
        if port is not None
        else default_port
    )

    # Fail immediately for literal IP URLs.
    try:
        literal = ipaddress.ip_address(
            host
        )

    except ValueError:
        literal = None

    if literal is not None:
        validate_ip_address(
            literal.compressed
        )

    return (
        scheme,
        host,
        port,
    )


async def resolve_public_url(
    url: str,
) -> ValidatedTarget:

    (
        scheme,
        host,
        port,
    ) = validate_url_syntax(
        url
    )

    try:
        literal = ipaddress.ip_address(
            host
        )

    except ValueError:
        literal = None

    if literal is not None:
        resolved = (
            validate_ip_address(
                literal.compressed
            ),
        )

        return ValidatedTarget(
            url=url,
            scheme=scheme,
            host=host,
            port=port,
            resolved_ips=resolved,
        )

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            host,
            port,
            0,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
        )

    except OSError as exc:
        raise NetworkGuardError(
            "DNS resolution failed "
            f"for {host}"
        ) from exc

    addresses = set()

    for info in infos:
        sockaddr = info[4]

        if not sockaddr:
            continue

        addresses.add(
            str(
                sockaddr[0]
            )
        )

    if not addresses:
        raise NetworkGuardError(
            "DNS returned no addresses "
            f"for {host}"
        )

    validated = []

    # Security rule:
    # every returned address must be public.
    # A mixed public/private DNS answer fails closed.
    for address in sorted(
        addresses
    ):
        validated.append(
            validate_ip_address(
                address
            )
        )

    return ValidatedTarget(
        url=url,
        scheme=scheme,
        host=host,
        port=port,
        resolved_ips=tuple(
            validated
        ),
    )
