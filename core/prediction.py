"""
Prediction Module

This module computes predictive signals (stress, burnout, danger) based on user emotional logs.
It uses heuristics for deterministic scoring and LLM for generating human-readable explanations.

Dependencies:
- profile_memory.ProfileMemory
- emotion_log.EmotionLog
- llm_wrapper.GeminiWrapper
"""

import datetime
import statistics
from typing import List, Dict, Tuple, Any, Optional
from memory.profile_memory import ProfileMemory
from memory.emotion_log import EmotionLog
from core.llm_wrapper import GeminiWrapper
from core.chaos import ChaosPredictor

# --- Configurable Thresholds and Weights ---

# Stress Configuration
STRESS_BASE_SCALE = 9.0       # Multiplier for avg severity (0-10 -> 0-90)
STRESS_VOLATILITY_WEIGHT = 10.0 # Multiplier for stddev
STRESS_TAG_PENALTY = 5        # Points per negative tag occurrence
STRESS_CONSECUTIVE_THRESHOLD = 6.0
STRESS_CONSECUTIVE_DAYS = 3
STRESS_CONSECUTIVE_PENALTY = 15
STRESS_TAGS = ["anxious", "stressed", "overwhelmed", "panic", "worry"]

# Burnout Configuration
BURNOUT_TAGS = ["tired", "exhausted", "drained", "burnout", "fatigue", "empty"]
BURNOUT_WORKLOAD_KEYWORDS = ["work", "job", "deadline", "busy", "overworked", "study", "school"]
BURNOUT_TAG_RATIO_WEIGHT = 50 # If 100% of logs have burnout tags, add 50 points
BURNOUT_TREND_PENALTY = 20    # If stability declining and severity rising

# Danger Configuration
DANGER_CRISIS_KEYWORDS = ["suicide", "suicidal", "kill myself", "hurt myself", "end it", "die", "death", "self-harm", "drugs", "overdose", "substance abuse", "pills"]
DANGER_HOPELESS_TAGS = ["hopeless", "despair", "worthless", "trapped"]
DANGER_SEVERITY_SPIKE_THRESHOLD = 8.0
DANGER_SPIKE_WEIGHT = 20
DANGER_TAG_WEIGHT = 15

class Predictor:
    """
    Computes stress, burnout, and danger predictions from user data.
    """

    def __init__(self, profile_memory: ProfileMemory, emotion_log: EmotionLog, llm: GeminiWrapper, config: dict = None):
        """
        Initialize the Predictor.

        Args:
            profile_memory: Instance of ProfileMemory.
            emotion_log: Instance of EmotionLog.
            llm: Instance of GeminiWrapper.
            config: Optional dictionary to override default thresholds/weights.
        """
        self.profile_memory = profile_memory
        self.emotion_log = emotion_log
        self.llm = llm
        self.config = config or {}
        self.chaos_predictor = ChaosPredictor(llm)

    def predict_all(self, user_id: str, session_report: Optional[dict] = None, chat_history: Optional[List[dict]] = None) -> Dict[str, Any]:
        """
        Compute all predictions for a user.
        
        Args:
            user_id: User ID
            session_report: Optional session report
            chat_history: Optional chat conversation history
        """
        # Get recent logs
        recent_logs_7 = self.emotion_log.get_recent_logs(user_id, days=7)
        recent_logs_30 = self.emotion_log.get_recent_logs(user_id, days=30)
        profile = self.profile_memory.get_profile(user_id)
        
        # If no data, return safe defaults
        if not recent_logs_7 and not recent_logs_30:
            return {
                "stress_prediction": 0,
                "burnout_prediction": 0,
                "danger_prediction": 0,
                "chaos_prediction": 0,
                "explanations": {
                    "stress": "No recent data.",
                    "burnout": "No recent data.",
                    "danger": "No recent data.",
                    "chaos": "No recent data."
                },
                "trend_summary": {
                    "7_day_trend": "stable",
                    "30_day_trend": "stable"
                },
                "crisis_detected": False
            }

        # Compute Scores
        stress_score, stress_reason = self.compute_stress(recent_logs_7)
        burnout_score, burnout_reason = self.compute_burnout(recent_logs_30, profile)
        danger_score, danger_reason, crisis_detected = self.compute_danger(recent_logs_30)
        
        # Compute Chaos (requires chat history)
        if chat_history:
            chaos_score, chaos_reason = self.chaos_predictor.compute_chaos(chat_history, recent_logs_30)
        else:
            chaos_score, chaos_reason = 0, "No conversation data available."
        
        # Compute Trends
        trends = self.compute_trend(recent_logs_30)

        # Generate Explanations (Try LLM, fallback to heuristic reasons)
        explanations = {
            "stress": stress_reason,
            "burnout": burnout_reason,
            "danger": danger_reason,
            "chaos": chaos_reason
        }
        
        # OPTIMIZATION: Skip LLM explanation enhancement to save API calls
        # Use heuristic reasons only (still accurate, just less detailed)
        # if recent_logs_7:
        #     try:
        #         llm_explanations = self._generate_llm_explanations(
        #             stress_score, burnout_score, danger_score, 
        #             stress_reason, burnout_reason, danger_reason,
        #             recent_logs_7
        #         )
        #         if llm_explanations:
        #             explanations = llm_explanations
        #     except Exception as e:
        #         # Silently fail back to heuristic reasons
        #         pass

        # Safety Override for Danger Explanation
        if crisis_detected:
            explanations["danger"] += " CRITICAL: Consider contacting a trusted person or a local crisis hotline; I am not a therapist."

        return {
            "stress_prediction": stress_score,
            "burnout_prediction": burnout_score,
            "danger_prediction": danger_score,
            "chaos_prediction": chaos_score,
            "explanations": explanations,
            "trend_summary": trends,
            "crisis_detected": crisis_detected
        }

    def compute_stress(self, recent_logs: List[dict]) -> Tuple[int, str]:
        """
        Compute stress score (0-100) based on recent logs (typically 7 days).
        """
        if not recent_logs:
            return 20, "Insufficient data for stress analysis."

        # 1. Average Severity
        severities = [log.get("severity", 0) for log in recent_logs]
        avg_severity = statistics.mean(severities)
        score = avg_severity * STRESS_BASE_SCALE

        # 2. Volatility (Standard Deviation)
        if len(severities) > 1:
            volatility = statistics.stdev(severities)
            score += volatility * STRESS_VOLATILITY_WEIGHT

        # 3. Negative Tags Frequency
        tag_count = 0
        for log in recent_logs:
            tags = log.get("emotion_tags", [])
            for tag in tags:
                if str(tag).lower() in STRESS_TAGS:
                    tag_count += 1
        score += tag_count * STRESS_TAG_PENALTY

        # 4. Consecutive High Severity
        consecutive_high = 0
        max_consecutive = 0
        # Sort by timestamp to ensure order
        sorted_logs = sorted(recent_logs, key=lambda x: x.get("timestamp", ""))
        
        for log in sorted_logs:
            if log.get("severity", 0) >= STRESS_CONSECUTIVE_THRESHOLD:
                consecutive_high += 1
            else:
                max_consecutive = max(max_consecutive, consecutive_high)
                consecutive_high = 0
        max_consecutive = max(max_consecutive, consecutive_high)

        if max_consecutive >= STRESS_CONSECUTIVE_DAYS:
            score += STRESS_CONSECUTIVE_PENALTY

        # Clamp and Reason
        score = min(100, max(0, int(score)))
        
        reason = f"Based on average severity of {avg_severity:.1f}/10"
        if max_consecutive >= STRESS_CONSECUTIVE_DAYS:
            reason += " and persistent high intensity."
        elif tag_count > 2:
            reason += " and frequent stress indicators."
        else:
            reason += "."

        return score, reason

    def compute_burnout(self, recent_logs: List[dict], profile: dict) -> Tuple[int, str]:
        """
        Compute burnout score (0-100) based on longer-term logs (30 days) and profile.
        """
        if not recent_logs:
            return 10, "Insufficient data for burnout analysis."

        score = 0.0
        
        # 1. Tag Ratio
        burnout_tag_count = 0
        total_logs = len(recent_logs)
        for log in recent_logs:
            tags = log.get("emotion_tags", [])
            for tag in tags:
                if str(tag).lower() in BURNOUT_TAGS:
                    burnout_tag_count += 1
                    break # Count at most once per log
        
        if total_logs > 0:
            ratio = burnout_tag_count / total_logs
            score += ratio * BURNOUT_TAG_RATIO_WEIGHT

        # 2. Trend Analysis (Declining Stability + Rising Severity)
        # Split into halves
        mid = total_logs // 2
        if mid > 0:
            sorted_logs = sorted(recent_logs, key=lambda x: x.get("timestamp", ""))
            first_half = sorted_logs[:mid]
            second_half = sorted_logs[mid:]
            
            avg_stab_1 = statistics.mean([l.get("stability", 5) for l in first_half])
            avg_stab_2 = statistics.mean([l.get("stability", 5) for l in second_half])
            
            avg_sev_1 = statistics.mean([l.get("severity", 0) for l in first_half])
            avg_sev_2 = statistics.mean([l.get("severity", 0) for l in second_half])
            
            if avg_stab_2 < avg_stab_1 and avg_sev_2 > avg_sev_1:
                score += BURNOUT_TREND_PENALTY

        # 3. Profile Workload Check
        # Since 'current_conflicts' is not in profile, check personal_notes
        notes = profile.get("personal_notes", "").lower()
        if any(kw in notes for kw in BURNOUT_WORKLOAD_KEYWORDS):
            score += 15

        # Clamp and Reason
        score = min(100, max(0, int(score)))
        
        reason = "Analysis of energy levels and stability trends."
        if score > 60:
            reason = "High indicators of exhaustion and declining stability detected."
        elif score > 30:
            reason = "Moderate signs of fatigue observed."

        return score, reason

    def compute_danger(self, recent_logs: List[dict]) -> Tuple[int, str, bool]:
        """
        Compute danger score and check for crisis keywords.
        """
        if not recent_logs:
            return 0, "No recent data.", False

        # Check for Joke Retraction (Auto-Recovery)
        # If the LATEST log says "joke", "kidding", etc., we override the danger score.
        latest_log = recent_logs[-1] if recent_logs else {}
        latest_text = latest_log.get("raw_text", "").lower()
        joke_keywords = ["joke", "joking", "kidding", "prank", "false alarm", "didn't mean it"]
        
        if any(kw in latest_text for kw in joke_keywords):
            # Override danger score
            return 20, "User retracted threat (stated it was a joke).", False

        score = 0.0
        crisis_detected = False
        reason = "No immediate risks detected."

        # 1. Explicit Keyword Search
        for log in recent_logs:
            text = log.get("raw_text", "").lower()
            tags = [str(t).lower() for t in log.get("emotion_tags", [])]
            
            # Check text and tags
            if any(kw in text for kw in DANGER_CRISIS_KEYWORDS) or \
               any(kw in tags for kw in DANGER_CRISIS_KEYWORDS):
                return 100, "Explicit crisis keywords detected in recent logs.", True

        # 2. Severity Spikes
        spike_count = sum(1 for l in recent_logs if l.get("severity", 0) >= DANGER_SEVERITY_SPIKE_THRESHOLD)
        score += spike_count * DANGER_SPIKE_WEIGHT

        # 3. Hopelessness Tags
        hopeless_count = 0
        for log in recent_logs:
            tags = [str(t).lower() for t in log.get("emotion_tags", [])]
            if any(t in DANGER_HOPELESS_TAGS for t in tags):
                hopeless_count += 1
        score += hopeless_count * DANGER_TAG_WEIGHT

        # Clamp
        score = min(100, max(0, int(score)))
        
        if score >= 80:
            crisis_detected = True
            reason = "Critical levels of distress and hopelessness detected."
        elif score > 40:
            reason = "Concerning spikes in severity and negative outlook."

        return score, reason, crisis_detected

    def generate_predictive_analysis(self, chat_history: List[dict], predictions: dict) -> str:
        """
        Generate forward-looking predictions based on conversation context.
        Analyzes what the user is discussing and predicts future consequences.
        
        Args:
            chat_history: Recent conversation history
            predictions: Current prediction scores
            
        Returns:
            Predictive analysis text
        """
        if not chat_history or len(chat_history) < 2:
            return "Not enough conversation data for predictive analysis."
        
        # Extract recent user messages
        user_messages = [turn.get("content", "") for turn in chat_history[-6:] if turn.get("role") == "user"]
        if not user_messages:
            return "No user messages to analyze."
        
        conversation_summary = "\n".join([f"- {msg}" for msg in user_messages[-3:]])
        
        # Get current scores
        stress = predictions.get("stress_prediction", 0)
        burnout = predictions.get("burnout_prediction", 0)
        danger = predictions.get("danger_prediction", 0)
        chaos = predictions.get("chaos_prediction", 0)
        
        try:
            prompt = f"""Based on this conversation, generate a brief predictive analysis of potential future consequences if current patterns continue.

Recent conversation:
{conversation_summary}

Current state:
- Stress: {stress}/100
- Burnout: {burnout}/100
- Danger: {danger}/100
- Chaos: {chaos}/100

Analyze the conversation for key themes (e.g., substance use, burnout, relationship issues, work stress, etc.) and predict SHORT-TERM (1-2 weeks) and LONG-TERM (1-3 months) consequences if this pattern continues.

Format:
SHORT-TERM: [2-3 specific consequences]
LONG-TERM: [2-3 specific consequences]

Keep it concise, specific, and relevant to what the user is actually discussing. If there are no concerning patterns, say "No significant risks detected."
"""
            
            response = self.llm.generate_response(prompt)
            return response.strip()
            
        except Exception as e:
            # Fallback to heuristic analysis
            if danger >= 70:
                return "SHORT-TERM: Immediate safety risk, potential for crisis escalation\nLONG-TERM: Serious mental health consequences if help is not sought"
            elif burnout >= 60:
                return "SHORT-TERM: Continued exhaustion, decreased performance\nLONG-TERM: Potential burnout, health issues, relationship strain"
            elif stress >= 60:
                return "SHORT-TERM: Increased anxiety, sleep issues\nLONG-TERM: Chronic stress, potential health problems"
            else:
                return "No significant risks detected based on current conversation."

    def compute_trend(self, recent_logs: List[dict]) -> dict:
        """
        Compute 7-day and 30-day trends.
        """
        def get_trend_str(logs):
            if not logs or len(logs) < 2:
                return "stable"
            
            sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", ""))
            mid = len(sorted_logs) // 2
            
            # Compare average severity
            first_half = [l.get("severity", 0) for l in sorted_logs[:mid]]
            second_half = [l.get("severity", 0) for l in sorted_logs[mid:]]
            
            avg_1 = statistics.mean(first_half)
            avg_2 = statistics.mean(second_half)
            
            diff = avg_2 - avg_1
            if diff > 1.5:
                return "declining" # Severity increasing = condition declining
            elif diff < -1.5:
                return "improving" # Severity decreasing = condition improving
            else:
                return "stable"

        # Filter for 7 days
        cutoff_7 = datetime.datetime.now() - datetime.timedelta(days=7)
        logs_7 = []
        for log in recent_logs:
            try:
                ts = datetime.datetime.fromisoformat(log.get("timestamp", ""))
                if ts >= cutoff_7:
                    logs_7.append(log)
            except:
                continue

        return {
            "7_day_trend": get_trend_str(logs_7),
            "30_day_trend": get_trend_str(recent_logs)
        }

    def _generate_llm_explanations(self, stress, burnout, danger, s_reason, b_reason, d_reason, logs) -> Optional[Dict[str, str]]:
        """
        Use LLM to generate friendlier explanations.
        """
        # Summarize last 3 logs for context
        log_summary = ""
        for log in logs[-3:]:
            log_summary += f"- {log.get('summary', 'No summary')}\n"

        prompt = f"""
        Based on these metrics and recent logs, write 3 short, one-line friendly explanations for a user's emotional state.
        
        Metrics:
        - Stress: {stress}/100 ({s_reason})
        - Burnout: {burnout}/100 ({b_reason})
        - Danger: {danger}/100 ({d_reason})
        
        Recent Log Summaries:
        {log_summary}
        
        Return ONLY a JSON object:
        {{
            "stress": "friendly one-line explanation",
            "burnout": "friendly one-line explanation",
            "danger": "friendly one-line explanation"
        }}
        """
        
        try:
            response = self.llm.generate_response(prompt)
            import json
            
            # Clean markdown
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
                
            return json.loads(cleaned)
        except:
            return None
