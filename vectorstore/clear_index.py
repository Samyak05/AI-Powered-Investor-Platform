
import os

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

load_dotenv()


def clear_index() -> None:
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")

    if not all([endpoint, index_name, api_key]):
        raise ValueError(
            "Missing Azure AI Search configuration in .env"
        )

    confirm = input(
        f"Delete ALL documents from index '{index_name}'? "
        "Type DELETE to confirm: "
    )

    if confirm != "DELETE":
        print("Cancelled. No documents were deleted.")
        return

    client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(api_key),
    )

    total_deleted = 0

    while True:
        results = list(
            client.search(
                search_text="*",
                select=["id"],
                top=1000,
            )
        )

        if not results:
            break

        documents = [{"id": result["id"]} for result in results]
        response = client.delete_documents(documents=documents)

        deleted = sum(item.succeeded for item in response)
        total_deleted += deleted

        print(f"Deleted {deleted} documents.")

        # Avoid an infinite loop if deletion fails.
        if deleted == 0:
            raise RuntimeError(
                "No documents were deleted in this batch. "
                "Check the index key field and permissions."
            )

    print(f"Finished. Deleted {total_deleted} documents.")


if __name__ == "__main__":
    clear_index()
