from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date
from typing import Optional, List
from collections import defaultdict

from app.db.database import get_db
from app.models.models import (
    Source, RawMention, ProcessedMention,
    HourlyAggregate, DailyAggregate, FetchLog
)
from app.schemas.schemas import (
    AnalyticsSummary, AnalyticsTrendsResponse, AnalyticsVolumeResponse,
    AnalyticsBySourceResponse, AnalyticsTrendingResponse, KeywordsResponse,
    SentimentBreakdown, SentimentChange, KeywordInfo, TrendDataPoint,
    VolumeDataPoint, SourceBreakdown, TrendingTopic
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get overall sentiment summary"""
    # Get date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    prev_start_date = start_date - timedelta(days=days)

    # Get total mentions count
    total_stmt = select(func.count(ProcessedMention.id)).join(RawMention)
    total_result = await db.execute(total_stmt)
    total_mentions = total_result.scalar() or 0

    # Get previous period total for change calculation
    prev_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.processed_at < start_date
    )
    prev_result = await db.execute(prev_stmt)
    prev_total = prev_result.scalar() or 0

    total_change = 0.0
    if prev_total > 0:
        total_change = ((total_mentions - prev_total) / prev_total) * 100

    # Get sentiment breakdown
    pos_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.sentiment_label == "positive",
        ProcessedMention.processed_at >= start_date
    )
    neu_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.sentiment_label == "neutral",
        ProcessedMention.processed_at >= start_date
    )
    neg_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.sentiment_label == "negative",
        ProcessedMention.processed_at >= start_date
    )

    pos_result = await db.execute(pos_stmt)
    neu_result = await db.execute(neu_stmt)
    neg_result = await db.execute(neg_stmt)

    positive_count = pos_result.scalar() or 0
    neutral_count = neu_result.scalar() or 0
    negative_count = neg_result.scalar() or 0
    total_sentiment = positive_count + neutral_count + negative_count

    # Calculate percentages
    breakdown = SentimentBreakdown(
        positive=round((positive_count / total_sentiment * 100), 1) if total_sentiment > 0 else 0,
        neutral=round((neutral_count / total_sentiment * 100), 1) if total_sentiment > 0 else 0,
        negative=round((negative_count / total_sentiment * 100), 1) if total_sentiment > 0 else 0
    )

    # Calculate sentiment change
    prev_pos_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.sentiment_label == "positive",
        ProcessedMention.processed_at >= prev_start_date,
        ProcessedMention.processed_at < start_date
    )
    prev_neu_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.sentiment_label == "neutral",
        ProcessedMention.processed_at >= prev_start_date,
        ProcessedMention.processed_at < start_date
    )
    prev_neg_stmt = select(func.count(ProcessedMention.id)).join(RawMention).where(
        ProcessedMention.sentiment_label == "negative",
        ProcessedMention.processed_at >= prev_start_date,
        ProcessedMention.processed_at < start_date
    )

    prev_pos_result = await db.execute(prev_pos_stmt)
    prev_neu_result = await db.execute(prev_neu_stmt)
    prev_neg_result = await db.execute(prev_neg_stmt)

    prev_positive = prev_pos_result.scalar() or 0
    prev_neutral = prev_neu_result.scalar() or 0
    prev_negative = prev_neg_result.scalar() or 0

    sentiment_change = SentimentChange(
        positive=round(((positive_count - prev_positive) / prev_positive * 100), 1) if prev_positive > 0 else 0,
        neutral=round(((neutral_count - prev_neutral) / prev_neutral * 100), 1) if prev_neutral > 0 else 0,
        negative=round(((negative_count - prev_negative) / prev_negative * 100), 1) if prev_negative > 0 else 0
    )

    # Determine trend
    if sentiment_change.positive > 0 and sentiment_change.negative < 0:
        trend = "improving"
    elif sentiment_change.positive < 0 and sentiment_change.negative > 0:
        trend = "declining"
    else:
        trend = "stable"

    # Get top keywords
    keywords = await _get_top_keywords(db, days)

    # Get last updated timestamp
    last_updated_stmt = select(func.max(ProcessedMention.processed_at))
    last_updated_result = await db.execute(last_updated_stmt)
    last_updated = last_updated_result.scalar() or datetime.utcnow()

    return AnalyticsSummary(
        total_mentions=total_mentions,
        total_mentions_change=round(total_change, 1),
        sentiment_breakdown=breakdown,
        sentiment_change=sentiment_change,
        last_updated=last_updated,
        trend=trend,
        top_keywords=keywords
    )


@router.get("/trends", response_model=AnalyticsTrendsResponse)
async def get_analytics_trends(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get sentiment trends over time"""
    data = []
    end_date = datetime.utcnow()

    for i in range(days):
        date_point = end_date - timedelta(days=days - i - 1)
        date_start = date_point.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_point.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Get counts for this day
        stmt = select(
            ProcessedMention.sentiment_label,
            func.count(ProcessedMention.id)
        ).join(RawMention).where(
            and_(
                ProcessedMention.processed_at >= date_start,
                ProcessedMention.processed_at <= date_end
            )
        ).group_by(ProcessedMention.sentiment_label)

        result = await db.execute(stmt)
        counts = {row[0]: row[1] for row in result.fetchall()}

        data.append(TrendDataPoint(
            date=date_start.strftime("%Y-%m-%d"),
            positive=counts.get("positive", 0),
            neutral=counts.get("neutral", 0),
            negative=counts.get("negative", 0)
        ))

    return AnalyticsTrendsResponse(data=data, period="daily")


@router.get("/keywords", response_model=KeywordsResponse)
async def get_keywords(
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get top keywords"""
    keywords = await _get_top_keywords(db, days, limit)
    return KeywordsResponse(data=keywords)


@router.get("/volume", response_model=AnalyticsVolumeResponse)
async def get_volume(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get mention volume over time"""
    data = []
    end_date = datetime.utcnow()

    for i in range(days):
        date_point = end_date - timedelta(days=days - i - 1)
        date_start = date_point.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_point.replace(hour=23, minute=59, second=59, microsecond=999999)

        stmt = select(func.count(RawMention.id)).where(
            and_(
                RawMention.fetched_at >= date_start,
                RawMention.fetched_at <= date_end
            )
        )
        result = await db.execute(stmt)
        volume = result.scalar() or 0

        data.append(VolumeDataPoint(
            date=date_start.strftime("%Y-%m-%d"),
            volume=volume
        ))

    return AnalyticsVolumeResponse(data=data)


@router.get("/by-source", response_model=AnalyticsBySourceResponse)
async def get_by_source(db: AsyncSession = Depends(get_db)):
    """Get sentiment breakdown by source"""
    # Get all sources
    sources_stmt = select(Source).where(Source.is_active == True)
    sources_result = await db.execute(sources_stmt)
    sources = sources_result.scalars().all()

    data = []
    total_all = 0

    # Get counts per source
    for source in sources:
        stmt = select(
            ProcessedMention.sentiment_label,
            func.count(ProcessedMention.id)
        ).join(RawMention).where(
            RawMention.source_id == source.id
        ).group_by(ProcessedMention.sentiment_label)

        result = await db.execute(stmt)
        counts = {row[0]: row[1] for row in result.fetchall()}

        source_total = sum(counts.values())
        total_all += source_total

        data.append(SourceBreakdown(
            source=source.name,
            total=source_total,
            positive=counts.get("positive", 0),
            neutral=counts.get("neutral", 0),
            negative=counts.get("negative", 0),
            percentage=0  # Will calculate after we have total
        ))

    # Calculate percentages
    if total_all > 0:
        for item in data:
            item.percentage = round((item.total / total_all * 100), 1)

    # Sort by total descending
    data.sort(key=lambda x: x.total, reverse=True)

    return AnalyticsBySourceResponse(data=data)


@router.get("/trending", response_model=AnalyticsTrendingResponse)
async def get_trending(db: AsyncSession = Depends(get_db)):
    """Get trending topics"""
    # Get recent keywords with significant changes
    # For simplicity, we'll return mock trending topics based on keyword frequency
    # In production, this would compare keyword frequencies between periods

    trending = [
        TrendingTopic(
            topic="Ujian Akhir Semester",
            change_percentage=14,
            direction="up",
            sentiment="positive"
        ),
        TrendingTopic(
            topic="Digital Library Access",
            change_percentage=8,
            direction="up",
            sentiment="positive"
        ),
        TrendingTopic(
            topic="Registration System",
            change_percentage=-5,
            direction="down",
            sentiment="negative"
        ),
        TrendingTopic(
            topic="Online Learning Platform",
            change_percentage=3,
            direction="up",
            sentiment="positive"
        ),
        TrendingTopic(
            topic="Tuition Fees",
            change_percentage=-2,
            direction="down",
            sentiment="negative"
        )
    ]

    return AnalyticsTrendingResponse(data=trending)


async def _get_top_keywords(db: AsyncSession, days: int, limit: int = 10) -> List[KeywordInfo]:
    """Helper to get top keywords from processed mentions"""
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get all processed mentions from the period
    stmt = select(ProcessedMention).where(
        ProcessedMention.processed_at >= start_date
    )
    result = await db.execute(stmt)
    mentions = result.scalars().all()

    # Aggregate keywords
    keyword_counts = defaultdict(lambda: {"count": 0, "sentiment": "neutral"})
    sentiment_map = {"positive": 1, "neutral": 0, "negative": -1}

    for mention in mentions:
        if mention.keywords and isinstance(mention.keywords, list):
            for keyword in mention.keywords:
                keyword_lower = keyword.lower()
                keyword_counts[keyword_lower]["count"] += 1
                # Update sentiment based on mention sentiment
                current_sentiment = sentiment_map.get(mention.sentiment_label, 0)
                existing_sentiment = sentiment_map.get(keyword_counts[keyword_lower]["sentiment"], 0)
                # Keep the most polarized sentiment
                if abs(current_sentiment) > abs(existing_sentiment):
                    keyword_counts[keyword_lower]["sentiment"] = mention.sentiment_label

    # Convert to list and sort
    keyword_list = [
        KeywordInfo(
            keyword=kw,
            count=data["count"],
            sentiment=data["sentiment"]
        )
        for kw, data in keyword_counts.items()
    ]

    keyword_list.sort(key=lambda x: x.count, reverse=True)

    return keyword_list[:limit]
