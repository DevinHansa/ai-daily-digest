---
description: Skills and patterns learned building the AI News Digest multi-agent system
---

# AI News Digest — Skills & Patterns

## 1. Multi-Agent Pipeline Orchestration
- **Pattern**: Sequential pipeline with graceful fallbacks at every stage
- **Key insight**: Each agent should have a self-contained fallback that produces acceptable output without any API dependency
- **Implementation**: `run_digest.py` orchestrates Fetch → URL Dedup → Semantic Dedup → Pre-Score → Critic Agent → Editor Agent → Compose → Send → Save
- **Lesson**: Never let one agent's failure kill the entire pipeline

## 2. Semantic Deduplication with Vector Embeddings
- **Pattern**: ChromaDB + sentence-transformers for local, zero-cost semantic similarity
- **Model**: `all-MiniLM-L6-v2` (80MB, 384-dim embeddings, runs on CPU in ~2s)
- **Threshold**: 0.72 cosine similarity blocks duplicates while allowing related-but-different stories
- **Key insight**: Keyword matching fails catastrophically for dedup — "OpenAI's enterprise push" and "OpenAI expands into corporate market" share zero keywords but are the same story. Embeddings solve this instantly.
- **Expiry**: Articles expire from memory after 7 days so topics can be revisited with new developments

## 3. LLM Prompt Engineering for Editorial AI
- **Anti-pattern**: Vague prompts produce vague output ("A major AI company released a new model")
- **Pattern**: Include explicit BAD vs GOOD examples in the prompt itself
- **Pattern**: Demand specific artifacts (model names, dollar figures, benchmark scores)
- **Pattern**: Define audience precisely ("Senior AI engineers with 3 minutes")
- **Key insight**: Temperature 0.2 for scoring/evaluation, 0.5 for creative writing (TL;DRs)

## 4. Gemini API Rate Limit Handling
- **Pattern**: Exponential backoff with 3 retries, then graceful degradation
- **Key insight**: Free-tier Gemini quota (~1500 req/day) can be exhausted during development. Build fallbacks that produce acceptable (not broken) output.
- **Anti-pattern**: Infinite retry loops that hang the process
- **Pattern**: Set a hard retry cap and let the fallback handle it

## 5. RSS Feed Aggregation at Scale
- **Pattern**: Combine 10+ feeds with type tagging (news vs company blog)
- **Libraries**: `feedparser` for RSS, `arxiv` package for arXiv API, `requests` for HN
- **Key insight**: Not all feeds are equal — news outlets (TechCrunch, The Verge) produce higher-signal content than company blogs which are often marketing
- **Pattern**: Pre-score by source reputation before spending API tokens

## 6. Dark-Mode HTML Email Design
- **Pattern**: Inline CSS only (email clients strip <style> tags)
- **Pattern**: Gradient headers, card-based layouts, category-colored badges
- **Pattern**: Use emoji as lightweight icons (📰 🔬 🚀) instead of image assets
- **Key insight**: Email CSS is 10 years behind web CSS — test in Gmail, Outlook, Apple Mail

## 7. Memory Architecture
- **Layer 1**: URL dedup (fast, exact match via JSON file)
- **Layer 2**: Semantic dedup (ChromaDB cosine similarity, catches same-story-different-words)
- **Pattern**: URL dedup runs first as a cheap filter, then semantic dedup processes the remaining articles
- **Key insight**: Memory must expire — 7-day TTL prevents the system from blocking everything after a few weeks

## 8. Windows Task Scheduler Integration
- **Pattern**: Use `schtasks /Create` with `/SC DAILY /ST 07:30` for scheduled runs
- **Key insight**: Task Scheduler requires full paths to python.exe and the script
- **Pattern**: Log to both stdout and a file so scheduled runs can be debugged

## 9. Git Security for Public Repos
- **Pattern**: `.env` for secrets, `.env.example` for documentation, `.gitignore` for exclusion
- **Key insight**: Always sanitize before the first commit — `git filter-branch` is painful
- **Pattern**: Never hardcode API keys, even temporarily during development
