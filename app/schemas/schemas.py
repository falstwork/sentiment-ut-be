from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


# Source schemas
class SourceBase(BaseModel):
    name: str
    type: str
    url: Optional[str] = None
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceResponse(SourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Mention schemas
class MentionBase(BaseModel):
    source: str
    content: str
    author: Optional[str] = None
    sentiment: str
    sentiment_score: float
    posted_at: Optional[datetime] = None
    url: Optional[str] = None


class MentionResponse(MentionBase):
    id: int

    class Config:
        from_attributes = True


class MentionDetail(MentionResponse):
    clean_text: Optional[str] = None
    sentiment_confidence: float
    keywords: Optional[List[str]] = None


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class MentionsListResponse(BaseModel):
    data: List[MentionResponse]
    pagination: PaginationInfo


# Analytics schemas
class SentimentBreakdown(BaseModel):
    positive: float
    neutral: float
    negative: float


class SentimentChange(BaseModel):
    positive: float
    neutral: float
    negative: float


class KeywordInfo(BaseModel):
    keyword: str
    count: int
    sentiment: str


class AnalyticsSummary(BaseModel):
    total_mentions: int
    total_mentions_change: float
    sentiment_breakdown: SentimentBreakdown
    sentiment_change: SentimentChange
    last_updated: datetime
    trend: str
    top_keywords: List[KeywordInfo]


class TrendDataPoint(BaseModel):
    date: str
    positive: int
    neutral: int
    negative: int


class AnalyticsTrendsResponse(BaseModel):
    data: List[TrendDataPoint]
    period: str


class VolumeDataPoint(BaseModel):
    date: str
    volume: int


class AnalyticsVolumeResponse(BaseModel):
    data: List[VolumeDataPoint]


class SourceBreakdown(BaseModel):
    source: str
    total: int
    positive: int
    neutral: int
    negative: int
    percentage: float


class AnalyticsBySourceResponse(BaseModel):
    data: List[SourceBreakdown]


class TrendingTopic(BaseModel):
    topic: str
    change_percentage: float
    direction: str  # 'up' or 'down'
    sentiment: str


class AnalyticsTrendingResponse(BaseModel):
    data: List[TrendingTopic]


class KeywordsResponse(BaseModel):
    data: List[KeywordInfo]


# Fetch schemas
class FetchManualRequest(BaseModel):
    source: Optional[str] = None  # If None, fetch all sources


class FetchManualResponse(BaseModel):
    status: str
    job_id: str
    sources_triggered: List[str]


class FetchStatusResponse(BaseModel):
    job_id: str
    status: str
    sources: List[str]
    items_fetched: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# Health check
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
