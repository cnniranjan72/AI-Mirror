"""
NLP Enrichment Layer
Input: caption + hashtags
Output: topics, sentiment, intent
Uses keyword mapping (no external API)
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Topic keywords (expanded for better detection)
TOPIC_KEYWORDS = {
    "finance": ["money", "invest", "crypto", "stock", "business", "market", "trading", "wealth", "rupee", "dollar", "bank", "cash", "profit", "income"],
    "fitness": ["gym", "workout", "fitness", "diet", "muscle", "health", "exercise", "training", "body", "fit"],
    "education": ["learn", "study", "course", "roadmap", "career", "tutorial", "guide", "skill", "knowledge", "teach"],
    "technology": ["ai", "ml", "tech", "software", "coding", "programming", "code", "developer", "app", "data", "algorithm"],
    "entertainment": ["fun", "comedy", "meme", "viral", "funny", "dance", "music", "trending", "entertainment", "reels"],
    "lifestyle": ["life", "daily", "routine", "habit", "vlog", "day", "morning", "night", "lifestyle"],
    "food": ["food", "recipe", "cook", "eat", "meal", "restaurant", "cooking", "kitchen", "dish", "taste"],
    "travel": ["travel", "trip", "vacation", "place", "destination", "tour", "explore", "adventure", "visit"],
}

# Sentiment keywords
POSITIVE_WORDS = ["good", "great", "amazing", "love", "happy", "best", "awesome", "excellent", "perfect", "beautiful", "wonderful", "fantastic"]
NEGATIVE_WORDS = ["bad", "hate", "worst", "terrible", "awful", "sad", "angry", "disappointed", "fail", "boring"]

# Intent keywords
INTENT_KEYWORDS = {
    "educational": ["learn", "how", "tutorial", "guide", "tips", "roadmap", "course", "teach", "explain", "understand"],
    "entertainment": ["fun", "funny", "comedy", "meme", "dance", "music", "entertainment", "enjoy", "watch"],
    "promotional": ["buy", "sale", "discount", "offer", "deal", "shop", "product", "link", "price", "order"],
}


def detect_topics(text: str, hashtags: List[str]) -> List[str]:
    """Detect topics from caption and hashtags"""
    text = text.lower()
    topics = []
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(word in text for word in keywords):
            topics.append(topic)
    
    # Also check hashtags
    for tag in hashtags:
        tag_lower = tag.lower().replace("#", "")
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(word in tag_lower for word in keywords):
                if topic not in topics:
                    topics.append(topic)
    
    return topics if topics else ["general"]


def detect_sentiment(text: str) -> str:
    """Detect sentiment from text"""
    text = text.lower()
    positive_count = sum(1 for word in POSITIVE_WORDS if word in text)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    return "neutral"


def detect_intent(text: str) -> str:
    """Detect intent from text"""
    text = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(word in text for word in keywords):
            return intent
    return "entertainment"


def enrich(caption: str, hashtags: List[str]) -> Dict[str, Any]:
    """
    Enrich a caption with NLP analysis
    
    Returns:
        {
            "topics": [...],
            "sentiment": "...",
            "intent": "..."
        }
    """
    text = f"{caption} {' '.join(hashtags)}"
    
    topics = detect_topics(text, hashtags)
    sentiment = detect_sentiment(text)
    intent = detect_intent(text)
    
    logger.info(f"[ENRICH] topics={topics} sentiment={sentiment} intent={intent}")
    
    return {
        "topics": topics,
        "sentiment": sentiment,
        "intent": intent,
    }
