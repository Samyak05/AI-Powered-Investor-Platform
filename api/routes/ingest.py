"""POST /api/ingest  -> run the full pipeline in the background
GET  /api/ingest/{job_id} -> poll progress / result
"""
import logging
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from api.schemas import COMPANY_PATTERN, YEAR_PATTERN, IngestAccepted, IngestJobOut
from ingestion.ingest_documents import parse_company_year
from services import ingestion_service
from services.jobs import Job, JobConflictError, job_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingestion"])

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))


def _to_out(job: Job) -> IngestJobOut:
    done = sum(1 for s in job.steps if s.status == "done")
    current = next((s.name for s in job.steps if s.status == "running"), None)
    return IngestJobOut(
        job_id=job.job_id,
        status=job.status,
        company=job.company,
        year=job.year,
        filename=job.filename,
        progress=100 if job.status == "completed" else int(done / len(job.steps) * 100),
        current_step=current,
        steps=[s.__dict__ for s in job.steps],
        error=job.error,
        result=job.result,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _save_pdf(upload: UploadFile, final_path: Path) -> None:
    """Stream the upload to disk, enforcing size limit and PDF signature."""
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = final_path.parent / f".upload-{uuid.uuid4().hex}.part"
    max_bytes, size = MAX_UPLOAD_MB * 1024 * 1024, 0
    try:
        with tmp.open("wb") as out:
            while block := upload.file.read(1024 * 1024):
                size += len(block)
                if size > max_bytes:
                    raise HTTPException(413, f"File exceeds {MAX_UPLOAD_MB} MB limit.")
                out.write(block)
        with tmp.open("rb") as f:
            if f.read(5) != b"%PDF-":
                raise HTTPException(400, "The uploaded file is not a valid PDF.")
        os.replace(tmp, final_path)
    finally:
        tmp.unlink(missing_ok=True)


@router.post("/ingest", status_code=202, response_model=IngestAccepted)
def ingest_report(
    request: Request,
    file: UploadFile = File(..., description="Annual report PDF"),
    company: str | None = Form(None, description="Defaults to the file name, e.g. 2024_Apple.pdf"),
    year: str | None = Form(None, description="Defaults to the file name, e.g. 2024_Apple.pdf"),
) -> IngestAccepted:
    """Upload a report and start the full ingestion pipeline."""
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files are supported.")

    parsed_company, parsed_year = parse_company_year(Path(filename))
    company = (company or "").strip() or parsed_company
    year = (year or "").strip() or parsed_year

    if not re.fullmatch(COMPANY_PATTERN, company or ""):
        raise HTTPException(
            422, "Invalid company. Use letters/digits/spaces only, or name the file like 2024_Apple.pdf."
        )
    if not re.fullmatch(YEAR_PATTERN, year or ""):
        raise HTTPException(
            422, "Could not determine the report year. Pass `year` or name the file like 2024_Apple.pdf."
        )

    try:
        job = job_store.create(company=company, year=year, filename=filename)
    except JobConflictError as exc:
        raise HTTPException(409, str(exc)) from exc

    # Canonical name keeps raw_pdfs/ consistent with the 2024_Apple.pdf convention.
    safe_company = re.sub(r"[^A-Za-z0-9]+", "-", company).strip("-")
    pdf_path = ingestion_service.RAW_PDF_DIR / f"{year}_{company}.pdf"
    try:
        _save_pdf(file, pdf_path)
    except Exception:
        job_store.discard(job.job_id)
        raise

    ingestion_service.submit_ingestion(job.job_id, pdf_path, company, year)
    return IngestAccepted(
        job_id=job.job_id,
        company=company,
        year=year,
        status_url=request.app.url_path_for("get_ingest_job", job_id=job.job_id),
    )


@router.get("/ingest/{job_id}", response_model=IngestJobOut, name="get_ingest_job")
def get_ingest_job(job_id: str) -> IngestJobOut:
    """Poll an ingestion job (every 1-2 s) until status is completed/failed."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job (jobs are cleared when the server restarts).")
    return _to_out(job)
