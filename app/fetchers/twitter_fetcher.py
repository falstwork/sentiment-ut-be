import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class TwitterFetcher:
    """Fetcher for Twitter/X tweets"""

    def __init__(self):
        self.base_url = "https://api.twitter.com/2"
        self.bearer_token = settings.TWITTER_BEARER_TOKEN
        self.search_terms = ["Universitas Terbuka", "UT Indonesia", "#UniversitasTerbuka"]

    def _get_headers(self) -> dict:
        """Get headers with bearer token"""
        if self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}"}
        return {}

    async def fetch_twitter(self) -> List[dict]:
        """Fetch tweets from Twitter API v2"""
        results = []

        logger.info(f"[TwitterFetcher] Bearer token configured: {'YES (len=' + str(len(self.bearer_token)) + ')' if self.bearer_token else 'NO'}")

        if not self.bearer_token:
            logger.warning("[TwitterFetcher] No bearer token found → returning MOCK DATA")
            return self._get_mock_data()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for term in self.search_terms[:2]:  # Limit queries
                try:
                    url = f"{self.base_url}/tweets/search/recent"
                    params = {
                        "query": f"{term} lang:id",
                        "max_results": 10,
                        "tweet.fields": "created_at,author_id,public_metrics",
                        "expansions": "author_id",
                        "user.fields": "name,username"
                    }
                    headers = self._get_headers()

                    logger.info(f"[TwitterFetcher] Hitting API for term: '{term}' → {url}")
                    response = await client.get(url, params=params, headers=headers)
                    logger.info(f"[TwitterFetcher] Response status for '{term}': {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        tweets = data.get("data", [])
                        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                        logger.info(f"[TwitterFetcher] Got {len(tweets)} tweets for term '{term}'")

                        for tweet in tweets:
                            author = users.get(tweet.get("author_id", ""), {})
                            created_at_str = tweet.get("created_at", "")

                            try:
                                posted_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                            except Exception:
                                posted_at = datetime.utcnow()

                            results.append({
                                "external_id": tweet.get("id", ""),
                                "content": tweet.get("text", ""),
                                "author": author.get("username", "unknown"),
                                "posted_at": posted_at,
                                "url": f"https://twitter.com/i/web/status/{tweet.get('id', '')}",
                                "source_name": "Twitter (X)",
                                "source_type": "twitter",
                                "metadata": {
                                    "author_id": tweet.get("author_id", ""),
                                    "author_name": author.get("name", ""),
                                    "retweet_count": tweet.get("public_metrics", {}).get("retweet_count", 0),
                                    "like_count": tweet.get("public_metrics", {}).get("like_count", 0)
                                }
                            })
                    elif response.status_code == 429:
                        logger.warning(f"[TwitterFetcher] Rate limited for term '{term}' → returning MOCK DATA")
                        break
                    else:
                        logger.warning(f"[TwitterFetcher] Non-200 response ({response.status_code}) for '{term}' → returning MOCK DATA")
                        logger.debug(f"[TwitterFetcher] Response body: {response.text[:500]}")
                        break
                except Exception as e:
                    logger.error(f"[TwitterFetcher] Exception for term '{term}': {e} → returning MOCK DATA")
                    continue

        if not results:
            logger.warning("[TwitterFetcher] No results from API → returning MOCK DATA")
            return self._get_mock_data()

        logger.info(f"[TwitterFetcher] Returning {len(results)} REAL tweets")
        return results

    def _get_mock_data(self) -> List[dict]:
        """Return mock data for demo purposes when API is not configured"""
        return [
            {
                "external_id": "mock_twitter_1",
                "content": "Universitas Terbuka emang solusi tepat buat yang mau kuliah sambil kerja. Fleksibel dan terjangkau!",
                "author": "@pendidikan_ind",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "Twitter (X)",
                "source_type": "twitter",
                "metadata": {"retweet_count": 12, "like_count": 45}
            },
            {
                "external_id": "mock_twitter_2",
                "content": "Server pendaftaran UT lagi down lagi nih, hope they fix this soon",
                "author": "@mahasiswa_ut",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "Twitter (X)",
                "source_type": "twitter",
                "metadata": {"retweet_count": 5, "like_count": 8}
            },
            {
                "external_id": "mock_twitter_3",
                "content": "Selamat kepada Graduates UT tahun 2026! Prestasi membanggakan.",
                "author": "@berita_pendidikan",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "Twitter (X)",
                "source_type": "twitter",
                "metadata": {"retweet_count": 89, "like_count": 234}
            }
        ]


# Singleton instance
twitter_fetcher = TwitterFetcher()
