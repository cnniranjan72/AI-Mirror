"""
Reward function for RL system
Calculates rewards based on behavioral deltas and alignment progress
"""
from typing import Dict, Optional, List
import logging
import statistics

logger = logging.getLogger(__name__)


class RewardCalculator:
    """
    Calculates rewards for RL system based on behavioral outcomes
    Uses behavioral deltas with smoothing to avoid noise
    """
    
    def __init__(self, smoothing_window: int = 3):
        """
        Initialize reward calculator
        
        Args:
            smoothing_window: Number of recent rewards to smooth over
        """
        self.smoothing_window = smoothing_window
        self.reward_history: Dict[str, List[float]] = {}
    
    def calculate_reward(
        self,
        user_id: str,
        followed: bool,
        before_metrics: Optional[Dict] = None,
        after_metrics: Optional[Dict] = None,
        alignment_progress: Optional[float] = None,
        user_rating: Optional[int] = None
    ) -> float:
        """
        Calculate reward using behavioral deltas
        
        Reward components:
        - Δ attention_score (weight: 0.3)
        - Δ engagement_score (weight: 0.25)
        - Δ scroll_speed (negative, weight: 0.2)
        - alignment_progress (weight: 0.15)
        - user_followed_action (weight: 0.1)
        
        Args:
            user_id: User identifier
            followed: Whether user followed the action
            before_metrics: Metrics before action
            after_metrics: Metrics after action
            alignment_progress: Progress toward goal (0-1)
            user_rating: Optional user rating (1-5)
            
        Returns:
            Smoothed reward value (-1 to 1)
        """
        reward = 0.0
        components = {}
        
        # Component 1: User followed action (base reward)
        if followed:
            follow_reward = 0.2
        else:
            follow_reward = -0.3
        components['follow'] = follow_reward
        reward += follow_reward
        
        # Component 2-4: Behavioral deltas
        if before_metrics and after_metrics:
            # Δ attention_score (higher is better)
            delta_attention = after_metrics.get('attention_score', 0) - before_metrics.get('attention_score', 0)
            attention_reward = delta_attention * 0.3
            components['attention_delta'] = delta_attention
            reward += attention_reward
            
            # Δ engagement_score (higher is better)
            delta_engagement = after_metrics.get('engagement_score', 0) - before_metrics.get('engagement_score', 0)
            engagement_reward = delta_engagement * 0.25
            components['engagement_delta'] = delta_engagement
            reward += engagement_reward
            
            # Δ scroll_speed (lower is better, so negative delta is good)
            before_speed = before_metrics.get('activity_level', 0)
            after_speed = after_metrics.get('activity_level', 0)
            delta_speed = before_speed - after_speed  # Inverted: reduction is positive
            
            # Normalize by before_speed to get percentage change
            if before_speed > 0:
                speed_change_pct = delta_speed / before_speed
            else:
                speed_change_pct = 0
            
            speed_reward = speed_change_pct * 0.2
            components['speed_delta'] = delta_speed
            reward += speed_reward
        
        # Component 5: Alignment progress
        if alignment_progress is not None:
            alignment_reward = alignment_progress * 0.15
            components['alignment'] = alignment_progress
            reward += alignment_reward
        
        # Bonus: User rating
        if user_rating is not None:
            rating_reward = (user_rating - 3) * 0.1
            components['rating'] = user_rating
            reward += rating_reward
        
        # Clip to [-1, 1]
        raw_reward = max(-1.0, min(1.0, reward))
        
        # Apply smoothing
        smoothed_reward = self._smooth_reward(user_id, raw_reward)
        
        logger.info(f"Reward calculated: raw={raw_reward:.3f}, smoothed={smoothed_reward:.3f}, components={components}")
        
        return smoothed_reward
    
    def _smooth_reward(self, user_id: str, reward: float) -> float:
        """
        Apply exponential moving average smoothing to reduce noise
        
        Args:
            user_id: User identifier
            reward: Raw reward value
            
        Returns:
            Smoothed reward
        """
        if user_id not in self.reward_history:
            self.reward_history[user_id] = []
        
        self.reward_history[user_id].append(reward)
        
        # Keep only recent history
        if len(self.reward_history[user_id]) > self.smoothing_window:
            self.reward_history[user_id] = self.reward_history[user_id][-self.smoothing_window:]
        
        # Calculate smoothed reward (exponential moving average)
        if len(self.reward_history[user_id]) == 1:
            return reward
        
        # EMA with alpha = 0.3 (gives more weight to recent)
        alpha = 0.3
        smoothed = reward
        for i in range(len(self.reward_history[user_id]) - 2, -1, -1):
            smoothed = alpha * self.reward_history[user_id][i] + (1 - alpha) * smoothed
        
        return smoothed
    
    def calculate_behavior_change(
        self,
        before_metrics: Dict,
        after_metrics: Dict,
        goal_type: str
    ) -> float:
        """
        Calculate behavior change score
        
        Args:
            before_metrics: Metrics before action
            after_metrics: Metrics after action
            goal_type: Type of goal (reduce_usage, improve_attention, etc.)
            
        Returns:
            Change score (-1 to 1)
        """
        if goal_type == "reduce_usage":
            # Lower watch time is better
            before = before_metrics.get('total_watch_time', 0)
            after = after_metrics.get('total_watch_time', 0)
            
            if before == 0:
                return 0.0
            
            change = (before - after) / before
            return max(-1.0, min(1.0, change))
        
        elif goal_type == "improve_attention":
            # Higher attention score is better
            before = before_metrics.get('attention_score', 0)
            after = after_metrics.get('attention_score', 0)
            
            change = after - before
            return max(-1.0, min(1.0, change * 2))  # Scale up
        
        elif goal_type == "improve_engagement":
            # Higher engagement is better
            before = before_metrics.get('engagement_score', 0)
            after = after_metrics.get('engagement_score', 0)
            
            change = after - before
            return max(-1.0, min(1.0, change * 2))
        
        elif goal_type == "reduce_activity":
            # Lower activity is better
            before = before_metrics.get('activity_level', 0)
            after = after_metrics.get('activity_level', 0)
            
            if before == 0:
                return 0.0
            
            change = (before - after) / before
            return max(-1.0, min(1.0, change))
        
        else:
            return 0.0
    
    def calculate_alignment_improvement(
        self,
        before_gap: float,
        after_gap: float
    ) -> float:
        """
        Calculate improvement in alignment gap
        
        Args:
            before_gap: Gap before action
            after_gap: Gap after action
            
        Returns:
            Improvement score (-1 to 1)
        """
        # Positive if gap decreased (good)
        improvement = before_gap - after_gap
        
        # Normalize
        return max(-1.0, min(1.0, improvement * 2))


def get_reward_calculator() -> RewardCalculator:
    """Get reward calculator instance"""
    return RewardCalculator()
