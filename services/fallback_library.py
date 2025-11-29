"""
Fallback Library Module

Provides fallback suggestions and templates for the SuggestionEngine when the LLM is unavailable
or fails to generate valid suggestions. Includes crisis resources and phase-appropriate activities.
"""

import uuid
from typing import List, Dict, Any

def get_fallback_suggestions(phase: str, num: int = 3) -> List[Dict[str, Any]]:
    """
    Get fallback suggestions based on the user's phase.
    
    Args:
        phase: The user's current phase (CRISIS, HURT, AT_RISK, STABLE).
        num: Number of suggestions to return.
        
    Returns:
        List of suggestion dictionaries.
    """
    suggestions = []
    
    if phase == "CRISIS":
        suggestions = [
            {
                "text": "Contact a crisis hotline or trusted person.",
                "reason": "Connecting with support is crucial right now.",
                "permission_prompt": "Would you be willing to make a call?",
                "difficulty": "hard",
                "category": "social",
                "meta": {"tied_to": "danger"}
            },
            {
                "text": "Practice 4-7-8 breathing.",
                "reason": "Helps calm the nervous system immediately.",
                "permission_prompt": "Can we try breathing together for a moment?",
                "difficulty": "very_easy",
                "category": "comfort",
                "meta": {"tied_to": "stress"}
            },
            {
                "text": "Ground yourself: Name 5 things you see.",
                "reason": "Brings focus back to the present moment.",
                "permission_prompt": "Would you like to try a quick grounding exercise?",
                "difficulty": "very_easy",
                "category": "comfort",
                "meta": {"tied_to": "stress"}
            }
        ]
    elif phase == "HURT":
        suggestions = [
            {
                "text": "Take a gentle 5-minute walk.",
                "reason": "Movement helps process emotions.",
                "permission_prompt": "Do you feel up for a short walk?",
                "difficulty": "easy",
                "category": "physical",
                "meta": {"tied_to": "burnout"}
            },
            {
                "text": "Listen to a comforting song.",
                "reason": "Music can soothe and shift mood.",
                "permission_prompt": "Would you like to put on some music?",
                "difficulty": "very_easy",
                "category": "comfort",
                "meta": {"tied_to": "stress"}
            },
            {
                "text": "Write down one thing on your mind.",
                "reason": "Getting thoughts out can reduce mental load.",
                "permission_prompt": "Would journaling a few sentences help?",
                "difficulty": "easy",
                "category": "reflective",
                "meta": {"tied_to": "stress"}
            }
        ]
    elif phase == "AT_RISK":
        suggestions = [
            {
                "text": "Take a 15-minute break from screens.",
                "reason": "Reduces digital fatigue and stress.",
                "permission_prompt": "Could you take a short break now?",
                "difficulty": "easy",
                "category": "comfort",
                "meta": {"tied_to": "burnout"}
            },
            {
                "text": "Drink a glass of water.",
                "reason": "Hydration supports physical and mental regulation.",
                "permission_prompt": "Would you like to grab some water?",
                "difficulty": "very_easy",
                "category": "physical",
                "meta": {"tied_to": "burnout"}
            },
            {
                "text": "Connect with a friend.",
                "reason": "Social connection buffers against stress.",
                "permission_prompt": "Is there someone you'd like to message?",
                "difficulty": "medium",
                "category": "social",
                "meta": {"tied_to": "stress"}
            }
        ]
    else: # STABLE
        suggestions = [
            {
                "text": "Reflect on a recent win.",
                "reason": "Reinforces positive feelings and progress.",
                "permission_prompt": "Would you like to note a recent success?",
                "difficulty": "easy",
                "category": "reflective",
                "meta": {"tied_to": "profile"}
            },
            {
                "text": "Try a new creative activity.",
                "reason": "Stimulates growth and engagement.",
                "permission_prompt": "Are you interested in trying something new?",
                "difficulty": "medium",
                "category": "creative",
                "meta": {"tied_to": "profile"}
            },
            {
                "text": "Plan a small treat for yourself.",
                "reason": "Self-care maintains stability.",
                "permission_prompt": "What small treat would you enjoy?",
                "difficulty": "easy",
                "category": "comfort",
                "meta": {"tied_to": "profile"}
            }
        ]
    
    # Ensure we have enough suggestions by cycling if needed
    while len(suggestions) < num:
        suggestions.append(suggestions[len(suggestions) % 3])
        
    # Trim to requested number
    result = suggestions[:num]
    
    # Add IDs and structure
    final_suggestions = []
    for s in result:
        s_copy = s.copy()
        s_copy["id"] = str(uuid.uuid4())
        # Ensure meta exists
        if "meta" not in s_copy:
            s_copy["meta"] = {"tied_to": "general"}
        final_suggestions.append(s_copy)
        
    return final_suggestions
