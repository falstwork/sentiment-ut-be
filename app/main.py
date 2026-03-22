from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from app.core.config import settings
from app.db.database import init_db
from app.api import analytics, mentions, sources, fetch
from app.schemas.schemas import HealthResponse
from app.services.scheduler import fetch_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting up Sentiment UT API...")
    await init_db()
    logger.info("Database initialized")

    # Seed demo data
    await seed_demo_data()

    # Start scheduler
    fetch_scheduler.start()

    # Run immediate fetch on startup (Twitter/YouTube/Reddit/RSS API)
    logger.info("[Startup] Running IMMEDIATE fetch on startup...")
    await fetch_scheduler.fetch_all_sources()
    logger.info("[Startup] Startup fetch completed")

    yield

    # Shutdown
    logger.info("Shutting down...")
    fetch_scheduler.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(mentions.router, prefix=settings.API_PREFIX)
app.include_router(sources.router, prefix=settings.API_PREFIX)
app.include_router(fetch.router, prefix=settings.API_PREFIX)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        timestamp=datetime.utcnow()
    )


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Sentiment UT API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


async def seed_demo_data():
    """Seed database with demo data if empty"""
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.database import async_session_maker
    from app.models.models import Source, RawMention, ProcessedMention
    from app.services.sentiment import sentiment_analyzer
    from app.services.keyword import keyword_extractor
    from datetime import datetime, timedelta
    import random

    async with async_session_maker() as db:
        # Check if we already have data
        count_stmt = select(func.count(RawMention.id))
        result = await db.execute(count_stmt)
        existing_count = result.scalar() or 0

        if existing_count > 0:
            logger.info(f"[SeedDemo] Database has {existing_count} mentions — SKIPPING seed (data already exists)")
            return

        logger.info("[SeedDemo] No existing data — seeding demo data (MOCK, not from Twitter/YouTube/Reddit API)")

        # Create sources
        sources_data = [
            {"name": "YouTube", "type": "youtube", "url": "https://youtube.com"},
            {"name": "Twitter (X)", "type": "twitter", "url": "https://twitter.com"},
            {"name": "Reddit", "type": "reddit", "url": "https://reddit.com"},
            {"name": "Google News", "type": "rss", "url": "https://news.google.com"}
        ]

        source_objects = []
        for src in sources_data:
            source = Source(**src, is_active=True)
            db.add(source)
            source_objects.append(source)

        await db.commit()

        # Demo content
        demo_content = [
            # {"content": "Pengalaman kuliah di Universitas Terbuka sangat fleksibel buat kerja dan keluarga. Sistem belajar mandiri yang sangat membantu.", "source_idx": 0, "sentiment": "positive"},
            # {"content": "Universitas Terbuka emang solusi tepat buat yang mau kuliah sambil kerja. Fleksibel dan terjangkau!", "source_idx": 1, "sentiment": "positive"},
            # {"content": "Tips belajar mandiri di UT biar lulus tepat waktu. Strategi manajemen waktu sangat penting.", "source_idx": 2, "sentiment": "neutral"},
            # {"content": "Server pendaftaran UT lagi down lagi nih, hope they fix this soon", "source_idx": 1, "sentiment": "negative"},
            # {"content": "Selamat kepada Graduates UT tahun 2026! Prestasi membanggakan.", "source_idx": 3, "sentiment": "positive"},
            # {"content": "Pembelajaran online di UT sangat mudah diakses dari mana saja. Platform digital mereka terus improve.", "source_idx": 0, "sentiment": "positive"},
            # {"content": "Biaya kuliah di Universitas Terbuka sangat terjangkau dibanding universitas lain.", "source_idx": 3, "sentiment": "positive"},
            # {"content": "Ujian akhir semester di UT cukup menantang tapi materinya lengkap.", "source_idx": 2, "sentiment": "neutral"},
            # {"content": "Digital library UT sangat membantu untuk riset dan tugas akhir.", "source_idx": 0, "sentiment": "positive"},
            # {"content": "Sistem registrasi online UT perlu diperbaiki, sering error saat高峰期.", "source_idx": 1, "sentiment": "negative"},
            # {"content": "Universitas Terbuka memberikan kesempatan pendidikan tinggi untuk semua orang.", "source_idx": 3, "sentiment": "positive"},
            # {"content": "Dosen-dosen di UT sangat kompeten dan membantu mahasiswa.", "source_idx": 2, "sentiment": "positive"},
            # {"content": "Kuliah umum dari UT selalu memberikan insight baru tentang pendidikan.", "source_idx": 0, "sentiment": "positive"},
            # {"content": "Proses pen台山 ijazah di UT cukup cepat dan efisien.", "source_idx": 1, "sentiment": "neutral"},
            # {"content": "Fleksibilitas waktu belajar di UT sangat cocok untuk pekerja.", "source_idx": 2, "sentiment": "positive"},
        ]

        # Insert mentions with varied dates over past 7 days
        for i, demo in enumerate(demo_content):
            source = source_objects[demo["source_idx"]]
            posted_at = datetime.utcnow() - timedelta(
                hours=random.randint(1, 168),  # Last 7 days
                minutes=random.randint(0, 59)
            )

            raw_mention = RawMention(
                source_id=source.id,
                external_id=f"demo_{i}_{datetime.utcnow().timestamp()}",
                content=demo["content"],
                author=f"User_{random.randint(1000, 9999)}",
                posted_at=posted_at,
                fetched_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
                url="",
                metadata={}
            )
            db.add(raw_mention)
            await db.commit()
            await db.refresh(raw_mention)

            # Analyze sentiment
            sentiment_result = sentiment_analyzer.analyze(demo["content"])
            keywords = keyword_extractor.extract_keywords(demo["content"])

            processed = ProcessedMention(
                mention_id=raw_mention.id,
                clean_text=sentiment_analyzer.preprocess(demo["content"]),
                sentiment_score=sentiment_result["sentiment_score"],
                sentiment_label=sentiment_result["sentiment_label"],
                sentiment_confidence=sentiment_result["sentiment_confidence"],
                keywords=keywords,
                processed_at=datetime.utcnow()
            )
            db.add(processed)
            await db.commit()

        logger.info(f"[SeedDemo] Seeded {len(demo_content)} demo mentions across {len(sources_data)} sources")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
