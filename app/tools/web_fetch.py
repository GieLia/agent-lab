import hashlib
import re

from datetime import (
    datetime,
    timezone,
)
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx

from .network_guard import (
    NetworkGuardError,
    resolve_public_url,
    validate_ip_address,
)


DEFAULT_MAX_BYTES = (
    2 * 1024 * 1024
)

DEFAULT_MAX_TEXT_CHARS = (
    200_000
)

DEFAULT_MAX_REDIRECTS = 4

DEFAULT_TIMEOUT_SECONDS = 15.0


ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "text/plain",
        "application/xhtml+xml",
    }
)

REDIRECT_CODES = frozenset(
    {
        301,
        302,
        303,
        307,
        308,
    }
)


class WebFetchError(
    RuntimeError
):
    pass


class _HTMLExtractor(
    HTMLParser
):

    BLOCK_TAGS = frozenset(
        {
            "address",
            "article",
            "aside",
            "blockquote",
            "br",
            "div",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "li",
            "main",
            "nav",
            "p",
            "section",
            "table",
            "td",
            "th",
            "tr",
        }
    )

    SKIP_TAGS = frozenset(
        {
            "script",
            "style",
            "noscript",
            "svg",
            "canvas",
        }
    )

    def __init__(
        self,
    ):
        super().__init__(
            convert_charrefs=True
        )

        self.parts = []
        self.title_parts = []

        self.skip_depth = 0
        self.in_title = False

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return

        if self.skip_depth:
            return

        if tag == "title":
            self.in_title = True

        if tag in self.BLOCK_TAGS:
            self.parts.append(
                "\n"
            )

    def handle_endtag(
        self,
        tag,
    ):

        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return

        if self.skip_depth:
            return

        if tag == "title":
            self.in_title = False

        if tag in self.BLOCK_TAGS:
            self.parts.append(
                "\n"
            )

    def handle_data(
        self,
        data,
    ):

        if self.skip_depth:
            return

        if self.in_title:
            self.title_parts.append(
                data
            )

        self.parts.append(
            data
        )


def _normalize_text(
    text: str,
) -> str:

    lines = []

    for raw_line in (
        text.splitlines()
    ):
        line = re.sub(
            r"\s+",
            " ",
            raw_line,
        ).strip()

        if line:
            lines.append(
                line
            )

    return "\n".join(
        lines
    )


def extract_document_text(
    body: str,
    content_type: str,
) -> tuple[
    str | None,
    str,
]:

    if (
        content_type
        in {
            "text/html",
            "application/xhtml+xml",
        }
    ):
        parser = _HTMLExtractor()

        try:
            parser.feed(
                body
            )
            parser.close()

        except Exception as exc:
            raise WebFetchError(
                "HTML parsing failed"
            ) from exc

        title = _normalize_text(
            " ".join(
                parser.title_parts
            )
        )

        text = _normalize_text(
            "".join(
                parser.parts
            )
        )

        return (
            title or None,
            text,
        )

    return (
        None,
        _normalize_text(
            body
        ),
    )


def _validate_peer(
    response: httpx.Response,
    *,
    required: bool = False,
):

    stream = response.extensions.get(
        "network_stream"
    )

    if stream is None:
        if required:
            raise WebFetchError(
                "Unable to verify peer "
                "network address"
            )

        return

    try:
        peer = stream.get_extra_info(
            "server_addr"
        )

    except Exception as exc:
        if required:
            raise WebFetchError(
                "Unable to read peer "
                "network address"
            ) from exc

        return

    if not peer:
        if required:
            raise WebFetchError(
                "Peer network address "
                "is unavailable"
            )

        return

    if isinstance(
        peer,
        tuple,
    ):
        address = peer[0]
    else:
        address = peer

    validate_ip_address(
        str(
            address
        )
    )


async def fetch_web(
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:

    if max_bytes < 1:
        raise WebFetchError(
            "max_bytes must be positive"
        )

    if max_text_chars < 1:
        raise WebFetchError(
            "max_text_chars must be positive"
        )

    if not (
        0 <= max_redirects <= 10
    ):
        raise WebFetchError(
            "max_redirects out of range"
        )

    timeout = httpx.Timeout(
        timeout_seconds
    )

    headers = {
        "User-Agent":
            "AgentLabResearch/0.1",
        "Accept":
            "text/html,"
            "application/xhtml+xml,"
            "text/plain;q=0.9",
    }

    current_url = url

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers=headers,
        transport=_transport,
    ) as client:

        for redirect_index in range(
            max_redirects + 1
        ):

            # Every request and every redirect target
            # is revalidated.
            await resolve_public_url(
                current_url
            )

            try:
                async with client.stream(
                    "GET",
                    current_url,
                ) as response:

                    _validate_peer(
                        response,
                        required=(
                            _transport
                            is None
                        ),
                    )

                    if (
                        response.status_code
                        in REDIRECT_CODES
                    ):
                        location = (
                            response.headers.get(
                                "location"
                            )
                        )

                        if not location:
                            raise WebFetchError(
                                "Redirect response "
                                "has no Location header"
                            )

                        if (
                            redirect_index
                            >= max_redirects
                        ):
                            raise WebFetchError(
                                "Maximum redirects "
                                "exceeded"
                            )

                        current_url = urljoin(
                            str(
                                response.url
                            ),
                            location,
                        )

                        continue

                    if not (
                        200
                        <= response.status_code
                        < 300
                    ):
                        raise WebFetchError(
                            "HTTP fetch failed "
                            f"with status "
                            f"{response.status_code}"
                        )

                    content_length = (
                        response.headers.get(
                            "content-length"
                        )
                    )

                    if content_length is not None:
                        try:
                            declared_length = int(
                                content_length
                            )

                        except ValueError as exc:
                            raise WebFetchError(
                                "Invalid Content-Length"
                            ) from exc

                        if declared_length < 0:
                            raise WebFetchError(
                                "Negative Content-Length"
                            )

                        if declared_length > max_bytes:
                            raise WebFetchError(
                                "Declared response size "
                                "exceeds maximum byte size"
                            )

                    content_type = (
                        response.headers.get(
                            "content-type",
                            "",
                        )
                        .split(
                            ";",
                            1,
                        )[0]
                        .strip()
                        .lower()
                    )

                    if (
                        content_type
                        not in ALLOWED_CONTENT_TYPES
                    ):
                        raise WebFetchError(
                            "Unsupported content type: "
                            f"{content_type or '<missing>'}"
                        )

                    chunks = []
                    total = 0

                    async for chunk in (
                        response.aiter_bytes()
                    ):
                        total += len(
                            chunk
                        )

                        if total > max_bytes:
                            raise WebFetchError(
                                "Response exceeds "
                                "maximum byte size"
                            )

                        chunks.append(
                            chunk
                        )

                    body_bytes = b"".join(
                        chunks
                    )

                    encoding = (
                        response.encoding
                        or "utf-8"
                    )

                    try:
                        body = (
                            body_bytes.decode(
                                encoding,
                                errors="replace",
                            )
                        )

                    except LookupError:
                        body = (
                            body_bytes.decode(
                                "utf-8",
                                errors="replace",
                            )
                        )

                    (
                        title,
                        text,
                    ) = extract_document_text(
                        body,
                        content_type,
                    )

                    if not text:
                        raise WebFetchError(
                            "Fetched document "
                            "contains no usable text"
                        )

                    truncated = False

                    if (
                        len(text)
                        > max_text_chars
                    ):
                        text = text[
                            :max_text_chars
                        ]

                        truncated = True

                    digest = hashlib.sha256(
                        text.encode(
                            "utf-8"
                        )
                    ).hexdigest()

                    return {
                        "requested_url":
                            url,
                        "final_url":
                            str(
                                response.url
                            ),
                        "status_code":
                            response.status_code,
                        "content_type":
                            content_type,
                        "title":
                            title,
                        "text":
                            text,
                        "text_sha256":
                            digest,
                        "fetched_at":
                            datetime.now(
                                timezone.utc
                            ).isoformat(),
                        "byte_count":
                            total,
                        "text_char_count":
                            len(text),
                        "truncated":
                            truncated,
                    }

            except httpx.HTTPError as exc:
                raise WebFetchError(
                    "HTTP fetch request failed"
                ) from exc

    raise WebFetchError(
        "Fetch did not produce a response"
    )
