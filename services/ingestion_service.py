import os

from langchain_openai import AzureOpenAIEmbeddings

from ingestion.ingest_documents import ingest_document
from vectorstore.azure_ai_search import AzureAISearchVectorStore


def process_pdf(pdf_path: str) -> None:
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_EMBEDDING_VERSION")
    )

    vector_store = AzureAISearchVectorStore(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME")
    )

    ingest_document(
        pdf_path=pdf_path,
        embeddings=embeddings,
        vector_store=vector_store
    )