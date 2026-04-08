"""
Behavioral Intelligence Engine - Main FastAPI Application
Processes behavioral data, generates embeddings, and provides query API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from app.api import ingest, query, profile, alignment, action, feedback, chat

# ==================== LOGGING CONFIGURATION ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Behavioral Intelligence Engine",
    description="AI-powered behavioral analysis and retrieval system",
    version="1.0.0"
)

# ==================== CORS MIDDLEWARE ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== INCLUDE ROUTERS ====================

# Core Intelligence
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(query.router, tags=["Query"])
app.include_router(profile.router, tags=["Profile"])

# RL & Alignment
app.include_router(alignment.router, tags=["Alignment"])
app.include_router(action.router, tags=["Action"])
app.include_router(feedback.router, tags=["Feedback"])

# Chat & RAG
app.include_router(chat.router, tags=["Chat"])

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 60)
    logger.info("Behavioral Intelligence Engine Starting...")
    logger.info("=" * 60)
    
    try:
        # Initialize embedding service (loads model)
        from app.services.embedding import get_embedding_service
        embedding_service = get_embedding_service()
        logger.info(f"Embedding model loaded (dimension: {embedding_service.get_embedding_dimension()})")
        
        # Initialize vector store
        from app.services.vector_store import get_vector_store
        vector_store = get_vector_store()
        logger.info(f"Vector store initialized (items: {vector_store.get_collection_count()})")
        
        logger.info("=" * 60)
        logger.info("Behavioral Intelligence Engine Ready!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise

# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": "Behavioral Intelligence Engine",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        from app.services.vector_store import get_vector_store
        vector_store = get_vector_store()
        collection_count = vector_store.get_collection_count()
        
        return {
            "status": "healthy",
            "vector_store": "connected",
            "collection_count": collection_count
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# ==================== ERROR HANDLERS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc)
    }
