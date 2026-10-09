"""Request / response models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Letters/digits/space/.&- only. No quotes, so values are safe inside OData filters.
COMPANY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 .&-]{0,59}$"
YEAR_PATTERN = r"^(19|20)\d{2}$"


# --- ingestion -------------------------------------------------------------
class IngestAccepted(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"
    company: str
    year: str
    status_url: str


class StepOut(BaseModel):
    name: str
    label: str
    status: Literal["pending", "running", "done", "failed"]
    detail: str | None = None


class JobError(BaseModel):
    step: str
    message: str


class IngestJobOut(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    company: str
    year: str
    filename: str
    progress: int = Field(description="0-100, based on completed steps")
    current_step: str | None
    steps: list[StepOut]
    error: JobError | None = None
    result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# --- KPIs ------------------------------------------------------------------
class KPIRecord(BaseModel):
    id: int | None = None
    company: str
    year: str
    revenue: str | None = None
    net_income: str | None = None
    operating_income: str | None = None
    cash_flow: str | None = None
    total_assets: str | None = None
    total_liabilities: str | None = None
    risk_factors: list[str] = []
    growth_drivers: list[str] = []
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: dict) -> "KPIRecord":
        def lines(value: str | None) -> list[str]:
            return [ln.strip() for ln in (value or "").splitlines() if ln.strip()]

        return cls(
            id=row.get("id"),
            company=row["company"],
            year=str(row["year"]),
            revenue=row.get("revenue"),
            net_income=row.get("net_income"),
            operating_income=row.get("operating_income"),
            cash_flow=row.get("cash_flow"),
            total_assets=row.get("total_assets"),
            total_liabilities=row.get("total_liabilities"),
            risk_factors=lines(row.get("risk_factors")),
            growth_drivers=lines(row.get("growth_drivers")),
            created_at=row.get("created_at"),
        )


# --- chat ------------------------------------------------------------------
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    company: str | None = Field(default=None, pattern=COMPANY_PATTERN)
    year: str | None = Field(default=None, pattern=YEAR_PATTERN)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatSource(BaseModel):
    index: int
    company: str | None
    year: str | None
    source_file: str | None
    snippet: str
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
