"""
run_digest.py — Multi-Agent AI News Digest Orchestrator

Pipeline:
  1. FETCH    — RSS (news outlets + company blogs) + arXiv + Hacker News
  2. MEMORY   — Remove already-seen URLs; load seen topics for Critic
  3. PRE-SCORE — Keyword ranking (no API) to pick best 15 candidates
  4. CRITIC   — Gemini Agent: score articles, detect topic duplicates, add critic notes
  5. EDITOR   — Gemini Agent: final curation, write TL;DRs, write "Big Picture" brief
  6. COMPOSE  — Build dark-mode HTML email
  7. SEND     — Gmail SMTP
  8. MEMORY   — Save sent article URLs + topic keywords

Usage:
  python run_digest.py                # Full live run
  python run_digest.py --dry-run      # Console preview + HTML file (no email)
  python run_digest.py --test-email   # Skip memory dedup, send real email
  python run_digest.py --force        # Re-send even seen articles
"""

import sys
import logging
import argparse
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("digest.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_digest")

SL_TZ = timezone(timedelta(hours=5, minutes=30))

# ─── Keyword pre-scorer (used before any API call) ────────────────────────────
_HIGH_VALUE_KEYWORDS = [
    "openai", "anthropic", "deepmind", "gemini", "gpt", "claude", "llama",
    "mistral", "grok", "sora", "dall-e", "ssi", "o1", "o3", "o4",
    "karpathy", "sutskever", "hassabis", "altman", "lecun", "hinton", "amodei",
    "transformer", "llm", "foundation model", "reasoning", "alignment", "agi",
    "reinforcement learning", "rlhf", "fine-tun", "multimodal", "benchmark",
    "agent", "agentic", "chain of thought", "tool use",
    "china", "regulation", "lawsuit", "copyright", "raises", "funding", "billion",
    "cold war", "ban", "executive order", "policy",
]

_HIGH_VALUE_SOURCES = {
    "OpenAI Blog", "Anthropic News", "Google DeepMind Blog",
    "Meta AI Blog", "Mistral AI News", "TechCrunch AI",
    "VentureBeat AI", "The Verge AI", "MIT Technology Review",
}


def _prescore(article: dict) -> int:
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    score = sum(1 for kw in _HIGH_VALUE_KEYWORDS if kw in text)
    if article.get("people_mentioned"):
        score += 3
    if article.get("source", "") in _HIGH_VALUE_SOURCES:
        score += 4
    if article.get("type") == "news":   # news outlets score higher than blogs
        score += 2
    return score


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI News Digest")
    parser.add_argument("--dry-run",    action="store_true", help="Print to console, save HTML, no email")
    parser.add_argument("--test-email", action="store_true", help="Send email, skip memory dedup")
    parser.add_argument("--force",      action="store_true", help="Re-send even seen articles")
    args = parser.parse_args()

    now_sl = datetime.now(SL_TZ)
    logger.info("=" * 65)
    logger.info("🧠  AI News Digest — Multi-Agent Pipeline Starting")
    logger.info(f"    Mode : {'DRY RUN' if args.dry_run else 'TEST EMAIL' if args.test_email else 'LIVE'}")
    logger.info(f"    Time : {now_sl.strftime('%Y-%m-%d %H:%M SL')}")
    logger.info("=" * 65)

    # ── STEP 1: FETCH ─────────────────────────────────────────────────────────
    logger.info("📡 STEP 1 — Fetching from all sources…")
    from fetchers.rss_fetcher        import fetch_rss_articles
    from fetchers.arxiv_fetcher      import fetch_arxiv_papers
    from fetchers.hackernews_fetcher import fetch_hn_articles

    rss      = fetch_rss_articles()
    arxiv    = fetch_arxiv_papers()
    hn       = fetch_hn_articles()

    all_articles = rss + arxiv + hn
    logger.info(f"📦 Fetched: {len(all_articles)} total  "
                f"(RSS: {len(rss)}, arXiv: {len(arxiv)}, HN: {len(hn)})")

    if not all_articles:
        logger.warning("⚠️  No articles fetched. Check network and feeds.")
        return

    # ── STEP 2: MEMORY — URL dedup + load seen topics ─────────────────────────
    logger.info("🧠 STEP 2 — Checking memory…")
    from processor.memory import filter_new_articles, get_seen_topics

    if not args.force:
        all_articles, skipped = filter_new_articles(all_articles)
        logger.info(f"    {len(all_articles)} new articles (skipped {skipped} already seen)")
    else:
        logger.info("    Skipping URL dedup (--force)")

    if not all_articles:
        logger.info("✅ Nothing new since the last digest. No email sent.")
        return

    seen_topics = get_seen_topics()
    logger.info(f"    {len(seen_topics)} topics in memory (won't repeat)")

    # ── STEP 3: PRE-SCORE — Keyword ranking (no API cost) ─────────────────────
    logger.info("🔑 STEP 3 — Keyword pre-scoring…")
    for a in all_articles:
        a["_prescore"] = _prescore(a)
    all_articles.sort(key=lambda x: x["_prescore"], reverse=True)
    candidates = all_articles[:15]   # send top 15 to Critic
    logger.info(f"    Top 15 candidates selected for Critic Agent")

    # ── STEP 4: CRITIC AGENT ──────────────────────────────────────────────────
    logger.info("🔍 STEP 4 — Critic Agent scoring…")
    from agents.critic_agent import run_critic
    critic_output = run_critic(candidates, seen_topics)
    logger.info(f"    {len(critic_output)} articles passed Critic Agent")

    if not critic_output:
        logger.warning("⚠️  Critic filtered all articles. Very quiet day or API issue.")
        return

    # ── STEP 5: EDITOR AGENT ──────────────────────────────────────────────────
    logger.info("✍️  STEP 5 — Editor Agent curating final digest…")
    from agents.editor_agent import run_editor
    final_articles, big_picture = run_editor(critic_output)
    logger.info(f"    {len(final_articles)} articles in final digest")
    logger.info(f"    Big Picture: {big_picture[:80]}…")

    if not final_articles:
        logger.warning("⚠️  Editor returned no articles.")
        return

    # ── STEP 6: COMPOSE HTML EMAIL ────────────────────────────────────────────
    logger.info("🎨 STEP 6 — Composing HTML email…")
    from email_sender.composer import build_html_email
    date_str = now_sl.strftime("%A, %d %B %Y")
    html = build_html_email(final_articles, date_str, big_picture=big_picture)

    # ── DRY RUN: Print and save ───────────────────────────────────────────────
    if args.dry_run:
        logger.info("\n" + "─" * 65)
        logger.info(f"📋 BIG PICTURE: {big_picture}")
        logger.info("─" * 65)
        for i, a in enumerate(final_articles, 1):
            logger.info(
                f"  [{i:2}] [{a.get('relevance_score', a.get('score',0)):2}/10] "
                f"[{a.get('category','?'):18}] {a.get('source',''):22} │ {a['title'][:65]}"
            )
            logger.info(f"         TL;DR: {a.get('tldr','')[:110]}")
            if a.get("critic_note"):
                logger.info(f"         CRITIC: {a['critic_note'][:100]}")
            logger.info(f"         URL: {a.get('url','')}")
            logger.info("")

        preview_path = "digest_preview.html"
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"💾 HTML preview saved to: {preview_path}")
        logger.info("✅ Dry run complete. No email sent.")
        return

    # ── STEP 7: SEND EMAIL ────────────────────────────────────────────────────
    logger.info("📬 STEP 7 — Sending email…")
    from email_sender.sender import send_digest
    success = send_digest(html)

    if success:
        # ── STEP 8: SAVE TO MEMORY ────────────────────────────────────────────
        logger.info("💾 STEP 8 — Saving to memory…")
        if not args.force:
            from processor.memory import save_digest
            save_digest(final_articles)
        logger.info("✅ Digest sent! Articles and topics saved to memory.")
    else:
        logger.error("❌ Email send failed. Memory NOT updated — will retry next run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
