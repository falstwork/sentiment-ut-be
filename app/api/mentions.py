from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.database import get_db
from app.models.models import RawMention, ProcessedMention, Source
from app.schemas.schemas import MentionResponse, MentionDetail, MentionsListResponse, PaginationInfo

router = APIRouter(prefix="/mentions", tags=["mentions"])


@router.get("/recent", response_model=MentionsListResponse)
async def get_recent_mentions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get recent mentions with pagination and filters"""
    # Build base query
    query = select(RawMention).join(ProcessedMention).options(
        selectinload(RawMention.source),
        selectinload(RawMention.processed_mention)
    )

    # Apply filters
    if source:
        # Find source by name or type
        source_stmt = select(Source).where(
            (Source.name.ilike(f"%{source}%")) | (Source.type == source)
        )
        source_result = await db.execute(source_stmt)
        source_obj = source_result.scalar_one_or_none()
        if source_obj:
            query = query.where(RawMention.source_id == source_obj.id)

    if sentiment:
        query = query.where(ProcessedMention.sentiment_label == sentiment.lower())

    if search:
        query = query.where(RawMention.content.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * limit
    query = query.order_by(desc(RawMention.fetched_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    mentions = result.scalars().all()

    # Convert to response format
    data = []
    for mention in mentions:
        sentiment_label = mention.processed_mention.sentiment_label if mention.processed_mention else "neutral"
        sentiment_score = mention.processed_mention.sentiment_score if mention.processed_mention else 0.0

        data.append(MentionResponse(
            id=mention.id,
            source=mention.source.name if mention.source else "Unknown",
            content=mention.content[:500] if mention.content else "",  # Truncate for preview
            author=mention.author or "Anonymous",
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            posted_at=mention.posted_at,
            url=mention.url
        ))

    total_pages = (total + limit - 1) // limit if limit > 0 else 0

    return MentionsListResponse(
        data=data,
        pagination=PaginationInfo(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages
        )
    )


@router.get("/{mention_id}", response_model=MentionDetail)
async def get_mention_detail(
    mention_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get single mention detail"""
    query = select(RawMention).where(RawMention.id == mention_id).options(
        selectinload(RawMention.source),
        selectinload(RawMention.processed_mention)
    )
    result = await db.execute(query)
    mention = result.scalar_one_or_none()

    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")

    processed = mention.processed_mention

    return MentionDetail(
        id=mention.id,
        source=mention.source.name if mention.source else "Unknown",
        content=mention.content,
        author=mention.author or "Anonymous",
        sentiment=processed.sentiment_label if processed else "neutral",
        sentiment_score=processed.sentiment_score if processed else 0.0,
        posted_at=mention.posted_at,
        url=mention.url,
        clean_text=processed.clean_text if processed else None,
        sentiment_confidence=processed.sentiment_confidence if processed else 0.0,
        keywords=processed.keywords if processed else None
    )
