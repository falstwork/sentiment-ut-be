import httpx
import logging
from datetime import datetime
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeFetcher:
    """Fetcher for YouTube videos and comments"""

    def __init__(self):
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.search_terms = ["Universitas Terbuka", "UT Indonesia", "kuliah terbuka"]
        self.api_key = settings.YOUTUBE_API_KEY

    async def fetch_youtube(self) -> List[dict]:
        """Fetch videos from YouTube Data API"""
        results = []

        logger.info(f"[YouTubeFetcher] API Key configured: {'YES' if self.api_key else 'NO'}")

        if not self.api_key:
            logger.warning("[YouTubeFetcher] No API key → returning MOCK DATA")
            return self._get_mock_data()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for term in self.search_terms:
                try:
                    # Search for videos
                    search_url = f"{self.base_url}/search"
                    params = {
                        "part": "snippet",
                        "q": term,
                        "type": "video",
                        "order": "relevance",
                        "publishedAfter": "2026-01-01T00:00:00Z",
                        "maxResults": 10,
                        "relevanceLanguage": "id"
                    }
                    headers = {"Accept": "application/json"}
                    logger.info(f"[YouTubeFetcher] Hitting API for term: '{term}'")
                    response = await client.get(
                        search_url,
                        params={**params, "key": self.api_key},
                        headers=headers
                    )
                    logger.info(f"[YouTubeFetcher] Response for '{term}': {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        items = data.get("items", [])
                        logger.info(f"[YouTubeFetcher] Got {len(items)} items for term '{term}'")

                        for item in items:
                            snippet = item.get("snippet", {})
                            video_id = item.get("id", {}).get("videoId", "")

                            if not video_id:
                                continue

                            published_str = snippet.get("publishedAt", "")
                            try:
                                posted_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                            except Exception:
                                posted_at = datetime.utcnow()

                            results.append({
                                "external_id": video_id,
                                "content": f"{snippet.get('title', '')} - {snippet.get('description', '')}",
                                "author": snippet.get("channelTitle", "Unknown"),
                                "posted_at": posted_at,
                                "url": f"https://youtube.com/watch?v={video_id}",
                                "source_name": "YouTube",
                                "source_type": "youtube",
                                "metadata": {
                                    "title": snippet.get("title", ""),
                                    "channel_id": snippet.get("channelId", ""),
                                    "channel_title": snippet.get("channelTitle", ""),
                                    "description": snippet.get("description", ""),
                                    "video_id": video_id
                                }
                            })
                    elif response.status_code == 403:
                        logger.warning(f"[YouTubeFetcher] 403 Forbidden for '{term}' — quota exceeded or invalid key → MOCK DATA")
                        break
                    elif response.status_code == 404:
                        logger.warning(f"[YouTubeFetcher] 404 Not Found for '{term}' → MOCK DATA")
                        break
                    else:
                        logger.warning(f"[YouTubeFetcher] Non-200 response ({response.status_code}) for '{term}'")
                except Exception as e:
                    logger.error(f"[YouTubeFetcher] Exception for term '{term}': {e}")
                    continue

        if not results:
            logger.warning("[YouTubeFetcher] No results from API → returning MOCK DATA")

        logger.info(f"[YouTubeFetcher] Returning {len(results)} results")
        return results

    def _get_mock_data(self) -> List[dict]:
        """Return mock data for demo purposes when API is not configured"""
        return [
            {
                "external_id": "mock_yt_1",
                "content": "Pengalaman kuliah di UT sangat fleksibel buat kerja dan keluarga. Sistem belajar mandiri yang sangat membantu.",
                "author": "Channel Edukasi Indonesia",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "YouTube",
                "source_type": "youtube",
                "metadata": {"title": "Review Universitas Terbuka", "channel_title": "Channel Edukasi Indonesia"}
            },
            {
                "external_id": "mock_yt_2",
                "content": "Tutorial pendaftaran UT online - step by step. Sangat mudah dipahami.",
                "author": "Info Kuliah Indonesia",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "YouTube",
                "source_type": "youtube",
                "metadata": {"title": "Tutorial Pendaftaran UT", "channel_title": "Info Kuliah Indonesia"}
            }
        ]


# Singleton instance
youtube_fetcher = YouTubeFetcher()
