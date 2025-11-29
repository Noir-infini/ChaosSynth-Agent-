"""
Emotion Log Module

This module records the user's daily emotional messages and stores them as timeline entries.
It integrates with the LLM wrapper to analyze emotions and uses the ProfileMemory
system for storage.
"""

import datetime
from typing import List, Dict, Optional, Any
from memory.profile_memory import ProfileMemory
from core.llm_wrapper import GeminiWrapper

class EmotionLog:
    """
    Manages emotional logs for users.
    
    Records emotional messages, analyzes them using Gemini, and stores them
    in the user's profile JSON file under a "logs" section.
    """

    def __init__(self):
        """Initialize EmotionLog with dependencies."""
        self.profile_memory = ProfileMemory()
        self.llm = GeminiWrapper()

    def add_log(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze text and add a new emotion log entry.
        
        Calls the LLM to analyze the emotion of the text, creates a structured
        log entry, and appends it to the user's profile.

        Args:
            user_id: The user's unique identifier.
            text: The text content to analyze and log.

        Returns:
            The created log entry with analysis results, or None if profile doesn't exist.
            Includes 'crisis_detected': True if severity >= 8 or specific tags are present.
        """
        # Check if profile exists - if not, do nothing as per requirements
        if not self.profile_memory.profile_exists(user_id):
            return None

        # Optimization: Skip LLM analysis for very short messages (likely greetings/commands)
        # unless they contain specific trigger words
        word_count = len(text.split())
        trigger_words = ["help", "die", "kill", "hurt", "sad", "bad", "depressed", "anxious", "scared", "afraid"]
        has_trigger = any(w in text.lower() for w in trigger_words)
        
        if word_count < 4 and not has_trigger:
            # Create a default neutral entry without API call
            timestamp = datetime.datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "raw_text": text,
                "emotion_tags": [],
                "severity": 0.0,
                "stability": 5.0,
                "summary": "Neutral (Short Input)"
            }
            
            # Update profile
            self.profile_memory.update_profile(user_id, {"logs": [log_entry]})
            return log_entry

        # Analyze emotion using LLM
        try:
            analysis = self.llm.analyze_emotion(text)
        except Exception as e:
            # If analysis fails, we cannot create a proper log entry
            print(f"Error analyzing emotion: {e}")
            return None

        # Create log entry
        timestamp = datetime.datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "raw_text": text,
            "emotion_tags": analysis.get("emotion_tags", []),
            "severity": analysis.get("severity", 0.0),
            "stability": analysis.get("stability", 0.0),
            "summary": analysis.get("summary", "")
        }

        # Update profile
        # We wrap the entry in a list for the 'logs' key.
        # ProfileMemory.update_profile handles appending to lists.
        self.profile_memory.update_profile(user_id, {"logs": [log_entry]})

        # Check for crisis (Optional enhancement)
        # Note: We return a copy with the flag, but don't save the flag to disk
        result_entry = log_entry.copy()
        
        is_crisis = False
        if result_entry["severity"] >= 8.0:
            is_crisis = True
        
        crisis_keywords = ["suicidal", "self-harm"]
        for tag in result_entry["emotion_tags"]:
            if isinstance(tag, str) and tag.lower() in crisis_keywords:
                is_crisis = True
                break
        
        if is_crisis:
            result_entry["crisis_detected"] = True

        return result_entry

    def get_recent_logs(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get logs from the last N days.

        Args:
            user_id: The user's unique identifier.
            days: Number of days to look back.

        Returns:
            List of log entries within the specified timeframe.
        """
        profile = self.profile_memory.get_profile(user_id)
        if not profile or "logs" not in profile:
            return []

        logs = profile["logs"]
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        recent_logs = []
        for log in logs:
            try:
                # Parse ISO timestamp
                log_time = datetime.datetime.fromisoformat(log["timestamp"])
                if log_time >= cutoff_date:
                    recent_logs.append(log)
            except (ValueError, KeyError):
                continue

        return recent_logs

    def get_last_log(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent log entry.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The last log entry or None if no logs exist.
        """
        profile = self.profile_memory.get_profile(user_id)
        if not profile or "logs" not in profile or not profile["logs"]:
            return None

        return profile["logs"][-1]
