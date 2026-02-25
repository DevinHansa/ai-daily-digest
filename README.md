# AI News Digest

Your personal daily AI news digest — filters the noise and delivers only the **important** AI developments straight to your inbox every morning.

## What it does

- **Fetches** AI news from: OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, Hugging Face, arXiv, Hacker News, and more
- **Filters** with Gemini AI — only keeps high-signal articles (scored ≥ 6/10)
- **Summarizes** every article into a clean 2-3 sentence TL;DR
- **Emails** a beautiful dark-mode HTML digest at **7:30 AM Sri Lanka time** daily

Tracked people: Andrej Karpathy, Demis Hassabis, Ilya Sutskever, Sam Altman, Boris Cherny, Peter Steinberg, and more.

---

## Setup (First Time)

### 1. Install dependencies
```powershell
cd e:\ai_news_digest
pip install -r requirements.txt
```

### 2. Configure your Gmail sender

You need to create a **Gmail App Password** (not your normal Gmail password):
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification → **App Passwords**
3. Select **Mail** → **Windows Computer** → Generate
4. Copy the 16-character password

### 3. Edit the `.env` file

Open `e:\ai_news_digest\.env` and fill in:
```
GMAIL_SENDER=your_gmail_address@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

> ⚠️ The Gemini API key and recipient email are already filled in.

### 4. Test the pipeline
```powershell
# Dry run - prints digest to console, saves digest_preview.html
python run_digest.py --dry-run

# Send a real test email
python run_digest.py --test-email
```

### 5. Schedule daily delivery at 7:30 AM
```powershell
# Run as Administrator!
python scheduler/setup_scheduler.py
```

---

## Project Structure

```
ai_news_digest/
├── .env                      ← Your secrets (do not share!)
├── config.py                 ← Add/remove sources and tracked people here
├── run_digest.py             ← Main script
├── fetchers/
│   ├── rss_fetcher.py        ← Company blogs (OpenAI, Anthropic, DeepMind…)
│   ├── arxiv_fetcher.py      ← Latest AI research papers
│   └── hackernews_fetcher.py ← HN top AI stories
├── processor/
│   ├── filter.py             ← Gemini AI scoring & summarization
│   └── deduplicator.py       ← Skip already-seen articles
├── email_sender/
│   ├── composer.py           ← HTML email builder
│   └── sender.py             ← Gmail SMTP sender
├── scheduler/
│   └── setup_scheduler.py    ← Windows Task Scheduler setup
└── data/
    └── seen_articles.json    ← Auto-created, tracks seen URLs
```

---

## CLI Reference

| Command | Description |
|---|---|
| `python run_digest.py` | Full run — fetch, filter, and send email |
| `python run_digest.py --dry-run` | Preview in console + save HTML, no email |
| `python run_digest.py --test-email` | Send real email (bypass dedup) |
| `python run_digest.py --force` | Re-send even for already seen articles |
| `python scheduler/setup_scheduler.py` | Register daily schedule |
| `python scheduler/setup_scheduler.py --status` | Check schedule status |
| `python scheduler/setup_scheduler.py --remove` | Remove schedule |

---

## Customization

Edit `config.py` to:
- Add/remove RSS feeds (`COMPANY_FEEDS`)
- Add/remove tracked people (`TRACKED_PEOPLE`)
- Change how many articles per digest (`MAX_ARTICLES_PER_DIGEST`)
- Change the relevance threshold (`MIN_RELEVANCE_SCORE`, default 6/10)
- Change article lookback window (`LOOKBACK_HOURS`, default 30)
