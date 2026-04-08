"""
Query API endpoint
Retrieves relevant behavioral insights using RAG-style retrieval with insight generation
"""
from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional

from app.models.schemas import QueryRequest, QueryResponse, QueryResult
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store
from app.services.insight_engine import get_insight_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_behavioral_insights(
    request: QueryRequest,
    generate_insight: bool = Query(default=True, description="Generate human-readable insight")
):
    """
    Query behavioral insights using semantic search with optional insight generation
    
    Process:
    1. Embed the query text
    2. Search ChromaDB for similar embeddings
    3. Optionally generate human-readable insight
    4. Return top-k results with scores
    
    Args:
        request: QueryRequest with query text and top_k
        generate_insight: Whether to generate insight from results
        
    Returns:
        QueryResponse with relevant results and optional insight
    """
    try:
        logger.info(f"Received query: '{request.query}' (top_k={request.top_k}, insight={generate_insight})")
        
        # Get services
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()
        
        # Check if collection has data
        collection_count = vector_store.get_collection_count()
        if collection_count == 0:
            logger.warning("No data in collection")
            return QueryResponse(
                results=[],
                query=request.query,
                insight=None
            )
        
        logger.info(f"Collection has {collection_count} items")
        
        # Generate query embedding
        query_embedding = embedding_service.embed_text(request.query)
        logger.debug("Query embedding generated")
        
        # Search vector store
        search_results = vector_store.query(
            query_embedding=query_embedding,
            top_k=request.top_k
        )
        
        # Format results
        results = []
        retrieved_docs = []
        
        # ChromaDB returns results in this structure:
        # {'documents': [[...]], 'distances': [[...]], 'metadatas': [[...]]}
        documents = search_results.get('documents', [[]])[0]
        distances = search_results.get('distances', [[]])[0]
        metadatas = search_results.get('metadatas', [[]])[0]
        
        for doc, distance, metadata in zip(documents, distances, metadatas):
            # Convert distance to similarity score (lower distance = higher similarity)
            # Using simple inverse: score = 1 / (1 + distance)
            score = 1.0 / (1.0 + distance)
            
            results.append(QueryResult(
                text=doc,
                score=round(score, 4),
                metadata=metadata
            ))
            
            # Store for insight generation
            retrieved_docs.append({
                'text': doc,
                'score': score,
                'metadata': metadata
            })
        
        logger.info(f"Returning {len(results)} results")
        
        # Generate insight if requested
        insight_data = None
        if generate_insight and retrieved_docs:
            insight_engine = get_insight_engine()
            insight_data = insight_engine.generate_insight(request.query, retrieved_docs)
            logger.info(f"Generated insight: {insight_data.get('insight', '')[:100]}...")
        
        return QueryResponse(
            results=results,
            query=request.query,
            insight=insight_data
        )
        
    except Exception as e:
        logger.error(f"Error in query endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
