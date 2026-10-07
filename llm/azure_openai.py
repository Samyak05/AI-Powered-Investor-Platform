import os

from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


def get_openai_client() -> OpenAI:
    """
    Create Azure OpenAI client.

    Returns:
        Azure OpenAI client.
    """
    return OpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=os.getenv("AZURE_OPENAI_CHAT_ENDPOINT")
    )


def get_structured_completion(
    prompt: str,
    response_model: type[BaseModel],
    model: str | None = None
) -> BaseModel:
    """
    Generate structured output using Azure OpenAI Responses API..

    Args:
        prompt: Input prompt.
        response_model: Pydantic response model.
        model: Azure OpenAI deployment name.

    Returns:
        Parsed Pydantic response model.
    """
    # Read deployment name from environment when not provided; do not fallback to a hardcoded name
    model = model or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")


    if not model:
        raise RuntimeError(
            "Missing AZURE_OPENAI_CHAT_DEPLOYMENT in .env"
        )

    client = get_openai_client()

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": "You are an expert financial analyst."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        text_format=response_model
    )

    parsed = response.output_parsed

    print("[debug] Structured parsed output:", parsed)

    return parsed