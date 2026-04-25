"""
Content Expansion Layer
Converts short captions into rich, embeddable text.
No external API — uses keyword expansion and template generation.
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Domain knowledge for expansion
DOMAIN_EXPANSIONS: Dict[str, str] = {
    "ml": "machine learning including supervised learning, unsupervised learning, neural networks, and model evaluation",
    "ai": "artificial intelligence covering natural language processing, computer vision, reinforcement learning, and generative models",
    "python": "Python programming language used for data science, web development, automation, and machine learning",
    "javascript": "JavaScript programming for web applications, frontend frameworks like React, and backend with Node.js",
    "react": "React.js frontend framework for building interactive user interfaces with component-based architecture",
    "crypto": "cryptocurrency and blockchain technology including Bitcoin, Ethereum, DeFi, and digital wallets",
    "trading": "financial trading involving stock market analysis, technical indicators, risk management, and portfolio strategies",
    "gym": "physical fitness training including weight training, progressive overload, muscle hypertrophy, and recovery",
    "yoga": "yoga practice combining physical postures, breathing techniques, meditation, and mindfulness",
    "diet": "nutrition and dietary planning including macronutrients, meal prep, calorie management, and healthy eating",
    "startup": "startup ecosystem including product development, fundraising, market validation, and scaling strategies",
    "coding": "software development including algorithms, data structures, system design, and clean code practices",
    "dsa": "data structures and algorithms including arrays, trees, graphs, dynamic programming, and sorting algorithms",
    "invest": "investment strategies including stocks, mutual funds, ETFs, real estate, and compound interest",
    "roadmap": "structured learning path with milestones, resources, timelines, and skill progression",
    "skincare": "skincare routine including cleansing, moisturizing, sunscreen, serums, and dermatological treatments",
    "travel": "travel experiences including destinations, itineraries, budget planning, and cultural exploration",
    "recipe": "cooking recipe with ingredients, preparation steps, cooking techniques, and serving suggestions",
    "meditation": "meditation practice for mental clarity, stress reduction, focus improvement, and emotional balance",
    "productivity": "productivity techniques including time management, deep work, goal setting, and habit formation",
}

# Content templates per intent
TEMPLATES = {
    "educational": "This content covers {topics_str}. {expansion} The educational focus emphasizes learning and skill development in these areas.",
    "entertainment": "This entertaining content relates to {topics_str}. {expansion} It captures attention through engaging and relatable presentation.",
    "promotional": "This promotional content showcases {topics_str}. {expansion} It aims to drive engagement and consumer interest.",
    "inspirational": "This motivational content focuses on {topics_str}. {expansion} It inspires action through personal stories and empowering messages.",
}

DEFAULT_TEMPLATE = "This content explores {topics_str}. {expansion} It reflects the creator's perspective on these subjects."


def expand(
    caption: str,
    hashtags: List[str],
    enrichment: Dict[str, Any],
) -> str:
    """
    Expand a short caption into rich, embeddable text.

    Args:
        caption: raw caption text
        hashtags: list of hashtags
        enrichment: output from enrichment layer (topics, sentiment, intent)

    Returns:
        Expanded text string (3-5 sentences)
    """
    topics = enrichment.get("topics", ["general"])
    sentiment = enrichment.get("sentiment", "neutral")
    intent = enrichment.get("intent", "entertainment")

    # Build keyword expansions
    all_words = set(re.findall(r"[a-z]+", (caption + " " + " ".join(hashtags)).lower()))
    expansions = []
    for word in all_words:
        if word in DOMAIN_EXPANSIONS:
            expansions.append(DOMAIN_EXPANSIONS[word])

    # Build expansion text
    if expansions:
        expansion = "Key concepts include: " + "; ".join(expansions[:3]) + "."
    elif caption and len(caption) > 20:
        expansion = f'The content discusses: "{caption[:120]}."'
    else:
        expansion = "The content presents information in a concise visual format."

    # Build topics string
    topics_str = ", ".join(topics) if topics else "general interest"

    # Add sentiment context
    sentiment_text = {
        "positive": "The tone is upbeat and encouraging.",
        "negative": "The tone carries critical or cautionary undertones.",
        "neutral": "The tone is informational and balanced.",
    }.get(sentiment, "")

    # Pick template
    template = TEMPLATES.get(intent, DEFAULT_TEMPLATE)
    base = template.format(topics_str=topics_str, expansion=expansion)

    # Add hashtag context if present
    hashtag_text = ""
    if hashtags:
        clean_tags = [h.lstrip("#") for h in hashtags[:5]]
        hashtag_text = f" Tagged with: {', '.join(clean_tags)}."

    expanded = f"{base} {sentiment_text}{hashtag_text}".strip()

    logger.debug("Expanded text length: %d chars", len(expanded))
    return expanded
