"""
agents/editor_agent.py — Final editorial curation and summary writing.

The Editor Agent uses one Gemini call to:
  1. Select the best N articles ensuring category diversity
  2. Write engaging, specific TL;DRs with real facts and numbers
  3. Write "why it matters" impact notes
  4. Generate a "Today's Big Picture" executive summary

Falls back to prescore-based selection with clean messaging if Gemini is unavailable.
"""

import os
import json
import logging
import time
from typing import List, Dict, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

from config import MAX_ARTICLES_PER_DIGEST

load_dotenv()
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

_EDITOR_MODEL = None


def _get_model():
    global _EDITOR_MODEL
    if _EDITOR_MODEL is None:
        _EDITOR_MODEL = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"temperature": 0.5, "response_mime_type": "application/json"},
        )
    return _EDITOR_MODEL


# ── Optimized Editor Prompt ──────────────────────────────────────────────────
_EDITOR_PROMPT = """You are the Chief Editor of "AI Daily" — the briefing that top AI engineers actually read.

YOUR VOICE: Authoritative but accessible. Think Bloomberg Terminal meets Hacker News. No corporate jargon, no filler, no "exciting times ahead" platitudes.

TASK:
1. Select exactly {max_articles} articles from the candidates below
2. Ensure diversity: include research, product launches, AND industry/business news
3. Write each TL;DR as 2-3 punchy sentences with SPECIFIC details (model names, dollar figures, benchmark scores, company names — never vague)
4. Write a "why_it_matters" for each: ONE bold sentence about real-world impact
5. Write "big_picture": A compelling 2-sentence overview that ties today's stories together into a narrative

STYLE RULES FOR TL;DRs:
- BAD: "A major AI company released a new model that shows improvements."
- GOOD: "Anthropic's Claude 3.5 Sonnet scores 88.7% on HumanEval, up from 84.9%, while cutting inference costs by 40%. The model also adds native tool use and 200K context."

RETURN THIS EXACT JSON:
{{
  "big_picture": "<2-sentence narrative tying today's stories together>",
  "articles": [
    {{
      "index": <original index from input>,
      "tldr": "<2-3 specific, fact-dense sentences>",
      "why_it_matters": "<One bold sentence on real-world impact>",
      "category": "<Research | Product Launch | Funding | Policy | Tool/Library | Industry News | Opinion>"
    }}
  ]
}}

CANDIDATES (pre-scored by Critic):
{articles}

Return ONLY valid JSON. No markdown fences. Exactly {max_articles} articles."""


def _format_for_editor(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles):
        score = a.get("score", a.get("relevance_score", 0))
        lines.append(
            f"[{i}] SCORE:{score}/10 | CATEGORY:{a.get('category','?')} | "
            f"SOURCE:{a.get('source','')}"
        )
        lines.append(f"    TITLE: {a.get('title', '')}")
        if a.get("critic_note"):
            lines.append(f"    CRITIC NOTE: {a['critic_note']}")
        lines.append(f"    SUMMARY: {a.get('summary', '')[:350]}")
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
                logger.warning(f"[Editor] Rate-limited (attempt {attempt+1}). Waiting {wait}s…")
                time.sleep(wait)
            else:
                logger.warning(f"[Editor] Attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5)
    raise RuntimeError("Editor Agent: Gemini failed after retries")


def _generate_fallback_big_picture(articles: List[Dict]) -> str:
    """Generate a professional big_picture from article titles — no 'Gemini unavailable' leaks."""
    titles = [a.get("title", "") for a in articles[:3] if a.get("title")]
    if len(titles) >= 2:
        return (
            f"Today's top stories span {titles[0][:60]} and {titles[1][:60]}. "
            f"Read on for {len(articles)} curated updates shaping the AI landscape."
        )
    return f"Today's digest features {len(articles)} developments across the AI ecosystem."


def run_editor(articles: List[Dict]) -> Tuple[List[Dict], str]:
    """
    Curate the final digest. Returns (final_articles, big_picture_summary).
    """
    if not articles:
        return [], "No AI news found for today."

    candidates = articles[:20]

    prompt = _EDITOR_PROMPT.format(
        max_articles=MAX_ARTICLES_PER_DIGEST,
        articles=_format_for_editor(candidates),
    )

    try:
        raw = _call_gemini(prompt)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(raw)

        big_picture = result.get("big_picture", "Today's AI landscape continues to evolve rapidly.")
        selected = result.get("articles", [])

        final = []
        for item in selected:
            idx = item.get("index")
            if idx is None or idx >= len(candidates):
                continue
            article = dict(candidates[idx])
            article["tldr"] = item.get("tldr", article.get("summary", "")[:280])
            article["why_it_matters"] = item.get("why_it_matters", "")
            article["category"] = item.get("category", article.get("category", "Other"))
            article["relevance_score"] = article.get("score", article.get("relevance_score", 7))
            final.append(article)

        logger.info(f"[Editor] Gemini selected {len(final)} articles with Big Picture")
        return final, big_picture

    except Exception as e:
        logger.warning(f"[Editor] Gemini unavailable ({e}). Using fallback selection…")
        fallback = []
        for a in candidates[:MAX_ARTICLES_PER_DIGEST]:
            a = dict(a)
            a.setdefault("tldr", a.get("summary", "")[:280])
            a.setdefault("why_it_matters", "")
            a["relevance_score"] = a.get("score", a.get("relevance_score", 6))
            fallback.append(a)

        big_picture = _generate_fallback_big_picture(fallback)
        logger.info(f"[Editor] Fallback: {len(fallback)} articles selected")
        return fallback, big_picture
