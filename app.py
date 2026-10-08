from fastapi import FastAPI

from routes.ingestion import router as ingestion_router
from routes.kpis import router as kpi_router


app = FastAPI(
    title="Investor Intelligence Platform"
)


app.include_router(
    ingestion_router,
    prefix="/api"
)

app.include_router(
    kpi_router,
    prefix="/api"
)


@app.get("/")
def root():
    return {
        "message": "Investor Intelligence Platform API"
    }