"""
Event Normalizer
Converts source-specific event formats into unified BehaviorEvent schema
"""
from typing import Dict, Any
import logging
from datetime import datetime
import uuid

from backend.shared.contracts import BehaviorEvent, EventSource, ContentType


logger = logging.getLogger(__name__)


class EventNormalizer:
    """
    Normalizes events from different sources into BehaviorEvent schema
    
    Responsibilities:
    - Convert extension-specific format to BehaviorEvent
    - Convert dashboard-specific format to BehaviorEvent
    - Convert mobile-specific format to BehaviorEvent
    - Handle missing fields with sensible defaults
    """
    
    def normalize_extension_event(self, raw_event: Dict[str, Any]) -> BehaviorEvent:
        """
        Normalize Chrome Extension event to BehaviorEvent
        
        Extension format (legacy):
        {
            "reel_id": str,
            "username": str,
            "caption": str,
            "hashtags": List[str],
            "audio_info": str,
            "watch_time": float,
            "liked": bool,
            "timestamp": str,
            "session_id": str
        }
        
        Args:
            raw_event: Raw event from extension
            
        Returns:
            Normalized BehaviorEvent
        """
        try:
            # Generate event ID if not present
            event_id = raw_event.get("event_id", f"evt_{uuid.uuid4().hex[:12]}")
            
            # Parse timestamp
            timestamp_str = raw_event.get("timestamp", datetime.utcnow().isoformat())
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            # Create normalized event
            behavior_event = BehaviorEvent(
                # Core identification
                event_id=event_id,
                source=EventSource.CHROME_EXTENSION,
                timestamp=timestamp,
                session_id=raw_event.get("session_id", f"sess_{uuid.uuid4().hex[:12]}"),
                
                # Content identification
                content_id=raw_event.get("reel_id", f"content_{uuid.uuid4().hex[:12]}"),
                content_type=ContentType.REEL,
                
                # Content metadata
                creator=raw_event.get("username"),
                caption=raw_event.get("caption"),
                hashtags=raw_event.get("hashtags", []),
                audio_info=raw_event.get("audio_info"),
                
                # Behavioral metrics
                watch_time=float(raw_event.get("watch_time", 0.0)),
                liked=bool(raw_event.get("liked", False)),
                saved=bool(raw_event.get("saved", False)),
                shared=bool(raw_event.get("shared", False)),
                commented=bool(raw_event.get("commented", False)),
                replay_count=int(raw_event.get("replay_count", 0)),
                scroll_speed=raw_event.get("scroll_speed"),
                
                # Context
                device_type=raw_event.get("device_type", "unknown"),
                platform=raw_event.get("platform", "instagram"),
                
                # Raw data
                raw_metadata={
                    "source_format": "extension_v1",
                    "original_payload": raw_event
                }
            )
            
            return behavior_event
            
        except Exception as e:
            logger.error(f"Error normalizing extension event: {str(e)}", exc_info=True)
            raise
    
    def normalize_dashboard_event(self, raw_event: Dict[str, Any]) -> BehaviorEvent:
        """
        Normalize Dashboard event to BehaviorEvent (future)
        
        Args:
            raw_event: Raw event from dashboard
            
        Returns:
            Normalized BehaviorEvent
        """
        # Future implementation
        raise NotImplementedError("Dashboard event normalization not yet implemented")
    
    def normalize_mobile_event(self, raw_event: Dict[str, Any]) -> BehaviorEvent:
        """
        Normalize Mobile App event to BehaviorEvent (future)
        
        Args:
            raw_event: Raw event from mobile app
            
        Returns:
            Normalized BehaviorEvent
        """
        # Future implementation
        raise NotImplementedError("Mobile event normalization not yet implemented")
    
    def normalize_saved_reel_event(self, raw_event: Dict[str, Any]) -> BehaviorEvent:
        """
        Normalize Saved Reel event to BehaviorEvent (future)
        
        Args:
            raw_event: Raw event from saved reels
            
        Returns:
            Normalized BehaviorEvent
        """
        # Future implementation
        raise NotImplementedError("Saved reel event normalization not yet implemented")
    
    def normalize_browser_agent_event(self, raw_event: Dict[str, Any]) -> BehaviorEvent:
        """
        Normalize Browser Agent event to BehaviorEvent (future)
        
        Args:
            raw_event: Raw event from browser agent
            
        Returns:
            Normalized BehaviorEvent
        """
        # Future implementation
        raise NotImplementedError("Browser agent event normalization not yet implemented")
