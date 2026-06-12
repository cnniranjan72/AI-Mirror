"""
Behavior Gateway Module
Normalizes all incoming events into unified BehaviorEvent schema
Ensures downstream modules never consume source-specific payloads
"""
from typing import List, Dict, Any
import logging
from datetime import datetime
import uuid

from backend.shared.contracts import BehaviorEvent, EventSource
from .event_normalizer import EventNormalizer


logger = logging.getLogger(__name__)


class BehaviorGateway:
    """
    Central gateway for all behavioral events
    
    Responsibilities:
    - Normalize events from any source into BehaviorEvent schema
    - Validate event integrity
    - Enrich events with metadata
    - Route events to appropriate processors
    
    Future sources:
    - Chrome Extension
    - Dashboard
    - Mobile App
    - Saved Reels
    - Browser Agents
    """
    
    def __init__(self):
        """Initialize behavior gateway"""
        self.normalizer = EventNormalizer()
        logger.info("BehaviorGateway initialized")
    
    def ingest_from_extension(self, extension_payload: Dict[str, Any]) -> List[BehaviorEvent]:
        """
        Ingest events from Chrome Extension
        
        Args:
            extension_payload: Raw payload from extension
            
        Returns:
            List of normalized BehaviorEvent objects
        """
        try:
            logger.info(f"Ingesting events from Chrome Extension")
            
            # Extract events from extension payload
            raw_events = extension_payload.get("events", [])
            if not raw_events:
                logger.warning("No events found in extension payload")
                return []
            
            # Normalize each event
            normalized_events = []
            for raw_event in raw_events:
                try:
                    behavior_event = self.normalizer.normalize_extension_event(raw_event)
                    normalized_events.append(behavior_event)
                except Exception as e:
                    logger.error(f"Failed to normalize event: {str(e)}")
                    continue
            
            logger.info(f"Successfully normalized {len(normalized_events)} events from extension")
            return normalized_events
            
        except Exception as e:
            logger.error(f"Error ingesting from extension: {str(e)}", exc_info=True)
            raise
    
    def ingest_from_dashboard(self, dashboard_payload: Dict[str, Any]) -> List[BehaviorEvent]:
        """
        Ingest events from Dashboard
        
        Args:
            dashboard_payload: Raw payload from dashboard
            
        Returns:
            List of normalized BehaviorEvent objects
        """
        try:
            logger.info(f"Ingesting events from Dashboard")
            
            # Future implementation
            # For now, return empty list
            logger.warning("Dashboard ingestion not yet implemented")
            return []
            
        except Exception as e:
            logger.error(f"Error ingesting from dashboard: {str(e)}", exc_info=True)
            raise
    
    def ingest_from_mobile(self, mobile_payload: Dict[str, Any]) -> List[BehaviorEvent]:
        """
        Ingest events from Mobile App (future)
        
        Args:
            mobile_payload: Raw payload from mobile app
            
        Returns:
            List of normalized BehaviorEvent objects
        """
        try:
            logger.info(f"Ingesting events from Mobile App")
            
            # Future implementation
            logger.warning("Mobile ingestion not yet implemented")
            return []
            
        except Exception as e:
            logger.error(f"Error ingesting from mobile: {str(e)}", exc_info=True)
            raise
    
    def ingest_from_saved_reels(self, saved_reels_payload: Dict[str, Any]) -> List[BehaviorEvent]:
        """
        Ingest events from Saved Reels (future)
        
        Args:
            saved_reels_payload: Raw payload from saved reels
            
        Returns:
            List of normalized BehaviorEvent objects
        """
        try:
            logger.info(f"Ingesting events from Saved Reels")
            
            # Future implementation
            logger.warning("Saved reels ingestion not yet implemented")
            return []
            
        except Exception as e:
            logger.error(f"Error ingesting from saved reels: {str(e)}", exc_info=True)
            raise
    
    def ingest_from_browser_agent(self, agent_payload: Dict[str, Any]) -> List[BehaviorEvent]:
        """
        Ingest events from Browser Agent (future)
        
        Args:
            agent_payload: Raw payload from browser agent
            
        Returns:
            List of normalized BehaviorEvent objects
        """
        try:
            logger.info(f"Ingesting events from Browser Agent")
            
            # Future implementation
            logger.warning("Browser agent ingestion not yet implemented")
            return []
            
        except Exception as e:
            logger.error(f"Error ingesting from browser agent: {str(e)}", exc_info=True)
            raise
    
    def validate_events(self, events: List[BehaviorEvent]) -> List[BehaviorEvent]:
        """
        Validate behavioral events
        
        Args:
            events: List of BehaviorEvent objects
            
        Returns:
            List of valid BehaviorEvent objects
        """
        valid_events = []
        
        for event in events:
            try:
                # Validate required fields
                if not event.event_id:
                    logger.warning("Event missing event_id, skipping")
                    continue
                
                if not event.content_id:
                    logger.warning(f"Event {event.event_id} missing content_id, skipping")
                    continue
                
                if event.watch_time < 0:
                    logger.warning(f"Event {event.event_id} has negative watch_time, skipping")
                    continue
                
                valid_events.append(event)
                
            except Exception as e:
                logger.error(f"Error validating event: {str(e)}")
                continue
        
        logger.info(f"Validated {len(valid_events)}/{len(events)} events")
        return valid_events
    
    def enrich_events(self, events: List[BehaviorEvent]) -> List[BehaviorEvent]:
        """
        Enrich events with additional metadata
        
        Args:
            events: List of BehaviorEvent objects
            
        Returns:
            List of enriched BehaviorEvent objects
        """
        enriched_events = []
        
        for event in events:
            try:
                # Add processing timestamp if not present
                if "processed_at" not in event.raw_metadata:
                    event.raw_metadata["processed_at"] = datetime.utcnow().isoformat()
                
                # Add gateway version
                event.raw_metadata["gateway_version"] = "1.0.0"
                
                enriched_events.append(event)
                
            except Exception as e:
                logger.error(f"Error enriching event {event.event_id}: {str(e)}")
                enriched_events.append(event)  # Add anyway
                continue
        
        return enriched_events
    
    def process_batch(
        self,
        payload: Dict[str, Any],
        source: EventSource
    ) -> List[BehaviorEvent]:
        """
        Process a batch of events from any source
        
        Args:
            payload: Raw payload
            source: Event source
            
        Returns:
            List of validated and enriched BehaviorEvent objects
        """
        try:
            # Route to appropriate ingestion method
            if source == EventSource.CHROME_EXTENSION:
                events = self.ingest_from_extension(payload)
            elif source == EventSource.DASHBOARD:
                events = self.ingest_from_dashboard(payload)
            elif source == EventSource.MOBILE_APP:
                events = self.ingest_from_mobile(payload)
            elif source == EventSource.SAVED_REELS:
                events = self.ingest_from_saved_reels(payload)
            elif source == EventSource.BROWSER_AGENT:
                events = self.ingest_from_browser_agent(payload)
            else:
                raise ValueError(f"Unknown event source: {source}")
            
            # Validate events
            valid_events = self.validate_events(events)
            
            # Enrich events
            enriched_events = self.enrich_events(valid_events)
            
            logger.info(f"Processed batch: {len(enriched_events)} events from {source}")
            return enriched_events
            
        except Exception as e:
            logger.error(f"Error processing batch from {source}: {str(e)}", exc_info=True)
            raise


def get_behavior_gateway() -> BehaviorGateway:
    """Get singleton behavior gateway instance"""
    if not hasattr(get_behavior_gateway, "_instance"):
        get_behavior_gateway._instance = BehaviorGateway()
    return get_behavior_gateway._instance
