"""
Contextual Bandit RL System
Lightweight reinforcement learning for action selection
"""
from typing import Dict, List, Optional
import json
import os
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextualBandit:
    """
    Epsilon-greedy contextual bandit for action selection
    """
    
    def __init__(
        self,
        epsilon: float = 0.2,
        decay_rate: float = 0.995,
        storage_path: str = "./rl_data"
    ):
        """
        Initialize contextual bandit
        
        Args:
            epsilon: Exploration rate (0-1)
            decay_rate: Epsilon decay rate per update
            storage_path: Directory to persist bandit parameters
        """
        self.epsilon = epsilon
        self.initial_epsilon = epsilon
        self.decay_rate = decay_rate
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        # Action statistics: {action_id: {count, total_reward, avg_reward}}
        self.action_stats = self._load_stats()
        
        # Action history: {user_id: [{action_id, reward, timestamp}]}
        self.history = self._load_history()
    
    def _load_stats(self) -> Dict:
        """Load action statistics from disk"""
        stats_file = os.path.join(self.storage_path, "action_stats.json")
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_stats(self):
        """Save action statistics to disk"""
        stats_file = os.path.join(self.storage_path, "action_stats.json")
        with open(stats_file, 'w') as f:
            json.dump(self.action_stats, f, indent=2)
    
    def _load_history(self) -> Dict:
        """Load action history from disk"""
        history_file = os.path.join(self.storage_path, "action_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_history(self):
        """Save action history to disk"""
        history_file = os.path.join(self.storage_path, "action_history.json")
        with open(history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def select_action(
        self,
        available_actions: List[Dict],
        user_id: str,
        state: Optional[Dict] = None
    ) -> Dict:
        """
        Select action using epsilon-greedy policy
        
        Args:
            available_actions: List of available actions
            user_id: User identifier
            state: Current state (optional, for context)
            
        Returns:
            Selected action
        """
        if not available_actions:
            raise ValueError("No actions available")
        
        # Exploration: random action
        if random.random() < self.epsilon:
            action = random.choice(available_actions)
            logger.info(f"Exploration: selected random action {action['action_id']}")
            return action
        
        # Exploitation: best action based on estimated reward
        best_action = None
        best_value = -float('inf')
        
        for action in available_actions:
            action_id = action['action_id']
            
            # Get action statistics
            if action_id in self.action_stats:
                stats = self.action_stats[action_id]
                value = stats['avg_reward']
                
                # UCB bonus for exploration
                count = stats['count']
                total_count = sum([s['count'] for s in self.action_stats.values()])
                if total_count > 0 and count > 0:
                    ucb_bonus = (2 * (total_count ** 0.5)) / (count ** 0.5)
                    value += ucb_bonus * 0.1  # Small UCB weight
            else:
                # New action: give optimistic initial value
                value = 0.5
            
            if value > best_value:
                best_value = value
                best_action = action
        
        logger.info(f"Exploitation: selected best action {best_action['action_id']} (value: {best_value:.3f})")
        return best_action
    
    def update(
        self,
        user_id: str,
        action_id: str,
        reward: float
    ) -> Dict:
        """
        Update bandit with feedback
        
        Args:
            user_id: User identifier
            action_id: Action that was taken
            reward: Observed reward
            
        Returns:
            Updated action statistics
        """
        # Initialize action stats if new
        if action_id not in self.action_stats:
            self.action_stats[action_id] = {
                "count": 0,
                "total_reward": 0.0,
                "avg_reward": 0.0
            }
        
        # Update statistics
        stats = self.action_stats[action_id]
        stats['count'] += 1
        stats['total_reward'] += reward
        stats['avg_reward'] = stats['total_reward'] / stats['count']
        
        # Decay epsilon (reduce exploration over time)
        self.epsilon = max(0.05, self.epsilon * self.decay_rate)
        
        # Store in history
        if user_id not in self.history:
            self.history[user_id] = []
        
        self.history[user_id].append({
            "action_id": action_id,
            "reward": reward,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Persist to disk
        self._save_stats()
        self._save_history()
        
        logger.info(f"Updated action {action_id}: count={stats['count']}, avg_reward={stats['avg_reward']:.3f}, epsilon={self.epsilon:.3f}")
        
        return stats
    
    def get_action_stats(self, action_id: str) -> Optional[Dict]:
        """
        Get statistics for specific action
        
        Args:
            action_id: Action identifier
            
        Returns:
            Action statistics or None
        """
        return self.action_stats.get(action_id)
    
    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get action history for user
        
        Args:
            user_id: User identifier
            limit: Maximum number of records to return
            
        Returns:
            List of action history records
        """
        history = self.history.get(user_id, [])
        return history[-limit:]
    
    def get_top_actions(self, top_k: int = 5) -> List[Dict]:
        """
        Get top performing actions
        
        Args:
            top_k: Number of top actions to return
            
        Returns:
            List of top actions with statistics
        """
        sorted_actions = sorted(
            self.action_stats.items(),
            key=lambda x: x[1]['avg_reward'],
            reverse=True
        )
        
        return [
            {
                "action_id": action_id,
                **stats
            }
            for action_id, stats in sorted_actions[:top_k]
        ]
    
    def reset_epsilon(self):
        """Reset epsilon to initial value"""
        self.epsilon = self.initial_epsilon
        logger.info(f"Reset epsilon to {self.epsilon}")


# Global instance
_bandit = None


def get_bandit() -> ContextualBandit:
    """Get or create bandit instance"""
    global _bandit
    if _bandit is None:
        _bandit = ContextualBandit(epsilon=0.2, decay_rate=0.995)
    return _bandit
