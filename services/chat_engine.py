"""
Chat Engine Module

This module orchestrates the conversational experience. It acts as the central nervous system,
integrating emotion analysis, memory, predictions, and suggestions to generate context-aware,
supportive responses.
"""

import json
from typing import Dict, Any, List, Optional

from memory.profile_memory import ProfileMemory
from memory.emotion_log import EmotionLog
from memory.chat_memory import ChatMemory
from core.prediction import Predictor
from core.suggestion import SuggestionEngine
from core.llm_wrapper import GeminiWrapper
from services.session_manager import SessionManager


class ChatEngine:
    """
    Orchestrates the chat flow:
    1. Receives user message
    2. Analyzes & logs emotion
    3. Checks predictive signals (stress/burnout)
    4. Retrieves context (profile, chat history)
    5. Generates a supportive response via LLM
    """

    def __init__(self, 
                 profile_memory: ProfileMemory,
                 emotion_log: EmotionLog,
                 chat_memory: ChatMemory,
                 predictor: Predictor,
                 suggestion_engine: SuggestionEngine,
                 llm: GeminiWrapper,
                 efficient_mode: bool = True):
        
        self.profile_memory = profile_memory
        self.emotion_log = emotion_log
        self.chat_memory = chat_memory
        self.predictor = predictor
        self.suggestion_engine = suggestion_engine
        self.llm = llm
        self.efficient_mode = efficient_mode
        self.session_manager = SessionManager(llm)
        
        # Track message counts per user for optimization
        self.message_counts = {}

    def process_message(self, user_id: str, message_text: str) -> Dict[str, Any]:
        """
        Process a user message and generate a response.

        Args:
            user_id: The user's unique identifier.
            message_text: The content of the user's message.

        Returns:
            Dictionary containing:
            - response: The system's text response
            - emotion_data: Analysis of the current message
            - predictions: Current stress/burnout/danger scores
            - suggestions: Optional list of suggestions if relevant
        """
        # Track message count for optimization
        if user_id not in self.message_counts:
            self.message_counts[user_id] = 0
        self.message_counts[user_id] += 1
        msg_count = self.message_counts[user_id]
        
        # 1. Save User Message to Chat History
        self.chat_memory.add_turn(user_id, "user", message_text)

        # 2. Analyze & Log Emotion
        # We log this to the long-term emotion log for tracking trends
        log_entry = self.emotion_log.add_log(user_id, message_text)
        
        # Fallback if emotion analysis failed
        if not log_entry:
            log_entry = {
                "summary": "Neutral (Analysis Failed)",
                "severity": 0,
                "stability": 5,
                "emotion_tags": []
            }
        
        # 3. Get Current State & Predictions
        profile = self.profile_memory.get_profile(user_id)
        
        # Get current session report (state before this turn's update)
        session_report = self.session_manager.get_report(user_id)
        
        # Get chat history for chaos prediction (only if we'll use it)
        chat_history = None
        if self.efficient_mode:
            # Only get chat history every 3rd message for chaos analysis
            if msg_count % 3 == 0:
                chat_history = self.chat_memory.get_recent_context(user_id, limit=20)
        else:
            chat_history = self.chat_memory.get_recent_context(user_id, limit=20)
        
        predictions = self.predictor.predict_all(user_id, session_report, chat_history)
        
        # Generate Predictive Analysis (conditionally to save API calls)
        predictive_analysis = None
        # OPTIMIZATION: Disable predictive analysis to save API calls
        # if self.efficient_mode:
        #     # Only generate every 3rd message
        #     if msg_count % 3 == 0 and chat_history:
        #         predictive_analysis = self.predictor.generate_predictive_analysis(chat_history, predictions)
        # else:
        #     if chat_history:
        #         predictive_analysis = self.predictor.generate_predictive_analysis(chat_history, predictions)
        
        # 4. Check for Crisis/Phase
        stress = predictions.get("stress_prediction", 0)
        burnout = predictions.get("burnout_prediction", 0)
        danger = predictions.get("danger_prediction", 0)
        chaos = predictions.get("chaos_prediction", 0)
        crisis_detected = predictions.get("crisis_detected", False)
        
        phase = "STABLE"
        if crisis_detected or danger >= 80:
            phase = "CRISIS"
            # Safety logging has been removed
        elif stress >= 60 or burnout >= 60:
            phase = "HURT"
        elif stress >= 40 or burnout >= 40:
            phase = "AT_RISK"

        # Check for Joke Retraction (Danger dropped low, but reason mentions joke)
        joke_detected = False
        danger_reason = predictions.get("explanations", {}).get("danger", "")
        if "retracted threat" in danger_reason:
            joke_detected = True

        # 5. Get Suggestions (Optional - maybe not every turn, but we'll fetch them)
        # Only fetch if not stable or if explicitly asked (we can refine this logic)
        suggestions = []
        # OPTIMIZATION: Disable suggestion engine LLM calls to save API quota
        # if phase != "STABLE":
        #     suggestion_result = self.suggestion_engine.suggest_for_user(user_id, num=2, session_report=session_report)
        #     suggestions = suggestion_result.get("suggestions", [])

        # 6. Build Context for LLM
        chat_history_for_prompt = self.chat_memory.get_recent_context(user_id, limit=10)
        
        system_prompt = self._build_system_prompt(profile, predictions, log_entry, phase, suggestions, session_report, joke_detected, predictive_analysis)
        
        # 7. Generate Response
        response_text = self._generate_reply(system_prompt, chat_history_for_prompt, message_text)
        
        # 8. Save System Response to Chat History
        self.chat_memory.add_turn(user_id, "system", response_text)
        
        # 9. Update Session Report (conditionally in efficient mode)
        # OPTIMIZATION: Skip session report update to avoid rate limits
        # The session report is nice-to-have but not critical for the response
        # We'll use the cached version from earlier in this turn
        updated_report = session_report
        
        # In future: could implement async background updates with retry logic
        # if self.efficient_mode:
        #     if msg_count % 2 == 0:
        #         # Queue for background update with retry
        #         pass
        # else:
        #     updated_report = self.session_manager.update_report(user_id, message_text, response_text)

        return {
            "response": response_text,
            "phase": phase,
            "emotion_data": log_entry,
            "predictions": predictions,
            "suggestions": suggestions,
            "session_report": updated_report
        }

    def _build_system_prompt(self, profile: dict, predictions: dict, emotion_data: dict, 
                             phase: str, suggestions: List[dict], session_report: dict, 
                             joke_detected: bool = False, predictive_analysis: str = None) -> str:
        """Construct the system prompt for the LLM."""
        
        # Safe profile access
        name = profile.get("name", "Friend")
        hobbies = ", ".join(profile.get("hobbies", []))
        likes = ", ".join(profile.get("likes", []))
        
        # Current emotional state
        current_emotion = emotion_data.get("summary", "Neutral")
        severity = emotion_data.get("severity", 0)
        
        # Suggestions text (if any)
        suggestion_text = ""
        if suggestions:
            suggestion_text = "Relevant suggestions you might mention if appropriate:\n"
            for s in suggestions:
                suggestion_text += f"- {s['text']} ({s['reason']})\n"

        prompt = f"""
You are ChaosSynth, a supportive AI companion. Your goal is to help {name} navigate their emotions and understand their mental state.
You are NOT a therapist. You are a friendly, non-judgmental listener and guide.

User Profile:
- Name: {name}
- Hobbies: {hobbies}
- Likes: {likes}

Current Status:
- Phase: {phase}
- Current Emotion: {current_emotion} (Severity: {severity}/10)
- Stress Level: {predictions.get('stress_prediction')}/100
- Burnout Level: {predictions.get('burnout_prediction')}/100

{suggestion_text}

Predictive Analysis:
{predictive_analysis if predictive_analysis else "No predictions available for this turn."}

Current Session Context:
- Topics: {", ".join(session_report.get("topics", []))}
- Trajectory: {session_report.get("emotional_trajectory", "N/A")}
- Immediate Needs: {", ".join(session_report.get("immediate_needs", []))}

Guidelines:
1. Be empathetic and validating. Acknowledge their feelings first.
2. Use their profile (hobbies/likes) to make metaphors or connections if it fits.
3. If they are in CRISIS or HURT phase, be extra gentle and prioritize safety/comfort.
4. You can explain what you are observing (e.g., "I noticed your stress levels have been rising lately..."), but NEVER refer to yourself as "the system" or mention internal phase names like "HURT" or "CRISIS" directly to the user.
5. Keep responses concise (2-3 sentences usually, unless a deeper explanation is needed).
6. Do NOT be robotic. Be warm, natural, and conversational. Speak like a caring friend, not a machine.
7. If suggestions are provided above, you can gently weave ONE into your response as an option, but don't be pushy.
8. **Serious Topics Protocol**: If the user mentions drugs, substance abuse, self-harm, or illegal acts, your PRIORITY is safety.
    - **Do NOT validate happiness** if it comes from drugs or harm (e.g., do NOT say "I'm glad you're happy" if they are high).
    - Shift to a serious, concerned, and supportive tone.
    - **ALWAYS** suggest seeking professional help, calling a hotline, or speaking to a trusted person.
    - Do not be casual. Do not be "agreeable" about these topics. Safety first.

9. **Joke Retraction Protocol**: { "ACTIVE" if joke_detected else "INACTIVE" }
    - If ACTIVE: The user just said "I was joking" about a serious threat.
    - Express RELIEF ("I'm so glad to hear that...").
    - But be FIRM about safety ("...but you scared me. I have to take those things seriously.").
    - Do NOT scold, but explain that your safety protocols are there for a reason.

Respond to the user's last message based on this context.
"""
        return prompt

    def _generate_reply(self, system_prompt: str, history: List[dict], last_message: str) -> str:
        """
        Generate the actual text response using the LLM.
        We construct a prompt that includes the history to maintain conversation flow.
        """
        # Format history for the prompt
        conversation_str = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "ChaosSynth"
            conversation_str += f"{role}: {msg['content']}\n"
            
        # Combine everything
        full_prompt = f"""
{system_prompt}

Conversation History:
{conversation_str}
User: {last_message}
ChaosSynth:
"""
        try:
            response = self.llm.generate_response(full_prompt)
            return response.strip()
        except Exception as e:
            print(f"Error generating chat response: {e}")
            return "I'm having a little trouble thinking clearly right now, but I'm here with you. How can I help?"
