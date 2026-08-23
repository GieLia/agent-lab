from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values


ENV_FILE = Path("/opt/agent-lab/app/.env")


def get_db_uri() -> str:
    config = dotenv_values(ENV_FILE)

    password = config.get(
        "AGENT_DB_PASSWORD"
    )

    if not password:
        raise RuntimeError(
            "AGENT_DB_PASSWORD is missing"
        )

    host = str(
        config.get(
            "AGENT_DB_HOST",
            "127.0.0.1",
        )
    )

    port = str(
        config.get(
            "AGENT_DB_PORT",
            "5432",
        )
    )

    database = str(
        config.get(
            "AGENT_DB_NAME",
            "agentlab",
        )
    )

    user = str(
        config.get(
            "AGENT_DB_USER",
            "agentlab",
        )
    )

    user_encoded = quote(
        user,
        safe="",
    )

    password_encoded = quote(
        str(password),
        safe="",
    )

    database_encoded = quote(
        database,
        safe="",
    )

    return (
        "postgresql://"
        f"{user_encoded}:"
        f"{password_encoded}"
        f"@{host}:"
        f"{port}/"
        f"{database_encoded}"
    )
