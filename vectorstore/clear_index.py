import os

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

load_dotenv()


def clear_index() -> None:
    client = SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))
    )

    results = client.search(
        search_text="*",
        select=["id"],
        top=1000
    )

    documents = [{"id": result["id"]} for result in results]

    if not documents:
        print("Index is already empty.")
        return

    client.delete_documents(documents=documents)

    print(f"Deleted {len(documents)} documents.")


if __name__ == "__main__":
    clear_index()