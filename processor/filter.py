"""
processor/filter.py — Uses Gemini to score, summarize, and categorize articles.

Free-tier safe: batches of 5 articles with 12s pause between batches.
Exponential backoff on 429 rate-limit errors (30s, 60s, 90s, 120s).
"""

import os
import json
import logging
import time
from typing import List, Dict

import google.generativeai as genai
from dotenv import load_dotenv

from config import MAX_ARTICLES_PER_DIGEST, MIN_RELEVANCE_SCORE, TRACKED_PEOPLE

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

_MODEL = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"temperature": 0.3, "response_mime_type": "application/json"},
)

_SYSTEM_PROMPT = """You are an expert AI research analyst. Your job is to evaluate news articles and research papers about artificial intelligence and return a JSON array.

For each article evaluate:
1. Relevance to cutting-edge AI development (products, research, tools, opinions from top researchers)
2. Whether it is from or about: OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, xAI, SSI, or top AI figures: {people}

Return a JSON ARRAY where each element is:
{{
  "index": <original index number>,
  "relevance_score": <integer 0-10, 10 = extremely important AI news>,
  "tldr": "<2-3 sentence summary. Be specific: mention key numbers, model names, capabilities>",
  "category": "<one of: Research | Product Launch | Tool/Library | Opinion/Interview | Policy | Other>",
  "why_important": "<1 sentence: what makes this significant for AI practitioners>"
}}

Only include entries with relevance_score >= {min_score}. Skip duplicates or off-topic articles silently (just omit them from output).
""".format(
    people=", ".join(TRACKED_PEOPLE),
    min_score=MIN_RELEVANCE_SCORE,
)


def _build_batch_prompt(articles: List[Dict]) -> str:
    lines = [_SYSTEM_PROMPT, "\n\nArticles to evaluate:\n"]
    for i, a in enumerate(articles):
        lines.append(f"[{i}] SOURCE: {a.get('source', 'Unknown')}")
        lines.append(f"    TITLE: {a.get('title', '')}")
        if a.get("authors"):
            lines.append(f"    AUTHORS: {a['authors']}")
        if a.get("people_mentioned"):
            lines.append(f"    PEOPLE MENTIONED: {', '.join(a['people_mentioned'])}")
        lines.append(f"    SUMMARY: {a.get('summary', '')[:300]}")
        lines.append("")
    lines.append("\nReturn ONLY a valid JSON array. No markdown code fences.")
    return "\n".join(lines)


def _call_gemini_with_retry(prompt: str, retries: int = 4) -> str:
    for attempt in range(retries):
        try:
            response = _MODEL.generate_content(prompt)
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                wait = 30 * (attempt + 1)   # 30s → 60s → 90s → 120s
                logger.warning(f"[Gemini] Rate-limited (attempt {attempt+1}/{retries}). Waiting {wait}s…")
                time.sleep(wait)
            else:
                logger.warning(f"[Gemini] Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(10)
    raise RuntimeError("Gemini API failed after all retries")


# ─── Keyword-based pre-scorer ─────────────────────────────────────────────────
# Runs BEFORE Gemini to rank/filter articles, so we only send the best ~10 to API
_HIGH_VALUE_KEYWORDS = [
    "openai", "anthropic", "deepmind", "gemini", "gpt", "claude", "llama",
    "mistral", "grok", "o1", "o3", "o4", "sora", "dall-e", "ssi",
    "karpathy", "sutskever", "hassabis", "altman", "lecun", "hinton",
    "transformer", "llm", "foundation model", "reasoning", "alignment", "agi",
    "reinforcement learning", "rlhf", "fine-tun", "multimodal", "benchmark",
    "agent", "agentic", "tool use", "chain of thought",
]


def _keyword_prescore(article: Dict) -> int:
    """Fast keyword-based pre-score: 0-5. No API call needed."""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    score = sum(1 for kw in _HIGH_VALUE_KEYWORDS if kw in text)
    # Boost for people mentions
    if article.get("people_mentioned"):
        score += 3
    # Boost for company sources
    if article.get("source", "") in (
        "OpenAI Blog", "Anthropic News", "Google DeepMind Blog",
        "Meta AI Blog", "Mistral AI News", "Safe Superintelligence (SSI)",
    ):
        score += 4
    return score


def filter_and_summarize(articles: List[Dict]) -> List[Dict]:
    """
    Phase 1: Keyword pre-score all articles (no API).
    Phase 2: Send top 10 to one single Gemini call.
    Phase 3: If Gemini fails, return keyword-scored articles with basic summaries.
    """
    if not articles:
        logger.info("[Filter] No articles to process")
        return []

    # Phase 1 — keyword pre-score
    for a in articles:
        a["_prescore"] = _keyword_prescore(a)

    ranked = sorted(articles, key=lambda x: x["_prescore"], reverse=True)
    candidates = ranked[:10]   # Only send top 10 to Gemini — 1 API call

    logger.info(f"[Filter] Sending {len(candidates)} pre-ranked articles to Gemini…")
    prompt = _build_batch_prompt(candidates)

    try:
        raw = _call_gemini_with_retry(prompt)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        results = json.loads(raw)

        enriched = []
        for item in results:
            idx = item.get("index")
            if idx is None or idx >= len(candidates):
                continue
            article = dict(candidates[idx])
            article["relevance_score"] = item.get("relevance_score", 0)
            article["tldr"] = item.get("tldr", "")
            article["category"] = item.get("category", "Other")
            article["why_important"] = item.get("why_important", "")
            enriched.append(article)

        enriched.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        enriched = enriched[:MAX_ARTICLES_PER_DIGEST]
        logger.info(f"[Filter] ✅ {len(enriched)} articles passed Gemini filter")
        return enriched

    except (json.JSONDecodeError, RuntimeError, Exception) as e:
        logger.warning(f"[Filter] Gemini unavailable ({e}). Using keyword-only fallback…")
        # Fallback: return pre-scored articles with truncated summaries as TL;DR
        fallback = []
        for a in candidates[:MAX_ARTICLES_PER_DIGEST]:
            if a["_prescore"] >= 2:  # at least 2 keyword matches
                a["relevance_score"] = min(a["_prescore"] + 4, 9)  # rough mapping
                a["tldr"] = a.get("summary", "")[:280]
                a["category"] = a.get("category", "Other")
                a["why_important"] = ""
                fallback.append(a)
        logger.info(f"[Filter] Fallback: returning {len(fallback)} keyword-matched articles")
        return fallback
