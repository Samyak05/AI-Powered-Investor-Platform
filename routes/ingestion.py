import os
import shutil

from fastapi import APIRouter, File, UploadFile

from services.ingestion_service import process_pdf


router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("")
async def ingest_pdf(file: UploadFile = File(...)):

    upload_dir = "data/raw_pdfs"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    process_pdf(file_path)

    return {
        "message": "PDF processed successfully",
        "filename": file.filename
    }