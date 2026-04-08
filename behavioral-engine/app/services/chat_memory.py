"""
Chat Memory - Stores conversation history
"""
from typing import List, Dict
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChatMemory:
    """
    Manages chat conversation history
    """
    
    def __init__(self, storage_path: str = "./chat_data", max_history: int = 50):
        """
        Initialize chat memory
        
        Args:
            storage_path: Directory to store chat history
            max_history: Maximum messages to keep per user
        """
        self.storage_path = storage_path
        self.max_history = max_history
        os.makedirs(storage_path, exist_ok=True)
        self.conversations = self._load_conversations()
    
    def _load_conversations(self) -> Dict:
        """Load conversations from disk"""
        conv_file = os.path.join(self.storage_path, "conversations.json")
        if os.path.exists(conv_file):
            try:
                with open(conv_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_conversations(self):
        """Save conversations to disk"""
        conv_file = os.path.join(self.storage_path, "conversations.json")
        with open(conv_file, 'w') as f:
            json.dump(self.conversations, f, indent=2)
    
    def add_message(
        self,
        user_id: str,
        role: str,
        content: str
    ):
        """
        Add message to conversation history
        
        Args:
            user_id: User identifier
            role: Message role (user or assistant)
            content: Message content
        """
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.conversations[user_id].append(message)
        
        # Trim history if too long
        if len(self.conversations[user_id]) > self.max_history:
            self.conversations[user_id] = self.conversations[user_id][-self.max_history:]
        
        self._save_conversations()
        logger.debug(f"Added {role} message for user {user_id}")
    
    def get_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get conversation history for user
        
        Args:
            user_id: User identifier
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        history = self.conversations.get(user_id, [])
        return history[-limit:]
    
    def get_context_summary(
        self,
        user_id: str,
        last_n: int = 5
    ) -> str:
        """
        Get summary of recent conversation for context
        
        Args:
            user_id: User identifier
            last_n: Number of recent messages to include
            
        Returns:
            Context summary string
        """
        history = self.get_history(user_id, limit=last_n)
        
        if not history:
            return ""
        
        summary_parts = []
        for msg in history:
            role = msg['role']
            content = msg['content'][:100]  # Truncate
            summary_parts.append(f"{role}: {content}")
        
        return " | ".join(summary_parts)
    
    def clear_history(self, user_id: str):
        """
        Clear conversation history for user
        
        Args:
            user_id: User identifier
        """
        if user_id in self.conversations:
            self.conversations[user_id] = []
            self._save_conversations()
            logger.info(f"Cleared history for user {user_id}")


# Global instance
_chat_memory = None


def get_chat_memory() -> ChatMemory:
    """Get or create chat memory instance"""
    global _chat_memory
    if _chat_memory is None:
        _chat_memory = ChatMemory()
    return _chat_memory
