"""
email_sender/composer.py — Builds a beautiful dark-mode HTML email digest.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict

# Sri Lanka is UTC+5:30
SL_TZ = timezone(timedelta(hours=5, minutes=30))

# Category → icon mapping
CATEGORY_ICONS = {
    "Research": "🔬",
    "Product Launch": "🚀",
    "Tool/Library": "🛠️",
    "Opinion/Interview": "💬",
    "Opinion": "💬",
    "Policy": "⚖️",
    "Policy/Legal": "⚖️",
    "Funding": "💰",
    "News": "📰",
    "Community": "🟠",
    "Company": "🏛️",
    "Other": "📌",
}

CATEGORY_COLORS = {
    "Research": "#6c63ff",
    "Product Launch": "#00d4aa",
    "Tool/Library": "#ff9f43",
    "Opinion/Interview": "#54a0ff",
    "Opinion": "#54a0ff",
    "Policy": "#ff6b6b",
    "Policy/Legal": "#ff6b6b",
    "Funding": "#ffd32a",
    "News": "#e84393",
    "Community": "#ffa502",
    "Company": "#2ed573",
    "Other": "#747d8c",
}


def _score_bar(score: int) -> str:
    """Render a simple relevance score bar (e.g. ████░░░ 7/10)."""
    filled = round(score / 2)  # out of 5 blocks
    empty = 5 - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {score}/10"


def _format_date(pub) -> str:
    if not pub:
        return "Recently"
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    sl_time = pub.astimezone(SL_TZ)
    return sl_time.strftime("%d %b %Y, %I:%M %p SL")


def _group_by_category(articles: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for a in articles:
        cat = a.get("category", "Other")
        groups.setdefault(cat, []).append(a)
    # Sort categories by highest avg score
    return dict(
        sorted(
            groups.items(),
            key=lambda kv: sum(a.get("relevance_score", 0) for a in kv[1]) / len(kv[1]),
            reverse=True,
        )
    )


def _render_article_card(article: Dict, rank: int) -> str:
    cat = article.get("category", "Other")
    color = CATEGORY_COLORS.get(cat, "#747d8c")
    icon = CATEGORY_ICONS.get(cat, "📌")
    score = article.get("relevance_score", 0)
    people = article.get("people_mentioned", [])
    people_html = ""
    if people:
        tags = " ".join(
            f'<span style="background:#1a1a2e;border:1px solid #6c63ff;color:#6c63ff;'
            f'border-radius:20px;padding:2px 10px;font-size:11px;margin-right:5px;">👤 {p}</span>'
            for p in people
        )
        people_html = f'<div style="margin-top:8px">{tags}</div>'

    authors_html = ""
    if article.get("authors"):
        authors_html = f'<p style="color:#888;font-size:12px;margin:4px 0">✍️ {article["authors"]}</p>'

    why_html = ""
    why_text = article.get("why_it_matters") or article.get("why_important") or article.get("critic_note") or ""
    if why_text:
        why_html = f'''
        <div style="border-left:3px solid {color};padding-left:12px;margin-top:10px;
                    color:#aaa;font-size:13px;font-style:italic;">
            💡 {why_text}
        </div>'''

    return f"""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a4a;
        border-left: 4px solid {color};
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 18px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    ">
        <!-- Header row -->
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px">
            <div style="display:flex;align-items:center;gap:10px">
                <span style="
                    background:{color}22;border:1px solid {color};
                    color:{color};border-radius:20px;padding:3px 12px;
                    font-size:12px;font-weight:600;letter-spacing:0.5px;
                ">{icon} {cat}</span>
                <span style="color:#666;font-size:12px">{article.get('logo','')} {article.get('source','')}</span>
            </div>
            <div style="color:#888;font-size:12px">
                <span style="font-family:monospace;letter-spacing:1px;color:{color}">{_score_bar(score)}</span>
                &nbsp;·&nbsp; {_format_date(article.get('published'))}
            </div>
        </div>

        <!-- Title -->
        <h3 style="margin:0 0 10px 0;font-size:17px;line-height:1.4">
            <a href="{article.get('url','#')}" style="color:#e0e0ff;text-decoration:none;">
                <span style="color:{color};font-weight:700">#{rank}</span> {article.get('title','')}
            </a>
        </h3>

        {authors_html}

        <!-- TL;DR -->
        <p style="color:#c0c0d8;font-size:14px;line-height:1.7;margin:8px 0;">
            {article.get('tldr', article.get('summary', '')[:300])}
        </p>

        {why_html}
        {people_html}

        <!-- Read more button -->
        <div style="margin-top:14px">
            <a href="{article.get('url','#')}" style="
                display:inline-block;background:linear-gradient(135deg,{color},{color}88);
                color:#fff;text-decoration:none;padding:7px 18px;border-radius:20px;
                font-size:13px;font-weight:600;letter-spacing:0.3px;
            ">Read full article →</a>
        </div>
    </div>
    """


def build_html_email(articles: List[Dict], date_str: str = None, big_picture: str = "") -> str:
    """
    Build the full HTML email from a list of enriched article dicts.
    Returns the HTML string.
    """
    now_sl = datetime.now(SL_TZ)
    if not date_str:
        date_str = now_sl.strftime("%A, %d %B %Y")

    total = len(articles)
    groups = _group_by_category(articles)

    # Build category nav pills
    nav_pills = " ".join(
        f'<span style="background:#1a1a2e;border:1px solid {CATEGORY_COLORS.get(cat,"#444")};'
        f'color:{CATEGORY_COLORS.get(cat,"#aaa")};border-radius:20px;padding:4px 14px;'
        f'font-size:12px;font-weight:600;display:inline-block;margin:3px;">'
        f'{CATEGORY_ICONS.get(cat,"📌")} {cat} ({len(arts)})</span>'
        for cat, arts in groups.items()
    )

    # Build article cards grouped by category
    sections_html = ""
    rank = 1
    for cat, arts in groups.items():
        color = CATEGORY_COLORS.get(cat, "#747d8c")
        icon = CATEGORY_ICONS.get(cat, "📌")
        art_cards = "".join(_render_article_card(a, rank + i) for i, a in enumerate(arts))
        rank += len(arts)
        sections_html += f"""
        <div style="margin-bottom:30px">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                <div style="height:2px;flex:1;background:linear-gradient(90deg,{color},transparent)"></div>
                <h2 style="color:{color};font-size:15px;font-weight:700;margin:0;
                            letter-spacing:1px;text-transform:uppercase;white-space:nowrap">
                    {icon} {cat}
                </h2>
                <div style="height:2px;flex:1;background:linear-gradient(90deg,transparent,{color})"></div>
            </div>
            {art_cards}
        </div>
        """

    empty_html = ""
    if total == 0:
        empty_html = """
        <div style="text-align:center;padding:60px 20px;color:#555">
            <div style="font-size:48px;margin-bottom:16px">🌙</div>
            <h3 style="color:#888;margin:0">Nothing new today</h3>
            <p style="color:#555;margin-top:8px">No significant AI news since yesterday's digest.</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI News Digest — {date_str}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0d0d1a; font-family:'Inter',sans-serif; color:#e0e0ff; }}
  a {{ color:#6c63ff; }}
</style>
</head>
<body style="background:#0d0d1a;padding:0;margin:0">

<!-- Outer wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d1a;min-height:100vh">
<tr><td>
<div style="max-width:720px;margin:0 auto;padding:20px 16px 40px">

  <!-- ── HEADER ── -->
  <div style="
    background: linear-gradient(135deg, #1a1a3e 0%, #0d0d2a 60%, #1a0a2e 100%);
    border: 1px solid #2a2a5a;
    border-radius: 20px;
    padding: 36px 32px;
    margin-bottom: 28px;
    text-align: center;
    position: relative;
    overflow: hidden;
  ">
    <!-- Decorative glow -->
    <div style="
      position:absolute;top:-40px;left:50%;transform:translateX(-50%);
      width:300px;height:120px;
      background:radial-gradient(ellipse,#6c63ff44 0%,transparent 70%);
      pointer-events:none;
    "></div>

    <div style="font-size:40px;margin-bottom:10px">🧠</div>
    <h1 style="
      font-size:28px;font-weight:700;letter-spacing:-0.5px;
      background:linear-gradient(135deg,#a78bfa,#60a5fa,#34d399);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
      background-clip:text;margin-bottom:8px;
    ">AI News Digest</h1>
    <p style="color:#888;font-size:15px;margin-bottom:18px">
      {date_str} &nbsp;·&nbsp; Curated by Gemini AI
    </p>

    <!-- Stats bar -->
    <div style="
      display:inline-flex;gap:24px;background:#0d0d2a;border:1px solid #2a2a5a;
      border-radius:40px;padding:10px 24px;margin-bottom:20px;
    ">
      <div style="text-align:center">
        <div style="font-size:22px;font-weight:700;color:#a78bfa">{total}</div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Articles</div>
      </div>
      <div style="width:1px;background:#2a2a5a"></div>
      <div style="text-align:center">
        <div style="font-size:22px;font-weight:700;color:#60a5fa">{len(groups)}</div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Categories</div>
      </div>
      <div style="width:1px;background:#2a2a5a"></div>
      <div style="text-align:center">
        <div style="font-size:22px;font-weight:700;color:#34d399">
          {max((a.get('relevance_score',0) for a in articles), default=0)}/10
        </div>
        <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Top Score</div>
      </div>
    </div>

    <!-- Category pills -->
    <div style="line-height:2.2">
      {nav_pills}
    </div>
  </div>

  <!-- ── BIG PICTURE (Editor's executive brief) ── -->
  {f'''
  <div style="
    background: linear-gradient(135deg, #0f1a2e 0%, #0a0a1a 100%);
    border: 1px solid #1a3a5a;
    border-left: 4px solid #60a5fa;
    border-radius: 14px;
    padding: 20px 26px;
    margin-bottom: 24px;
  ">
    <div style="font-size:11px;font-weight:700;letter-spacing:2px;color:#60a5fa;
                text-transform:uppercase;margin-bottom:10px">🌍 Today\'s Big Picture</div>
    <p style="color:#c8d8f0;font-size:15px;line-height:1.8;margin:0;font-style:italic;">
      {big_picture}
    </p>
  </div>
  ''' if big_picture else ""}

  <!-- ── TOP PICK CALLOUT (if articles exist) ── -->
  {"" if not articles else _render_top_pick(articles[0])}

  <!-- ── ARTICLE SECTIONS ── -->
  {sections_html or empty_html}

  <!-- ── FOOTER ── -->
  <div style="
    text-align:center;border-top:1px solid #1a1a3a;margin-top:30px;
    padding-top:24px;color:#444;font-size:12px;line-height:1.8;
  ">
    <p>🤖 Powered by <strong style="color:#6c63ff">Gemini 2.0 Flash</strong> — Critic &amp; Editor Agents · Sources: TechCrunch, VentureBeat, The Verge, Wired, MIT Tech Review, Ars Technica, OpenAI, Anthropic, DeepMind, arXiv, Hacker News &amp; more</p>
    <p style="margin-top:6px">This digest is auto-generated daily at <strong style="color:#aaa">7:30 AM Sri Lanka Time</strong></p>
    <p style="margin-top:6px">
      <a href="mailto:as2020323@sci.sjp.ac.lk" style="color:#3a3a6a">Unsubscribe</a>
    </p>
  </div>

</div>
</td></tr>
</table>
</body>
</html>"""


def _render_top_pick(article: Dict) -> str:
    """Render the golden 'Top Pick of the Day' callout for the #1 article."""
    return f"""
    <div style="
        background: linear-gradient(135deg, #1f1535 0%, #0f0f2a 100%);
        border: 1px solid #5040a0;
        border-radius: 16px;
        padding: 22px 26px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    ">
      <div style="
        position:absolute;top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,#a78bfa,#60a5fa,#34d399);
      "></div>
      <div style="font-size:12px;font-weight:700;letter-spacing:2px;color:#a78bfa;
                  text-transform:uppercase;margin-bottom:10px">
        ⭐ Top Pick Today
      </div>
      <h2 style="font-size:20px;margin-bottom:10px;line-height:1.4">
        <a href="{article.get('url','#')}" style="color:#e8e0ff;text-decoration:none">
          {article.get('title','')}
        </a>
      </h2>
      <p style="color:#b0a8d0;font-size:14px;line-height:1.7">
        {article.get('tldr', article.get('summary','')[:300])}
      </p>
      <div style="margin-top:14px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <a href="{article.get('url','#')}" style="
          background:linear-gradient(135deg,#a78bfa,#60a5fa);color:#fff;
          text-decoration:none;padding:8px 20px;border-radius:20px;
          font-size:13px;font-weight:700;
        ">Read Now →</a>
        <span style="color:#666;font-size:13px">
          {article.get('logo','')} {article.get('source','')} &nbsp;·&nbsp;
          Score: <strong style="color:#a78bfa">{article.get('relevance_score',0)}/10</strong>
        </span>
      </div>
    </div>
    """
