"""
processor/memory.py — URL-based dedup memory.

Stores seen article URLs to prevent sending the exact same link twice.
Semantic (topic) dedup is handled by processor/vector_memory.py using embeddings.
"""

import json
import logging
import os
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "memory.json")


def _load() -> Dict:
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        return {"seen_urls": []}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Migrate old format: drop seen_topics if present
            if "seen_topics" in data:
                del data["seen_topics"]
            return data
    except Exception as e:
        logger.warning(f"[Memory] Could not load memory file: {e}")
        return {"seen_urls": []}


def _save(data: Dict):
    data["seen_urls"] = data["seen_urls"][-3000:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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


def save_urls(articles: List[Dict]):
    """Save article URLs after a successful send."""
    data = _load()
    seen_urls = set(data.get("seen_urls", []))
    for a in articles:
        if a.get("url"):
            seen_urls.add(a["url"])
    data["seen_urls"] = list(seen_urls)
    _save(data)
    logger.info(f"[Memory] Saved {len(articles)} article URLs")
