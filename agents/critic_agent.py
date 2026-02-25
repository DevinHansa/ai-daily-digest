"""
agents/critic_agent.py — Critically evaluates articles for importance and novelty.

The Critic Agent receives up to 15 pre-scored articles and uses ONE Gemini call to:
  1. Score each on real-world impact (0-10)
  2. Flag topic duplicates (same story, different source)
  3. Add a critic_note explaining WHY it matters
  4. Check against seen_topics to avoid repeating stories from past digests

Returns a deduplicated, ranked list ready for the Editor.
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

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

_CRITIC_MODEL = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"temperature": 0.2, "response_mime_type": "application/json"},
)

_CRITIC_PROMPT_TEMPLATE = """You are a senior AI industry analyst and editorial critic. Your job is to ruthlessly evaluate the following articles for an expert daily AI digest.

**Digest audience:** AI engineers, researchers, and tech leaders who want only the most important AI developments.

**Previously covered topics (DO NOT repeat these):**
{seen_topics}

**Tracked key people:** {people}

**Evaluation criteria:**
- Score 9-10: Major product launch, breakthrough research, significant policy/legal event, statements from top AI leaders
- Score 7-8: Important but not breaking — notable research, product updates, funding rounds
- Score 5-6: Marginally relevant — minor updates, repackaged old news
- Score 0-4: Noise — irrelevant, clickbait, duplicate topic already in digest or in seen_topics above

**For each article return:**
{{
  "index": <index>,
  "score": <0-10>,
  "is_duplicate_topic": <true/false — is this covered by seen_topics or by another article in this batch?>,
  "topic_keywords": "<3-5 short keywords summarizing the core topic, e.g. 'anthropic china claude training'>",
  "critic_note": "<One sharp sentence on why this matters OR why it is weak>",
  "category": "<News | Research | Product Launch | Policy/Legal | Funding | Tool/Library | Opinion>"
}}

Return a JSON ARRAY with one entry per article. Include ALL articles in the output (even low-scored ones) so the Editor can make final decisions.

---
Articles to evaluate:
{articles}

Return ONLY a valid JSON array. No markdown fences."""


def _format_articles_for_prompt(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles):
        lines.append(f"[{i}] SOURCE: {a.get('source', 'Unknown')} | TYPE: {a.get('type', 'unknown')}")
        lines.append(f"    TITLE: {a.get('title', '')}")
        if a.get("authors"):
            lines.append(f"    AUTHORS: {a['authors']}")
        if a.get("people_mentioned"):
            lines.append(f"    PEOPLE MENTIONED: {', '.join(a['people_mentioned'])}")
        lines.append(f"    SUMMARY: {a.get('summary', '')[:350]}")
        lines.append("")
    return "\n".join(lines)


def _call_with_retry(prompt: str, retries: int = 4) -> str:
    for attempt in range(retries):
        try:
            response = _CRITIC_MODEL.generate_content(prompt)
            return response.text
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                wait = 30 * (attempt + 1)
                logger.warning(f"[Critic] Rate-limited (attempt {attempt+1}/{retries}). Waiting {wait}s…")
                time.sleep(wait)
            else:
                logger.warning(f"[Critic] Attempt {attempt+1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(10)
    raise RuntimeError("Critic Agent: Gemini API failed after all retries")


def run_critic(articles: List[Dict], seen_topics: List[str]) -> List[Dict]:
    """Score and annotate articles."""
    if not articles:
        return []

    seen_topics_str = "\n".join(f"- {t}" for t in seen_topics) if seen_topics else "None yet (first digest)"
    articles_str = _format_articles_for_prompt(articles)

    prompt = _CRITIC_PROMPT_TEMPLATE.format(
        seen_topics=seen_topics_str,
        people=", ".join(TRACKED_PEOPLE),
        articles=articles_str,
    )

    try:
        raise RuntimeError("TEMP: skip API for test")
        raw = _call_with_retry(prompt)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        results = json.loads(raw)

        for item in results:
            idx = item.get("index")
            if idx is None or idx >= len(articles):
                continue
            articles[idx]["score"] = item.get("score", 0)
            articles[idx]["is_duplicate_topic"] = item.get("is_duplicate_topic", False)
            articles[idx]["topic_keywords"] = item.get("topic_keywords", "")
            articles[idx]["critic_note"] = item.get("critic_note", "")
            articles[idx]["category"] = item.get("category", articles[idx].get("category", "Other"))

        logger.info(f"[Critic] Scored {len(results)} articles")

    except Exception as e:
        logger.warning(f"[Critic] Gemini unavailable ({e}). Using keyword fallback scoring…")
        # Fallback: extract key terms from title for dedup + scoring
        _STOPWORDS = {"the","a","an","is","are","was","were","in","on","at","to","for",
                       "of","and","or","but","with","by","from","as","its","it","that",
                       "this","has","have","had","will","can","do","does","not","be",
                       "been","being","new","say","says","said","how","why","what","when",
                       "who","which","could","would","should","may","about","into","over",
                       "after","before","between","through","during","up","out","more",
                       "than","also","just","now","even","still","most","very","some",
                       "all","us","we","they","their","our","your","its","an"}

        def _extract_title_keywords(title: str) -> str:
            """Pull meaningful words from title — company names, products, verbs."""
            words = [w.strip(",:;!?\"'()[]{}") for w in title.split()]
            meaningful = [w for w in words if w.lower() not in _STOPWORDS and len(w) > 2]
            return " ".join(meaningful[:5]).lower()

        def _titles_overlap(title_kw: str, seen_kw: str) -> bool:
            """Check if two keyword strings share enough in common to be the same story."""
            t_words = set(title_kw.lower().split())
            s_words = set(seen_kw.lower().split())
            if not t_words or not s_words:
                return False
            overlap = len(t_words & s_words)
            # If 2+ meaningful words overlap, it's likely the same story
            return overlap >= 2

        for a in articles:
            title_kw = _extract_title_keywords(a.get("title", ""))

            is_dup = False
            for st in seen_topics:
                if _titles_overlap(title_kw, st):
                    is_dup = True
                    logger.info(f"[Critic] Fallback dedup: '{a.get('title','')[:50]}' matches seen topic '{st}'")
                    break

            ps = a.get("_prescore", 0)
            a["score"] = min(ps + 4, 9)
            a["is_duplicate_topic"] = is_dup
            a["topic_keywords"] = title_kw if not is_dup else ""
            a["critic_note"] = ""
            a.setdefault("category", "Other")

    # Filter out duplicates, sort by score
    unique = [a for a in articles if not a.get("is_duplicate_topic", False)]
    unique.sort(key=lambda x: x.get("score", 0), reverse=True)

    logger.info(f"[Critic] {len(unique)} unique articles after dedup (from {len(articles)})")
    return unique
