"""
fetchers/rss_fetcher.py — Fetches articles from RSS/Atom feeds.
Now covers BOTH company blogs AND AI news outlets (TechCrunch, Verge, etc.)
"""

import feedparser
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from config import ALL_RSS_FEEDS, LOOKBACK_HOURS, TRACKED_PEOPLE

logger = logging.getLogger(__name__)


def _parse_entry(entry: dict, feed_cfg: dict) -> Dict:
    """Convert a feedparser entry into a standardised article dict."""
    feed_name = feed_cfg["name"]
    feed_logo = feed_cfg.get("logo", "📰")
    feed_type = feed_cfg.get("type", "news")

    pub_date = None
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        if hasattr(entry, attr) and getattr(entry, attr):
            pub_date = datetime(*getattr(entry, attr)[:6], tzinfo=timezone.utc)
            break

    summary = getattr(entry, "summary", "") or ""
    if "<" in summary and ">" in summary:
        try:
            from bs4 import BeautifulSoup
            summary = BeautifulSoup(summary, "html.parser").get_text(separator=" ", strip=True)
        except Exception:
            pass
    summary = summary[:500]

    return {
        "title": getattr(entry, "title", "Untitled"),
        "url": getattr(entry, "link", ""),
        "summary": summary,
        "source": feed_name,
        "logo": feed_logo,
        "type": feed_type,
        "published": pub_date,
        "category": "News" if feed_type == "news" else "Company",
    }


def fetch_rss_articles() -> List[Dict]:
    """
    Fetches articles from ALL RSS feeds (news outlets + company blogs)
    published within LOOKBACK_HOURS.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles = []

    for feed_cfg in ALL_RSS_FEEDS:
        name = feed_cfg["name"]
        url = feed_cfg["url"]
        try:
            feed = feedparser.parse(url, agent="AINewsDigest/1.0")
            entries = feed.get("entries", [])
            count = 0

            for entry in entries:
                article = _parse_entry(entry, feed_cfg)

                if article["published"] and article["published"] < cutoff:
                    continue

                people_mentioned = [
                    p for p in TRACKED_PEOPLE
                    if p.lower() in (article["title"] + article["summary"]).lower()
                ]
                if people_mentioned:
                    article["people_mentioned"] = people_mentioned

                if article["url"]:
                    articles.append(article)
                    count += 1

            logger.debug(f"[RSS] {name}: {count} articles in window")

        except Exception as e:
            logger.warning(f"[RSS] Failed to fetch {name} ({url}): {e}")

    news_count = sum(1 for a in articles if a.get("type") == "news")
    company_count = sum(1 for a in articles if a.get("type") == "company")
    logger.info(f"[RSS] Total: {len(articles)} articles (News: {news_count}, Company: {company_count})")
    return articles

