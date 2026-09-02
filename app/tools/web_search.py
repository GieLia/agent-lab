import os
import re

from typing import Any

import httpx

from .network_guard import (
    NetworkGuardError,
    resolve_public_url,
    validate_url_syntax,
)


BRAVE_SEARCH_ENDPOINT = (
    "https://api.search.brave.com/"
    "res/v1/web/search"
)

DEFAULT_TIMEOUT_SECONDS = 15.0

MAX_RESPONSE_BYTES = (
    2 * 1024 * 1024
)


class WebSearchError(
    RuntimeError
):
    pass


def _validate_query(
    query: str,
):

    if not isinstance(
        query,
        str,
    ):
        raise WebSearchError(
            "Search query must "
            "be a string"
        )

    query = query.strip()

    if not query:
        raise WebSearchError(
            "Search query is empty"
        )

    if len(query) > 400:
        raise WebSearchError(
            "Search query exceeds "
            "400 characters"
        )

    if len(
        query.split()
    ) > 50:
        raise WebSearchError(
            "Search query exceeds "
            "50 words"
        )


def _validate_language(
    value: str,
    field: str,
):

    if not re.fullmatch(
        r"[A-Za-z0-9-]{2,16}",
        value,
    ):
        raise WebSearchError(
            f"Invalid {field}"
        )


async def search_web(
    query: str,
    *,
    count: int = 5,
    country: str | None = None,
    search_lang: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:

    _validate_query(
        query
    )

    if not (
        1 <= count <= 10
    ):
        raise WebSearchError(
            "count must be between 1 and 10"
        )

    if country is not None:
        if not re.fullmatch(
            r"[A-Za-z]{2}",
            country,
        ):
            raise WebSearchError(
                "country must be a "
                "2-letter code"
            )

        country = (
            country.upper()
        )

    if search_lang is not None:
        _validate_language(
            search_lang,
            "search_lang",
        )

    if api_key is None:
        api_key = os.getenv(
            "BRAVE_SEARCH_API_KEY"
        )

    if not api_key:
        raise WebSearchError(
            "BRAVE_SEARCH_API_KEY "
            "is not configured"
        )

    # Provider endpoint itself is also
    # subject to the public-network guard.
    await resolve_public_url(
        BRAVE_SEARCH_ENDPOINT
    )

    params = {
        "q":
            query.strip(),
        "count":
            count,
    }

    if country is not None:
        params[
            "country"
        ] = country

    if search_lang is not None:
        params[
            "search_lang"
        ] = search_lang

    headers = {
        "Accept":
            "application/json",
        "Accept-Encoding":
            "gzip",
        "X-Subscription-Token":
            api_key,
        "User-Agent":
            "AgentLabResearch/0.1",
    }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            timeout_seconds
        ),
        follow_redirects=False,
        transport=_transport,
    ) as client:

        try:
            response = await client.get(
                BRAVE_SEARCH_ENDPOINT,
                params=params,
                headers=headers,
            )

        except httpx.HTTPError as exc:
            raise WebSearchError(
                "Brave Search HTTP "
                "request failed"
            ) from exc

    if (
        len(
            response.content
        )
        > MAX_RESPONSE_BYTES
    ):
        raise WebSearchError(
            "Brave Search response "
            "exceeds maximum size"
        )

    if response.status_code != 200:
        raise WebSearchError(
            "Brave Search returned "
            f"HTTP {response.status_code}"
        )

    try:
        payload = response.json()

    except ValueError as exc:
        raise WebSearchError(
            "Brave Search returned "
            "invalid JSON"
        ) from exc

    web = payload.get(
        "web"
    )

    if not isinstance(
        web,
        dict,
    ):
        raw_results = []

    else:
        raw_results = (
            web.get(
                "results"
            )
            or []
        )

    results = []

    for item in raw_results:

        if not isinstance(
            item,
            dict,
        ):
            continue

        url = item.get(
            "url"
        )

        title = item.get(
            "title"
        )

        description = (
            item.get(
                "description"
            )
            or ""
        )

        if not (
            isinstance(
                url,
                str,
            )
            and isinstance(
                title,
                str,
            )
        ):
            continue

        # Search result is syntax-validated here.
        # Full DNS/public-address validation occurs
        # when web.fetch is invoked.
        try:
            validate_url_syntax(
                url
            )

        except NetworkGuardError:
            continue

        results.append(
            {
                "rank":
                    len(results) + 1,
                "title":
                    title.strip(),
                "url":
                    url,
                "snippet":
                    str(
                        description
                    ).strip(),
            }
        )

        if (
            len(results)
            >= count
        ):
            break

    return {
        "provider":
            "brave",
        "query":
            query.strip(),
        "result_count":
            len(results),
        "results":
            results,
    }
