from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from app.db.database import get_db, async_session_maker
from app.models.models import Source, FetchLog
from app.schemas.schemas import FetchManualRequest, FetchManualResponse, FetchStatusResponse
from app.services.scheduler import fetch_scheduler

router = APIRouter(prefix="/fetch", tags=["fetch"])

# In-memory job tracking
fetch_jobs = {}


@router.post("/manual", response_model=FetchManualResponse)
async def trigger_manual_fetch(
    request: FetchManualRequest = None
):
    """Trigger manual fetch"""
    job_id = str(uuid.uuid4())
    sources_triggered = []

    # Determine which sources to fetch
    if request and request.source:
        sources_to_fetch = [request.source.lower()]
    else:
        sources_to_fetch = ["youtube", "twitter", "reddit", "rss"]

    # Start fetch job
    fetch_jobs[job_id] = {
        "status": "started",
        "sources": sources_to_fetch,
        "items_fetched": 0,
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "error_message": None
    }

    # Trigger async fetch (fire and forget)
    for source_type in sources_to_fetch:
        sources_triggered.append(source_type)
        try:
            await fetch_scheduler.fetch_source(source_type, job_id)
        except Exception as e:
            fetch_jobs[job_id]["error_message"] = str(e)
            fetch_jobs[job_id]["status"] = "failed"

    # Update job status
    fetch_jobs[job_id]["status"] = "completed"
    fetch_jobs[job_id]["completed_at"] = datetime.utcnow()

    return FetchManualResponse(
        status="started",
        job_id=job_id,
        sources_triggered=sources_triggered
    )


@router.get("/status/{job_id}", response_model=FetchStatusResponse)
async def get_fetch_status(job_id: str):
    """Get fetch job status"""
    if job_id not in fetch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = fetch_jobs[job_id]

    return FetchStatusResponse(
        job_id=job_id,
        status=job["status"],
        sources=job["sources"],
        items_fetched=job["items_fetched"],
        started_at=job["started_at"],
        completed_at=job.get("completed_at"),
        error_message=job.get("error_message")
    )
