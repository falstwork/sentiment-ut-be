from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 'rss', 'reddit', 'twitter', 'youtube'
    url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    raw_mentions = relationship("RawMention", back_populates="source")
    fetch_logs = relationship("FetchLog", back_populates="source")
    hourly_aggregates = relationship("HourlyAggregate", back_populates="source")
    daily_aggregates = relationship("DailyAggregate", back_populates="source")


class RawMention(Base):
    __tablename__ = "raw_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    external_id = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    url = Column(Text, nullable=True)
    mention_metadata = Column(JSON, nullable=True)

    source = relationship("Source", back_populates="raw_mentions")
    processed_mention = relationship("ProcessedMention", back_populates="raw_mention", uselist=False)


class ProcessedMention(Base):
    __tablename__ = "processed_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mention_id = Column(Integer, ForeignKey("raw_mentions.id"), nullable=False, unique=True)
    clean_text = Column(Text, nullable=True)
    sentiment_score = Column(Float, default=0.0)  # -1 to 1
    sentiment_label = Column(String(20), default="neutral")  # positive, neutral, negative
    sentiment_confidence = Column(Float, default=0.0)  # 0 to 1
    keywords = Column(JSON, nullable=True)  # JSON array of keywords
    processed_at = Column(DateTime, default=datetime.utcnow)

    raw_mention = relationship("RawMention", back_populates="processed_mention")


class HourlyAggregate(Base):
    __tablename__ = "hourly_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    hour_bucket = Column(DateTime, nullable=False)
    positive_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)

    source = relationship("Source", back_populates="hourly_aggregates")


class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    date_bucket = Column(Date, nullable=False)
    positive_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)

    source = relationship("Source", back_populates="daily_aggregates")


class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    items_fetched = Column(Integer, default=0)
    items_new = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    status = Column(String(20), default="success")  # success, partial, failed
    error_message = Column(Text, nullable=True)

    source = relationship("Source", back_populates="fetch_logs")


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    channel_title = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
