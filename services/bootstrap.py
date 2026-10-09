"""Startup checks and first-run provisioning (DB table, search index)."""
import logging
import os

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient

from database.create_table import create_tables
from vectorstore.create_index import create_index

logger = logging.getLogger(__name__)

REQUIRED_ENV = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_CHAT_ENDPOINT",
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_SEARCH_INDEX_NAME",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DATABASE",
]


def missing_env_vars() -> list[str]:
    return [name for name in REQUIRED_ENV if not os.getenv(name)]


def ensure_search_index() -> None:
    """Create the index only if it does not exist (never alters an existing one)."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    try:
        client.get_index(index_name)
        logger.info("Search index '%s' found.", index_name)
    except ResourceNotFoundError:
        logger.info("Search index '%s' missing; creating.", index_name)
        create_index(endpoint=endpoint, api_key=api_key, index_name=index_name)


def bootstrap() -> None:
    """Best-effort provisioning. Failures are logged, not fatal, so the API
    still starts and /health/ready reports what is wrong."""
    missing = missing_env_vars()
    if missing:
        logger.warning("Missing environment variables: %s", ", ".join(missing))
        return
    for name, fn in (("database table", create_tables), ("search index", ensure_search_index)):
        try:
            fn()
        except Exception:  # noqa: BLE001
            logger.exception("Could not ensure %s at startup", name)
