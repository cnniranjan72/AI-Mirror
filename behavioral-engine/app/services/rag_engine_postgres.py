"""
RAG Engine using PostgreSQL vector store
Replaces ChromaDB-based retrieval with PostgreSQL + pgvector
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from app.services.vector_store_postgres import get_vector_store
from app.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine using PostgreSQL
    """
    
    def __init__(self):
        """Initialize RAG engine"""
        self.embedding_service = None
        self.vector_store = None
        logger.info("RAG Engine initialized with PostgreSQL backend")
    
    async def initialize(self):
        """Initialize services"""
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        if self.vector_store is None:
            self.vector_store = await get_vector_store()
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        doc_types: Optional[List[str]] = None,
        include_chat_history: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query with type filtering and chat history
        
        Args:
            user_id: User identifier
            query: Query text
            top_k: Number of results to retrieve
            doc_types: Optional list of document types to filter
            include_chat_history: Include relevant chat history in context
            
        Returns:
            List of relevant context documents
        """
        await self.initialize()
        
        # Generate query embedding
        query_embedding = self.embedding_service.encode(query)
        
        # Retrieve from vector store with type filtering
        results = await self.vector_store.query(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            doc_types=doc_types,  # Use multiple types filtering
            recency_weight=0.0001  # Balance similarity with recency
        )
        
        # Format results
        context_docs = []
        for i, doc in enumerate(results['documents'][0]):
            context_docs.append({
                'content': doc,
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'type': results['metadatas'][0][i].get('type', 'unknown')
            })
        
        # Add relevant chat history if requested
        if include_chat_history:
            chat_history = await self.vector_store.get_chat_history(
                user_id=user_id,
                limit=5
            )
            
            # Add recent chat context
            for msg in chat_history[-3:]:  # Last 3 messages
                context_docs.append({
                    'content': f"[{msg['role'].upper()}]: {msg['message']}",
                    'metadata': msg['metadata'],
                    'distance': 0.0,  # Chat history is always relevant
                    'type': 'chat_history'
                })
        
        return context_docs
    
    async def retrieve_behavioral_context(
        self,
        user_id: str,
        query: str,
        include_sessions: bool = True,
        include_traits: bool = True,
        include_trends: bool = True,
        include_chat_history: bool = True,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive behavioral context with type filtering
        
        Args:
            user_id: User identifier
            query: Query text
            include_sessions: Include session summaries
            include_traits: Include behavioral traits
            include_trends: Include behavioral trends
            include_chat_history: Include chat history
            top_k: Number of results per category
            
        Returns:
            Dictionary with categorized context
        """
        await self.initialize()
        
        # Generate query embedding
        query_embedding = self.embedding_service.encode(query)
        
        context = {
            'sessions': [],
            'traits': [],
            'trends': [],
            'chat_history': [],
            'recent_activity': []
        }
        
        # Build list of types to retrieve
        doc_types = []
        if include_sessions:
            doc_types.append('session_summary')
        if include_traits:
            doc_types.append('behavioral_traits')
        if include_trends:
            doc_types.append('behavioral_trend')
        
        # Single query with multiple types (more efficient)
        if doc_types:
            results = await self.vector_store.query(
                user_id=user_id,
                query_embedding=query_embedding,
                top_k=top_k * len(doc_types),
                doc_types=doc_types,  # Filter by multiple types
                recency_weight=0.0001  # Balance similarity with recency
            )
            
            # Categorize results by type
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                doc_type = metadata.get('type', 'unknown')
                
                result_item = {
                    'content': doc,
                    'metadata': metadata,
                    'distance': results['distances'][0][i]
                }
                
                if doc_type == 'session_summary':
                    context['sessions'].append(result_item)
                elif doc_type == 'behavioral_traits':
                    context['traits'].append(result_item)
                elif doc_type == 'behavioral_trend':
                    context['trends'].append(result_item)
        
        # Get chat history
        if include_chat_history:
            chat_history = await self.vector_store.get_chat_history(
                user_id=user_id,
                limit=5
            )
            context['chat_history'] = chat_history
        
        # Get recent activity
        recent_docs = await self.vector_store.get_recent_documents(
            user_id=user_id,
            limit=10
        )
        context['recent_activity'] = recent_docs
        
        return context
    
    async def fuse_context(
        self,
        context: Dict[str, Any],
        query: str,
        max_tokens: int = 2000
    ) -> str:
        """
        Fuse retrieved context into a coherent prompt including chat history
        
        Args:
            context: Retrieved context dictionary
            query: Original query
            max_tokens: Maximum tokens for context (approximate)
            
        Returns:
            Fused context string
        """
        fused_parts = []
        
        # Add chat history first (most recent context)
        if context.get('chat_history'):
            fused_parts.append("## Recent Conversation")
            for msg in context['chat_history'][-3:]:
                role = msg['role'].upper()
                fused_parts.append(f"- [{role}]: {msg['message'][:150]}")
        
        # Add recent activity
        if context.get('recent_activity'):
            fused_parts.append("\n## Recent Activity")
            for doc in context['recent_activity'][:3]:
                fused_parts.append(f"- {doc['content'][:200]}")
        
        # Add behavioral traits
        if context.get('traits'):
            fused_parts.append("\n## Behavioral Traits")
            for trait in context['traits'][:2]:
                fused_parts.append(f"- {trait['content'][:200]}")
        
        # Add trends
        if context.get('trends'):
            fused_parts.append("\n## Behavioral Trends")
            for trend in context['trends'][:2]:
                fused_parts.append(f"- {trend['content'][:200]}")
        
        # Add sessions
        if context.get('sessions'):
            fused_parts.append("\n## Session History")
            for session in context['sessions'][:2]:
                fused_parts.append(f"- {session['content'][:200]}")
        
        fused_context = "\n".join(fused_parts)
        
        # Truncate if too long (rough approximation: 4 chars per token)
        max_chars = max_tokens * 4
        if len(fused_context) > max_chars:
            fused_context = fused_context[:max_chars] + "..."
        
        return fused_context
    
    async def generate_response(
        self,
        user_id: str,
        query: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate RAG response with retrieved context
        
        Args:
            user_id: User identifier
            query: User query
            system_prompt: Optional system prompt override
            
        Returns:
            Response dictionary with answer and context
        """
        await self.initialize()
        
        # Retrieve behavioral context
        context = await self.retrieve_behavioral_context(
            user_id=user_id,
            query=query,
            top_k=3
        )
        
        # Fuse context
        fused_context = await self.fuse_context(context, query)
        
        # Build prompt
        if system_prompt is None:
            system_prompt = """You are an AI Mirror - a behavioral digital twin that helps users understand their social media usage patterns. 
You provide insights based on their behavioral data, helping them make informed decisions about their digital wellbeing."""
        
        prompt = f"""{system_prompt}

# Behavioral Context
{fused_context}

# User Query
{query}

# Response
Provide a helpful, insightful response based on the user's behavioral data."""
        
        # Note: Actual LLM call would go here
        # For now, return the context and prompt
        return {
            'prompt': prompt,
            'context': context,
            'fused_context': fused_context,
            'query': query
        }
    
    async def store_interaction(
        self,
        user_id: str,
        query: str,
        response: str
    ) -> None:
        """
        Store user interaction for future retrieval
        
        Args:
            user_id: User identifier
            query: User query
            response: System response
        """
        await self.initialize()
        
        # Generate embeddings
        query_embedding = self.embedding_service.encode(query)
        response_embedding = self.embedding_service.encode(response)
        
        # Store in chat history
        await self.vector_store.add_chat_message(
            user_id=user_id,
            message=query,
            role='user',
            embedding=query_embedding,
            metadata={'timestamp': datetime.now().isoformat()}
        )
        
        await self.vector_store.add_chat_message(
            user_id=user_id,
            message=response,
            role='assistant',
            embedding=response_embedding,
            metadata={'timestamp': datetime.now().isoformat()}
        )


# Global instance
_rag_engine = None


async def get_rag_engine() -> RAGEngine:
    """
    Get or create the global RAG engine instance
    
    Returns:
        RAGEngine instance
    """
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
        await _rag_engine.initialize()
    return _rag_engine
