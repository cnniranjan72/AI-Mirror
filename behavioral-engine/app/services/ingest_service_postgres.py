"""
Ingest service for behavioral data using PostgreSQL
Handles data ingestion with user_id support
"""

from typing import Dict, Any, List
import logging
from datetime import datetime
import uuid

from app.services.vector_store_postgres import get_vector_store
from app.services.embedding import get_embedding_service
from app.services.feature_engineering import compute_behavioral_traits

logger = logging.getLogger(__name__)


class IngestService:
    """
    Service for ingesting behavioral data into PostgreSQL
    """
    
    def __init__(self):
        """Initialize ingest service"""
        self.embedding_service = None
        self.vector_store = None
        logger.info("Ingest service initialized with PostgreSQL backend")
    
    async def initialize(self):
        """Initialize services"""
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        if self.vector_store is None:
            self.vector_store = await get_vector_store()
    
    async def ingest_behavioral_event(
        self,
        user_id: str,
        event_data: Dict[str, Any]
    ) -> str:
        """
        Ingest a single behavioral event
        
        Args:
            user_id: User identifier
            event_data: Event data dictionary
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        # Create text representation for embedding
        text = self._create_event_text(event_data)
        
        # Generate embedding
        embedding = self.embedding_service.encode(text)
        
        # Prepare metadata
        metadata = {
            'reel_id': event_data.get('reel_id', ''),
            'username': event_data.get('username', ''),
            'watch_time': event_data.get('watch_time', 0),
            'liked': event_data.get('liked', False),
            'timestamp': event_data.get('timestamp', datetime.now().isoformat()),
            'session_id': event_data.get('session_id', '')
        }
        
        # Store in vector database
        doc_id = await self.vector_store.add_embedding(
            user_id=user_id,
            embedding=embedding,
            text=text,
            metadata=metadata,
            doc_type='behavioral_event'
        )
        
        logger.debug(f"Ingested behavioral event for user {user_id}")
        return doc_id
    
    async def ingest_session_summary(
        self,
        user_id: str,
        session_data: Dict[str, Any]
    ) -> str:
        """
        Ingest a session summary
        
        Args:
            user_id: User identifier
            session_data: Session summary data
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        # Create text representation
        text = self._create_session_text(session_data)
        
        # Generate embedding
        embedding = self.embedding_service.encode(text)
        
        # Prepare metadata
        metadata = {
            'session_id': session_data.get('session_id', ''),
            'total_watch_time': session_data.get('total_watch_time', 0),
            'avg_watch_time': session_data.get('avg_watch_time', 0),
            'like_ratio': session_data.get('like_ratio', 0),
            'reels_count': session_data.get('reels_count', 0),
            'session_duration': session_data.get('session_duration', 0),
            'timestamp': session_data.get('timestamp', datetime.now().isoformat())
        }
        
        # Store in vector database
        doc_id = await self.vector_store.add_embedding(
            user_id=user_id,
            embedding=embedding,
            text=text,
            metadata=metadata,
            doc_type='session_summary'
        )
        
        logger.info(f"Ingested session summary for user {user_id}")
        return doc_id
    
    async def ingest_behavioral_traits(
        self,
        user_id: str,
        traits_data: Dict[str, Any]
    ) -> str:
        """
        Ingest behavioral traits
        
        Args:
            user_id: User identifier
            traits_data: Behavioral traits data
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        # Create text representation
        text = self._create_traits_text(traits_data)
        
        # Generate embedding
        embedding = self.embedding_service.encode(text)
        
        # Prepare metadata
        metadata = {
            'attention_score': traits_data.get('attention_score', 0),
            'engagement_score': traits_data.get('engagement_score', 0),
            'activity_level': traits_data.get('activity_level', 0),
            'content_diversity': traits_data.get('content_diversity', 0),
            'session_id': traits_data.get('session_id', ''),
            'timestamp': traits_data.get('timestamp', datetime.now().isoformat())
        }
        
        # Store in vector database
        doc_id = await self.vector_store.add_embedding(
            user_id=user_id,
            embedding=embedding,
            text=text,
            metadata=metadata,
            doc_type='behavioral_traits'
        )
        
        logger.debug(f"Ingested behavioral traits for user {user_id}")
        return doc_id
    
    async def ingest_behavioral_trend(
        self,
        user_id: str,
        trend_data: Dict[str, Any]
    ) -> str:
        """
        Ingest behavioral trend
        
        Args:
            user_id: User identifier
            trend_data: Trend data
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        # Create text representation
        text = self._create_trend_text(trend_data)
        
        # Generate embedding
        embedding = self.embedding_service.encode(text)
        
        # Prepare metadata
        metadata = {
            'trend_type': trend_data.get('trend_type', ''),
            'value': trend_data.get('value', 0),
            'change': trend_data.get('change', 0),
            'period': trend_data.get('period', ''),
            'timestamp': trend_data.get('timestamp', datetime.now().isoformat())
        }
        
        # Store in vector database
        doc_id = await self.vector_store.add_embedding(
            user_id=user_id,
            embedding=embedding,
            text=text,
            metadata=metadata,
            doc_type='behavioral_trend'
        )
        
        logger.debug(f"Ingested behavioral trend for user {user_id}")
        return doc_id
    
    async def ingest_persona_update(
        self,
        user_id: str,
        persona_data: Dict[str, Any]
    ) -> str:
        """
        Ingest persona update
        
        Args:
            user_id: User identifier
            persona_data: Persona data
            
        Returns:
            Document ID
        """
        await self.initialize()
        
        # Create text representation
        text = self._create_persona_text(persona_data)
        
        # Generate embedding
        embedding = self.embedding_service.encode(text)
        
        # Prepare metadata
        metadata = {
            'archetype': persona_data.get('archetype', ''),
            'confidence': persona_data.get('confidence', 0),
            'traits': persona_data.get('traits', {}),
            'timestamp': persona_data.get('timestamp', datetime.now().isoformat())
        }
        
        # Store in vector database
        doc_id = await self.vector_store.add_embedding(
            user_id=user_id,
            embedding=embedding,
            text=text,
            metadata=metadata,
            doc_type='persona_update'
        )
        
        logger.info(f"Ingested persona update for user {user_id}")
        return doc_id
    
    async def ingest_batch(
        self,
        user_id: str,
        events: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Ingest multiple events in batch
        
        Args:
            user_id: User identifier
            events: List of event data dictionaries
            
        Returns:
            List of document IDs
        """
        await self.initialize()
        
        # Prepare batch data
        embeddings = []
        texts = []
        metadatas = []
        doc_types = []
        
        for event in events:
            # Determine event type
            event_type = event.get('type', 'behavioral_event')
            
            # Create text representation
            if event_type == 'session_summary':
                text = self._create_session_text(event)
            elif event_type == 'behavioral_traits':
                text = self._create_traits_text(event)
            elif event_type == 'behavioral_trend':
                text = self._create_trend_text(event)
            elif event_type == 'persona_update':
                text = self._create_persona_text(event)
            else:
                text = self._create_event_text(event)
            
            # Generate embedding
            embedding = self.embedding_service.encode(text)
            
            # Prepare metadata
            metadata = {k: v for k, v in event.items() if k != 'type'}
            metadata['timestamp'] = event.get('timestamp', datetime.now().isoformat())
            
            embeddings.append(embedding)
            texts.append(text)
            metadatas.append(metadata)
            doc_types.append(event_type)
        
        # Batch insert
        doc_ids = await self.vector_store.add_embeddings_batch(
            user_id=user_id,
            embeddings=embeddings,
            texts=texts,
            metadatas=metadatas,
            doc_types=doc_types
        )
        
        logger.info(f"Ingested {len(events)} events for user {user_id}")
        return doc_ids
    
    def _create_event_text(self, event_data: Dict[str, Any]) -> str:
        """Create text representation of behavioral event"""
        parts = []
        
        if 'username' in event_data:
            parts.append(f"User watched content from @{event_data['username']}")
        
        if 'watch_time' in event_data:
            parts.append(f"Watch time: {event_data['watch_time']:.1f}s")
        
        if 'caption' in event_data and event_data['caption']:
            parts.append(f"Caption: {event_data['caption'][:100]}")
        
        if 'hashtags' in event_data and event_data['hashtags']:
            hashtags = ', '.join(event_data['hashtags'][:5])
            parts.append(f"Hashtags: {hashtags}")
        
        if 'liked' in event_data and event_data['liked']:
            parts.append("Liked this content")
        
        return ". ".join(parts)
    
    def _create_session_text(self, session_data: Dict[str, Any]) -> str:
        """Create text representation of session summary"""
        parts = [
            f"Session with {session_data.get('reels_count', 0)} reels",
            f"Total watch time: {session_data.get('total_watch_time', 0):.1f}s",
            f"Average watch time: {session_data.get('avg_watch_time', 0):.1f}s",
            f"Like ratio: {session_data.get('like_ratio', 0):.2%}"
        ]
        return ". ".join(parts)
    
    def _create_traits_text(self, traits_data: Dict[str, Any]) -> str:
        """Create text representation of behavioral traits"""
        parts = [
            f"Attention score: {traits_data.get('attention_score', 0):.2f}",
            f"Engagement score: {traits_data.get('engagement_score', 0):.2f}",
            f"Activity level: {traits_data.get('activity_level', 0):.2f}",
            f"Content diversity: {traits_data.get('content_diversity', 0):.2f}"
        ]
        return ". ".join(parts)
    
    def _create_trend_text(self, trend_data: Dict[str, Any]) -> str:
        """Create text representation of behavioral trend"""
        trend_type = trend_data.get('trend_type', 'unknown')
        value = trend_data.get('value', 0)
        change = trend_data.get('change', 0)
        period = trend_data.get('period', 'recent')
        
        direction = "increased" if change > 0 else "decreased"
        return f"{trend_type} {direction} to {value:.2f} over {period} period"
    
    def _create_persona_text(self, persona_data: Dict[str, Any]) -> str:
        """Create text representation of persona"""
        archetype = persona_data.get('archetype', 'Unknown')
        confidence = persona_data.get('confidence', 0)
        
        parts = [
            f"Behavioral archetype: {archetype}",
            f"Confidence: {confidence:.2%}"
        ]
        
        if 'traits' in persona_data:
            traits = persona_data['traits']
            if isinstance(traits, dict):
                trait_strs = [f"{k}: {v}" for k, v in list(traits.items())[:3]]
                parts.append(f"Key traits: {', '.join(trait_strs)}")
        
        return ". ".join(parts)


# Global instance
_ingest_service = None


async def get_ingest_service() -> IngestService:
    """
    Get or create the global ingest service instance
    
    Returns:
        IngestService instance
    """
    global _ingest_service
    if _ingest_service is None:
        _ingest_service = IngestService()
        await _ingest_service.initialize()
    return _ingest_service
