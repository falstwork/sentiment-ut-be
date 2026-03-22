import httpx
import base64
import logging
from datetime import datetime
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedditFetcher:
    """Fetcher for Reddit posts and comments"""

    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.search_terms = ["Universitas Terbuka", "UT kuliah", "Universitas Terbuka Indonesia"]
        self.subreddits = ["indonesia", "kuliah", "beasiswa", "PendidikanIndonesia"]

    def _get_auth_header(self) -> dict:
        """Get authentication header for Reddit API"""
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            credentials = f"{settings.REDDIT_CLIENT_ID}:{settings.REDDIT_CLIENT_SECRET}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {}

    async def _get_access_token(self, client: httpx.AsyncClient) -> Optional[str]:
        """Get Reddit OAuth access token"""
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            return None

        try:
            response = await client.post(
                f"{self.base_url}/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                headers=self._get_auth_header()
            )
            if response.status_code == 200:
                return response.json().get("access_token")
        except Exception:
            pass
        return None

    async def fetch_reddit(self) -> List[dict]:
        """Fetch posts from Reddit"""
        results = []
        access_token = None

        headers = {
            "User-Agent": settings.REDDIT_USER_AGENT
        }

        logger.info(f"[RedditFetcher] Client ID configured: {'YES' if settings.REDDIT_CLIENT_ID else 'NO'}")
        logger.info(f"[RedditFetcher] Client Secret configured: {'YES' if settings.REDDIT_CLIENT_SECRET else 'NO'}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get access token
            if settings.REDDIT_CLIENT_ID:
                logger.info("[RedditFetcher] Attempting to get access token...")
                access_token = await self._get_access_token(client)
                if access_token:
                    logger.info("[RedditFetcher] Access token obtained successfully")
                    headers["Authorization"] = f"Bearer {access_token}"
                else:
                    logger.warning("[RedditFetcher] Failed to get access token → using unauthenticated requests")

            # Fetch from each subreddit
            for subreddit in self.subreddits:
                try:
                    url = f"{self.base_url}/r/{subreddit}/search.json"
                    params = {
                        "q": "Universitas Terbuka",
                        "limit": 10,
                        "sort": "relevance",
                        "t": "month"
                    }
                    logger.info(f"[RedditFetcher] Hitting: {url} (r/{subreddit})")
                    response = await client.get(url, headers=headers, params=params)
                    logger.info(f"[RedditFetcher] Response for r/{subreddit}: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        children = data.get("data", {}).get("children", [])
                        logger.info(f"[RedditFetcher] Got {len(children)} posts from r/{subreddit}")

                        for child in children:
                            post = child.get("data", {})
                            created_utc = post.get("created_utc", 0)
                            posted_at = datetime.fromtimestamp(created_utc) if created_utc else datetime.utcnow()

                            results.append({
                                "external_id": post.get("id", ""),
                                "content": post.get("title", "") + " " + post.get("selftext", ""),
                                "author": post.get("author", "[deleted]"),
                                "posted_at": posted_at,
                                "url": f"https://reddit.com{post.get('permalink', '')}",
                                "source_name": f"Reddit r/{subreddit}",
                                "source_type": "reddit",
                                "metadata": {
                                    "subreddit": subreddit,
                                    "score": post.get("score", 0),
                                    "num_comments": post.get("num_comments", 0),
                                    "title": post.get("title", "")
                                }
                            })
                    elif response.status_code == 401:
                        logger.warning(f"[RedditFetcher] 401 Unauthorized for r/{subreddit} — invalid credentials → MOCK DATA")
                        break
                    elif response.status_code == 429:
                        logger.warning(f"[RedditFetcher] 429 Rate limited for r/{subreddit} → MOCK DATA")
                        break
                    else:
                        logger.warning(f"[RedditFetcher] Non-200 response ({response.status_code}) for r/{subreddit}")
                except Exception as e:
                    logger.error(f"[RedditFetcher] Exception for r/{subreddit}: {e}")
                    continue

        # If no authenticated results, return mock data for demo
        if not results:
            logger.warning("[RedditFetcher] No results → returning MOCK DATA")
            results = self._get_mock_data()

        logger.info(f"[RedditFetcher] Returning {len(results)} results")
        return results

    def _get_mock_data(self) -> List[dict]:
        """Return mock data for demo purposes when API is not configured"""
        return [
            {
                "external_id": "mock_reddit_1",
                "content": "Pengalaman kuliah di Universitas Terbuka - sangat fleksibel untuk pekerja seperti saya. Bisa belajar mandiri dengan jadwal sendiri.",
                "author": "reddit_user_1",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "Reddit r/indonesia",
                "source_type": "reddit",
                "metadata": {"subreddit": "indonesia", "score": 45, "num_comments": 12}
            },
            {
                "external_id": "mock_reddit_2",
                "content": "Tips belajar mandiri di UT biar lulus tepat waktu. Strategi manajemen waktu sangat penting.",
                "author": "reddit_user_2",
                "posted_at": datetime.utcnow(),
                "url": "",
                "source_name": "Reddit r/kuliah",
                "source_type": "reddit",
                "metadata": {"subreddit": "kuliah", "score": 28, "num_comments": 8}
            }
        ]


# Singleton instance
reddit_fetcher = RedditFetcher()
