"""Background wrapper around the project's existing ingestion pipeline.

The pipeline implementation remains in ingestion/ingest_documents.py:
PDF -> Markdown -> semantic chunks -> Azure AI Search -> KPI extraction -> PostgreSQL.
This service only schedules it and exposes job status.
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from database.metrics import get_metrics
from ingestion.ingest_documents import ingest_document
from services import clients
from services.jobs import STEP_LABELS, job_store

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_PDF_DIR = REPO_ROOT / "data" / "raw_pdfs"
MARKDOWN_DIR = REPO_ROOT / "data" / "markdown"

_executor = ThreadPoolExecutor(
    max_workers=max(1, int(os.getenv("INGEST_MAX_WORKERS", "2"))),
    thread_name_prefix="ingest",
)


class PipelineError(Exception):
    """A safe-to-display pipeline error."""


def submit_ingestion(job_id: str, pdf_path: Path, company: str, year: str) -> None:
    _executor.submit(run_ingestion, job_id, pdf_path, company, year)


def shutdown_executor() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)


def run_ingestion(job_id: str, pdf_path: Path, company: str, year: str) -> None:
    step = "pipeline"
    try:
        job_store.start(job_id)
        job_store.step_start(job_id, step)
        # Do not reimplement the pipeline here. Call the user's existing function.
        ingest_document(
            pdf_path=str(pdf_path),
            embeddings=clients.get_embeddings(),
            vector_store=clients.get_vector_store(),
        )

        # ingest_document() already persists metrics. Read the latest saved row
        # for the response; this is informational and does not alter persistence.
        rows = get_metrics()
        latest = next(
            (
                row for row in rows
                if str(row.get("company", "")).lower() == company.lower()
                and str(row.get("year", "")) == str(year)
            ),
            None,
        )
        result = {"company": company, "year": str(year)}
        if latest is not None:
            result["metrics"] = {
                key: value for key, value in latest.items()
                if key not in {"id", "created_at"}
            }
        job_store.step_done(job_id, step, "Existing ingestion pipeline completed")
        job_store.complete(job_id, result)
        logger.info("Ingestion complete: %s %s (job %s)", company, year, job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion %s failed", job_id)
        job_store.fail(
            job_id,
            step,
            f"{STEP_LABELS[step]} failed ({type(exc).__name__}). See server logs for details.",
        )
