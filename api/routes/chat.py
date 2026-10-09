"""RAG chat endpoint."""
import logging

from fastapi import APIRouter, HTTPException

from api.schemas import ChatRequest, ChatResponse
from services.chat_service import answer_question

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Answer a question from the ingested reports (optionally scoped to one report)."""
    try:
        result = answer_question(
            question=req.question,
            company=req.company,
            year=req.year,
            history=[t.model_dump() for t in req.history],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat failed")
        raise HTTPException(502, "The AI service could not answer right now. Please retry.") from exc
    return ChatResponse(**result)
