"""
Chat Memory Module

This module manages the conversational history between the user and the system.
It stores chat logs in a separate JSON file per user to maintain context for
multi-turn interactions.
"""

import json
import os
import datetime
from typing import List, Dict, Optional, Any

class ChatMemory:
    """
    Manages persistent chat history for users.
    
    Stores conversation turns (user messages and system responses) to allow
    the system to maintain context and "remember" what was just discussed.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the ChatMemory manager.
        
        Args:
            data_dir: Directory path where chat JSON files will be stored.
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_chat_path(self, user_id: str) -> str:
        """Get the file path for a user's chat history."""
        return os.path.join(self.data_dir, f"{user_id}_chat.json")
    
    def _load_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Load chat history from file."""
        filepath = self._get_chat_path(user_id)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_history(self, user_id: str, history: List[Dict[str, Any]]) -> None:
        """Save chat history to file safely."""
        filepath = self._get_chat_path(user_id)
        temp_filepath = filepath + ".tmp"
        
        try:
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            os.replace(temp_filepath, filepath)
        except Exception:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass

    def add_turn(self, user_id: str, role: str, content: str, metadata: Dict = None) -> Dict[str, Any]:
        """
        Add a single message to the chat history.
        
        Args:
            user_id: The user's unique identifier.
            role: 'user' or 'system'.
            content: The text content of the message.
            metadata: Optional dictionary for extra info (e.g., related suggestion ID).
            
        Returns:
            The created message object.
        """
        message = {
            "id": str(datetime.datetime.now().timestamp()), # Simple ID
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        history = self._load_history(user_id)
        history.append(message)
        
        # Limit history length to prevent infinite growth (keep last 50 turns)
        if len(history) > 50:
            history = history[-50:]
            
        self._save_history(user_id, history)
        return message

    def get_recent_context(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent chat messages for context.
        
        Args:
            user_id: The user's unique identifier.
            limit: Number of recent messages to return.
            
        Returns:
            List of message objects.
        """
        history = self._load_history(user_id)
        return history[-limit:]

    def clear_history(self, user_id: str) -> None:
        """Clear chat history for a user."""
        filepath = self._get_chat_path(user_id)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
