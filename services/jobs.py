"""In-memory job tracking for the existing ingestion pipeline."""
from __future__ import annotations

import copy
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone

STEPS: list[tuple[str, str]] = [
    ("pipeline", "Run existing PDF-to-PostgreSQL pipeline"),
]
STEP_LABELS = dict(STEPS)
ACTIVE = {"queued", "running"}


class JobConflictError(Exception):
    """An ingestion for the same company/year is already queued or running."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class StepState:
    name: str
    label: str
    status: str = "pending"
    detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class Job:
    job_id: str
    company: str
    year: str
    filename: str
    status: str = "queued"
    steps: list[StepState] = field(default_factory=list)
    error: dict | None = None
    result: dict | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


class JobStore:
    def __init__(self, max_jobs: int = 200) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.RLock()
        self._max_jobs = max_jobs

    def create(self, company: str, year: str, filename: str) -> Job:
        with self._lock:
            for job in self._jobs.values():
                if (job.status in ACTIVE and job.year == year
                        and job.company.lower() == company.lower()):
                    raise JobConflictError(
                        f"An ingestion for {company} {year} is already in progress "
                        f"(job {job.job_id})."
                    )
            job = Job(
                job_id=uuid.uuid4().hex,
                company=company,
                year=year,
                filename=filename,
                steps=[StepState(name=n, label=l) for n, l in STEPS],
            )
            self._jobs[job.job_id] = job
            self._evict()
            return copy.deepcopy(job)

    def discard(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return copy.deepcopy(job) if job else None

    def start(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.updated_at = _now()

    def step_start(self, job_id: str, step: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            state = self._step(job, step)
            state.status, state.started_at = "running", _now()
            job.updated_at = _now()

    def step_detail(self, job_id: str, step: str, detail: str) -> None:
        with self._lock:
            self._step(self._jobs[job_id], step).detail = detail
            self._jobs[job_id].updated_at = _now()

    def step_done(self, job_id: str, step: str, detail: str | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            state = self._step(job, step)
            state.status, state.finished_at = "done", _now()
            if detail is not None:
                state.detail = detail
            job.updated_at = _now()

    def complete(self, job_id: str, result: dict) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status, job.result = "completed", result
            job.updated_at = _now()

    def fail(self, job_id: str, step: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            state = self._step(job, step)
            state.status, state.finished_at = "failed", _now()
            job.status = "failed"
            job.error = {"step": step, "message": message}
            job.updated_at = _now()

    @staticmethod
    def _step(job: Job, name: str) -> StepState:
        return next(s for s in job.steps if s.name == name)

    def _evict(self) -> None:
        while len(self._jobs) > self._max_jobs:
            oldest_finished = next(
                (k for k, j in self._jobs.items() if j.status not in ACTIVE), None
            )
            if oldest_finished is None:
                break
            del self._jobs[oldest_finished]


job_store = JobStore()
