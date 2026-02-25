"""
agents/critic_agent.py — Scores articles for importance, novelty, and impact.

The Critic Agent uses one Gemini call to:
  1. Score each article on real-world impact (0-10)
  2. Flag within-batch duplicates (same story, different source)
  3. Write a concise critic_note on why it matters
  4. Categorize each article

Semantic dedup against past digests is handled UPSTREAM by vector_memory.py.
This agent only needs to evaluate the quality of already-deduplicated articles.
"""

import os
import json
import logging
import time
from typing import List, Dict

import google.generativeai as genai
from dotenv import load_dotenv

from config import TRACKED_PEOPLE

load_dotenv()
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

_CRITIC_MODEL = None


def _get_model():
    global _CRITIC_MODEL
    if _CRITIC_MODEL is None:
        _CRITIC_MODEL = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"},
        )
    return _CRITIC_MODEL


# ── Optimized Critic Prompt ──────────────────────────────────────────────────
_CRITIC_PROMPT = """You are a ruthless editorial critic for the world's most trusted daily AI briefing.

AUDIENCE: Senior AI engineers, researchers, VCs, and CTOs who have 3 minutes to scan today's AI news.

RULES:
- Score 9-10: ONLY for genuinely major events — billion-dollar deals, breakthrough papers on arxiv with >100 citations potential, new flagship model releases (GPT-5, Claude 4, Gemini 2), major government policy changes
- Score 7-8: Important and timely — notable funding rounds (>$50M), significant product updates, industry partnerships, key personnel moves
- Score 5-6: Nice to know — minor updates, opinion pieces, conference talks, incremental improvements
- Score 0-4: DO NOT INCLUDE — clickbait, listicles, generic "AI will change the world" articles, rehashed old news, press releases disguised as news

KEY PEOPLE TO WATCH: {people}

CRITICAL: If two articles in this batch cover THE SAME EVENT (even from different sources), mark all but the best-sourced one as is_duplicate_topic=true.

For EACH article, return:
{{
  "index": <original index>,
  "score": <0-10>,
  "is_duplicate_topic": <true if another article in this batch covers the same event>,
  "critic_note": "<One punchy sentence: WHY this matters to an AI practitioner, or WHY it's weak>",
  "category": "<Research | Product Launch | Funding | Policy | Tool/Library | Industry News | Opinion>"
}}

Return a JSON ARRAY. Include ALL articles (even low-scored) so the Editor can decide.

---
ARTICLES:
{articles}

Return ONLY valid JSON array. No markdown."""


def _format_articles(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles):
        lines.append(f"[{i}] SOURCE: {a.get('source', '?')} | TYPE: {a.get('type', '?')}")
        lines.append(f"    TITLE: {a.get('title', '')}")
        if a.get("people_mentioned"):
            lines.append(f"    KEY PEOPLE: {', '.join(a['people_mentioned'])}")
        lines.append(f"    SUMMARY: {a.get('summary', '')[:400]}")
        lines.append("")
    return "\n".join(lines)


def _call_gemini(prompt: str, retries: int = 3) -> str:
    model = _get_model()
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "rate" in err:
                wait = 20 * (attempt + 1)
                logger.warning(f"[Critic] Rate-limited (attempt {attempt+1}). Waiting {wait}s…")
                time.sleep(wait)
            else:
                logger.warning(f"[Critic] Attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5)
    raise RuntimeError("Critic Agent: Gemini failed after retries")


def run_critic(articles: List[Dict]) -> List[Dict]:
    """
    Score and rank articles. Dedup is already handled by vector memory upstream.
    Returns articles sorted by score, with within-batch duplicates removed.
    """
    if not articles:
        return []

    prompt = _CRITIC_PROMPT.format(
        people=", ".join(TRACKED_PEOPLE),
        articles=_format_articles(articles),
    )

    try:
        raw = _call_gemini(prompt)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        results = json.loads(raw)

        for item in results:
            idx = item.get("index")
            if idx is None or idx >= len(articles):
                continue
            articles[idx]["score"] = item.get("score", 0)
            articles[idx]["is_duplicate_topic"] = item.get("is_duplicate_topic", False)
            articles[idx]["critic_note"] = item.get("critic_note", "")
            articles[idx]["category"] = item.get("category", articles[idx].get("category", "Other"))

        logger.info(f"[Critic] Gemini scored {len(results)} articles")

    except Exception as e:
        logger.warning(f"[Critic] Gemini unavailable ({e}). Using prescore fallback…")
        # Simple fallback: use pre-score, no within-batch dedup but that's OK
        for a in articles:
            ps = a.get("_prescore", 0)
            a["score"] = min(ps + 4, 9)
            a["is_duplicate_topic"] = False
            a["critic_note"] = ""
            a.setdefault("category", "Other")

    # Remove within-batch duplicates, sort by score descending
    unique = [a for a in articles if not a.get("is_duplicate_topic", False)]
    unique.sort(key=lambda x: x.get("score", 0), reverse=True)

    logger.info(f"[Critic] {len(unique)} articles after within-batch dedup (from {len(articles)})")
    return unique
