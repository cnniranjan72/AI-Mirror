"""
Context Builder for RAG system
Retrieves and structures relevant context from vector database
"""
from typing import Dict, List
import logging
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds structured context for RAG responses
    """
    
    def __init__(self):
        """Initialize context builder"""
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
    
    def build_context(
        self,
        query: str,
        user_id: str,
        top_k: int = 10
    ) -> Dict:
        """
        Build context from query and user data
        
        Args:
            query: User query
            user_id: User identifier
            top_k: Number of documents to retrieve
            
        Returns:
            Structured context dictionary
        """
        # Embed query
        query_embedding = self.embedding_service.embed_text(query)
        
        # Retrieve relevant documents
        results = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k
        )
        
        # Group by type
        context = {
            "session_summaries": [],
            "behavioral_traits": [],
            "trends": [],
            "personas": [],
            "actions": [],
            "raw_documents": []
        }
        
        if not results.get('documents'):
            return context
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        for doc, metadata, distance in zip(documents, metadatas, distances):
            doc_type = metadata.get('type', 'unknown')
            score = 1.0 / (1.0 + distance)
            
            doc_data = {
                "text": doc,
                "metadata": metadata,
                "score": round(score, 3)
            }
            
            context["raw_documents"].append(doc_data)
            
            if doc_type == "session_summary":
                context["session_summaries"].append(doc_data)
            elif doc_type == "behavioral_traits":
                context["behavioral_traits"].append(doc_data)
            elif doc_type == "trend":
                context["trends"].append(doc_data)
            elif doc_type == "persona":
                context["personas"].append(doc_data)
            elif doc_type == "action":
                context["actions"].append(doc_data)
        
        logger.info(f"Built context: {len(context['session_summaries'])} summaries, "
                   f"{len(context['behavioral_traits'])} traits, {len(context['trends'])} trends")
        
        return context
    
    def get_recent_context(
        self,
        user_id: str,
        context_type: str = "all",
        limit: int = 5
    ) -> List[Dict]:
        """
        Get recent context of specific type
        
        Args:
            user_id: User identifier
            context_type: Type of context to retrieve
            limit: Maximum number of items
            
        Returns:
            List of context items
        """
        # Build type-specific query
        if context_type == "traits":
            query_text = "behavioral traits attention engagement"
        elif context_type == "summaries":
            query_text = "session summary watch time reels"
        elif context_type == "trends":
            query_text = "behavioral trends patterns changes"
        else:
            query_text = "user behavior patterns"
        
        query_embedding = self.embedding_service.embed_text(query_text)
        results = self.vector_store.query(query_embedding=query_embedding, top_k=limit)
        
        items = []
        if results.get('documents'):
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                if context_type == "all" or metadata.get('type') == context_type:
                    items.append({
                        "text": doc,
                        "metadata": metadata
                    })
        
        return items[:limit]


def get_context_builder() -> ContextBuilder:
    """Get context builder instance"""
    return ContextBuilder()
