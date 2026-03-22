from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, date
from typing import List, Optional
import json

from app.models.models import (
    Source, RawMention, ProcessedMention,
    HourlyAggregate, DailyAggregate, FetchLog
)
from app.services.sentiment import sentiment_analyzer
from app.services.keyword import keyword_extractor


class DataProcessor:
    """Service for processing mentions and computing aggregates"""

    async def process_mention(self, db: AsyncSession, raw_mention: RawMention) -> ProcessedMention:
        """Process a single raw mention with sentiment analysis and keyword extraction"""
        # Analyze sentiment
        sentiment_result = sentiment_analyzer.analyze(raw_mention.content)

        # Extract keywords
        keywords = keyword_extractor.extract_keywords(raw_mention.content)

        # Create processed mention
        processed = ProcessedMention(
            mention_id=raw_mention.id,
            clean_text=sentiment_analyzer.preprocess(raw_mention.content),
            sentiment_score=sentiment_result["sentiment_score"],
            sentiment_label=sentiment_result["sentiment_label"],
            sentiment_confidence=sentiment_result["sentiment_confidence"],
            keywords=keywords,
            processed_at=datetime.utcnow()
        )

        return processed

    async def update_aggregates(self, db: AsyncSession, source_id: int, sentiment_label: str):
        """Update hourly and daily aggregates after new mention is processed"""
        now = datetime.utcnow()
        today = date.today()

        # Update hourly aggregate
        hour_bucket = now.replace(minute=0, second=0, microsecond=0)

        # Check if hourly aggregate exists
        stmt = select(HourlyAggregate).where(
            and_(
                HourlyAggregate.source_id == source_id,
                HourlyAggregate.hour_bucket == hour_bucket
            )
        )
        result = await db.execute(stmt)
        hourly_agg = result.scalar_one_or_none()

        if hourly_agg:
            # Update existing
            if sentiment_label == "positive":
                hourly_agg.positive_count += 1
            elif sentiment_label == "neutral":
                hourly_agg.neutral_count += 1
            else:
                hourly_agg.negative_count += 1
            hourly_agg.total_count += 1
        else:
            # Create new
            hourly_agg = HourlyAggregate(
                source_id=source_id,
                hour_bucket=hour_bucket,
                positive_count=1 if sentiment_label == "positive" else 0,
                neutral_count=1 if sentiment_label == "neutral" else 0,
                negative_count=1 if sentiment_label == "negative" else 0,
                total_count=1
            )
            db.add(hourly_agg)

        # Update daily aggregate
        stmt = select(DailyAggregate).where(
            and_(
                DailyAggregate.source_id == source_id,
                DailyAggregate.date_bucket == today
            )
        )
        result = await db.execute(stmt)
        daily_agg = result.scalar_one_or_none()

        if daily_agg:
            if sentiment_label == "positive":
                daily_agg.positive_count += 1
            elif sentiment_label == "neutral":
                daily_agg.neutral_count += 1
            else:
                daily_agg.negative_count += 1
            daily_agg.total_count += 1
        else:
            daily_agg = DailyAggregate(
                source_id=source_id,
                date_bucket=today,
                positive_count=1 if sentiment_label == "positive" else 0,
                neutral_count=1 if sentiment_label == "neutral" else 0,
                negative_count=1 if sentiment_label == "negative" else 0,
                total_count=1
            )
            db.add(daily_agg)

        await db.commit()


# Singleton instance
data_processor = DataProcessor()
