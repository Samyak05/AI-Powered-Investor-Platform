"""RAG chat: Query -> Azure AI Search (hybrid) -> GPT -> grounded answer."""
from __future__ import annotations

import logging
import os

from azure.search.documents.models import VectorizedQuery

from services import clients

logger = logging.getLogger(__name__)

TOP_K = int(os.getenv("CHAT_TOP_K", "8"))
MAX_CHUNK_CHARS = 3500
MAX_HISTORY_MESSAGES = 6
NO_CONTEXT_ANSWER = (
    "I couldn't find anything relevant in the ingested reports. "
    "Try rephrasing, or upload the report first."
)

SYSTEM_PROMPT = """You are an expert financial analyst assistant for an Investor Intelligence Platform.
Answer the question using ONLY the numbered excerpts from annual reports provided in the context.
- If the excerpts do not contain the answer, say you could not find it in the ingested reports. Do not guess.
- Quote financial figures exactly as written in the report, including units and currency.
- Cite the excerpts you used like [1], [2].
- Be concise; use short bullets when it helps."""


def _odata(value: str) -> str:
    """Escape single quotes in Azure AI Search OData string literals."""
    return value.replace("'", "''")


def doc_filter(company: str, year: str) -> str:
    """Build an Azure AI Search filter for a company and financial year."""
    return (
        f"company eq '{_odata(company)}' "
        f"and year eq '{_odata(year)}'"
    )



def _build_filter(company: str | None, year: str | None) -> str | None:
    if company and year:
        return doc_filter(company, year)
    if company:
        return f"company eq '{_odata(company)}'"
    if year:
        return f"year eq '{_odata(year)}'"
    return None


def retrieve(question: str, company: str | None, year: str | None) -> list[dict]:
    """Hybrid (keyword + vector) search over the indexed chunks."""
    vector = clients.get_embeddings().embed_query(question)
    results = clients.get_vector_store().client.search(
        search_text=question,
        vector_queries=[
            VectorizedQuery(
                vector=vector, k_nearest_neighbors=TOP_K, fields="content_vector"
            )
        ],
        filter=_build_filter(company, year),
        top=TOP_K,
        select=["content", "company", "year", "source_file"],
    )
    return [
        {
            "content": (r.get("content") or "")[:MAX_CHUNK_CHARS],
            "company": r.get("company"),
            "year": r.get("year"),
            "source_file": r.get("source_file"),
            "score": r.get("@search.score"),
        }
        for r in results
    ]


def _complete(messages: list[dict]) -> str:
    """Single GPT call (isolated so tests can stub it)."""
    model = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not model:
        raise RuntimeError("Missing AZURE_OPENAI_CHAT_DEPLOYMENT in .env")
    response = clients.get_chat_client().responses.create(model=model, input=messages)
    return response.output_text


def answer_question(
    question: str,
    company: str | None = None,
    year: str | None = None,
    history: list[dict] | None = None,
) -> dict:
    docs = retrieve(question, company, year)
    if not docs:
        return {"answer": NO_CONTEXT_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[{i}] {d['company']} FY{d['year']} ({d['source_file']})\n{d['content']}"
        for i, d in enumerate(docs, start=1)
    )
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-MAX_HISTORY_MESSAGES:]:
        if turn.get("role") in ("user", "assistant"):
            messages.append({"role": turn["role"], "content": turn["content"][:2000]})
    messages.append(
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    )

    answer = _complete(messages)
    sources = [
        {
            "index": i,
            "company": d["company"],
            "year": d["year"],
            "source_file": d["source_file"],
            "snippet": d["content"][:300],
            "score": d["score"],
        }
        for i, d in enumerate(docs, start=1)
    ]
    return {"answer": answer, "sources": sources}
