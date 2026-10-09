"""Shared, lazily-created Azure clients (one instance per process)."""
import os
from functools import lru_cache

from langchain_openai import AzureOpenAIEmbeddings
from openai import OpenAI

from llm.azure_openai import get_openai_client
from vectorstore.azure_ai_search import AzureAISearchVectorStore, Retriever


@lru_cache(maxsize=1)
def get_embeddings() -> AzureOpenAIEmbeddings:
    """Embedding model used for semantic chunking, indexing and chat queries."""
    return AzureOpenAIEmbeddings(
        azure_deployment=os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        ),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_EMBEDDING_VERSION", "2024-02-01"),
    )


@lru_cache(maxsize=1)
def get_vector_store() -> AzureAISearchVectorStore:
    """Azure AI Search vector store."""
    return AzureAISearchVectorStore(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
    )


def get_retriever() -> Retriever:
    """Retriever used by the KPI extractor."""
    return Retriever(get_vector_store().client)


@lru_cache(maxsize=1)
def get_chat_client() -> OpenAI:
    """GPT client used by the chat endpoint."""
    return get_openai_client()
