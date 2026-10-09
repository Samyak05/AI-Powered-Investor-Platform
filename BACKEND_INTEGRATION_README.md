# Backend integration for the existing RAG project

This package merges the API backend with the existing project. The existing pipeline modules are preserved:
- `ingestion/ingest_documents.py`
- `ingestion/pdf_to_markdown.py`
- `ingestion/semantic_chunker.py`
- `vectorstore/azure_ai_search.py`
- `vectorstore/create_index.py`
- `rag/kpi_extractor_rag.py`
- `database/postgres_sql.py`
- `database/create_table.py`
- `database/save_metrics.py`
- `database/metrics.py`
- `llm/azure_openai.py`

## Main routes
- `POST /api/ingest` — accepts a PDF and queues the existing `ingest_document()` function.
- `GET /api/ingest/{job_id}` — reports queued/running/completed/failed status.
- `POST /api/chat` — RAG question answering.
- `GET /api/kpis` and `GET /api/kpis/{company}/{year}` — PostgreSQL KPI records.
- `GET /health` and `GET /health/ready` — health/readiness.
- `GET /docs` — interactive FastAPI docs.

## Important behavior
The API's background service deliberately calls `ingestion.ingest_documents.ingest_document()` rather than duplicating or replacing its pipeline. The job status therefore reports the pipeline as one step. This keeps the backend compatible with the current pipeline and avoids changing its internals.

The upload filename is saved as `{year}_{company}.pdf` so the existing `parse_company_year()` function receives the requested company/year. The upload route accepts only letters, digits, spaces, `.`, `&`, and `-` in company names.

## Setup
1. Merge/replace your project directory with this archive, or copy the added backend files into your existing project. The existing pipeline files in this archive are preserved from the uploaded `project.zip`.
2. Create your own `.env` using `.env.example` as a template. Do not commit secrets.
3. Install the dependencies already used by your project plus FastAPI/Uvicorn/multipart if not installed:
   - `fastapi`
   - `uvicorn[standard]`
   - `python-multipart`
4. Run from the project root:
   `python app.py`
5. Open `http://127.0.0.1:8000/docs`.

## Notes
- Job tracking is in memory and resets when the server restarts; this is suitable for a local prototype.
- This package does not include your real `.env` secrets.
- It intentionally does not replace `database/postgres_sql.py` with the instructor backend's alternate version.
