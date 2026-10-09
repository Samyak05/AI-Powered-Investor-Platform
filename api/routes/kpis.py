"""KPI dashboard data from PostgreSQL."""
import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from api.schemas import KPIRecord
from database.metrics import get_metrics

logger = logging.getLogger(__name__)
router = APIRouter(tags=["kpis"])


def _load() -> list[KPIRecord]:
    try:
        rows = get_metrics()
    except SQLAlchemyError as exc:
        logger.exception("Could not read financial_metrics")
        raise HTTPException(503, "Database unavailable.") from exc
    records = [KPIRecord.from_row(r) for r in rows]
    return sorted(records, key=lambda r: (r.company.lower(), r.year), reverse=False)


@router.get("/kpis", response_model=list[KPIRecord])
def list_kpis(
    company: str | None = Query(None),
    year: str | None = Query(None),
) -> list[KPIRecord]:
    """Latest KPIs per company/year. Optional filters."""
    records = _load()
    if company:
        records = [r for r in records if r.company.lower() == company.lower()]
    if year:
        records = [r for r in records if r.year == year]
    return records


@router.get("/kpis/{company}/{year}", response_model=KPIRecord)
def get_kpis(company: str, year: str) -> KPIRecord:
    for r in _load():
        if r.company.lower() == company.lower() and r.year == year:
            return r
    raise HTTPException(404, f"No KPIs found for {company} {year}.")
