import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.core.config import settings
from app.fetchers.rss_fetcher import rss_fetcher
from app.fetchers.reddit_fetcher import reddit_fetcher
from app.fetchers.youtube_fetcher import youtube_fetcher
from app.fetchers.twitter_fetcher import twitter_fetcher
from app.services.sentiment import sentiment_analyzer
from app.services.keyword import keyword_extractor
from app.db.database import async_session_maker
from app.models.models import Source, RawMention, ProcessedMention, FetchLog

logger = logging.getLogger(__name__)


class FetchScheduler:
    """Scheduler service for periodic data fetching"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    def start(self):
        """Start the scheduler"""
        if not self._is_running:
            logger.info(f"[Scheduler] Starting with interval: {settings.FETCH_INTERVAL_HOURS} hour(s)")

            # Add the recurring job
            self.scheduler.add_job(
                self.fetch_all_sources,
                trigger=IntervalTrigger(hours=settings.FETCH_INTERVAL_HOURS),
                id="fetch_all_sources",
                replace_existing=True,
                max_instances=1
            )
            self.scheduler.start()
            self._is_running = True
            logger.info(f"[Scheduler] Scheduler started. First fetch will run in {settings.FETCH_INTERVAL_HOURS} hour(s)")
            logger.info(f"[Scheduler] To trigger immediately: POST /api/fetch/manual")

    def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("[Scheduler] Stopped")

    async def fetch_all_sources(self):
        """Fetch data from all sources"""
        job_id = str(uuid.uuid4())
        logger.info(f"[Scheduler] === Starting scheduled fetch job: {job_id} ===")

        sources = ["youtube", "twitter", "reddit", "rss"]

        for source_type in sources:
            logger.info(f"[Scheduler] --- Fetching source: {source_type} ---")
            await self.fetch_source(source_type, job_id)

        logger.info(f"[Scheduler] === Completed scheduled fetch job: {job_id} ===")

    async def fetch_source(self, source_type: str, job_id: Optional[str] = None):
        """Fetch data from a specific source"""
        if job_id is None:
            job_id = str(uuid.uuid4())

        async with async_session_maker() as db:
            try:
                # Get or create source
                source = await self._get_or_create_source(db, source_type)
                if not source:
                    return

                # Log fetch start
                fetch_log = FetchLog(
                    source_id=source.id,
                    fetched_at=datetime.utcnow(),
                    status="running"
                )
                db.add(fetch_log)
                await db.commit()

                # Fetch data based on source type
                if source_type == "youtube":
                    data = await youtube_fetcher.fetch_youtube()
                elif source_type == "twitter":
                    data = await twitter_fetcher.fetch_twitter()
                elif source_type == "reddit":
                    data = await reddit_fetcher.fetch_reddit()
                elif source_type == "rss":
                    data = await rss_fetcher.fetch_google_news()
                else:
                    data = []

                # Process and store mentions
                items_new = 0
                items_updated = 0

                # Filter items - must contain "Universitas Terbuka" in both title AND content
                filtered_items = [item for item in data if self._filter_universitas_terbuka(item)]
                logger.info(f"[Scheduler] Filtered {len(data)} items to {len(filtered_items)} containing 'Universitas Terbuka'")

                for item in filtered_items:
                    result = await self._store_mention(db, source, item)
                    if result == "new":
                        items_new += 1
                    elif result == "updated":
                        items_updated += 1

                # Update fetch log
                fetch_log.items_fetched = len(data)
                fetch_log.items_new = items_new
                fetch_log.items_updated = items_updated
                fetch_log.status = "success"
                await db.commit()

                logger.info(f"[Scheduler] Fetched {len(data)} items from {source_type}: {items_new} new, {items_updated} updated")

            except Exception as e:
                logger.error(f"[Scheduler] Error fetching {source_type}: {e}")
                # Update fetch log with error
                await db.rollback()

    async def _get_or_create_source(self, db: AsyncSession, source_type: str) -> Optional[Source]:
        """Get or create a source record"""
        type_mapping = {
            "youtube": ("YouTube", "youtube", "https://youtube.com"),
            "twitter": ("Twitter (X)", "twitter", "https://twitter.com"),
            "reddit": ("Reddit", "reddit", "https://reddit.com"),
            "rss": ("Google News", "rss", "https://news.google.com")
        }

        if source_type not in type_mapping:
            return None

        name, stype, url = type_mapping[source_type]

        # Check if source exists
        stmt = select(Source).where(Source.type == stype)
        result = await db.execute(stmt)
        source = result.scalar_one_or_none()

        if not source:
            source = Source(
                name=name,
                type=stype,
                url=url,
                is_active=True
            )
            db.add(source)
            await db.commit()
            await db.refresh(source)

        return source

    def _filter_universitas_terbuka(self, item: dict) -> bool:
        """Filter: both title AND content must contain 'Universitas Terbuka' (case-insensitive)"""
        title = item.get("metadata", {}).get("title", "").lower()
        content = item.get("content", "").lower()
        keyword = "universitas terbuka"
        return keyword in title and keyword in content

    async def _store_mention(self, db: AsyncSession, source: Source, item: dict) -> str:
        """Store a mention and process it. Returns 'new', 'updated', or 'existing'"""
        external_id = item.get("external_id", "")

        # Check if mention already exists
        stmt = select(RawMention).where(
            and_(
                RawMention.source_id == source.id,
                RawMention.external_id == external_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing mention
            existing.content = item.get("content", existing.content)
            existing.author = item.get("author", existing.author)
            existing.fetched_at = datetime.utcnow()
            await db.commit()

            # Re-process sentiment
            sentiment_result = sentiment_analyzer.analyze(existing.content)
            keywords = keyword_extractor.extract_keywords(existing.content)

            if existing.processed_mention:
                existing.processed_mention.sentiment_score = sentiment_result["sentiment_score"]
                existing.processed_mention.sentiment_label = sentiment_result["sentiment_label"]
                existing.processed_mention.sentiment_confidence = sentiment_result["sentiment_confidence"]
                existing.processed_mention.keywords = keywords
                existing.processed_mention.processed_at = datetime.utcnow()
            await db.commit()

            return "updated"

        # Create new mention
        raw_mention = RawMention(
            source_id=source.id,
            external_id=external_id,
            content=item.get("content", ""),
            author=item.get("author", "Unknown"),
            posted_at=item.get("posted_at", datetime.utcnow()),
            fetched_at=datetime.utcnow(),
            url=item.get("url", ""),
            metadata=item.get("metadata", {})
        )
        db.add(raw_mention)
        await db.commit()
        await db.refresh(raw_mention)

        # Process sentiment
        sentiment_result = sentiment_analyzer.analyze(raw_mention.content)
        keywords = keyword_extractor.extract_keywords(raw_mention.content)

        processed_mention = ProcessedMention(
            mention_id=raw_mention.id,
            clean_text=sentiment_analyzer.preprocess(raw_mention.content),
            sentiment_score=sentiment_result["sentiment_score"],
            sentiment_label=sentiment_result["sentiment_label"],
            sentiment_confidence=sentiment_result["sentiment_confidence"],
            keywords=keywords,
            processed_at=datetime.utcnow()
        )
        db.add(processed_mention)
        await db.commit()

        return "new"


# Singleton instance
fetch_scheduler = FetchScheduler()
