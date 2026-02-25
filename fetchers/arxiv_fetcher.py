"""
fetchers/arxiv_fetcher.py — Fetches recent AI research papers from arXiv.
"""

import arxiv
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from config import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS, LOOKBACK_HOURS

logger = logging.getLogger(__name__)


def fetch_arxiv_papers() -> List[Dict]:
    """
    Fetches the most recent papers from arXiv AI/ML/NLP categories
    published in the last LOOKBACK_HOURS and returns standardised article dicts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles = []

    # Build query string for multiple categories
    cat_query = " OR ".join(f"cat:{cat}" for cat in ARXIV_CATEGORIES)

    try:
        client = arxiv.Client(num_retries=3, delay_seconds=2)
        search = arxiv.Search(
            query=cat_query,
            max_results=ARXIV_MAX_RESULTS,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        for result in client.results(search):
            published = result.published
            if published and published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)

            if published and published < cutoff:
                continue

            authors = ", ".join(a.name for a in result.authors[:4])
            if len(result.authors) > 4:
                authors += " et al."

            articles.append({
                "title": result.title,
                "url": result.entry_id,
                "summary": result.summary[:600],
                "source": "arXiv",
                "logo": "📄",
                "published": published,
                "category": "Research",
                "authors": authors,
            })

        logger.info(f"[arXiv] {len(articles)} papers fetched")
    except Exception as e:
        logger.warning(f"[arXiv] Fetch failed: {e}")

    return articles
