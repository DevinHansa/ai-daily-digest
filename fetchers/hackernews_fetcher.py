"""
fetchers/hackernews_fetcher.py — Fetches top AI-related stories from Hacker News.
"""

import requests
import logging
from typing import List, Dict

from config import HN_TOP_STORIES_COUNT, HN_AI_KEYWORDS

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"


def _is_ai_related(title: str) -> bool:
    """Quick keyword check before sending to LLM."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in HN_AI_KEYWORDS)


def fetch_hn_articles() -> List[Dict]:
    """
    Fetches top HN stories, filters for AI-related titles,
    and returns standardised article dicts.
    """
    articles = []

    try:
        # Get top story IDs
        resp = requests.get(f"{HN_API}/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:HN_TOP_STORIES_COUNT]

        for story_id in story_ids:
            try:
                s_resp = requests.get(f"{HN_API}/item/{story_id}.json", timeout=8)
                s_resp.raise_for_status()
                story = s_resp.json()

                if not story or story.get("type") != "story":
                    continue

                title = story.get("title", "")
                if not _is_ai_related(title):
                    continue

                url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                score = story.get("score", 0)
                comments = story.get("descendants", 0)

                articles.append({
                    "title": title,
                    "url": url,
                    "summary": f"HN Score: {score} points | {comments} comments",
                    "source": "Hacker News",
                    "logo": "🟠",
                    "published": None,
                    "category": "Community",
                    "hn_score": score,
                })

            except Exception as e:
                logger.debug(f"[HN] Skipping story {story_id}: {e}")

        logger.info(f"[HN] {len(articles)} AI stories found in top {HN_TOP_STORIES_COUNT}")
    except Exception as e:
        logger.warning(f"[HN] Fetch failed: {e}")

    return articles
