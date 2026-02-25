"""
processor/deduplicator.py — Tracks seen article URLs to avoid email repeats.
"""

import json
import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

SEEN_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "seen_articles.json")


def _load_seen() -> set:
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception as e:
        logger.warning(f"[Dedup] Could not load seen file: {e}")
        return set()


def _save_seen(seen: set):
    # Keep only last 2000 URLs to avoid file bloat
    seen_list = list(seen)[-2000:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, indent=2)


def filter_new_articles(articles: List[Dict]) -> List[Dict]:
    """Remove articles whose URLs have already been seen."""
    seen = _load_seen()
    new_articles = [a for a in articles if a.get("url") not in seen]
    logger.info(f"[Dedup] {len(articles)} articles → {len(new_articles)} new (skipped {len(articles) - len(new_articles)})")
    return new_articles


def mark_articles_seen(articles: List[Dict]):
    """Add article URLs to the seen set after a successful digest send."""
    seen = _load_seen()
    for a in articles:
        if a.get("url"):
            seen.add(a["url"])
    _save_seen(seen)
    logger.info(f"[Dedup] Marked {len(articles)} articles as seen")
