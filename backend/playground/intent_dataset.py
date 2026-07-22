"""
Intent Classification Evaluation Dataset — 110 manually curated queries.

Balanced across all 11 UserIntentType values.
Each entry: (query, expected_intent_string)
"""
from typing import List, Tuple

INTENT_DATASET: List[Tuple[str, str]] = [
    # ── IDENTITY_QUESTION (10) ──────────────────────────────────────────
    ("What kind of learner am I?", "identity_question"),
    ("What type of person am I?", "identity_question"),
    ("Who am I as a learner?", "identity_question"),
    ("Describe my identity as a viewer", "identity_question"),
    ("What are my core interests?", "identity_question"),
    ("Tell me about my personality", "identity_question"),
    ("What sort of content consumer am I?", "identity_question"),
    ("What kind of viewer am I?", "identity_question"),
    ("Describe my profile and preferences", "identity_question"),
    ("What defines my identity?", "identity_question"),

    # ── EXPLANATION (10) ────────────────────────────────────────────────
    ("Why have my interests changed recently?", "explanation"),
    ("Why do I keep watching cooking videos?", "explanation"),
    ("Why did my preferences shift?", "explanation"),
    ("What caused my change in taste?", "explanation"),
    ("Explain why I started learning Python", "explanation"),
    ("Why has my viewing pattern changed?", "explanation"),
    ("What led to my new hobby?", "explanation"),
    ("How come I suddenly like photography?", "explanation"),
    ("What factors led to my interest in AI?", "explanation"),
    ("Why are my habits changing?", "explanation"),

    # ── BEHAVIORAL_QUESTION (10) ────────────────────────────────────────
    ("What creators influence me the most?", "behavioral_question"),
    ("What are my strongest behavioral patterns?", "behavioral_question"),
    ("How often do I watch educational content?", "behavioral_question"),
    ("What are my viewing habits?", "behavioral_question"),
    ("How much time do I spend on tutorials?", "behavioral_question"),
    ("What are my daily routines?", "behavioral_question"),
    ("Who influences my content choices?", "behavioral_question"),
    ("What are my scrolling patterns?", "behavioral_question"),
    ("How frequently do I watch AI content?", "behavioral_question"),
    ("What are my most watched topics?", "behavioral_question"),

    # ── REFLECTION (10) ─────────────────────────────────────────────────
    ("How has my AI learning evolved?", "reflection"),
    ("What have I been learning lately?", "reflection"),
    ("How have my tastes changed over time?", "reflection"),
    ("What have I been watching recently?", "reflection"),
    ("How has my content diet changed?", "reflection"),
    ("What am I learning these days?", "reflection"),
    ("How did my habits evolve this year?", "reflection"),
    ("What have I been noticing about my behavior?", "reflection"),
    ("How has my taste in content grown?", "reflection"),
    ("What progress have I made in my learning?", "reflection"),

    # ── INFORMATION (10) ────────────────────────────────────────────────
    ("What evidence supports that conclusion?", "information"),
    ("What is machine learning?", "information"),
    ("Tell me about Python programming", "information"),
    ("How does neural networking work?", "information"),
    ("What are the benefits of meditation?", "information"),
    ("Define what cognitive science is", "information"),
    ("How do recommendation systems work?", "information"),
    ("What does the data show about my habits?", "information"),
    ("What information is available about my learning?", "information"),
    ("Describe how memory consolidation works", "information"),

    # ── COMPARISON (10) ─────────────────────────────────────────────────
    ("Compare my interest in AI vs programming", "comparison"),
    ("What is the difference between Python and JavaScript?", "comparison"),
    ("Which is better for me, videos or articles?", "comparison"),
    ("How do my interests compare to last year?", "comparison"),
    ("What are the differences between my habits then and now?", "comparison"),
    ("Compare watching tutorials vs reading docs", "comparison"),
    ("How does my learning style differ from others?", "comparison"),
    ("Which content type do I prefer more?", "comparison"),
    ("What are the similarities between gaming and coding?", "comparison"),
    ("How do my evening and morning habits contrast?", "comparison"),

    # ── PREDICTION (10) ─────────────────────────────────────────────────
    ("Will I continue learning Python?", "prediction"),
    ("What will I be interested in next month?", "prediction"),
    ("Predict my future learning path", "prediction"),
    ("Will I keep watching science videos?", "prediction"),
    ("What are the trends in my content consumption?", "prediction"),
    ("How long will I stay interested in photography?", "prediction"),
    ("What is the likelihood I will finish this course?", "prediction"),
    ("Will I still be coding in a year?", "prediction"),
    ("What is next for my learning journey?", "prediction"),
    ("Forecast my interest in AI over the next quarter", "prediction"),

    # ── COACHING (10) ───────────────────────────────────────────────────
    ("How can I improve my learning habits?", "coaching"),
    ("Help me build a better study routine", "coaching"),
    ("What strategy should I use to learn faster?", "coaching"),
    ("Give me advice on staying focused", "coaching"),
    ("How can I get better at programming?", "coaching"),
    ("What tips do you have for consistent learning?", "coaching"),
    ("Should I focus on breadth or depth?", "coaching"),
    ("How can I achieve my learning goals?", "coaching"),
    ("What can I do to improve my productivity?", "coaching"),
    ("Suggest a plan to improve my skills", "coaching"),

    # ── RECOMMENDATION (10) ─────────────────────────────────────────────
    ("Recommend some good Python tutorials", "recommendation"),
    ("What should I watch next?", "recommendation"),
    ("Suggest interesting content for me", "recommendation"),
    ("What are good resources for learning AI?", "recommendation"),
    ("What else should I explore based on my interests?", "recommendation"),
    ("Any good channels for photography?", "recommendation"),
    ("What similar content would I enjoy?", "recommendation"),
    ("Recommend a learning path for data science", "recommendation"),
    ("What should I read after this course?", "recommendation"),
    ("Can you suggest some good fitness content?", "recommendation"),

    # ── MEMORY_QUESTION (10) ────────────────────────────────────────────
    ("What did I watch last week?", "memory_question"),
    ("Do you remember what I viewed yesterday?", "memory_question"),
    ("What was I watching earlier today?", "memory_question"),
    ("What content did I save last month?", "memory_question"),
    ("What did I watch before this session?", "memory_question"),
    ("What was I learning about last night?", "memory_question"),
    ("Did I watch any Python tutorials previously?", "memory_question"),
    ("Recall what I liked last week", "memory_question"),
    ("What happened during my last session?", "memory_question"),
    ("What did I do earlier in the app?", "memory_question"),

    # ── UNKNOWN (10) ────────────────────────────────────────────────────
    ("Hello", "unknown"),
    ("Good morning", "unknown"),
    ("Thank you", "unknown"),
    ("Okay", "unknown"),
    ("That is interesting", "unknown"),
    ("I see", "unknown"),
    ("Hi there", "unknown"),
    ("Nice", "unknown"),
    ("Cool", "unknown"),
    ("Yes", "unknown"),
]
