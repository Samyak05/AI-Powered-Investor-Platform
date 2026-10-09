"""Startup checks and first-run provisioning (DB table, search index)."""
import logging
import os

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient

from database.create_table import create_tables
from vectorstore.create_index import create_index

logger = logging.getLogger(__name__)

# Required Azure services configuration.
REQUIRED_AZURE_ENV = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_CHAT_ENDPOINT",
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_SEARCH_INDEX_NAME",
]


def database_is_configured() -> bool:
    """Accept either a SQLAlchemy URL or the existing local PostgreSQL settings."""
    database_url = os.getenv("DATABASE_URL")

    if database_url and database_url.strip():
        return True

    local_database_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_DATABASE",
    ]

    return all(os.getenv(name) for name in local_database_vars)


def missing_env_vars() -> list[str]:
    """Return missing configuration without requiring unused local DB settings."""
    missing = [
        name
        for name in REQUIRED_AZURE_ENV
        if not os.getenv(name)
    ]

    if not database_is_configured():
        missing.append(
            "DATABASE_URL (Neon) or "
            "POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_DATABASE"
        )

    return missing


def ensure_search_index() -> None:
    """Create the search index if missing; never modify an existing index."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

    if not endpoint or not api_key or not index_name:
        raise ValueError(
            "Azure AI Search requires AZURE_SEARCH_ENDPOINT, "
            "AZURE_SEARCH_API_KEY, and AZURE_SEARCH_INDEX_NAME."
        )

    client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )

    try:
        client.get_index(index_name)
        logger.info("Search index '%s' found.", index_name)

    except ResourceNotFoundError:
        logger.info("Search index '%s' missing; creating.", index_name)

        create_index(
            endpoint=endpoint,
            api_key=api_key,
            index_name=index_name,
        )


def bootstrap() -> None:
    """
    Best-effort startup provisioning.

    Failures are logged rather than preventing the API from starting.
    Readiness checks should report whether required services are usable.
    """
    missing = missing_env_vars()

    if missing:
        logger.warning(
            "Bootstrap skipped because configuration is missing: %s",
            ", ".join(missing),
        )
        return

    tasks = [
        ("database tables", create_tables),
        ("Azure AI Search index", ensure_search_index),
    ]

    for name, fn in tasks:
        try:
            fn()
            logger.info("Bootstrap check completed for %s.", name)

        except Exception:
            logger.exception("Could not ensure %s at startup.", name)