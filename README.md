<div align="center">

# 🧠 AI Daily Digest

**Your personal AI news intelligence system — so you never miss what matters.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Gemini](https://img.shields.io/badge/Gemini_2.0-Flash-orange?logo=google)](https://ai.google.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Memory-green?logo=databricks)](https://trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*A multi-agent system that reads 100+ AI sources, eliminates noise, and delivers a beautifully curated daily briefing to your inbox.*

</div>

---

## The Problem

You follow AI. So does everyone else. The result?

- 📰 **100+ articles/day** across TechCrunch, arXiv, Hacker News, company blogs…
- 🔄 **Same story, 8 sources** — "OpenAI raises funding" appears everywhere with different headlines
- 📉 **Signal-to-noise ratio approaching zero** — for every breakthrough paper, there are 50 "AI will change everything" opinion pieces
- ⏰ **No time to filter** — you're building AI systems, not reading about them

## The Solution

AI Daily Digest is a **multi-agent AI system** that does what a world-class editorial team would do — in 90 seconds:

> **Fetch → Deduplicate → Score → Curate → Write → Deliver**

Every morning, you get ONE email with 10 hand-picked stories, each with a sharp TL;DR, a "why it matters" note, and a big-picture executive summary tying them all together.

**No duplicates. No fluff. No clickbait.** Just the 10 things you actually need to know.

---

## How It Works

```mermaid
graph TD
    A["📡 Fetch<br/>100+ articles from<br/>RSS • arXiv • HN"] --> B["🔗 URL Dedup<br/>Block exact URLs<br/>already sent"]
    B --> C["🧠 Vector Memory<br/>Block semantically<br/>similar stories"]
    C --> D["🔑 Pre-Score<br/>Keyword ranking<br/>top 15 candidates"]
    D --> E["🔍 Critic Agent<br/>Gemini scores each<br/>on real-world impact"]
    E --> F["✍️ Editor Agent<br/>Picks final 10, writes<br/>TL;DRs + Big Picture"]
    F --> G["📬 Dark-Mode Email<br/>Beautiful HTML digest<br/>straight to your inbox"]
    G --> H["💾 Save to Memory<br/>ChromaDB embeddings<br/>for future dedup"]

    style A fill:#1a1a2e,stroke:#e94560,color:#fff
    style B fill:#1a1a2e,stroke:#0f3460,color:#fff
    style C fill:#1a1a2e,stroke:#533483,color:#fff
    style D fill:#1a1a2e,stroke:#e94560,color:#fff
    style E fill:#1a1a2e,stroke:#0f3460,color:#fff
    style F fill:#1a1a2e,stroke:#533483,color:#fff
    style G fill:#1a1a2e,stroke:#e94560,color:#fff
    style H fill:#1a1a2e,stroke:#0f3460,color:#fff
```

---

## Why Vector Memory Matters

Traditional dedup compares URLs or keywords. That fails:

| Headline A | Headline B | Keywords match? | Blocked? |
|---|---|:---:|:---:|
| "OpenAI expands enterprise push" | "OpenAI calls in consultants for corporate market" | ❌ | ❌ Old system |
| "Anthropic accuses Chinese labs" | "Claude scraped by Chinese AI companies" | ❌ | ❌ Old system |

**AI Daily Digest** uses **sentence-transformers** to embed article titles into a 384-dimensional vector space and checks **cosine similarity** against all previously sent articles:

```
Article: "OpenAI expands enterprise push"
   ↓ encode → [0.12, -0.34, 0.78, ..., 0.45]  (384 dims)
   ↓ cosine similarity vs stored embeddings
   ↓ similarity = 0.89 with "OpenAI calls in consultants for corporate market"
   ↓ 0.89 > 0.72 threshold → ❌ BLOCKED as duplicate
```

**Result:** Your readers never see the same story twice, even if it's told from a completely different angle.

---

## The Agent Architecture

```mermaid
graph LR
    subgraph "🔍 Critic Agent"
        CA["Gemini 2.0 Flash<br/>temp=0.2"]
        CA --> |"Score 0-10"| S1["Impact scoring"]
        CA --> |"Detect"| S2["Within-batch dedup"]
        CA --> |"Write"| S3["Critic notes"]
    end

    subgraph "✍️ Editor Agent"
        EA["Gemini 2.0 Flash<br/>temp=0.5"]
        EA --> |"Select"| E1["Top 10 with diversity"]
        EA --> |"Write"| E2["Fact-dense TL;DRs"]
        EA --> |"Compose"| E3["Big Picture summary"]
    end

    CA --> EA

    style CA fill:#0f3460,stroke:#e94560,color:#fff
    style EA fill:#533483,stroke:#e94560,color:#fff
```

Both agents have **built-in fallbacks** — if the Gemini API is rate-limited, the system gracefully degrades to keyword scoring without any reader-visible impact. No "service unavailable" messages, no broken emails.

---

## News Sources

| Source | Type | What we get |
|---|---|---|
| TechCrunch AI | 📰 News | Breaking industry stories |
| VentureBeat AI | 📰 News | Enterprise AI coverage |
| The Verge AI | 📰 News | Consumer AI products |
| MIT Technology Review | 📰 News | Long-form AI analysis |
| Ars Technica AI | 📰 News | Technical deep-dives |
| OpenAI Blog | 🏢 Company | Direct product announcements |
| Anthropic News | 🏢 Company | Claude updates, safety research |
| Google DeepMind Blog | 🏢 Company | Gemini, AlphaFold updates |
| arXiv (cs.CL + cs.AI) | 📄 Research | Latest papers, pre-prints |
| Hacker News | 💬 Community | What engineers are discussing |

---

## Project Structure

```
ai_news_digest/
│
├── run_digest.py              # 🎯 Pipeline orchestrator (8-step flow)
├── config.py                  # ⚙️ Feeds, keywords, thresholds
│
├── fetchers/                  # 📡 Data collection
│   ├── rss_fetcher.py         #    RSS/Atom feeds (10+ outlets)
│   ├── arxiv_fetcher.py       #    arXiv API (cs.CL, cs.AI)
│   └── hackernews_fetcher.py  #    HN top stories filtered by AI keywords
│
├── processor/                 # 🧠 Intelligence layer
│   ├── memory.py              #    URL dedup (JSON-based)
│   └── vector_memory.py       #    Semantic dedup (ChromaDB + MiniLM)
│
├── agents/                    # 🤖 AI editorial team
│   ├── critic_agent.py        #    Scores articles, detects duplicates
│   └── editor_agent.py        #    Curates final digest, writes TL;DRs
│
├── email_sender/              # 📬 Delivery
│   ├── composer.py            #    Dark-mode HTML email builder
│   └── sender.py              #    Gmail SMTP delivery
│
├── scheduler/                 # ⏰ Automation
│   └── setup_scheduler.py     #    Windows Task Scheduler setup
│
└── data/                      # 💾 Local state (gitignored)
    ├── memory.json            #    Seen URLs
    └── chroma_db/             #    Vector embeddings
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| **LLM** | Gemini 2.0 Flash | Fast, cheap, JSON mode |
| **Embeddings** | `all-MiniLM-L6-v2` | 80MB, runs locally, zero API cost |
| **Vector DB** | ChromaDB | Local, persistent, cosine similarity |
| **Email** | Gmail SMTP + Jinja2 | Free, reliable delivery |
| **Scheduling** | Windows Task Scheduler | Set-and-forget daily runs |

---

<div align="center">

**Built with ❤️ by [DevinHansa](https://github.com/DevinHansa)**

*Stop scrolling. Start knowing.*

</div>
