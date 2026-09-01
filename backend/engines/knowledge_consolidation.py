"""
Knowledge Consolidation Engine
Prevents repetitive memory and consolidates behavioral patterns
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import uuid
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from backend.shared.contracts import BehaviorEvent, BehaviorCluster


logger = logging.getLogger(__name__)

# Occurrence count at which cluster confidence saturates to 1.0. Previously 100,
# which is calibrated for power-user volumes — a typical user's per-topic
# occurrence count is single digits to low tens, so confidence never rose above
# ~0.05-0.10 and crushed every downstream score (identity confidence, avg
# stability, etc). 15 recurring views of a topic is a genuinely established
# pattern and should read as confident.
CONFIDENCE_SATURATION_COUNT = 15.0


def _confidence_from_count(occurrence_count: float) -> float:
    return min(1.0, occurrence_count / CONFIDENCE_SATURATION_COUNT)


# Words long enough to survive a naive length filter but carrying no topical
# meaning. Without this, captions contributed "because"/"through"/"already" as
# interests — the caption fallback took any word over five characters, so the
# interest graph filled up with connectives.
_STOPWORDS = frozenset("""
about above after again against already always among another because before
being below better betweencannot could during either enough every everyone
everything follow following friends really should since some someone something
sometimes still their theme themselves there therefore these things think this
those threw through today together tomorrow toward under until using video
watch watching what when where which while whole whose without would your
yours yourself amazing awesome beautiful perfect perfection favorite favourite
please thanks thank welcome subscribe comment share follow link click
""".split())

# A token has to look like a word to be a topic. Hashtags such as "#2024" or
# "#f4f" are noise, and single characters are never a subject.
_MIN_TOPIC_LENGTH = 4


def _normalize_topic_token(raw: str) -> Optional[str]:
    """Reduce a hashtag or caption word to a topic token, or None if it isn't
    one. Returning None rather than a placeholder is the point: an event we
    cannot classify must not be filed under a catch-all that then competes with
    real interests for importance."""
    if not raw:
        return None
    token = raw.strip().lower().lstrip("#").strip(".,!?:;\"'()[]{}")
    if len(token) < _MIN_TOPIC_LENGTH:
        return None
    # Must contain letters — rejects "2024", "100k", pure punctuation.
    if not any(ch.isalpha() for ch in token):
        return None
    if token in _STOPWORDS:
        return None
    return token


def _candidate_topics(event: BehaviorEvent) -> List[str]:
    """Topic candidates for one event, hashtags first, caption as fallback."""
    candidates = []
    for tag in (event.hashtags or []):
        token = _normalize_topic_token(tag)
        if token:
            candidates.append(token)

    # Only fall back to the caption when the creator supplied no hashtags —
    # hashtags are an explicit topical signal, caption words are an inference.
    if not candidates and event.caption:
        for word in event.caption.split():
            token = _normalize_topic_token(word)
            if token:
                candidates.append(token)

    return candidates


class KnowledgeConsolidationEngine:
    """
    Knowledge Consolidation Engine
    
    Responsibilities:
    - Semantic deduplication
    - Trend clustering
    - Topic clustering
    - Creator aggregation
    - Behavior frequency analysis
    - Memory compression
    - Confidence estimation
    - Temporal weighting
    
    Purpose:
    Prevent repetitive memory by consolidating similar behavioral patterns
    into evolving clusters rather than storing identical memories
    
    Example:
    100 AI roadmap reels → One evolving topic cluster with frequency, engagement, growth, confidence
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Knowledge Consolidation Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        self.similarity_threshold = self.config.get("similarity_threshold", 0.85)
        self.min_cluster_size = self.config.get("min_cluster_size", 3)
        self.temporal_decay_days = self.config.get("temporal_decay_days", 30)
        
        # In-memory cluster cache (in production, use database)
        self._cluster_cache: Dict[str, BehaviorCluster] = {}
        
        logger.info("KnowledgeConsolidationEngine initialized")
    
    def consolidate_events(
        self,
        events: List[BehaviorEvent],
        existing_clusters: Optional[List[BehaviorCluster]] = None
    ) -> Tuple[List[BehaviorCluster], List[BehaviorEvent]]:
        """
        Consolidate behavioral events into clusters
        
        Args:
            events: List of behavioral events
            existing_clusters: Existing clusters to update
            
        Returns:
            Tuple of (updated_clusters, unclustered_events)
        """
        try:
            logger.info(f"Consolidating {len(events)} events")
            
            # Initialize clusters
            clusters = {c.cluster_id: c for c in (existing_clusters or [])}
            unclustered_events = []
            
            # Group events by topic/creator
            topic_groups = self._group_by_topic(events)
            creator_groups = self._group_by_creator(events)
            
            # Process topic clusters
            clustered_event_ids = set()
            for topic, topic_events in topic_groups.items():
                if len(topic_events) >= self.min_cluster_size:
                    cluster = self._create_or_update_topic_cluster(
                        topic,
                        topic_events,
                        clusters
                    )
                    clusters[cluster.cluster_id] = cluster
                    clustered_event_ids.update(e.event_id for e in topic_events)
                else:
                    unclustered_events.extend(topic_events)

            # Events that yielded no usable topic candidate are skipped by
            # _group_by_topic entirely, so they never appear in topic_groups.
            # They still have to be reported here — the return contract is
            # "everything that did not become a topic cluster", and callers use
            # it to know what the pipeline could not classify. (They remain
            # eligible for creator clusters below.)
            already_reported = {e.event_id for e in unclustered_events}
            for event in events:
                if event.event_id not in clustered_event_ids and event.event_id not in already_reported:
                    unclustered_events.append(event)
                    already_reported.add(event.event_id)
            
            # Process creator clusters
            for creator, creator_events in creator_groups.items():
                if len(creator_events) >= self.min_cluster_size:
                    cluster = self._create_or_update_creator_cluster(
                        creator,
                        creator_events,
                        clusters
                    )
                    clusters[cluster.cluster_id] = cluster
            
            logger.info(f"Created/updated {len(clusters)} clusters, {len(unclustered_events)} unclustered events")
            
            return list(clusters.values()), unclustered_events
            
        except Exception as e:
            logger.error(f"Error consolidating events: {str(e)}", exc_info=True)
            raise
    
    def _group_by_topic(self, events: List[BehaviorEvent]) -> Dict[str, List[BehaviorEvent]]:
        """
        Group events by topic (extracted from hashtags/caption)
        
        Args:
            events: List of events
            
        Returns:
            Dictionary mapping topic to events
        """
        # Two passes. The first counts how often each candidate topic appears
        # across the whole batch; the second assigns each event to its most
        # BATCH-FREQUENT candidate rather than whichever hashtag the creator
        # happened to type first. Positional choice is why a one-off tag like
        # "perfection" could outrank a genuine recurring interest.
        frequency: Dict[str, int] = defaultdict(int)
        per_event: List[Tuple[BehaviorEvent, List[str]]] = []

        for event in events:
            candidates = _candidate_topics(event)
            per_event.append((event, candidates))
            for token in set(candidates):
                frequency[token] += 1

        topic_groups = defaultdict(list)

        for event, candidates in per_event:
            if not candidates:
                # Deliberately NOT grouped under a catch-all. An unclassifiable
                # event used to land in an "uncategorized" bucket which, being
                # the union of every unlabelled event, reliably became the
                # single largest cluster — and therefore the user's strongest
                # "interest". A bucket that means "we don't know" must never
                # outrank things we do know.
                continue
            primary_topic = max(candidates, key=lambda t: (frequency[t], -candidates.index(t)))
            topic_groups[primary_topic].append(event)

        return dict(topic_groups)
    
    def _group_by_creator(self, events: List[BehaviorEvent]) -> Dict[str, List[BehaviorEvent]]:
        """
        Group events by creator
        
        Args:
            events: List of events
            
        Returns:
            Dictionary mapping creator to events
        """
        creator_groups = defaultdict(list)
        
        for event in events:
            creator = event.creator or "unknown"
            creator_groups[creator].append(event)
        
        return dict(creator_groups)
    
    def _create_or_update_topic_cluster(
        self,
        topic: str,
        events: List[BehaviorEvent],
        existing_clusters: Dict[str, BehaviorCluster]
    ) -> BehaviorCluster:
        """
        Create or update a topic cluster
        
        Args:
            topic: Primary topic
            events: Events for this topic
            existing_clusters: Existing clusters
            
        Returns:
            Updated or new BehaviorCluster
        """
        # Find existing cluster for this topic
        existing_cluster = None
        for cluster in existing_clusters.values():
            if cluster.cluster_type == "topic" and cluster.primary_topic == topic:
                existing_cluster = cluster
                break
        
        # Calculate metrics
        total_watch_time = sum(e.watch_time for e in events)
        avg_watch_time = total_watch_time / len(events) if events else 0.0
        engagement_count = sum(1 for e in events if e.liked or e.saved or e.shared)
        engagement_rate = engagement_count / len(events) if events else 0.0
        
        # Extract related topics
        all_hashtags = []
        for event in events:
            all_hashtags.extend(event.hashtags or [])
        related_topics = list(set(all_hashtags))[:10]
        
        # Extract creators
        creators = list(set(e.creator for e in events if e.creator))[:10]
        
        # Calculate temporal weight (recent events weighted higher)
        # event.timestamp arrives timezone-aware (event_normalizer parses "Z"
        # as UTC) — utcnow() is naive and crashes the subtraction below.
        now = datetime.now(timezone.utc)
        temporal_weights = []
        for event in events:
            days_ago = (now - event.timestamp).days
            weight = max(0.0, 1.0 - (days_ago / self.temporal_decay_days))
            temporal_weights.append(weight)
        avg_temporal_weight = sum(temporal_weights) / len(temporal_weights) if temporal_weights else 0.5
        
        if existing_cluster:
            # Update existing cluster
            existing_cluster.occurrence_count += len(events)
            existing_cluster.last_seen = max(e.timestamp for e in events)
            existing_cluster.avg_watch_time = (
                (existing_cluster.avg_watch_time * (existing_cluster.occurrence_count - len(events)) +
                 total_watch_time) / existing_cluster.occurrence_count
            )
            existing_cluster.engagement_rate = (
                (existing_cluster.engagement_rate * (existing_cluster.occurrence_count - len(events)) +
                 engagement_count) / existing_cluster.occurrence_count
            )
            
            # Calculate growth rate
            days_since_first = (existing_cluster.last_seen - existing_cluster.first_seen).days or 1
            existing_cluster.growth_rate = existing_cluster.occurrence_count / days_since_first
            
            # Update temporal weight
            existing_cluster.temporal_weight = avg_temporal_weight
            
            # Update confidence (increases with more data)
            existing_cluster.confidence = _confidence_from_count(existing_cluster.occurrence_count)
            
            # Add new event IDs
            existing_cluster.event_ids.extend([e.event_id for e in events])
            
            # Update related topics and creators
            existing_cluster.related_topics = list(set(existing_cluster.related_topics + related_topics))[:10]
            existing_cluster.creators = list(set(existing_cluster.creators + creators))[:10]
            
            existing_cluster.updated_at = datetime.utcnow()
            
            return existing_cluster
        else:
            # Create new cluster
            first_seen = min(e.timestamp for e in events)
            last_seen = max(e.timestamp for e in events)
            
            cluster = BehaviorCluster(
                cluster_id=f"cluster_{uuid.uuid4().hex[:12]}",
                cluster_type="topic",
                primary_topic=topic,
                related_topics=related_topics,
                keywords=[topic] + related_topics[:5],
                occurrence_count=len(events),
                first_seen=first_seen,
                last_seen=last_seen,
                avg_watch_time=avg_watch_time,
                engagement_rate=engagement_rate,
                growth_rate=len(events) / max(1, (last_seen - first_seen).days or 1),
                confidence=_confidence_from_count(len(events)),
                temporal_weight=avg_temporal_weight,
                event_ids=[e.event_id for e in events],
                creators=creators,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={"topic_type": "hashtag_based"}
            )
            
            return cluster
    
    def _create_or_update_creator_cluster(
        self,
        creator: str,
        events: List[BehaviorEvent],
        existing_clusters: Dict[str, BehaviorCluster]
    ) -> BehaviorCluster:
        """
        Create or update a creator cluster
        
        Args:
            creator: Creator username
            events: Events for this creator
            existing_clusters: Existing clusters
            
        Returns:
            Updated or new BehaviorCluster
        """
        # Find existing cluster for this creator
        existing_cluster = None
        for cluster in existing_clusters.values():
            if cluster.cluster_type == "creator" and creator in cluster.creators:
                existing_cluster = cluster
                break
        
        # Calculate metrics
        total_watch_time = sum(e.watch_time for e in events)
        avg_watch_time = total_watch_time / len(events) if events else 0.0
        engagement_count = sum(1 for e in events if e.liked or e.saved or e.shared)
        engagement_rate = engagement_count / len(events) if events else 0.0
        
        # Extract topics
        all_hashtags = []
        for event in events:
            all_hashtags.extend(event.hashtags or [])
        topics = list(set(all_hashtags))[:10]
        
        # Calculate temporal weight
        # event.timestamp arrives timezone-aware (event_normalizer parses "Z"
        # as UTC) — utcnow() is naive and crashes the subtraction below.
        now = datetime.now(timezone.utc)
        temporal_weights = []
        for event in events:
            days_ago = (now - event.timestamp).days
            weight = max(0.0, 1.0 - (days_ago / self.temporal_decay_days))
            temporal_weights.append(weight)
        avg_temporal_weight = sum(temporal_weights) / len(temporal_weights) if temporal_weights else 0.5
        
        if existing_cluster:
            # Update existing cluster
            existing_cluster.occurrence_count += len(events)
            existing_cluster.last_seen = max(e.timestamp for e in events)
            existing_cluster.avg_watch_time = (
                (existing_cluster.avg_watch_time * (existing_cluster.occurrence_count - len(events)) +
                 total_watch_time) / existing_cluster.occurrence_count
            )
            existing_cluster.engagement_rate = (
                (existing_cluster.engagement_rate * (existing_cluster.occurrence_count - len(events)) +
                 engagement_count) / existing_cluster.occurrence_count
            )
            
            # Calculate growth rate
            days_since_first = (existing_cluster.last_seen - existing_cluster.first_seen).days or 1
            existing_cluster.growth_rate = existing_cluster.occurrence_count / days_since_first
            
            existing_cluster.temporal_weight = avg_temporal_weight
            existing_cluster.confidence = _confidence_from_count(existing_cluster.occurrence_count)
            existing_cluster.event_ids.extend([e.event_id for e in events])
            existing_cluster.related_topics = list(set(existing_cluster.related_topics + topics))[:10]
            existing_cluster.updated_at = datetime.utcnow()
            
            return existing_cluster
        else:
            # Create new cluster
            first_seen = min(e.timestamp for e in events)
            last_seen = max(e.timestamp for e in events)
            
            cluster = BehaviorCluster(
                cluster_id=f"cluster_{uuid.uuid4().hex[:12]}",
                cluster_type="creator",
                primary_topic=f"Content by {creator}",
                related_topics=topics,
                keywords=[creator] + topics[:5],
                occurrence_count=len(events),
                first_seen=first_seen,
                last_seen=last_seen,
                avg_watch_time=avg_watch_time,
                engagement_rate=engagement_rate,
                growth_rate=len(events) / max(1, (last_seen - first_seen).days or 1),
                confidence=_confidence_from_count(len(events)),
                temporal_weight=avg_temporal_weight,
                event_ids=[e.event_id for e in events],
                creators=[creator],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={"creator": creator}
            )
            
            return cluster
    
    def detect_trends(
        self,
        clusters: List[BehaviorCluster],
        lookback_days: int = 7
    ) -> List[BehaviorCluster]:
        """
        Detect trending clusters
        
        Args:
            clusters: List of clusters
            lookback_days: Days to look back for trend detection
            
        Returns:
            List of trending clusters
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            trending_clusters = []
            for cluster in clusters:
                # Check if cluster has recent activity
                if cluster.last_seen >= cutoff_date:
                    # Check if growth rate is positive
                    if cluster.growth_rate > 0.5:  # At least 0.5 events per day
                        # Check if engagement is high
                        if cluster.engagement_rate > 0.3:
                            trending_clusters.append(cluster)
            
            # Sort by growth rate
            trending_clusters.sort(key=lambda c: c.growth_rate, reverse=True)
            
            logger.info(f"Detected {len(trending_clusters)} trending clusters")
            return trending_clusters
            
        except Exception as e:
            logger.error(f"Error detecting trends: {str(e)}", exc_info=True)
            return []
    
    def compress_memory(
        self,
        clusters: List[BehaviorCluster],
        compression_threshold: float = 0.5
    ) -> List[BehaviorCluster]:
        """
        Compress low-confidence or old clusters
        
        Args:
            clusters: List of clusters
            compression_threshold: Confidence threshold for compression
            
        Returns:
            List of compressed clusters
        """
        try:
            compressed_clusters = []
            
            for cluster in clusters:
                # Skip high-confidence clusters
                if cluster.confidence >= compression_threshold:
                    compressed_clusters.append(cluster)
                    continue
                
                # Compress low-confidence clusters
                # In production, this would merge similar clusters or archive them
                logger.debug(f"Compressing cluster {cluster.cluster_id} (confidence: {cluster.confidence})")
                
                # For now, just keep them but mark as compressed
                cluster.metadata["compressed"] = True
                compressed_clusters.append(cluster)
            
            logger.info(f"Compressed {len(clusters) - len([c for c in compressed_clusters if not c.metadata.get('compressed')])} clusters")
            return compressed_clusters
            
        except Exception as e:
            logger.error(f"Error compressing memory: {str(e)}", exc_info=True)
            return clusters
    
    def find_similar_cluster(
        self,
        event_embedding: List[float],
        existing_clusters: List[BehaviorCluster],
        threshold: Optional[float] = None
    ) -> Optional[BehaviorCluster]:
        """
        Find similar cluster using cosine similarity
        
        Args:
            event_embedding: Embedding vector for new event
            existing_clusters: List of existing clusters
            threshold: Similarity threshold (uses default if None)
            
        Returns:
            Most similar cluster if similarity > threshold, None otherwise
        """
        try:
            if not existing_clusters:
                return None
            
            threshold = threshold or self.similarity_threshold
            
            # Get cluster embeddings
            cluster_embeddings = []
            valid_clusters = []
            
            for cluster in existing_clusters:
                if "representative_embedding" in cluster.metadata:
                    cluster_embeddings.append(cluster.metadata["representative_embedding"])
                    valid_clusters.append(cluster)
            
            if not cluster_embeddings:
                return None
            
            # Calculate cosine similarity
            event_emb_array = np.array(event_embedding).reshape(1, -1)
            cluster_emb_array = np.array(cluster_embeddings)
            
            similarities = cosine_similarity(event_emb_array, cluster_emb_array)[0]
            
            # Find most similar cluster
            max_similarity_idx = np.argmax(similarities)
            max_similarity = similarities[max_similarity_idx]
            
            if max_similarity >= threshold:
                logger.debug(f"Found similar cluster with similarity {max_similarity:.3f}")
                return valid_clusters[max_similarity_idx]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding similar cluster: {str(e)}", exc_info=True)
            return None
    
    def consolidate_with_embeddings(
        self,
        events: List[BehaviorEvent],
        event_embeddings: List[List[float]],
        existing_clusters: Optional[List[BehaviorCluster]] = None
    ) -> Tuple[List[BehaviorCluster], List[BehaviorEvent]]:
        """
        Consolidate events using semantic similarity
        
        Args:
            events: List of behavioral events
            event_embeddings: Corresponding embeddings for each event
            existing_clusters: Existing clusters to update
            
        Returns:
            Tuple of (updated_clusters, unclustered_events)
        """
        try:
            logger.info(f"Consolidating {len(events)} events with semantic similarity")
            
            if len(events) != len(event_embeddings):
                raise ValueError("Number of events must match number of embeddings")
            
            clusters = {c.cluster_id: c for c in (existing_clusters or [])}
            unclustered_events = []
            unclustered_embeddings = []
            
            # Process each event
            for event, embedding in zip(events, event_embeddings):
                # Find similar cluster
                similar_cluster = self.find_similar_cluster(
                    embedding,
                    list(clusters.values())
                )
                
                if similar_cluster:
                    # Update existing cluster
                    self._update_cluster_with_event(
                        similar_cluster,
                        event,
                        embedding
                    )
                else:
                    # Add to unclustered
                    unclustered_events.append(event)
                    unclustered_embeddings.append(embedding)
            
            # Create new clusters from unclustered events
            if len(unclustered_events) >= self.min_cluster_size:
                new_clusters = self._create_clusters_from_embeddings(
                    unclustered_events,
                    unclustered_embeddings
                )
                for cluster in new_clusters:
                    clusters[cluster.cluster_id] = cluster
                unclustered_events = []
            
            logger.info(f"Consolidated into {len(clusters)} clusters, {len(unclustered_events)} unclustered")
            
            return list(clusters.values()), unclustered_events
            
        except Exception as e:
            logger.error(f"Error consolidating with embeddings: {str(e)}", exc_info=True)
            raise
    
    def _update_cluster_with_event(
        self,
        cluster: BehaviorCluster,
        event: BehaviorEvent,
        embedding: List[float]
    ):
        """
        Update cluster with new event
        
        Args:
            cluster: Cluster to update
            event: New event
            embedding: Event embedding
        """
        try:
            # Update occurrence count
            cluster.occurrence_count += 1
            
            # Update timestamps
            cluster.last_seen = max(cluster.last_seen, event.timestamp)
            
            # Update watch time
            total_watch_time = cluster.avg_watch_time * (cluster.occurrence_count - 1) + event.watch_time
            cluster.avg_watch_time = total_watch_time / cluster.occurrence_count
            
            # Update engagement
            is_engaged = event.liked or event.saved or event.shared or event.commented
            total_engagement = cluster.engagement_rate * (cluster.occurrence_count - 1) + (1.0 if is_engaged else 0.0)
            cluster.engagement_rate = total_engagement / cluster.occurrence_count
            
            # Update growth rate
            days_since_first = (cluster.last_seen - cluster.first_seen).days or 1
            cluster.growth_rate = cluster.occurrence_count / days_since_first
            
            # Update confidence
            cluster.confidence = _confidence_from_count(cluster.occurrence_count)
            
            # Update temporal weight (event.timestamp is timezone-aware; use an
            # aware "now" too, or the subtraction below raises TypeError)
            now = datetime.now(timezone.utc)
            days_ago = (now - event.timestamp).days
            temporal_weight = max(0.0, 1.0 - (days_ago / self.temporal_decay_days))
            cluster.temporal_weight = (cluster.temporal_weight * 0.9 + temporal_weight * 0.1)
            
            # Add event ID
            cluster.event_ids.append(event.event_id)
            
            # Update creator list
            if event.creator and event.creator not in cluster.creators:
                cluster.creators.append(event.creator)
                cluster.creators = cluster.creators[:10]  # Keep top 10
            
            # Update related topics
            for hashtag in event.hashtags:
                if hashtag not in cluster.related_topics:
                    cluster.related_topics.append(hashtag)
            cluster.related_topics = cluster.related_topics[:10]  # Keep top 10
            
            # Update representative embedding (moving average)
            if "representative_embedding" in cluster.metadata:
                old_emb = np.array(cluster.metadata["representative_embedding"])
                new_emb = np.array(embedding)
                updated_emb = (old_emb * 0.9 + new_emb * 0.1).tolist()
                cluster.metadata["representative_embedding"] = updated_emb
            else:
                cluster.metadata["representative_embedding"] = embedding
            
            cluster.updated_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating cluster: {str(e)}", exc_info=True)
            raise
    
    def _create_clusters_from_embeddings(
        self,
        events: List[BehaviorEvent],
        embeddings: List[List[float]]
    ) -> List[BehaviorCluster]:
        """
        Create new clusters from unclustered events using embeddings
        
        Args:
            events: List of events
            embeddings: Corresponding embeddings
            
        Returns:
            List of new clusters
        """
        try:
            # Simple clustering: group by topic similarity
            # In production, use proper clustering algorithm (DBSCAN, HDBSCAN)
            
            clusters = []
            used_indices = set()
            
            for i, (event, embedding) in enumerate(zip(events, embeddings)):
                if i in used_indices:
                    continue
                
                # Find similar events
                similar_indices = [i]
                for j in range(i + 1, len(events)):
                    if j in used_indices:
                        continue
                    
                    # Calculate similarity
                    emb1 = np.array(embedding).reshape(1, -1)
                    emb2 = np.array(embeddings[j]).reshape(1, -1)
                    similarity = cosine_similarity(emb1, emb2)[0][0]
                    
                    if similarity >= self.similarity_threshold:
                        similar_indices.append(j)
                        used_indices.add(j)
                
                # Create cluster if enough similar events
                if len(similar_indices) >= self.min_cluster_size:
                    cluster_events = [events[idx] for idx in similar_indices]
                    cluster_embeddings = [embeddings[idx] for idx in similar_indices]
                    
                    # Calculate representative embedding (mean)
                    repr_embedding = np.mean(cluster_embeddings, axis=0).tolist()
                    
                    # Extract topic from events
                    all_hashtags = []
                    for e in cluster_events:
                        all_hashtags.extend(e.hashtags or [])
                    
                    topic = all_hashtags[0] if all_hashtags else "uncategorized"
                    
                    # Create cluster
                    cluster = self._create_cluster_from_events(
                        cluster_events,
                        topic,
                        repr_embedding
                    )
                    clusters.append(cluster)
                    
                    for idx in similar_indices:
                        used_indices.add(idx)
            
            logger.info(f"Created {len(clusters)} new clusters from embeddings")
            return clusters
            
        except Exception as e:
            logger.error(f"Error creating clusters from embeddings: {str(e)}", exc_info=True)
            return []
    
    def _create_cluster_from_events(
        self,
        events: List[BehaviorEvent],
        topic: str,
        representative_embedding: List[float]
    ) -> BehaviorCluster:
        """
        Create a behavior cluster from events
        
        Args:
            events: List of events
            topic: Primary topic
            representative_embedding: Representative embedding
            
        Returns:
            BehaviorCluster
        """
        try:
            first_seen = min(e.timestamp for e in events)
            last_seen = max(e.timestamp for e in events)
            
            total_watch_time = sum(e.watch_time for e in events)
            avg_watch_time = total_watch_time / len(events)
            
            engagement_count = sum(
                1 for e in events
                if e.liked or e.saved or e.shared or e.commented
            )
            engagement_rate = engagement_count / len(events)
            
            all_hashtags = []
            creators = []
            for event in events:
                all_hashtags.extend(event.hashtags or [])
                if event.creator:
                    creators.append(event.creator)
            
            related_topics = list(set(all_hashtags))[:10]
            creators = list(set(creators))[:10]
            
            days_span = (last_seen - first_seen).days or 1
            growth_rate = len(events) / days_span
            
            cluster = BehaviorCluster(
                cluster_id=f"cluster_{uuid.uuid4().hex[:12]}",
                cluster_type="topic",
                primary_topic=topic,
                related_topics=related_topics,
                keywords=[topic] + related_topics[:5],
                occurrence_count=len(events),
                first_seen=first_seen,
                last_seen=last_seen,
                avg_watch_time=avg_watch_time,
                engagement_rate=engagement_rate,
                growth_rate=growth_rate,
                confidence=_confidence_from_count(len(events)),
                temporal_weight=1.0,
                event_ids=[e.event_id for e in events],
                creators=creators,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={
                    "representative_embedding": representative_embedding,
                    "creation_method": "semantic_clustering"
                }
            )
            
            return cluster
            
        except Exception as e:
            logger.error(f"Error creating cluster: {str(e)}", exc_info=True)
            raise


def get_knowledge_consolidation_engine() -> KnowledgeConsolidationEngine:
    """Get singleton knowledge consolidation engine instance"""
    if not hasattr(get_knowledge_consolidation_engine, "_instance"):
        get_knowledge_consolidation_engine._instance = KnowledgeConsolidationEngine()
    return get_knowledge_consolidation_engine._instance
