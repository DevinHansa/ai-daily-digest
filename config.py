"""
config.py — Central configuration for all news sources and tracked entities.
Edit this file to add/remove sources or tracked people.
"""

# ─── AI News Outlets (THE MOST IMPORTANT — covers actual news stories) ────────
# These cover stories like "Anthropic accuses China", policy news, industry drama
AI_NEWS_FEEDS = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "logo": "📰",
        "type": "news",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/ai/feed/",
        "logo": "📰",
        "type": "news",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "logo": "📰",
        "type": "news",
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
        "logo": "📰",
        "type": "news",
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "logo": "🎓",
        "type": "news",
    },
    {
        "name": "Ars Technica AI",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "logo": "📰",
        "type": "news",
    },
    {
        "name": "Reuters Technology",
        "url": "https://feeds.reuters.com/reuters/technologyNews",
        "logo": "🌐",
        "type": "news",
    },
    {
        "name": "The Information AI",
        "url": "https://www.theinformation.com/feed",
        "logo": "📰",
        "type": "news",
    },
    {
        "name": "Bloomberg Technology",
        "url": "https://feeds.bloomberg.com/technology/news.rss",
        "logo": "💹",
        "type": "news",
    },
    {
        "name": "AI News (ainews.io)",
        "url": "https://buttondown.com/ainews/rss",
        "logo": "🤖",
        "type": "news",
    },
]

# ─── Tracked Companies (Official Blogs) ───────────────────────────────────────
COMPANY_FEEDS = [
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "logo": "🤖",
        "type": "company",
    },
    {
        "name": "Anthropic News",
        "url": "https://www.anthropic.com/rss.xml",
        "logo": "🧠",
        "type": "company",
    },
    {
        "name": "Google DeepMind Blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "logo": "🔬",
        "type": "company",
    },
    {
        "name": "Google AI Research",
        "url": "https://blog.research.google/feeds/posts/default",
        "logo": "🔬",
        "type": "company",
    },
    {
        "name": "Meta AI Blog",
        "url": "https://ai.meta.com/blog/feed/",
        "logo": "🌐",
        "type": "company",
    },
    {
        "name": "Mistral AI News",
        "url": "https://mistral.ai/feed",
        "logo": "💨",
        "type": "company",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "logo": "🤗",
        "type": "company",
    },
    {
        "name": "The Rundown AI",
        "url": "https://www.therundown.ai/feed",
        "logo": "📰",
        "type": "company",
    },
    {
        "name": "TLDR AI",
        "url": "https://tldr.tech/ai/rss",
        "logo": "⚡",
        "type": "company",
    },
]

# Combined list used by rss_fetcher
ALL_RSS_FEEDS = AI_NEWS_FEEDS + COMPANY_FEEDS

# ─── Tracked People ────────────────────────────────────────────────────────────
TRACKED_PEOPLE = [
    "Andrej Karpathy",
    "Demis Hassabis",
    "Ilya Sutskever",
    "Sam Altman",
    "Boris Cherny",
    "Peter Steinberg",
    "Yann LeCun",
    "Geoffrey Hinton",
    "Dario Amodei",
    "Daniela Amodei",
    "Sundar Pichai",
    "Jensen Huang",
]

# ─── arXiv Categories ──────────────────────────────────────────────────────────
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL"]
ARXIV_MAX_RESULTS = 15   # enough for critic to find the 2-3 best papers

# ─── Hacker News ──────────────────────────────────────────────────────────────
HN_TOP_STORIES_COUNT = 40

HN_AI_KEYWORDS = [
    "llm", "gpt", "claude", "gemini", "openai", "deepmind", "anthropic",
    "artificial intelligence", "machine learning", "neural network",
    "transformer", "diffusion", "reinforcement learning", "rl", "fine-tun",
    "ai model", "language model", "foundation model", "multimodal",
    "karpathy", "sutskever", "hassabis", "altman", "lecun", "mistral",
    "hugging face", "pytorch", "tensorflow", "jax",
    "benchmark", "reasoning", "agent", "alignment", "agi",
    "china", "regulation", "copyright", "lawsuit", "raises", "funding",
]

# ─── Digest Settings ──────────────────────────────────────────────────────────
MAX_ARTICLES_PER_DIGEST = 10   # editor picks the best 10
MIN_RELEVANCE_SCORE = 6
LOOKBACK_HOURS = 48            # 48h catches news since last digest + buffer
TOPIC_MEMORY_DAYS = 7          # remembered topics expire after 7 days
