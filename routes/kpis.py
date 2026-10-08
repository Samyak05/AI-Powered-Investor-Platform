from fastapi import APIRouter

from services.kpi_service import fetch_kpis


router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("")
def get_kpis():
    return {
        "data": fetch_kpis()
    }