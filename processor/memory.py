"""
processor/memory.py — Topic-aware memory system.

Stores both:
  - seen_urls: prevents exact duplicate articles
  - seen_topics: prevents similar stories even from different sources
    (e.g. "Anthropic China Claude" prevents 3 different articles about the same event)

Topics expire after TOPIC_MEMORY_DAYS (default 7) so stories can be revisited
when there's a new development a week later.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple

from config import TOPIC_MEMORY_DAYS

logger = logging.getLogger(__name__)

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "memory.json")


def _load() -> Dict:
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        return {"seen_urls": [], "seen_topics": []}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[Memory] Could not load memory file: {e}")
        return {"seen_urls": [], "seen_topics": []}


def _save(data: Dict):
    # Trim URL list to last 3000
    data["seen_urls"] = data["seen_urls"][-3000:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _purge_expired_topics(topics: List[Dict]) -> List[Dict]:
    """Remove topics older than TOPIC_MEMORY_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=TOPIC_MEMORY_DAYS)
    return [
        t for t in topics
        if datetime.fromisoformat(t["date"]).replace(tzinfo=timezone.utc) >= cutoff
    ]


def get_seen_topics() -> List[str]:
    """
    Returns a list of recent topic keyword strings for the Critic Agent prompt.
    e.g. ["anthropic china claude training", "openai o3 benchmark", ...]
    """
    data = _load()
    active = _purge_expired_topics(data.get("seen_topics", []))
    return [t["keywords"] for t in active]


def filter_new_articles(articles: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Remove articles whose URLs were already sent.
    Returns (new_articles, skipped_count).
    """
    data = _load()
    seen_urls = set(data.get("seen_urls", []))
    new = [a for a in articles if a.get("url") not in seen_urls]
    skipped = len(articles) - len(new)
    logger.info(f"[Memory] URL dedup: {len(new)} new, {skipped} skipped")
    return new, skipped


def save_digest(articles: List[Dict]):
    """
    After a successful send, save:
    - All article URLs to seen_urls
    - All topic_keywords to seen_topics (with expiry date)
    """
    data = _load()
    seen_urls = set(data.get("seen_urls", []))
    seen_topics = _purge_expired_topics(data.get("seen_topics", []))

    now_str = datetime.now(timezone.utc).isoformat()
    existing_kw = {t["keywords"] for t in seen_topics}

    for a in articles:
        if a.get("url"):
            seen_urls.add(a["url"])
        kw = a.get("topic_keywords", "").strip()
        if kw and kw not in existing_kw:
            seen_topics.append({"keywords": kw, "date": now_str})
            existing_kw.add(kw)

    data["seen_urls"] = list(seen_urls)
    data["seen_topics"] = seen_topics
    _save(data)
    logger.info(f"[Memory] Saved {len(articles)} articles and {len(seen_topics)} active topics")
