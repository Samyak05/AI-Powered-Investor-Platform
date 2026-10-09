import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from database.postgres_sql import get_engine
from services import clients
from services.bootstrap import missing_env_vars

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict:
    """Liveness probe: the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> JSONResponse:
    """Readiness probe: configuration, PostgreSQL and Azure AI Search reachable."""
    checks: dict[str, str] = {}

    missing = missing_env_vars()
    checks["config"] = "ok" if not missing else f"missing: {', '.join(missing)}"

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:  # noqa: BLE001
        logger.exception("Readiness: postgres check failed")
        checks["postgres"] = "unreachable"

    try:
        clients.get_vector_store().client.get_document_count()
        checks["search"] = "ok"
    except Exception:  # noqa: BLE001
        logger.exception("Readiness: search check failed")
        checks["search"] = "unreachable"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )
