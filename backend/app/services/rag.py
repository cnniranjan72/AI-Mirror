"""
RAG System — Retrieval-Augmented Generation
Template-based response generation (no LLM required).
Uses vector store retrieval + persona context.
"""

import logging
from typing import Dict, List, Any, Optional

from app.services import vector_store, embedding as emb

logger = logging.getLogger(__name__)

# Response templates
TEMPLATES = {
    "behavior_summary": (
        "Based on your recent activity, here's what I see:\n\n"
        "{context}\n\n"
        "Your behavioral profile suggests you are a **{persona}** "
        "with attention score {attention:.2f} and engagement {engagement:.2f}."
    ),
    "content_insight": (
        "Looking at your content consumption patterns:\n\n"
        "{context}\n\n"
        "You tend to gravitate toward {topics} content. "
        "Your curiosity score is {curiosity:.2f}."
    ),
    "recommendation": (
        "Based on your behavioral patterns:\n\n"
        "{context}\n\n"
        "**Recommendations:**\n{recommendations}"
    ),
    "default": (
        "Here's what I found relevant to your query:\n\n"
        "{context}\n\n"
        "This is based on {doc_count} behavioral data points."
    ),
}


async def query(
    user_id: str,
    query_text: str,
    top_k: int = 5,
    persona_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    RAG query: embed → retrieve → generate response.

    Args:
        user_id: user identifier
        query_text: natural language query
        top_k: number of documents to retrieve
        persona_data: optional persona context

    Returns:
        {answer, sources, query}
    """
    # 1. Embed the query
    query_vec = emb.encode(query_text)

    # 2. Hybrid retrieval (vector + keyword)
    docs = await vector_store.hybrid_search(
        user_id=user_id,
        query_embedding=query_vec,
        query_text=query_text,
        top_k=top_k,
    )

    # Fallback to pure vector search if hybrid returns nothing
    if not docs:
        docs = await vector_store.similarity_search(
            user_id=user_id,
            query_embedding=query_vec,
            top_k=top_k,
        )

    # 3. Build context from retrieved docs
    context_parts = []
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"{i}. {doc['text'][:200]}")
    context = "\n".join(context_parts) if context_parts else "No behavioral data found yet."

    # 4. Determine template
    q_lower = query_text.lower()
    if any(w in q_lower for w in ["pattern", "behavior", "summary", "how am i"]):
        template_key = "behavior_summary"
    elif any(w in q_lower for w in ["content", "watch", "topic", "interest"]):
        template_key = "content_insight"
    elif any(w in q_lower for w in ["recommend", "suggest", "should i", "improve"]):
        template_key = "recommendation"
    else:
        template_key = "default"

    # 5. Fill template
    persona = persona_data or {}
    template = TEMPLATES[template_key]

    answer = template.format(
        context=context,
        persona=persona.get("persona_label", "Emerging User"),
        attention=persona.get("traits", {}).get("attention_score", 0),
        engagement=persona.get("traits", {}).get("engagement_score", 0),
        curiosity=persona.get("traits", {}).get("curiosity_score", 0),
        topics=", ".join(persona.get("interest_vector", {}).get("top_topics", ["general"])),
        recommendations=_format_recommendations(persona.get("recommendations", [])),
        doc_count=len(docs),
    )

    logger.info("RAG query processed for user=%s template=%s docs=%d", user_id, template_key, len(docs))

    return {
        "answer": answer,
        "sources": [{"text": d["text"][:150], "score": d.get("hybrid_score", d.get("score", 0))} for d in docs[:3]],
        "query": query_text,
        "template_used": template_key,
        "docs_retrieved": len(docs),
    }


def _format_recommendations(recs: List[str]) -> str:
    if not recs:
        return "- Continue exploring diverse content\n- Take mindful breaks between sessions"
    return "\n".join(f"- {r}" for r in recs)
