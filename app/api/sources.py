from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.database import get_db
from app.models.models import Source
from app.schemas.schemas import SourceResponse, SourceCreate

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=List[SourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all sources"""
    stmt = select(Source).order_by(Source.name)
    result = await db.execute(stmt)
    sources = result.scalars().all()
    return sources


@router.post("", response_model=SourceResponse)
async def create_source(
    source: SourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new source"""
    new_source = Source(
        name=source.name,
        type=source.type,
        url=source.url,
        is_active=source.is_active
    )
    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)
    return new_source
