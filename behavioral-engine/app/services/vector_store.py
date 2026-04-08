"""
Vector store service using ChromaDB
Handles storage and retrieval of embeddings
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for managing vector storage with ChromaDB
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client and collection
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        logger.info(f"Initializing ChromaDB at: {persist_directory}")
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="behavioral_memory",
            metadata={"description": "Behavioral intelligence embeddings"}
        )
        
        logger.info(f"ChromaDB collection 'behavioral_memory' ready")
    
    def add_embedding(
        self,
        embedding: List[float],
        text: str,
        metadata: Dict[str, Any],
        doc_id: str
    ) -> None:
        """
        Add a single embedding to the collection
        
        Args:
            embedding: Vector embedding
            text: Original text
            metadata: Metadata dictionary
            doc_id: Unique document ID
        """
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        logger.debug(f"Added embedding with ID: {doc_id}")
    
    def add_embeddings_batch(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        doc_ids: List[str]
    ) -> None:
        """
        Add multiple embeddings in batch
        
        Args:
            embeddings: List of vector embeddings
            texts: List of original texts
            metadatas: List of metadata dictionaries
            doc_ids: List of unique document IDs
        """
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=doc_ids
        )
        logger.info(f"Added {len(embeddings)} embeddings to collection")
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query the collection for similar embeddings
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            
        Returns:
            Dictionary with results
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        logger.debug(f"Query returned {len(results['documents'][0])} results")
        return results
    
    def get_collection_count(self) -> int:
        """
        Get the number of items in the collection
        
        Returns:
            Count of items
        """
        return self.collection.count()
    
    def delete_collection(self) -> None:
        """
        Delete the entire collection (use with caution)
        """
        self.client.delete_collection("behavioral_memory")
        logger.warning("Collection 'behavioral_memory' deleted")
    
    def reset_collection(self) -> None:
        """
        Reset the collection (delete and recreate)
        """
        try:
            self.client.delete_collection("behavioral_memory")
        except:
            pass
        
        self.collection = self.client.get_or_create_collection(
            name="behavioral_memory",
            metadata={"description": "Behavioral intelligence embeddings"}
        )
        logger.info("Collection reset successfully")


# Global instance (singleton pattern)
_vector_store = None


def get_vector_store() -> VectorStoreService:
    """
    Get or create the global vector store instance
    
    Returns:
        VectorStoreService instance
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
