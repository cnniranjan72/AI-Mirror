"""
Identity Engine
Constructs computational identity from behaviors, evidence, inferences, and reflections
Identity represents FACTS about the user, not beliefs
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging
import uuid

from backend.reasoning import BehaviorObject, Inference, Evidence
from backend.reasoning.behavior_object import is_creator_behavior
from backend.reasoning.reasoning_context import ReasoningContext, ReflectionReference, GoalReference


logger = logging.getLogger(__name__)


class InterestNode(BaseModel):
    """Node in interest graph"""
    topic: str = Field(..., description="Topic name")
    strength: float = Field(..., ge=0.0, le=1.0, description="Interest strength")
    frequency: int = Field(..., description="Occurrence frequency")
    engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Engagement rate")
    last_engaged: datetime = Field(..., description="Last engagement timestamp")
    trend: str = Field(..., description="Trend direction (emerging/growing/stable/declining)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this interest")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs")


class InterestGraph(BaseModel):
    """Graph of user interests"""
    dominant_interests: List[InterestNode] = Field(default_factory=list, description="Top interests")
    emerging_interests: List[InterestNode] = Field(default_factory=list, description="Emerging interests")
    declining_interests: List[InterestNode] = Field(default_factory=list, description="Declining interests")
    stable_interests: List[InterestNode] = Field(default_factory=list, description="Stable long-term interests")
    total_topics: int = Field(default=0, description="Total unique topics")
    diversity_score: float = Field(..., ge=0.0, le=1.0, description="Interest diversity")


class CreatorNode(BaseModel):
    """Node in creator graph"""
    creator: str = Field(..., description="Creator username")
    affinity_score: float = Field(..., ge=0.0, le=1.0, description="Affinity to this creator")
    view_count: int = Field(..., description="Number of views")
    engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Engagement rate")
    avg_watch_time: float = Field(..., description="Average watch time")
    primary_topics: List[str] = Field(default_factory=list, description="Primary topics from this creator")
    last_viewed: datetime = Field(..., description="Last view timestamp")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in affinity")


class CreatorGraph(BaseModel):
    """Graph of creator affinities"""
    top_creators: List[CreatorNode] = Field(default_factory=list, description="Top creators by affinity")
    creator_diversity_score: float = Field(..., ge=0.0, le=1.0, description="Creator diversity")
    dependence_score: float = Field(..., ge=0.0, le=1.0, description="Dependence on few creators")
    total_creators: int = Field(default=0, description="Total unique creators")


class LearningStyle(BaseModel):
    """Learning style profile"""
    style_type: str = Field(..., description="Primary learning style (visual/analytical/practical/theoretical)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in style classification")
    completion_rate: float = Field(..., ge=0.0, le=1.0, description="Content completion rate")
    depth_preference: str = Field(..., description="Depth preference (quick/moderate/deep)")
    pace_preference: str = Field(..., description="Pace preference (fast/moderate/slow)")
    format_preferences: List[str] = Field(default_factory=list, description="Preferred content formats")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence")


class AttentionProfile(BaseModel):
    """Attention and focus profile"""
    avg_attention_span: float = Field(..., description="Average attention span in seconds")
    attention_consistency: float = Field(..., ge=0.0, le=1.0, description="Consistency of attention")
    attention_trend: str = Field(..., description="Attention trend (improving/stable/declining)")
    peak_attention_hours: List[int] = Field(default_factory=list, description="Peak attention hours")
    distraction_resistance: float = Field(..., ge=0.0, le=1.0, description="Resistance to distraction")
    focus_quality: float = Field(..., ge=0.0, le=1.0, description="Quality of focus")


class ExplorationProfile(BaseModel):
    """Exploration vs exploitation profile"""
    novelty_seeking_score: float = Field(..., ge=0.0, le=1.0, description="Novelty seeking tendency")
    exploration_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of exploring new topics")
    exploitation_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of deepening existing interests")
    topic_switching_frequency: float = Field(..., description="How often topics switch")
    comfort_zone_ratio: float = Field(..., ge=0.0, le=1.0, description="Time in comfort zone vs exploration")


class ConsistencyProfile(BaseModel):
    """Behavioral consistency profile"""
    overall_consistency: float = Field(..., ge=0.0, le=1.0, description="Overall behavioral consistency")
    topic_consistency: float = Field(..., ge=0.0, le=1.0, description="Topic consistency")
    temporal_consistency: float = Field(..., ge=0.0, le=1.0, description="Temporal pattern consistency")
    engagement_consistency: float = Field(..., ge=0.0, le=1.0, description="Engagement consistency")
    volatility_score: float = Field(..., ge=0.0, le=1.0, description="Behavioral volatility")


class HabitProfile(BaseModel):
    """Habit and routine profile"""
    has_daily_routine: bool = Field(..., description="Has established daily routine")
    routine_strength: float = Field(..., ge=0.0, le=1.0, description="Strength of routine")
    peak_usage_hours: List[int] = Field(default_factory=list, description="Peak usage hours")
    peak_usage_days: List[str] = Field(default_factory=list, description="Peak usage days")
    session_regularity: float = Field(..., ge=0.0, le=1.0, description="Session regularity")
    habit_stability: float = Field(..., ge=0.0, le=1.0, description="Habit stability over time")


class MotivationSignals(BaseModel):
    """Motivation and intent signals"""
    learning_motivation: float = Field(..., ge=0.0, le=1.0, description="Learning motivation level")
    entertainment_seeking: float = Field(..., ge=0.0, le=1.0, description="Entertainment seeking level")
    skill_building_intent: float = Field(..., ge=0.0, le=1.0, description="Skill building intent")
    curiosity_score: float = Field(..., ge=0.0, le=1.0, description="Curiosity level")
    goal_orientation: float = Field(..., ge=0.0, le=1.0, description="Goal orientation strength")
    intrinsic_motivation: float = Field(..., ge=0.0, le=1.0, description="Intrinsic motivation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in motivation assessment")


class BehaviorProfile(BaseModel):
    """Comprehensive behavioral profile"""
    total_events: int = Field(default=0, description="Total behavioral events")
    total_behaviors: int = Field(default=0, description="Total behavior objects")
    active_behaviors: int = Field(default=0, description="Currently active behaviors")
    avg_engagement_rate: float = Field(..., ge=0.0, le=1.0, description="Average engagement rate")
    avg_watch_time: float = Field(..., description="Average watch time")
    behavior_diversity: float = Field(..., ge=0.0, le=1.0, description="Behavioral diversity")
    behavior_stability: float = Field(..., ge=0.0, le=1.0, description="Behavioral stability")


class Identity(BaseModel):
    """
    Computational Identity
    
    Represents everything AIMirror currently KNOWS about the user (FACTS).
    Identity is constructed from:
    - Behavior Objects
    - Evidence
    - Inferences
    - Reflections
    - Goals
    
    Identity is NOT beliefs (that's Self Model).
    Identity stores measurable, evidence-based facts.
    """
    # Core identification
    identity_id: str = Field(..., description="Unique identity identifier")
    user_id: str = Field(..., description="User identifier")
    
    # Profiles
    behavior_profile: BehaviorProfile = Field(..., description="Behavioral profile")
    interest_graph: InterestGraph = Field(..., description="Interest graph")
    creator_graph: CreatorGraph = Field(..., description="Creator affinity graph")
    learning_style: LearningStyle = Field(..., description="Learning style profile")
    attention_profile: AttentionProfile = Field(..., description="Attention profile")
    exploration_profile: ExplorationProfile = Field(..., description="Exploration profile")
    consistency_profile: ConsistencyProfile = Field(..., description="Consistency profile")
    habit_profile: HabitProfile = Field(..., description="Habit profile")
    motivation_signals: MotivationSignals = Field(..., description="Motivation signals")
    
    # Timeline
    behavior_timeline: List[str] = Field(default_factory=list, description="Behavior object IDs in chronological order")
    
    # Topics
    dominant_topics: List[str] = Field(default_factory=list, description="Top dominant topics")
    emerging_topics: List[str] = Field(default_factory=list, description="Emerging topics")
    declining_topics: List[str] = Field(default_factory=list, description="Declining topics")
    
    # Long-term preferences
    long_term_preferences: Dict[str, float] = Field(default_factory=dict, description="Long-term topic preferences")
    
    # Confidence
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall identity confidence")
    identity_completeness: float = Field(..., ge=0.0, le=1.0, description="How complete the identity is")
    
    # Versioning
    identity_version: int = Field(default=1, description="Identity version number")
    
    # Evolution
    evolution_history: List[str] = Field(default_factory=list, description="Evolution snapshot IDs")
    major_shifts: List[Dict[str, Any]] = Field(default_factory=list, description="Major identity shifts")
    
    # Metadata
    created_at: datetime = Field(..., description="When identity was created")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_behavior_at: Optional[datetime] = Field(None, description="Last behavioral event timestamp")
    
    # Source tracking
    source_behavior_objects: List[str] = Field(default_factory=list, description="Source behavior object IDs")
    source_inferences: List[str] = Field(default_factory=list, description="Source inference IDs")
    source_evidence: List[str] = Field(default_factory=list, description="Source evidence IDs")
    source_reflections: List[str] = Field(default_factory=list, description="Source reflection IDs")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def update_version(self):
        """Increment version and update timestamp"""
        self.identity_version += 1
        self.updated_at = datetime.utcnow()
    
    def get_age_days(self) -> int:
        """Get identity age in days"""
        return (datetime.utcnow() - self.created_at).days
    
    def is_mature(self, min_days: int = 30) -> bool:
        """Check if identity is mature (enough data)"""
        return self.get_age_days() >= min_days and self.identity_completeness > 0.7


class IdentityEngine:
    """
    Identity Engine
    
    Constructs and maintains computational identity from:
    - Behavior Objects
    - Evidence
    - Inferences
    - Reflections
    - Goals
    
    Identity represents FACTS, not beliefs.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Identity Engine
        
        Args:
            config: Engine configuration
        """
        self.config = config or {}
        self.min_behaviors_for_identity = self.config.get("min_behaviors", 10)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.6)
        
        logger.info("IdentityEngine initialized")
    
    def construct_identity(
        self,
        user_id: str,
        behavior_objects: List[BehaviorObject],
        inferences: List[Inference],
        evidence: List[Evidence],
        reflections: Optional[List[ReflectionReference]] = None,
        goals: Optional[List[GoalReference]] = None,
        existing_identity: Optional[Identity] = None
    ) -> Identity:
        """
        Construct or update identity from behavioral data
        
        Args:
            user_id: User identifier
            behavior_objects: List of behavior objects
            inferences: List of inferences
            evidence: List of evidence
            reflections: Optional reflection references
            goals: Optional goal references
            existing_identity: Existing identity to update
            
        Returns:
            Identity object
        """
        try:
            logger.info(f"Constructing identity for user {user_id} from {len(behavior_objects)} behaviors")
            
            # Build profiles
            behavior_profile = self._build_behavior_profile(behavior_objects)
            interest_graph = self._build_interest_graph(behavior_objects, evidence)
            creator_graph = self._build_creator_graph(behavior_objects)
            learning_style = self._infer_learning_style(behavior_objects, inferences)
            attention_profile = self._build_attention_profile(behavior_objects)
            exploration_profile = self._build_exploration_profile(behavior_objects)
            consistency_profile = self._build_consistency_profile(behavior_objects)
            habit_profile = self._build_habit_profile(behavior_objects)
            motivation_signals = self._extract_motivation_signals(inferences, behavior_objects)
            
            # Extract topics
            dominant_topics = [node.topic for node in interest_graph.dominant_interests[:5]]
            emerging_topics = [node.topic for node in interest_graph.emerging_interests[:3]]
            declining_topics = [node.topic for node in interest_graph.declining_interests[:3]]
            
            # Build timeline (handle naive vs aware datetimes)
            def _safe_sort_key(b):
                dt = b.created_at
                if dt.tzinfo is None:
                    from datetime import timezone
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            sorted_behaviors = sorted(behavior_objects, key=_safe_sort_key)
            behavior_timeline = [b.unique_id for b in sorted_behaviors]
            
            # Calculate confidence
            overall_confidence = self._calculate_identity_confidence(
                behavior_objects,
                inferences,
                evidence
            )
            
            # Calculate completeness
            identity_completeness = self._calculate_completeness(behavior_objects, inferences)
            
            # Create or update identity
            if existing_identity:
                # CRITICAL: every freshly-computed field below must be written onto
                # the existing identity object. Previously this branch only called
                # update_version() and returned — every profile, topic list, and
                # overall_confidence/identity_completeness value computed above was
                # silently discarded, so the identity was frozen at whatever its
                # very first construction produced and never actually evolved
                # (confidence/completeness/topics stayed identical release after
                # release; only identity_version incremented).
                identity = existing_identity
                identity.update_version()
                identity.behavior_profile = behavior_profile
                identity.interest_graph = interest_graph
                identity.creator_graph = creator_graph
                identity.learning_style = learning_style
                identity.attention_profile = attention_profile
                identity.exploration_profile = exploration_profile
                identity.consistency_profile = consistency_profile
                identity.habit_profile = habit_profile
                identity.motivation_signals = motivation_signals
                identity.behavior_timeline = behavior_timeline
                identity.dominant_topics = dominant_topics
                identity.emerging_topics = emerging_topics
                identity.declining_topics = declining_topics
                identity.overall_confidence = overall_confidence
                identity.identity_completeness = identity_completeness
                identity.updated_at = datetime.utcnow()
                identity.source_behavior_objects = [b.unique_id for b in behavior_objects]
                identity.source_inferences = [i.inference_id for i in inferences]
                identity.source_evidence = [e.evidence_id for e in evidence]
            else:
                identity = Identity(
                    identity_id=f"identity_{user_id}_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    behavior_profile=behavior_profile,
                    interest_graph=interest_graph,
                    creator_graph=creator_graph,
                    learning_style=learning_style,
                    attention_profile=attention_profile,
                    exploration_profile=exploration_profile,
                    consistency_profile=consistency_profile,
                    habit_profile=habit_profile,
                    motivation_signals=motivation_signals,
                    behavior_timeline=behavior_timeline,
                    dominant_topics=dominant_topics,
                    emerging_topics=emerging_topics,
                    declining_topics=declining_topics,
                    overall_confidence=overall_confidence,
                    identity_completeness=identity_completeness,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    source_behavior_objects=[b.unique_id for b in behavior_objects],
                    source_inferences=[i.inference_id for i in inferences],
                    source_evidence=[e.evidence_id for e in evidence]
                )
            
            logger.info(f"Identity constructed: {identity.identity_id}, confidence: {overall_confidence:.2f}")
            return identity
            
        except Exception as e:
            logger.error(f"Error constructing identity: {str(e)}", exc_info=True)
            raise
    
    def _build_behavior_profile(self, behaviors: List[BehaviorObject]) -> BehaviorProfile:
        """Build behavioral profile from behaviors"""
        try:
            if not behaviors:
                return BehaviorProfile(
                    avg_engagement_rate=0.0,
                    avg_watch_time=0.0,
                    behavior_diversity=0.0,
                    behavior_stability=0.0
                )
            
            active_behaviors = [b for b in behaviors if b.is_active()]
            
            avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in behaviors) / len(behaviors)
            avg_watch = sum(b.watch_statistics.avg_watch_time for b in behaviors) / len(behaviors)
            
            # Diversity: unique topics / total behaviors
            unique_topics = len(set(b.topic for b in behaviors))
            diversity = min(1.0, unique_topics / len(behaviors))
            
            # Stability: average stability score
            stability = sum(b.stability_score for b in behaviors) / len(behaviors)
            
            return BehaviorProfile(
                total_events=sum(b.temporal_statistics.occurrence_count for b in behaviors),
                total_behaviors=len(behaviors),
                active_behaviors=len(active_behaviors),
                avg_engagement_rate=avg_engagement,
                avg_watch_time=avg_watch,
                behavior_diversity=diversity,
                behavior_stability=stability
            )
            
        except Exception as e:
            logger.error(f"Error building behavior profile: {str(e)}", exc_info=True)
            raise
    
    def _build_interest_graph(
        self,
        behaviors: List[BehaviorObject],
        evidence: List[Evidence]
    ) -> InterestGraph:
        """Build interest graph from behaviors"""
        try:
            # Group behaviors by topic
            from collections import defaultdict
            topic_behaviors = defaultdict(list)

            for behavior in behaviors:
                # Creator clusters are NOT interests. Consolidation emits two
                # kinds of behavior object and labels creator ones
                # "Content by <creator>"; feeding those in here put creator
                # names into the interest graph and straight through to
                # dominant_topics, so an identity's stated interests read as
                # ["#ai", "Content by lex_fridman_clips", ...] — a category
                # error, not a ranking problem. Creator affinity has its own
                # home in the creator graph, built from behavior.creators.
                if is_creator_behavior(behavior):
                    continue
                topic_behaviors[behavior.topic].append(behavior)
            
            # Create interest nodes
            all_nodes = []
            
            for topic, topic_behaviors_list in topic_behaviors.items():
                total_occurrences = sum(b.temporal_statistics.occurrence_count for b in topic_behaviors_list)
                avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in topic_behaviors_list) / len(topic_behaviors_list)
                def _safe_max_dt(items):
                    def _to_utc(dt):
                        if dt.tzinfo is None:
                            from datetime import timezone
                            return dt.replace(tzinfo=timezone.utc)
                        return dt
                    return max(items, key=_to_utc)
                last_engaged = _safe_max_dt(b.temporal_statistics.last_seen for b in topic_behaviors_list)
                
                # Determine trend
                lifecycle_states = [b.lifecycle_state for b in topic_behaviors_list]
                if "emerging" in lifecycle_states:
                    trend = "emerging"
                elif "growing" in lifecycle_states:
                    trend = "growing"
                elif "declining" in lifecycle_states:
                    trend = "declining"
                else:
                    trend = "stable"
                
                # Calculate strength
                strength = min(1.0, total_occurrences / 50.0) * avg_engagement
                
                # Get evidence
                evidence_ids = []
                for behavior in topic_behaviors_list:
                    evidence_ids.extend(behavior.evidence_references)
                
                node = InterestNode(
                    topic=topic,
                    strength=strength,
                    frequency=total_occurrences,
                    engagement_rate=avg_engagement,
                    last_engaged=last_engaged,
                    trend=trend,
                    confidence=sum(b.confidence_score for b in topic_behaviors_list) / len(topic_behaviors_list),
                    evidence_ids=evidence_ids[:5]
                )
                all_nodes.append(node)
            
            # Sort by strength
            all_nodes.sort(key=lambda n: n.strength, reverse=True)
            
            # Categorize
            dominant = [n for n in all_nodes if n.trend in ["stable", "growing"]][:5]
            emerging = [n for n in all_nodes if n.trend == "emerging"][:3]
            declining = [n for n in all_nodes if n.trend == "declining"][:3]
            stable = [n for n in all_nodes if n.trend == "stable"][:5]
            
            # Calculate diversity
            diversity = min(1.0, len(topic_behaviors) / 10.0)
            
            return InterestGraph(
                dominant_interests=dominant,
                emerging_interests=emerging,
                declining_interests=declining,
                stable_interests=stable,
                total_topics=len(topic_behaviors),
                diversity_score=diversity
            )
            
        except Exception as e:
            logger.error(f"Error building interest graph: {str(e)}", exc_info=True)
            raise
    
    def _build_creator_graph(self, behaviors: List[BehaviorObject]) -> CreatorGraph:
        """Build creator affinity graph"""
        try:
            from collections import defaultdict, Counter
            
            creator_data = defaultdict(lambda: {
                "views": 0,
                "total_engagement": 0.0,
                "total_watch_time": 0.0,
                "topics": [],
                "last_viewed": None
            })
            
            for behavior in behaviors:
                for creator in behavior.creators:
                    data = creator_data[creator]
                    data["views"] += behavior.temporal_statistics.occurrence_count
                    data["total_engagement"] += behavior.engagement_statistics.overall_engagement_rate
                    data["total_watch_time"] += behavior.watch_statistics.avg_watch_time
                    data["topics"].extend(behavior.subtopics[:2])
                    
                    if data["last_viewed"] is None or behavior.temporal_statistics.last_seen > data["last_viewed"]:
                        data["last_viewed"] = behavior.temporal_statistics.last_seen
            
            # Create creator nodes
            creator_nodes = []
            
            for creator, data in creator_data.items():
                view_count = data["views"]
                engagement_rate = data["total_engagement"] / view_count if view_count > 0 else 0.0
                avg_watch = data["total_watch_time"] / view_count if view_count > 0 else 0.0
                
                # Affinity score
                affinity = min(1.0, (view_count / 20.0) * 0.5 + engagement_rate * 0.5)
                
                # Top topics
                topic_counter = Counter(data["topics"])
                top_topics = [t[0] for t in topic_counter.most_common(3)]
                
                node = CreatorNode(
                    creator=creator,
                    affinity_score=affinity,
                    view_count=view_count,
                    engagement_rate=engagement_rate,
                    avg_watch_time=avg_watch,
                    primary_topics=top_topics,
                    last_viewed=data["last_viewed"],
                    confidence=min(1.0, view_count / 10.0)
                )
                creator_nodes.append(node)
            
            # Sort by affinity
            creator_nodes.sort(key=lambda n: n.affinity_score, reverse=True)
            
            # Calculate diversity
            total_creators = len(creator_nodes)
            diversity = min(1.0, total_creators / 15.0)
            
            # Calculate dependence (top 3 creators / total views)
            total_views = sum(n.view_count for n in creator_nodes)
            top_3_views = sum(n.view_count for n in creator_nodes[:3])
            dependence = top_3_views / total_views if total_views > 0 else 0.0
            
            return CreatorGraph(
                top_creators=creator_nodes[:10],
                creator_diversity_score=diversity,
                dependence_score=dependence,
                total_creators=total_creators
            )
            
        except Exception as e:
            logger.error(f"Error building creator graph: {str(e)}", exc_info=True)
            raise
    
    def _infer_learning_style(
        self,
        behaviors: List[BehaviorObject],
        inferences: List[Inference]
    ) -> LearningStyle:
        """Infer learning style from behaviors and inferences"""
        try:
            # Check for learning motivation inference
            learning_inferences = [i for i in inferences if "learning" in i.label.lower()]
            
            if not behaviors:
                return LearningStyle(
                    style_type="unknown",
                    confidence=0.0,
                    completion_rate=0.0,
                    depth_preference="unknown",
                    pace_preference="unknown"
                )
            
            # Completion rate from watch statistics
            avg_completion = sum(b.watch_statistics.completion_rate for b in behaviors) / len(behaviors)
            
            # Depth preference from watch time
            avg_watch = sum(b.watch_statistics.avg_watch_time for b in behaviors) / len(behaviors)
            if avg_watch > 20:
                depth = "deep"
            elif avg_watch > 10:
                depth = "moderate"
            else:
                depth = "quick"
            
            # Pace from frequency
            avg_frequency = sum(b.temporal_statistics.daily_frequency for b in behaviors) / len(behaviors)
            if avg_frequency > 3:
                pace = "fast"
            elif avg_frequency > 1:
                pace = "moderate"
            else:
                pace = "slow"
            
            # Style type (simplified)
            style = "analytical" if learning_inferences else "practical"
            
            confidence = 0.7 if learning_inferences else 0.5
            
            return LearningStyle(
                style_type=style,
                confidence=confidence,
                completion_rate=avg_completion,
                depth_preference=depth,
                pace_preference=pace,
                format_preferences=["video", "tutorial"],
                evidence_ids=[i.inference_id for i in learning_inferences[:3]]
            )
            
        except Exception as e:
            logger.error(f"Error inferring learning style: {str(e)}", exc_info=True)
            raise
    
    def _build_attention_profile(self, behaviors: List[BehaviorObject]) -> AttentionProfile:
        """Build attention profile"""
        try:
            if not behaviors:
                return AttentionProfile(
                    avg_attention_span=0.0,
                    attention_consistency=0.0,
                    attention_trend="unknown",
                    distraction_resistance=0.0,
                    focus_quality=0.0
                )
            
            avg_watch = sum(b.watch_statistics.avg_watch_time for b in behaviors) / len(behaviors)
            
            # Consistency from watch time std
            watch_stds = [b.watch_statistics.watch_time_std for b in behaviors]
            avg_std = sum(watch_stds) / len(watch_stds)
            consistency = max(0.0, 1.0 - (avg_std / avg_watch)) if avg_watch > 0 else 0.0
            
            # Trend (simplified)
            trend = "stable"
            
            # Distraction resistance from completion rate
            avg_completion = sum(b.watch_statistics.completion_rate for b in behaviors) / len(behaviors)
            
            # Focus quality from engagement
            avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in behaviors) / len(behaviors)
            
            return AttentionProfile(
                avg_attention_span=avg_watch,
                attention_consistency=consistency,
                attention_trend=trend,
                peak_attention_hours=[],
                distraction_resistance=avg_completion,
                focus_quality=avg_engagement
            )
            
        except Exception as e:
            logger.error(f"Error building attention profile: {str(e)}", exc_info=True)
            raise
    
    def _build_exploration_profile(self, behaviors: List[BehaviorObject]) -> ExplorationProfile:
        """Build exploration vs exploitation profile"""
        try:
            if not behaviors:
                return ExplorationProfile(
                    novelty_seeking_score=0.0,
                    exploration_rate=0.0,
                    exploitation_rate=0.0,
                    topic_switching_frequency=0.0,
                    comfort_zone_ratio=0.0
                )
            
            # Count emerging vs stable behaviors
            emerging_count = sum(1 for b in behaviors if b.is_emerging())
            stable_count = sum(1 for b in behaviors if b.is_stable())
            
            exploration_rate = emerging_count / len(behaviors)
            exploitation_rate = stable_count / len(behaviors)
            
            # Novelty seeking from emerging behaviors
            novelty_seeking = min(1.0, emerging_count / 5.0)
            
            # Topic switching (simplified)
            unique_topics = len(set(b.topic for b in behaviors))
            switching_freq = unique_topics / len(behaviors)
            
            # Comfort zone (stable behaviors ratio)
            comfort_zone = stable_count / len(behaviors)
            
            return ExplorationProfile(
                novelty_seeking_score=novelty_seeking,
                exploration_rate=exploration_rate,
                exploitation_rate=exploitation_rate,
                topic_switching_frequency=switching_freq,
                comfort_zone_ratio=comfort_zone
            )
            
        except Exception as e:
            logger.error(f"Error building exploration profile: {str(e)}", exc_info=True)
            raise
    
    def _build_consistency_profile(self, behaviors: List[BehaviorObject]) -> ConsistencyProfile:
        """Build consistency profile"""
        try:
            if not behaviors:
                return ConsistencyProfile(
                    overall_consistency=0.0,
                    topic_consistency=0.0,
                    temporal_consistency=0.0,
                    engagement_consistency=0.0,
                    volatility_score=0.0
                )
            
            # Overall consistency from stability scores
            overall = sum(b.stability_score for b in behaviors) / len(behaviors)
            
            # Topic consistency (how often same topics appear)
            from collections import Counter
            topic_counts = Counter(b.topic for b in behaviors)
            max_topic_count = max(topic_counts.values())
            topic_consistency = max_topic_count / len(behaviors)
            
            # Temporal consistency from recency scores
            temporal = sum(b.temporal_statistics.consistency_score for b in behaviors) / len(behaviors)
            
            # Engagement consistency (std of engagement rates)
            engagement_rates = [b.engagement_statistics.overall_engagement_rate for b in behaviors]
            import statistics
            engagement_std = statistics.stdev(engagement_rates) if len(engagement_rates) > 1 else 0.0
            engagement_consistency = max(0.0, 1.0 - engagement_std)
            
            # Volatility from trend changes
            volatility = sum(b.trend_information.volatility_score for b in behaviors) / len(behaviors)
            
            return ConsistencyProfile(
                overall_consistency=overall,
                topic_consistency=topic_consistency,
                temporal_consistency=temporal,
                engagement_consistency=engagement_consistency,
                volatility_score=volatility
            )
            
        except Exception as e:
            logger.error(f"Error building consistency profile: {str(e)}", exc_info=True)
            raise
    
    def _build_habit_profile(self, behaviors: List[BehaviorObject]) -> HabitProfile:
        """Build habit and routine profile"""
        try:
            if not behaviors:
                return HabitProfile(
                    has_daily_routine=False,
                    routine_strength=0.0,
                    session_regularity=0.0,
                    habit_stability=0.0
                )
            
            # Check for routine (simplified)
            avg_frequency = sum(b.temporal_statistics.daily_frequency for b in behaviors) / len(behaviors)
            has_routine = avg_frequency > 1.0
            routine_strength = min(1.0, avg_frequency / 3.0)
            
            # Session regularity from consistency
            regularity = sum(b.temporal_statistics.consistency_score for b in behaviors) / len(behaviors)
            
            # Habit stability from stability scores
            stability = sum(b.stability_score for b in behaviors) / len(behaviors)
            
            return HabitProfile(
                has_daily_routine=has_routine,
                routine_strength=routine_strength,
                peak_usage_hours=[],
                peak_usage_days=[],
                session_regularity=regularity,
                habit_stability=stability
            )
            
        except Exception as e:
            logger.error(f"Error building habit profile: {str(e)}", exc_info=True)
            raise
    
    def _extract_motivation_signals(
        self,
        inferences: List[Inference],
        behaviors: List[BehaviorObject]
    ) -> MotivationSignals:
        """Extract motivation signals from inferences"""
        try:
            # Find motivation-related inferences
            learning_inferences = [i for i in inferences if "learning" in i.label.lower() or "motivation" in i.label.lower()]
            entertainment_inferences = [i for i in inferences if "entertainment" in i.label.lower()]
            
            # Learning motivation
            learning_motivation = 0.0
            if learning_inferences:
                learning_motivation = sum(i.strength for i in learning_inferences) / len(learning_inferences)
            
            # Entertainment seeking
            entertainment_seeking = 0.0
            if entertainment_inferences:
                entertainment_seeking = sum(i.strength for i in entertainment_inferences) / len(entertainment_inferences)
            
            # Skill building from learning behaviors
            skill_building = learning_motivation * 0.8
            
            # Curiosity from exploration
            emerging_count = sum(1 for b in behaviors if b.is_emerging())
            curiosity = min(1.0, emerging_count / 5.0)
            
            # Goal orientation (simplified)
            goal_orientation = learning_motivation * 0.7
            
            # Intrinsic motivation from engagement
            if behaviors:
                avg_engagement = sum(b.engagement_statistics.overall_engagement_rate for b in behaviors) / len(behaviors)
                intrinsic = avg_engagement
            else:
                intrinsic = 0.0
            
            confidence = 0.7 if inferences else 0.5
            
            return MotivationSignals(
                learning_motivation=learning_motivation,
                entertainment_seeking=entertainment_seeking,
                skill_building_intent=skill_building,
                curiosity_score=curiosity,
                goal_orientation=goal_orientation,
                intrinsic_motivation=intrinsic,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error extracting motivation signals: {str(e)}", exc_info=True)
            raise
    
    def _calculate_identity_confidence(
        self,
        behaviors: List[BehaviorObject],
        inferences: List[Inference],
        evidence: List[Evidence]
    ) -> float:
        """Calculate overall identity confidence"""
        try:
            if not behaviors:
                return 0.0
            
            # Confidence from data volume
            data_volume_confidence = min(1.0, len(behaviors) / 20.0)
            
            # Confidence from behavior confidence
            behavior_confidence = sum(b.confidence_score for b in behaviors) / len(behaviors)
            
            # Confidence from evidence
            evidence_confidence = sum(e.confidence for e in evidence) / len(evidence) if evidence else 0.5
            
            # Confidence from inferences
            inference_confidence = sum(i.confidence for i in inferences) / len(inferences) if inferences else 0.5
            
            # Weighted average
            overall = (
                data_volume_confidence * 0.3 +
                behavior_confidence * 0.3 +
                evidence_confidence * 0.2 +
                inference_confidence * 0.2
            )
            
            return round(overall, 3)
            
        except Exception as e:
            logger.error(f"Error calculating identity confidence: {str(e)}", exc_info=True)
            return 0.5
    
    def _calculate_completeness(
        self,
        behaviors: List[BehaviorObject],
        inferences: List[Inference]
    ) -> float:
        """Calculate identity completeness"""
        try:
            # Completeness factors
            has_behaviors = len(behaviors) >= self.min_behaviors_for_identity
            has_inferences = len(inferences) > 0
            has_diverse_topics = len(set(b.topic for b in behaviors)) >= 3
            
            completeness = 0.0
            if has_behaviors:
                completeness += 0.4
            if has_inferences:
                completeness += 0.3
            if has_diverse_topics:
                completeness += 0.3
            
            return round(completeness, 3)
            
        except Exception as e:
            logger.error(f"Error calculating completeness: {str(e)}", exc_info=True)
            return 0.0


def get_identity_engine() -> IdentityEngine:
    """Get singleton identity engine instance"""
    if not hasattr(get_identity_engine, "_instance"):
        get_identity_engine._instance = IdentityEngine()
    return get_identity_engine._instance
