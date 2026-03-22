import feedparser
import httpx
import logging
import os
from datetime import datetime
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# File handler for RSS response logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
RSS_LOG_FILE = os.path.join(LOG_DIR, "rss_response.log")

def _log_to_file(message: str):
    """Append message to RSS log file"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(RSS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
    except Exception as e:
        logger.error(f"Failed to write to RSS log: {e}")


class RSSFetcher:
    """Fetcher for Google News RSS feeds"""

    def __init__(self):
        self.search_terms = ["Universitas Terbuka"]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def build_rss_url(self, search_term: str) -> str:
        """Build Google News RSS URL for search term with 2-year date filter"""
        encoded_term = search_term.replace(" ", "%20")
        return f"https://news.google.com/rss/search?q={encoded_term}%20when:730d%20lang:id&hl=id&gl=ID&ceid=ID:id"

    async def fetch_google_news(self) -> List[dict]:
        """Fetch news from Google News RSS"""
        results = []
        _log_to_file(f"=== START RSS FETCH ===")

        async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
            for term in self.search_terms:
                url = self.build_rss_url(term)
                logger.info(f"[RSSFetcher] Hitting: {url}")
                _log_to_file(f"URL: {url}")
                try:
                    response = await client.get(url)
                    logger.info(f"[RSSFetcher] Response for '{term}': status={response.status_code}, content_length={len(response.text)}")
                    _log_to_file(f"Response Status: {response.status_code}, Length: {len(response.text)}")
                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        logger.info(f"[RSSFetcher] Parsed feed for '{term}': {len(feed.entries)} entries")
                        _log_to_file(f"Feed Entries Count: {len(feed.entries)}")
                        for idx, entry in enumerate(feed.entries):  # No limit - all entries within date range
                            # Log raw entry details
                            entry_link = entry.get("link", "")
                            entry_id = entry.get("id", "")
                            entry_title = entry.get("title", "")
                            entry_summary = entry.get("summary", "")[:200] if entry.get("summary") else ""
                            entry_source = entry.get("source", "")
                            entry_author = entry.get("author", "Unknown")

                            _log_to_file(f"--- Entry {idx} ---")
                            _log_to_file(f"  Title: {entry_title}")
                            _log_to_file(f"  Link: {entry_link}")
                            _log_to_file(f"  ID: {entry_id}")
                            _log_to_file(f"  Source: {entry_source}")
                            _log_to_file(f"  Author: {entry_author}")
                            _log_to_file(f"  Summary (200 chars): {entry_summary}")

                            # Parse published date
                            published_at = None
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                try:
                                    published_at = datetime(*entry.published_parsed[:6])
                                    _log_to_file(f"  Published: {published_at}")
                                except Exception as e:
                                    _log_to_file(f"  Published Parse Error: {e}")
                                    pass

                            results.append({
                                "external_id": entry.get("id", entry.get("link", "")),
                                "content": entry.get("title", "") + ". " + entry.get("summary", ""),
                                "author": entry.get("author", "Unknown"),
                                "posted_at": published_at or datetime.utcnow(),
                                "url": entry.get("link", ""),
                                "source_name": "Google News",
                                "source_type": "rss",
                                "metadata": {
                                    "title": entry.get("title", ""),
                                    "source": entry.get("source", {}).get("href", "") if isinstance(entry.get("source"), dict) else str(entry.get("source", ""))
                                }
                            })
                    else:
                        logger.warning(f"[RSSFetcher] Non-200 response for '{term}': {response.status_code}")
                        _log_to_file(f"Non-200 Response: {response.status_code}")
                except Exception as e:
                    logger.error(f"[RSSFetcher] Exception for term '{term}': {e}")
                    _log_to_file(f"Exception: {e}")
                    continue

        _log_to_file(f"=== END RSS FETCH - Total Results: {len(results)} ===\n")
        logger.info(f"[RSSFetcher] Returning {len(results)} total results")
        return results


# Singleton instance
rss_fetcher = RSSFetcher()
