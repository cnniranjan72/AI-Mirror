"""
Vector store service using Neon PostgreSQL with pgvector
Replaces ChromaDB with PostgreSQL vector storage
"""

from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import uuid

from app.database import (
    get_db_connection,
    execute_query,
    execute_one,
    execute_insert,
    execute_many,
    list_to_vector
)

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for managing vector storage with PostgreSQL + pgvector
    """
    
    def __init__(self):
        """Initialize PostgreSQL vector store service"""
        logger.info("Initializing PostgreSQL vector store with pgvector")
    
    async def add_embedding(
        self,
        user_id: str,
        embedding: List[float],
        text: str,
        metadata: Dict[str, Any],
        doc_type: str = "behavioral_event",
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a single embedding to the database
        
        Args:
            user_id: User identifier
            embedding: Vector embedding (384 dimensions)
            text: Original text content
            metadata: Metadata dictionary
            doc_type: Type of document (session, trait, trend, persona, etc.)
            doc_id: Optional document ID (generated if not provided)
            
        Returns:
            Document ID
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        # Convert embedding to PostgreSQL vector format
        embedding_str = list_to_vector(embedding)
        
        # Convert metadata to JSONB
        metadata_json = json.dumps(metadata)
        
        query = """
            INSERT INTO behavioral_memory (user_id, type, content, embedding, metadata)
            VALUES ($1, $2, $3, $4::vector, $5::jsonb)
            RETURNING id
        """
        
        result = await execute_insert(
            query,
            user_id,
            doc_type,
            text,
            embedding_str,
            metadata_json
        )
        
        logger.debug(f"Added embedding for user {user_id}, type {doc_type}")
        return str(result['id'])
    
    async def add_embeddings_batch(
        self,
        user_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        doc_types: List[str],
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add multiple embeddings in batch
        
        Args:
            user_id: User identifier
            embeddings: List of vector embeddings
            texts: List of original texts
            metadatas: List of metadata dictionaries
            doc_types: List of document types
            doc_ids: Optional list of document IDs
            
        Returns:
            List of inserted document IDs
        """
        if doc_ids is None:
            doc_ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]
        
        # Prepare batch data
        batch_data = []
        for i, (embedding, text, metadata, doc_type) in enumerate(
            zip(embeddings, texts, metadatas, doc_types)
        ):
            embedding_str = list_to_vector(embedding)
            metadata_json = json.dumps(metadata)
            batch_data.append((
                user_id,
                doc_type,
                text,
                embedding_str,
                metadata_json
            ))
        
        query = """
            INSERT INTO behavioral_memory (user_id, type, content, embedding, metadata)
            VALUES ($1, $2, $3, $4::vector, $5::jsonb)
        """
        
        await execute_many(query, batch_data)
        
        logger.info(f"Added {len(embeddings)} embeddings for user {user_id}")
        return doc_ids
    
    async def query(
        self,
        user_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        doc_type: Optional[str] = None,
        doc_types: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        recency_weight: float = 0.0001
    ) -> Dict[str, Any]:
        """
        Query the database for similar embeddings using cosine similarity with recency weighting
        
        Args:
            user_id: User identifier
            query_embedding: Query vector embedding
            top_k: Number of results to return
            doc_type: Optional filter by single document type
            doc_types: Optional filter by multiple document types
            metadata_filter: Optional metadata filters
            recency_weight: Weight for recency in scoring (default: 0.0001)
            
        Returns:
            Dictionary with results containing documents, metadatas, distances
        """
        # Convert embedding to PostgreSQL vector format
        embedding_str = list_to_vector(query_embedding)
        
        # Build query with optional filters
        where_clauses = ["user_id = $1"]
        params = [user_id]
        param_count = 1
        
        # Handle type filtering (single or multiple types)
        if doc_types:
            param_count += 1
            where_clauses.append(f"type = ANY(${param_count})")
            params.append(doc_types)
        elif doc_type:
            param_count += 1
            where_clauses.append(f"type = ${param_count}")
            params.append(doc_type)
        
        if metadata_filter:
            for key, value in metadata_filter.items():
                param_count += 1
                where_clauses.append(f"metadata->>{key!r} = ${param_count}")
                params.append(str(value))
        
        where_clause = " AND ".join(where_clauses)
        
        param_count += 1
        embedding_param = f"${param_count}"
        param_count += 1
        limit_param = f"${param_count}"
        
        params.extend([embedding_str, top_k])
        
        # Query with recency weighting
        # Balances similarity with recency (newer documents get slight boost)
        query = f"""
            SELECT 
                id,
                content,
                metadata,
                type,
                created_at,
                embedding <-> {embedding_param}::vector AS distance,
                (embedding <-> {embedding_param}::vector) + 
                (EXTRACT(EPOCH FROM (NOW() - created_at)) * {recency_weight}) AS weighted_score
            FROM behavioral_memory
            WHERE {where_clause}
            ORDER BY weighted_score
            LIMIT {limit_param}
        """
        
        results = await execute_query(query, *params)
        
        # Format results to match ChromaDB structure
        documents = []
        metadatas = []
        distances = []
        ids = []
        
        for row in results:
            documents.append(row['content'])
            metadatas.append(row['metadata'])
            distances.append(float(row['distance']))
            ids.append(str(row['id']))
        
        logger.debug(f"Query returned {len(documents)} results for user {user_id}")
        
        return {
            'documents': [documents],  # Wrapped in list for ChromaDB compatibility
            'metadatas': [metadatas],
            'distances': [distances],
            'ids': [ids]
        }
    
    async def query_by_type(
        self,
        user_id: str,
        doc_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query documents by type without similarity search
        
        Args:
            user_id: User identifier
            doc_type: Document type to filter
            limit: Maximum number of results
            
        Returns:
            List of documents
        """
        query = """
            SELECT id, content, metadata, type, created_at
            FROM behavioral_memory
            WHERE user_id = $1 AND type = $2
            ORDER BY created_at DESC
            LIMIT $3
        """
        
        results = await execute_query(query, user_id, doc_type, limit)
        
        return [
            {
                'id': str(row['id']),
                'content': row['content'],
                'metadata': row['metadata'],
                'type': row['type'],
                'created_at': row['created_at'].isoformat()
            }
            for row in results
        ]
    
    async def get_recent_documents(
        self,
        user_id: str,
        limit: int = 20,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent documents for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of results
            doc_type: Optional filter by document type
            
        Returns:
            List of recent documents
        """
        if doc_type:
            query = """
                SELECT id, content, metadata, type, created_at
                FROM behavioral_memory
                WHERE user_id = $1 AND type = $2
                ORDER BY created_at DESC
                LIMIT $3
            """
            results = await execute_query(query, user_id, doc_type, limit)
        else:
            query = """
                SELECT id, content, metadata, type, created_at
                FROM behavioral_memory
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            results = await execute_query(query, user_id, limit)
        
        return [
            {
                'id': str(row['id']),
                'content': row['content'],
                'metadata': row['metadata'],
                'type': row['type'],
                'created_at': row['created_at'].isoformat()
            }
            for row in results
        ]
    
    async def get_collection_count(self, user_id: Optional[str] = None) -> int:
        """
        Get the number of items in the collection
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Count of items
        """
        if user_id:
            query = "SELECT COUNT(*) as count FROM behavioral_memory WHERE user_id = $1"
            result = await execute_one(query, user_id)
        else:
            query = "SELECT COUNT(*) as count FROM behavioral_memory"
            result = await execute_one(query)
        
        return result['count']
    
    async def delete_user_data(self, user_id: str) -> int:
        """
        Delete all data for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of deleted rows
        """
        query = "DELETE FROM behavioral_memory WHERE user_id = $1"
        async with get_db_connection() as conn:
            result = await conn.execute(query, user_id)
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[-1]) if result else 0
        
        logger.warning(f"Deleted {count} records for user {user_id}")
        return count
    
    async def add_chat_message(
        self,
        user_id: str,
        message: str,
        role: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a chat message to chat_history table
        
        Args:
            user_id: User identifier
            message: Chat message content
            role: Message role (user or assistant)
            embedding: Message embedding
            metadata: Optional metadata
            
        Returns:
            Message ID
        """
        embedding_str = list_to_vector(embedding)
        metadata_json = json.dumps(metadata or {})
        
        query = """
            INSERT INTO chat_history (user_id, message, role, embedding, metadata)
            VALUES ($1, $2, $3, $4::vector, $5::jsonb)
            RETURNING id
        """
        
        result = await execute_insert(
            query,
            user_id,
            message,
            role,
            embedding_str,
            metadata_json
        )
        
        return str(result['id'])
    
    async def get_chat_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent chat history for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of messages
            
        Returns:
            List of chat messages
        """
        query = """
            SELECT id, message, role, metadata, created_at
            FROM chat_history
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        results = await execute_query(query, user_id, limit)
        
        return [
            {
                'id': str(row['id']),
                'message': row['message'],
                'role': row['role'],
                'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat()
            }
            for row in reversed(results)  # Reverse to get chronological order
        ]
    
    async def hybrid_search(
        self,
        user_id: str,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        doc_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Hybrid search combining vector similarity and keyword matching
        
        Args:
            user_id: User identifier
            query_embedding: Query vector embedding
            query_text: Query text for keyword matching
            top_k: Number of results to return
            vector_weight: Weight for vector similarity (default: 0.7)
            keyword_weight: Weight for keyword matching (default: 0.3)
            doc_types: Optional filter by document types
            
        Returns:
            Dictionary with results containing documents, metadatas, scores
        """
        # Convert embedding to PostgreSQL vector format
        embedding_str = list_to_vector(query_embedding)
        
        # Build query with optional type filtering
        type_filter = ""
        params = [user_id, embedding_str, query_text, vector_weight, keyword_weight, top_k]
        
        if doc_types:
            type_filter = "AND type = ANY($7)"
            params.append(doc_types)
        
        query = f"""
            SELECT 
                id,
                content,
                metadata,
                type,
                created_at,
                (1 - (embedding <-> $2::vector)) AS similarity_score,
                ts_rank(content_tsv, plainto_tsquery('english', $3)) AS keyword_score,
                (
                    (1 - (embedding <-> $2::vector)) * $4 +
                    ts_rank(content_tsv, plainto_tsquery('english', $3)) * $5
                ) AS hybrid_score
            FROM behavioral_memory
            WHERE user_id = $1
            {type_filter}
            ORDER BY hybrid_score DESC
            LIMIT $6
        """
        
        results = await execute_query(query, *params)
        
        # Format results
        documents = []
        metadatas = []
        similarity_scores = []
        keyword_scores = []
        hybrid_scores = []
        ids = []
        
        for row in results:
            documents.append(row['content'])
            metadatas.append(row['metadata'])
            similarity_scores.append(float(row['similarity_score']))
            keyword_scores.append(float(row['keyword_score']))
            hybrid_scores.append(float(row['hybrid_score']))
            ids.append(str(row['id']))
        
        logger.debug(f"Hybrid search returned {len(documents)} results for user {user_id}")
        
        return {
            'documents': [documents],
            'metadatas': [metadatas],
            'similarity_scores': [similarity_scores],
            'keyword_scores': [keyword_scores],
            'hybrid_scores': [hybrid_scores],
            'ids': [ids]
        }


# Global instance (singleton pattern)
_vector_store = None


async def get_vector_store() -> VectorStoreService:
    """
    Get or create the global vector store instance
    
    Returns:
        VectorStoreService instance
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
