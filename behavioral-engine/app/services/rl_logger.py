"""
RL Actions Logger for training and analysis
Tracks actions, rewards, and state transitions
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import json

from app.database import execute_insert, execute_query

logger = logging.getLogger(__name__)


class RLLogger:
    """
    Logger for reinforcement learning actions and rewards
    Critical for RL training and research analysis
    """
    
    async def log_action(
        self,
        user_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        reward: float,
        feedback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an RL action with full state transition
        
        Args:
            user_id: User identifier
            action_type: Type of action (e.g., 'recommendation', 'suggestion', 'intervention')
            action_data: Action details
            state_before: User state before action
            state_after: User state after action
            reward: Computed reward value
            feedback: Optional user feedback
            context: Optional additional context
            
        Returns:
            Action log ID
        """
        query = """
            INSERT INTO actions_log (
                user_id, action_type, action_data, state_before, state_after,
                reward, feedback, context
            )
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6, $7, $8::jsonb)
            RETURNING id
        """
        
        result = await execute_insert(
            query,
            user_id,
            action_type,
            json.dumps(action_data),
            json.dumps(state_before),
            json.dumps(state_after),
            reward,
            feedback,
            json.dumps(context or {})
        )
        
        logger.info(f"Logged RL action for user {user_id}: {action_type} (reward: {reward:.3f})")
        return str(result['id'])
    
    async def get_user_actions(
        self,
        user_id: str,
        limit: int = 100,
        action_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get action history for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of actions
            action_type: Optional filter by action type
            
        Returns:
            List of action logs
        """
        if action_type:
            query = """
                SELECT id, action_type, action_data, state_before, state_after,
                       reward, feedback, context, created_at
                FROM actions_log
                WHERE user_id = $1 AND action_type = $2
                ORDER BY created_at DESC
                LIMIT $3
            """
            results = await execute_query(query, user_id, action_type, limit)
        else:
            query = """
                SELECT id, action_type, action_data, state_before, state_after,
                       reward, feedback, context, created_at
                FROM actions_log
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            results = await execute_query(query, user_id, limit)
        
        return [
            {
                'id': str(row['id']),
                'action_type': row['action_type'],
                'action_data': row['action_data'],
                'state_before': row['state_before'],
                'state_after': row['state_after'],
                'reward': float(row['reward']),
                'feedback': row['feedback'],
                'context': row['context'],
                'created_at': row['created_at'].isoformat()
            }
            for row in results
        ]
    
    async def get_action_statistics(
        self,
        user_id: str,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistical summary of actions
        
        Args:
            user_id: User identifier
            action_type: Optional filter by action type
            
        Returns:
            Statistics dictionary
        """
        if action_type:
            query = """
                SELECT 
                    COUNT(*) as action_count,
                    AVG(reward) as avg_reward,
                    STDDEV(reward) as reward_stddev,
                    MIN(reward) as min_reward,
                    MAX(reward) as max_reward,
                    SUM(CASE WHEN reward > 0 THEN 1 ELSE 0 END) as positive_rewards,
                    SUM(CASE WHEN reward < 0 THEN 1 ELSE 0 END) as negative_rewards
                FROM actions_log
                WHERE user_id = $1 AND action_type = $2
            """
            result = await execute_query(query, user_id, action_type)
        else:
            query = """
                SELECT 
                    COUNT(*) as action_count,
                    AVG(reward) as avg_reward,
                    STDDEV(reward) as reward_stddev,
                    MIN(reward) as min_reward,
                    MAX(reward) as max_reward,
                    SUM(CASE WHEN reward > 0 THEN 1 ELSE 0 END) as positive_rewards,
                    SUM(CASE WHEN reward < 0 THEN 1 ELSE 0 END) as negative_rewards
                FROM actions_log
                WHERE user_id = $1
            """
            result = await execute_query(query, user_id)
        
        if result:
            row = result[0]
            return {
                'action_count': int(row['action_count']),
                'avg_reward': float(row['avg_reward']) if row['avg_reward'] else 0.0,
                'reward_stddev': float(row['reward_stddev']) if row['reward_stddev'] else 0.0,
                'min_reward': float(row['min_reward']) if row['min_reward'] else 0.0,
                'max_reward': float(row['max_reward']) if row['max_reward'] else 0.0,
                'positive_rewards': int(row['positive_rewards']),
                'negative_rewards': int(row['negative_rewards'])
            }
        
        return {
            'action_count': 0,
            'avg_reward': 0.0,
            'reward_stddev': 0.0,
            'min_reward': 0.0,
            'max_reward': 0.0,
            'positive_rewards': 0,
            'negative_rewards': 0
        }
    
    async def get_high_reward_actions(
        self,
        user_id: str,
        threshold: float = 0.5,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get actions with high rewards for analysis
        
        Args:
            user_id: User identifier
            threshold: Minimum reward threshold
            limit: Maximum number of actions
            
        Returns:
            List of high-reward actions
        """
        query = """
            SELECT id, action_type, action_data, reward, created_at
            FROM actions_log
            WHERE user_id = $1 AND reward >= $2
            ORDER BY reward DESC, created_at DESC
            LIMIT $3
        """
        
        results = await execute_query(query, user_id, threshold, limit)
        
        return [
            {
                'id': str(row['id']),
                'action_type': row['action_type'],
                'action_data': row['action_data'],
                'reward': float(row['reward']),
                'created_at': row['created_at'].isoformat()
            }
            for row in results
        ]
    
    async def export_training_data(
        self,
        user_id: Optional[str] = None,
        min_samples: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Export data for RL model training
        
        Args:
            user_id: Optional user filter (None for all users)
            min_samples: Minimum number of samples required
            
        Returns:
            Training data in format: [(state, action, reward, next_state), ...]
        """
        if user_id:
            query = """
                SELECT user_id, action_type, action_data, state_before, 
                       state_after, reward
                FROM actions_log
                WHERE user_id = $1
                ORDER BY created_at
            """
            results = await execute_query(query, user_id)
        else:
            query = """
                SELECT user_id, action_type, action_data, state_before, 
                       state_after, reward
                FROM actions_log
                ORDER BY user_id, created_at
            """
            results = await execute_query(query)
        
        training_data = [
            {
                'user_id': row['user_id'],
                'state': row['state_before'],
                'action': {
                    'type': row['action_type'],
                    'data': row['action_data']
                },
                'reward': float(row['reward']),
                'next_state': row['state_after']
            }
            for row in results
        ]
        
        logger.info(f"Exported {len(training_data)} samples for RL training")
        
        if len(training_data) < min_samples:
            logger.warning(f"Only {len(training_data)} samples available (minimum: {min_samples})")
        
        return training_data


# Global instance
_rl_logger = None


async def get_rl_logger() -> RLLogger:
    """
    Get or create the global RL logger instance
    
    Returns:
        RLLogger instance
    """
    global _rl_logger
    if _rl_logger is None:
        _rl_logger = RLLogger()
    return _rl_logger
