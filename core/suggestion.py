"""
Suggestion Engine Module

Generates gentle, phase-appropriate suggestions for users based on their emotional state,
profile, and predictive signals. Uses LLM for friendly wording with robust fallbacks.
"""

import uuid
import datetime
import json
from typing import List, Dict, Any, Optional

from memory.profile_memory import ProfileMemory
from memory.emotion_log import EmotionLog
from core.prediction import Predictor
from core.llm_wrapper import GeminiWrapper
from services.fallback_library import get_fallback_suggestions
from services.feedback_loop import FeedbackLoop

class SuggestionEngine:
    """
    Generates supportive suggestions based on user data and predictions.
    """

    def __init__(self, profile_memory: ProfileMemory, emotion_log: EmotionLog,
                 predictor: Predictor, llm: GeminiWrapper, feedback_loop: FeedbackLoop, config: dict = None):
        """
        Initialize the SuggestionEngine.

        Args:
            profile_memory: Instance of ProfileMemory.
            emotion_log: Instance of EmotionLog.
            predictor: Instance of Predictor.
            llm: Instance of GeminiWrapper.
            feedback_loop: Instance of FeedbackLoop.
            config: Optional configuration dictionary.
        """
        self.profile_memory = profile_memory
        self.emotion_log = emotion_log
        self.predictor = predictor
        self.llm = llm
        self.feedback_loop = feedback_loop
        self.config = config or {}
        self.mascot_asset = "/mnt/data/a9fa5d35-d685-49d5-9e50-ed648825b2c2.png"

    def suggest_for_user(self, user_id: str, num: int = 3, session_report: Optional[dict] = None) -> Dict[str, Any]:
        """
        Generate suggestions for a user.

        Args:
            user_id: The user's unique identifier.
            num: Number of suggestions to generate.

        Returns:
            Dictionary containing phase, predictions, suggestions, and metadata.
        """
        # 1. Load Data
        profile = self.profile_memory.get_profile(user_id)
        recent_logs_7 = self.emotion_log.get_recent_logs(user_id, days=7)
        recent_logs_30 = self.emotion_log.get_recent_logs(user_id, days=30)
        
        # Get User Preferences from Feedback Loop
        preferences = self.feedback_loop.get_user_preferences(user_id)
        
        # 2. Get Predictions
        predictions = self.predictor.predict_all(user_id)
        
        stress = predictions.get("stress_prediction", 0)
        burnout = predictions.get("burnout_prediction", 0)
        danger = predictions.get("danger_prediction", 0)
        crisis_detected = predictions.get("crisis_detected", False)

        # 3. Determine Phase
        phase = "STABLE"
        if crisis_detected or danger >= 80:
            phase = "CRISIS"
        elif stress >= 60 or burnout >= 60 or danger >= 60:
            phase = "HURT"
        elif stress >= 40 or burnout >= 40 or danger >= 40:
            phase = "AT_RISK"
        
        # 4. Build Context Summary
        context = self._build_context_summary(profile, recent_logs_7, predictions)
        
        # 5. Generate Suggestions (LLM or Fallback)
        suggestions = []
        used_fallback = False
        
        # Skip LLM for CRISIS to ensure absolute safety and speed, or if LLM fails
        if phase == "CRISIS":
            suggestions = get_fallback_suggestions(phase, num)
            used_fallback = True
        else:
            try:
                suggestions = self._generate_llm_suggestions(context, phase, profile, num, predictions, preferences)
                if not suggestions:
                    suggestions = get_fallback_suggestions(phase, num)
                    used_fallback = True
            except Exception as e:
                print(f"LLM Suggestion Error: {e}")
                suggestions = get_fallback_suggestions(phase, num)
                used_fallback = True

        # 6. Validate and Enforce Safety
        valid_suggestions = self._validate_suggestions(suggestions, phase, predictions)
        
        # If validation stripped too many, fill with fallbacks
        if len(valid_suggestions) < num:
            fallbacks = get_fallback_suggestions(phase, num)
            # Add fallbacks that aren't duplicates (simple check by text)
            existing_texts = {s["text"] for s in valid_suggestions}
            for fb in fallbacks:
                if len(valid_suggestions) >= num:
                    break
                if fb["text"] not in existing_texts:
                    valid_suggestions.append(fb)

        # 7. Construct Response
        response = {
            "phase": phase,
            "predictions": {
                "stress": stress,
                "burnout": burnout,
                "danger": danger
            },
            "explanations": predictions.get("explanations", {}),
            "suggestions": valid_suggestions,
            "urgent": (phase == "CRISIS"),
            "timestamp": datetime.datetime.now().isoformat(),
            "mascot_asset": self.mascot_asset
        }
        
        return response

    def _build_context_summary(self, user_profile: dict, recent_logs: list, predictions: dict) -> str:
        """
        Build a compact, PII-masked summary for the LLM.
        """
        # Mask name
        safe_profile = user_profile.copy() if user_profile else {}
        if "name" in safe_profile:
            safe_profile["name"] = "User"
            
        # Summarize logs with ACTUAL user messages (last 5 for better context)
        log_summary = ""
        for log in recent_logs[-5:]:
            raw_text = log.get('raw_text', '')
            severity = log.get('severity', 0)
            summary = log.get('summary', 'N/A')
            # Include the actual text so LLM can see what user said
            if raw_text:
                log_summary += f"- User said: \"{raw_text}\" → {summary} (Severity: {severity}/10)\n"
            else:
                log_summary += f"- Mood: {summary} (Severity: {severity}/10)\n"
            
        summary = f"""
        User Profile:
        - Hobbies: {', '.join(safe_profile.get('hobbies', [])[:3])}
        - Goals: {', '.join(safe_profile.get('goals', [])[:2])}
        
        Recent User Messages & Emotional State:
        {log_summary}
        
        Predictions:
        - Stress: {predictions.get('stress_prediction')}/100
        - Burnout: {predictions.get('burnout_prediction')}/100
        - Danger: {predictions.get('danger_prediction')}/100
        """
        return summary[:2000] # Increased limit to include raw messages

    def _generate_llm_suggestions(self, context: str, phase: str, profile: dict, num: int, predictions: dict, preferences: dict) -> List[dict]:
        """
        Call LLM to generate suggestions.
        """
        pref_text = ""
        if preferences.get("preferred_category"):
            pref_text += f"- User prefers '{preferences['preferred_category']}' activities.\n"
        if preferences.get("preferred_difficulty"):
            pref_text += f"- User prefers '{preferences['preferred_difficulty']}' difficulty tasks.\n"
            
        prompt = f"""
        Generate {num} gentle, supportive, and ACTIONABLE suggestions for a user in the '{phase}' phase.
        
        Context:
        {context}
        
        User Preferences (Try to align with these if appropriate):
        {pref_text}
        
        CRITICAL INSTRUCTIONS:
        1. READ THE USER'S ACTUAL MESSAGES CAREFULLY. If they mention specific problems (bullying, family issues, work stress, etc.), 
           your suggestions MUST address those specific situations, not just generic self-care.
        2. For serious situations (bullying, harassment, family conflict), suggest:
           - Talking to specific trusted adults (school counselor, therapist, other family member)
           - Documenting incidents if relevant
           - Reaching out to helplines or support services
           - Creating safety plans if needed
        3. For high stress/danger situations, prioritize PRACTICAL ACTION over passive comfort activities.
        4. Suggestions must be safe, non-judgmental, and optional.
        5. No medical or legal advice, but DO suggest seeking professional help when appropriate.
        6. Format as JSON list of objects with keys: text, reason, permission_prompt, difficulty, category, meta.
        7. 'difficulty' must be: very_easy, easy, medium, or hard.
        8. 'category' must be: comfort, creative, physical, social, or reflective.
        9. 'meta' must contain 'tied_to' (stress, burnout, danger, or profile).
        10. KEEP IT CONCISE: 'text' must be under 280 characters, 'reason' under 180 characters.
        
        Return ONLY valid JSON.
        """
        
        try:
            response_text = self.llm.generate_response(prompt)
            
            # Clean markdown
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
                
            data = json.loads(cleaned)
            
            if isinstance(data, list):
                # Post-process to add IDs and snapshots if missing
                for item in data:
                    if "id" not in item:
                        item["id"] = str(uuid.uuid4())
                    if "meta" not in item:
                        item["meta"] = {"tied_to": "general"}
                    
                    # Add prediction snapshot
                    item["meta"]["prediction_snapshot"] = {
                        "stress": predictions.get("stress_prediction", 0),
                        "burnout": predictions.get("burnout_prediction", 0),
                        "danger": predictions.get("danger_prediction", 0)
                    }
                return data
            return []
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def _validate_suggestions(self, suggestions: List[dict], phase: str, predictions: dict) -> List[dict]:
        """
        Validate suggestions against safety rules and schema.
        """
        valid = []
        
        for i, s in enumerate(suggestions):
            # Schema check
            required_keys = ["text", "reason", "permission_prompt", "difficulty", "category"]
            if not all(key in s for key in required_keys):
                continue
                
            # Length check (increased limits to allow contextual advice)
            text_len = len(s["text"])
            reason_len = len(s["reason"])
            if text_len > 300 or reason_len > 200:
                continue
                
            # Safety check for CRISIS/High Danger
            if phase == "CRISIS":
                # In crisis, reject anything 'hard' or 'creative' that might be taxing
                if s["difficulty"] == "hard" and "hotline" not in s["text"].lower() and "help" not in s["text"].lower():
                    continue
                if s["category"] == "creative":
                    continue
            
            # Ensure ID exists
            if "id" not in s:
                s["id"] = str(uuid.uuid4())
                
            # Ensure meta snapshot exists
            if "meta" not in s:
                s["meta"] = {"tied_to": "general"}
            
            if "prediction_snapshot" not in s["meta"]:
                 s["meta"]["prediction_snapshot"] = {
                        "stress": predictions.get("stress_prediction", 0),
                        "burnout": predictions.get("burnout_prediction", 0),
                        "danger": predictions.get("danger_prediction", 0)
                    }

            valid.append(s)
            
        return valid

if __name__ == "__main__":
    print("Running SuggestionEngine test...")
    
    # Try to use real LLM if API key is available
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    llm_instance = None
    
    try:
        if os.getenv("GEMINI_API_KEY"):
            print("Using REAL Gemini API for suggestions...")
            llm_instance = GeminiWrapper()
        else:
            print("No API key found. Using MOCK LLM...")
    except Exception as e:
        print(f"Failed to init real LLM: {e}. Using MOCK LLM...")

    if not llm_instance:
        # Mock LLM wrapper for testing
        class MockLLM:
            def generate_response(self, prompt):
                import json
                return json.dumps([
                    {
                        "text": "Try taking a 5-minute walk outside",
                        "reason": "Physical movement can help reduce stress",
                        "permission_prompt": "Would you like to take a short walk?",
                        "difficulty": "easy",
                        "category": "physical"
                    },
                    {
                        "text": "Write down three things you're grateful for",
                        "reason": "Gratitude practice can shift perspective",
                        "permission_prompt": "Want to try a quick gratitude exercise?",
                        "difficulty": "very_easy",
                        "category": "reflective"
                    }
                ])
        llm_instance = MockLLM()
    
    # Initialize all required components
    print("Initializing components...")
    
    # Create test instances
    from memory.chat_memory import ChatMemory
    
    profile_mem = ProfileMemory()
    emotion_log = EmotionLog()
    chat_memory = ChatMemory()
    predictor = Predictor(profile_mem, emotion_log, llm_instance)
    feedback_loop = FeedbackLoop()
    
    # Use existing profile or create if doesn't exist
    test_user_id = "test_user"
    if not profile_mem.profile_exists(test_user_id):
        print("Creating new test profile...")
        profile_mem.create_profile(
            user_id=test_user_id,
            profile_data={
                "name": "Test User",
                "hobbies": ["coding", "reading", "music"],
                "goals": ["reduce stress", "improve focus"],
                "fears": ["deadlines", "social pressure"]
            }
        )
    else:
        print("Using existing test_user profile...")
    
    # Use existing chat history from data files if available
    print("Loading existing chat history from data files...")
    existing_chat = chat_memory.get_recent_context(test_user_id, limit=50)
    existing_logs = emotion_log.get_recent_logs(test_user_id, days=30)
    
    if existing_chat:
        print(f"Found {len(existing_chat)} existing chat messages")
    else:
        print("No existing chat history found - will use clean profile only")
    
    if existing_logs:
        print(f"Found {len(existing_logs)} existing emotion logs")
    else:
        print("No existing emotion logs found")

    
    # Initialize SuggestionEngine
    suggestion_engine = SuggestionEngine(
        profile_memory=profile_mem,
        emotion_log=emotion_log,
        predictor=predictor,
        llm=llm_instance,
        feedback_loop=feedback_loop
    )
    
    # Generate suggestions
    print(f"\nGenerating suggestions for user: {test_user_id}...")
    result = suggestion_engine.suggest_for_user(test_user_id, num=3)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"Phase: {result['phase']}")
    print(f"Urgent: {result['urgent']}")
    print(f"\nPredictions:")
    print(f"  - Stress: {result['predictions']['stress']}/100")
    print(f"  - Burnout: {result['predictions']['burnout']}/100")
    print(f"  - Danger: {result['predictions']['danger']}/100")
    
    print(f"\n{'='*60}")
    print(f"Suggestions ({len(result['suggestions'])}):")
    print(f"{'='*60}")
    
    for i, suggestion in enumerate(result['suggestions'], 1):
        print(f"\n[{i}] {suggestion['text']}")
        print(f"    Reason: {suggestion['reason']}")
        print(f"    Difficulty: {suggestion['difficulty']}")
        print(f"    Category: {suggestion['category']}")
        print(f"    Permission: {suggestion['permission_prompt']}")
    
    print(f"\n{'='*60}")
    print(f"Timestamp: {result['timestamp']}")
