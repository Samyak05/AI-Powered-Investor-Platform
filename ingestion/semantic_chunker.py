from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import AzureOpenAIEmbeddings

load_dotenv()


def read_markdown(markdown_file: str) -> str:
    """Read markdown content from disk."""
    return Path(markdown_file).read_text(encoding="utf-8")


def chunk_markdown(markdown_file: str, embeddings) -> list[Document]:
    """Generate semantic chunks from markdown."""
    markdown_content = read_markdown(markdown_file)

    splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile"
    )

    return splitter.create_documents([markdown_content])


if __name__ == "__main__":
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_EMBEDDING_VERSION", "2024-02-01")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    if not endpoint or not api_key:
        raise RuntimeError(
            "Missing Azure OpenAI credentials. "
            "Set AZURE_OPENAI_ENDPOINT and "
            "AZURE_OPENAI_API_KEY in .env."
        )

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=embedding_deployment,
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    repo_root = Path(__file__).resolve().parents[1]
    markdown_file = repo_root / "data" / "markdown" / "2024_Apple.md"

    chunks = chunk_markdown(
        markdown_file=str(markdown_file),
        embeddings=embeddings
    )

    print(f"Generated {len(chunks)} chunks\n")

    for index, chunk in enumerate(chunks[:3]):
        print("=" * 80)
        print(f"Chunk {index + 1}")
        print("=" * 80)
        print(chunk.page_content[:1000])
        print()