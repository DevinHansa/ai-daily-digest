"""
processor/vector_memory.py — Semantic vector memory using ChromaDB.

Stores article title+summary embeddings locally. Each run:
  1. Embeds candidate articles using sentence-transformers (all-MiniLM-L6-v2)
  2. Queries ChromaDB for cosine similarity against all previously sent articles
  3. Filters out articles with similarity > threshold (default 0.75)
  4. After sending, stores the sent articles for future dedup

No API cost — everything runs locally.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple

import chromadb
from sentence_transformers import SentenceTransformer

from config import TOPIC_MEMORY_DAYS

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
_COLLECTION_NAME = "sent_articles"

# ── Similarity threshold ──────────────────────────────────────────────────────
# Articles with cosine similarity > this value are considered duplicates.
# 0.75 = very similar topic, 0.85 = near-identical, 0.60 = loosely related
SIMILARITY_THRESHOLD = 0.72

# ── Model (loaded lazily) ─────────────────────────────────────────────────────
_model = None
_client = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        logger.info("[VectorMem] Loading sentence-transformers model (first run only)…")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_collection():
    global _client, _collection
    if _collection is None:
        os.makedirs(_DB_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=_DB_DIR)
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _make_text(article: Dict) -> str:
    """Combine title + summary into a single string for embedding."""
    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()[:300]
    return f"{title}. {summary}" if summary else title


def _purge_expired():
    """Remove articles older than TOPIC_MEMORY_DAYS from the collection."""
    collection = _get_collection()
    if collection.count() == 0:
        return

    cutoff = (datetime.now(timezone.utc) - timedelta(days=TOPIC_MEMORY_DAYS)).isoformat()

    try:
        # Get all items and filter by date
        all_items = collection.get(include=["metadatas"])
        expired_ids = [
            id_ for id_, meta in zip(all_items["ids"], all_items["metadatas"])
            if meta.get("date", "") < cutoff
        ]
        if expired_ids:
            collection.delete(ids=expired_ids)
            logger.info(f"[VectorMem] Purged {len(expired_ids)} expired articles (>{TOPIC_MEMORY_DAYS} days old)")
    except Exception as e:
        logger.warning(f"[VectorMem] Purge failed: {e}")


def filter_similar(articles: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Remove articles that are semantically similar to previously sent articles.
    Returns (new_articles, num_filtered).
    """
    collection = _get_collection()
    _purge_expired()

    if collection.count() == 0:
        logger.info("[VectorMem] Empty memory — all articles are new")
        return articles, 0

    model = _get_model()
    new_articles = []
    filtered = 0

    for article in articles:
        text = _make_text(article)
        if not text.strip():
            new_articles.append(article)
            continue

        # Embed and query
        embedding = model.encode(text).tolist()
        results = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances", "metadatas"],
        )

        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Cosine similarity = 1 - distance
        if results["distances"] and results["distances"][0]:
            distance = results["distances"][0][0]
            similarity = 1 - distance

            if similarity >= SIMILARITY_THRESHOLD:
                old_title = results["metadatas"][0][0].get("title", "?") if results["metadatas"][0] else "?"
                logger.info(
                    f"[VectorMem] BLOCKED (sim={similarity:.2f}): "
                    f"'{article.get('title','')[:50]}' ≈ '{old_title[:50]}'"
                )
                filtered += 1
                continue

        new_articles.append(article)

    logger.info(f"[VectorMem] {len(new_articles)} new, {filtered} blocked as duplicates")
    return new_articles, filtered


def save_articles(articles: List[Dict]):
    """Store sent articles in ChromaDB for future dedup."""
    if not articles:
        return

    collection = _get_collection()
    model = _get_model()
    now_str = datetime.now(timezone.utc).isoformat()

    texts = []
    embeddings = []
    ids = []
    metadatas = []

    for i, article in enumerate(articles):
        text = _make_text(article)
        if not text.strip():
            continue

        # Use URL as a unique ID, or generate one
        article_id = article.get("url", f"article_{now_str}_{i}")
        # ChromaDB IDs must be strings and unique
        article_id = article_id.replace("https://", "").replace("http://", "")[:512]

        texts.append(text)
        ids.append(article_id)
        metadatas.append({
            "title": article.get("title", "")[:200],
            "source": article.get("source", ""),
            "date": now_str,
            "url": article.get("url", ""),
        })

    if not texts:
        return

    embeddings = model.encode(texts).tolist()

    # Upsert to handle duplicates gracefully
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    logger.info(f"[VectorMem] Stored {len(texts)} articles in vector memory")

