"""
agents/editor_agent.py — Final editorial curation and summary writing.

The Editor Agent receives the Critic's top-scored articles and uses ONE Gemini call to:
  1. Select the final 10 best articles ensuring category diversity
     (at least: 1 News, 1 Research, 1 Product — no single category dominates)
  2. Write a polished, insightful 3-sentence TL;DR for each
  3. Write a "Today's Big Picture" 2-sentence executive briefing for the email header
  4. Ensure the digest tells a coherent story about the current state of AI

Falls back gracefully if Gemini is unavailable.
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

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

_EDITOR_MODEL = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"temperature": 0.4, "response_mime_type": "application/json"},
)

_EDITOR_PROMPT_TEMPLATE = """You are the Chief Editor of the world's most concise and trusted daily AI briefing. Your audience are busy AI engineers and researchers who want only the highest-signal updates.

**Your job:**
1. Select the best {max_articles} articles from the list below
2. Ensure diversity: include at least 1 News story, 1 Research paper, 1 Product/company update
3. Write a sharp 3-sentence TL;DR per selected article (specific facts, numbers, model names — no vague generalities)
4. Write a "big_picture" field: a 2-sentence executive briefing summarizing today's overall AI landscape

**Return a JSON object with this exact structure:**
{{
  "big_picture": "<2-sentence overview of today's AI developments>",
  "articles": [
    {{
      "index": <original index from input>,
      "tldr": "<3 specific, insightful sentences>",
      "why_it_matters": "<one bold sentence on real-world impact>",
      "category": "<News | Research | Product Launch | Policy/Legal | Funding | Tool/Library | Opinion>"
    }}
  ]
}}

Only include {max_articles} articles in the output array. Prioritize score but ensure diversity.
Articles with is_duplicate_topic=true should NOT be selected unless there's no alternative.

---
Candidate articles (pre-scored by Critic Agent):
{articles}

Return ONLY valid JSON. No markdown fences."""


def _format_for_editor(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles):
        score = a.get("score", a.get("relevance_score", 0))
        lines.append(
            f"[{i}] SCORE:{score}/10 | CATEGORY:{a.get('category','?')} | "
            f"SOURCE:{a.get('source','')} | DUPLICATE:{a.get('is_duplicate_topic', False)}"
        )
        lines.append(f"    TITLE: {a.get('title', '')}")
        if a.get("critic_note"):
            lines.append(f"    CRITIC'S NOTE: {a['critic_note']}")
        if a.get("people_mentioned"):
            lines.append(f"    KEY PEOPLE: {', '.join(a['people_mentioned'])}")
        lines.append(f"    SUMMARY: {a.get('summary', '')[:300]}")
        lines.append("")
    return "\n".join(lines)


def _call_with_retry(prompt: str, retries: int = 4) -> str:
    for attempt in range(retries):
        try:
            response = _EDITOR_MODEL.generate_content(prompt)
            return response.text
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                wait = 30 * (attempt + 1)
                logger.warning(f"[Editor] Rate-limited (attempt {attempt+1}/{retries}). Waiting {wait}s…")
                time.sleep(wait)
            else:
                logger.warning(f"[Editor] Attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(10)
    raise RuntimeError("Editor Agent: Gemini API failed after all retries")


def run_editor(articles: List[Dict]) -> Tuple[List[Dict], str]:
    """
    Curate the final digest from critic-approved articles.
    """
    if not articles:
        return [], "No AI news found for today."

    candidates = articles[:20]

    prompt = _EDITOR_PROMPT_TEMPLATE.format(
        max_articles=MAX_ARTICLES_PER_DIGEST,
        articles=_format_for_editor(candidates),
    )

    try:
        raw = _call_with_retry(prompt)
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
            # Merge score as relevance_score for the email composer
            article["relevance_score"] = article.get("score", article.get("relevance_score", 7))
            final.append(article)

        logger.info(f"[Editor] Final selection: {len(final)} articles | Big Picture written")
        return final, big_picture

    except Exception as e:
        logger.warning(f"[Editor] Gemini unavailable ({e}). Using fallback selection…")
        # Fallback: top N by score with basic TL;DR
        fallback = []
        for a in candidates[:MAX_ARTICLES_PER_DIGEST]:
            a = dict(a)
            a.setdefault("tldr", a.get("summary", "")[:280])
            a.setdefault("why_it_matters", "")
            a["relevance_score"] = a.get("score", a.get("relevance_score", 6))
            fallback.append(a)

        # Generate a professional-sounding big picture from article sources
        sources = list(set(a.get("source", "") for a in fallback if a.get("source")))[:4]
        source_str = ", ".join(sources[:3])
        if len(sources) > 3:
            source_str += f" and {len(sources) - 3} more"
        big_picture = (
            f"Today's digest covers {len(fallback)} developments across the AI landscape, "
            f"with stories from {source_str}."
        )
        logger.info(f"[Editor] Fallback: {len(fallback)} articles selected")
        return fallback, big_picture
