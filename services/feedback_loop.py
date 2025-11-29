"""
Feedback Loop Module

This module tracks user interactions with suggestions to learn what works.
It records feedback (accepted, rejected, completed, helpfulness rating) and
provides analytics to adapt future suggestions.
"""

import json
import os
import datetime
from typing import List, Dict, Optional, Any

class FeedbackLoop:
    """
    Manages feedback on suggestions.
    
    Stores outcomes of suggestions (e.g., "User accepted 'Take a walk'") to
    refine the system's understanding of user preferences.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
    def _get_feedback_path(self, user_id: str) -> str:
        return os.path.join(self.data_dir, f"{user_id}_feedback.json")
        
    def _load_feedback(self, user_id: str) -> List[Dict[str, Any]]:
        filepath = self._get_feedback_path(user_id)
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_feedback(self, user_id: str, data: List[Dict[str, Any]]) -> None:
        filepath = self._get_feedback_path(user_id)
        temp_filepath = filepath + ".tmp"
        try:
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_filepath, filepath)
        except:
            pass

    def log_interaction(self, user_id: str, suggestion_id: str, action: str, 
                       suggestion_meta: Dict = None, rating: int = None) -> Dict[str, Any]:
        """
        Log a user's interaction with a suggestion.
        
        Args:
            user_id: User ID.
            suggestion_id: UUID of the suggestion.
            action: 'accepted', 'rejected', 'completed', 'dismissed'.
            suggestion_meta: Metadata from the suggestion (category, difficulty, etc.).
            rating: Optional 1-5 rating if action is 'completed'.
            
        Returns:
            The created feedback entry.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "suggestion_id": suggestion_id,
            "action": action,
            "rating": rating,
            "meta": suggestion_meta or {}
        }
        
        history = self._load_feedback(user_id)
        history.append(entry)
        self._save_feedback(user_id, history)
        return entry

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze feedback history to determine user preferences.
        
        Returns:
            Dictionary with preferred categories, difficulties, and success rates.
        """
        history = self._load_feedback(user_id)
        if not history:
            return {"preferred_category": None, "preferred_difficulty": None}
            
        # Counters
        cat_counts = {}
        diff_counts = {}
        actions = {"accepted": 0, "rejected": 0, "completed": 0}
        
        for entry in history:
            action = entry.get("action")
            meta = entry.get("meta", {})
            category = meta.get("category")
            difficulty = meta.get("difficulty")
            
            if action in actions:
                actions[action] += 1
            
            # Only count positive interactions for preference
            if action in ["accepted", "completed"]:
                if category:
                    cat_counts[category] = cat_counts.get(category, 0) + 1
                if difficulty:
                    diff_counts[difficulty] = diff_counts.get(difficulty, 0) + 1
                    
        # Determine top picks
        top_category = max(cat_counts, key=cat_counts.get) if cat_counts else None
        top_difficulty = max(diff_counts, key=diff_counts.get) if diff_counts else None
        
        total = len(history)
        acceptance_rate = (actions["accepted"] + actions["completed"]) / total if total > 0 else 0
        
        return {
            "preferred_category": top_category,
            "preferred_difficulty": top_difficulty,
            "acceptance_rate": acceptance_rate,
            "total_interactions": total
        }
