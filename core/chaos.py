"""
Chaos Prediction Module

This module analyzes the conversation flow and emotional patterns between the user and the AI
to determine a "Chaos Score". This score reflects the volatility, incoherence, or erratic nature
of the interaction.
"""

from typing import List, Tuple, Dict, Any, Optional
import statistics
from core.llm_wrapper import GeminiWrapper

class ChaosPredictor:
    """
    Computes chaos prediction based on chat history and emotional logs.
    """

    def __init__(self, llm: GeminiWrapper):
        """
        Initialize the ChaosPredictor.

        Args:
            llm: Instance of GeminiWrapper for potential advanced analysis.
        """
        self.llm = llm

    def compute_chaos(self, chat_history: List[dict], recent_logs: List[dict]) -> Tuple[int, str]:
        """
        Compute Chaos score based on conversation analysis.
        Analyzes the dialogue between user and AI for erratic patterns.
        
        Args:
            chat_history: List of chat turns (user/system messages)
            recent_logs: Emotion logs for supplementary analysis
            
        Returns:
            Tuple containing (chaos_score, reason)
        """
        if not chat_history or len(chat_history) < 4:
            return 0, "Not enough conversation data to determine chaos."

        # Extract only recent conversation (last 10 turns)
        recent_chat = chat_history[-10:]
        
        # === HEURISTIC ANALYSIS ===
        
        # 1. Topic Volatility (using Semantic Emotion Mapping)
        user_messages = [turn for turn in recent_chat if turn.get("role") == "user"]
        if len(user_messages) < 3:
            return 0, "Not enough user messages to determine chaos (need at least 3)."
        
        # Semantic mapping for emotion tags
        emotion_map = {
            "positive": ["joy", "happy", "happiness", "excited", "excitement", "love", "great", "amazing", "wonderful", "fantastic", "contentment", "well-being", "anticipation", "positive", "trust", "pride", "relief"],
            "negative": ["sad", "sadness", "angry", "anger", "hate", "terrible", "awful", "depressed", "depression", "miserable", "misery", "empty", "numb", "fear", "anxiety", "negative", "disgust", "shame", "guilt", "remorse"],
            "high_energy": ["excited", "excitement", "angry", "anger", "joy", "panic", "mania", "surprise", "fear", "anxiety"],
            "low_energy": ["sad", "sadness", "depressed", "depression", "bored", "boredom", "tired", "fatigue", "calm", "contentment", "relief"]
        }

        def get_base_emotions(tags):
            base_emotions = set()
            for tag in tags:
                tag_lower = str(tag).lower()
                for base, keywords in emotion_map.items():
                    if tag_lower in keywords:
                        base_emotions.add(base)
            return base_emotions

        # Get corresponding emotion logs for user messages
        topic_changes = 0
        prev_base_emotions = set()
        
        for msg in user_messages[-5:]:  # Last 5 user messages
            # Find matching log by timestamp proximity or content
            msg_text = msg.get("content", "")
            matching_log = None
            for log in recent_logs[-10:]:
                if log.get("raw_text", "") == msg_text:
                    matching_log = log
                    break
            
            if matching_log:
                current_tags = matching_log.get("emotion_tags", [])
                current_base_emotions = get_base_emotions(current_tags)
                
                # If we have previous emotions and current ones, check for intersection
                # If NO intersection in BASE emotions, it's a topic/mood shift
                if prev_base_emotions and current_base_emotions:
                    intersection = current_base_emotions.intersection(prev_base_emotions)
                    
                    # Check for polarity flip (Positive <-> Negative) even if they share energy levels
                    has_polarity_flip = False
                    if ("positive" in prev_base_emotions and "negative" in current_base_emotions) or \
                       ("negative" in prev_base_emotions and "positive" in current_base_emotions):
                        has_polarity_flip = True
                    
                    if not intersection or has_polarity_flip:
                        topic_changes += 1
                
                if current_base_emotions:
                    prev_base_emotions = current_base_emotions
        
        # Normalize: 3+ topic changes in 5 messages = high chaos
        topic_volatility_score = min(100, (topic_changes / 3.0) * 100)
        
        # 2. Message Length Variance (erratic = high variance)
        user_msg_lengths = [len(msg.get("content", "")) for msg in user_messages]
        if len(user_msg_lengths) > 1:
            mean_len = sum(user_msg_lengths) / len(user_msg_lengths)
            variance = sum((x - mean_len) ** 2 for x in user_msg_lengths) / len(user_msg_lengths)
            std_dev = variance ** 0.5
            # High std_dev (>50 chars) suggests erratic messaging
            length_variance_score = min(100, (std_dev / 50.0) * 100)
        else:
            length_variance_score = 0
        
        # 3. Contradiction Detection (check consecutive messages for emotional whiplash)
        contradictions = 0
        positive_keywords = ["happy", "great", "amazing", "love", "excited", "wonderful", "fantastic", "joy", "good", "nice"]
        negative_keywords = ["hate", "angry", "sad", "terrible", "awful", "depressed", "miserable", "empty", "numb", "bad", "worst"]
        
        # Check consecutive messages for emotional flips
        prev_sentiment = None
        for msg in user_messages[-5:]:
            text = msg.get("content", "").lower()
            current_sentiment = None
            
            # Simple negation handling
            is_negated = "not " in text or "don't " in text or "never " in text
            
            has_positive = any(kw in text for kw in positive_keywords)
            has_negative = any(kw in text for kw in negative_keywords)
            
            if has_positive and not is_negated:
                current_sentiment = "positive"
            elif has_positive and is_negated:
                current_sentiment = "negative"
            elif has_negative and not is_negated:
                current_sentiment = "negative"
            elif has_negative and is_negated:
                current_sentiment = "positive"
            
            # If sentiment flips from positive to negative or vice versa, that's a contradiction
            if prev_sentiment and current_sentiment and prev_sentiment != current_sentiment:
                contradictions += 1
            
            if current_sentiment:
                prev_sentiment = current_sentiment
        
        # Each contradiction is worth more (40 points each, max 100)
        contradiction_score = min(100, contradictions * 40)
        
        # === LLM ANALYSIS (DISABLED FOR OPTIMIZATION) ===
        # OPTIMIZATION: Skip expensive LLM coherence rating, use heuristics only
        llm_coherence_score = 0
        # try:
        #     # Build conversation summary for LLM
        #     conv_summary = "\n".join([
        #         f"{'User' if turn.get('role') == 'user' else 'AI'}: {turn.get('content', '')[:100]}"
        #         for turn in recent_chat[-6:]
        #     ])
        #     
        #     prompt = f"""
        # # Analyze this conversation for CHAOS (incoherence, topic jumping, contradictions, erratic behavior).
        # # Rate from 0-100 where:
        # # - 0 = Perfectly coherent, focused conversation
        # # - 50 = Some topic changes but generally coherent
        # # - 100 = Extremely chaotic, incoherent, contradictory, erratic
        # # 
        # # Conversation:
        # # {conv_summary}
        # # 
        # # Return ONLY a number from 0-100.
        # # """
        #     response = self.llm.generate_response(prompt)
        #     # Extract number from response
        #     import re
        #     match = re.search(r'\b(\d{1,3})\b', response)
        #     if match:
        #         llm_coherence_score = int(match.group(1))
        #         llm_coherence_score = min(100, max(0, llm_coherence_score))
        # except Exception as e:
        #     # If LLM fails, just use heuristics
        #     pass
        
        # === COMBINE SCORES ===
        # If LLM worked, use it heavily (60%), otherwise rely on heuristics
        if llm_coherence_score > 0:
            final_score = int(
                (llm_coherence_score * 0.6) +
                (topic_volatility_score * 0.2) +
                (contradiction_score * 0.1) +
                (length_variance_score * 0.1)
            )
        else:
            final_score = int(
                (topic_volatility_score * 0.4) +
                (contradiction_score * 0.4) +
                (length_variance_score * 0.2)
            )
        
        final_score = min(100, max(0, final_score))
        
        # Generate reason
        reason = "Stable, coherent conversation."
        if final_score > 70:
            reason = "High conversational chaos detected: erratic topic changes, contradictions, or incoherent dialogue."
        elif final_score > 40:
            reason = "Moderate conversational instability: some topic jumping or emotional shifts."
        
        return final_score, reason

    def predict_impact(self, chaos_score: int, reason: str, chat_history: List[dict] = None) -> Dict[str, str]:
        """
        Predicts the long-term impact of the current chaos level on the user using Gemini.
        Returns a dictionary with predictions for 7, 30, and 60 days.
        """
        # Default fallback predictions
        fallback_predictions = {
            "7 Days": "Cognitive Strain: You will feel increasingly drained trying to maintain context.",
            "30 Days": "Emotional Disconnect: Frustration will peak. You may start treating the AI as an adversary.",
            "60 Days": "System Abandonment: High likelihood of giving up on this workflow."
        }
        
        if chaos_score < 40:
            fallback_predictions = {
                "7 Days": "Flow State: Interactions feel effortless.",
                "30 Days": "Skill Amplification: You are learning to prompt better.",
                "60 Days": "Symbiosis: The system feels like an extension of your mind."
            }
        elif chaos_score < 70:
            fallback_predictions = {
                "7 Days": "Friction: You'll notice you have to repeat yourself often.",
                "30 Days": "Reduced Efficiency: You will subconsciously limit complexity.",
                "60 Days": "Habitual Annoyance: Using the system becomes a chore."
            }

        try:
            # Prepare context for LLM
            context = f"Chaos Score: {chaos_score}/100\nReason: {reason}\n"
            if chat_history:
                recent = chat_history[-5:]
                context += "Recent Chat:\n" + "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in recent])
            
            prompt = f"""
            Analyze the following user-AI interaction state:
            {context}
            
            Predict the psychological and practical impact on the user if this pattern continues for:
            - 7 Days
            - 30 Days
            - 60 Days
            
            Provide the output strictly as a JSON object with keys "7 Days", "30 Days", and "60 Days". 
            Keep descriptions concise (max 2 sentences each).
            IMPORTANT: Address the user directly using "You".
            CRITICAL CONSTRAINT: Do NOT mention "AI", "chatbot", "system", "technology", or "this interaction". Focus PURELY on the user's internal psychological state, cognitive function, and real-world social relationships.
            """
            
            response = self.llm.generate_response(prompt)
            
            # Simple parsing attempt (assuming LLM returns valid JSON or close to it)
            import json
            import re
            
            # Extract JSON block if present
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                # Fallback if no JSON found
                return fallback_predictions
                
        except Exception as e:
            print(f"Prediction generation failed: {e}")
            return fallback_predictions

if __name__ == "__main__":
    print("Running ChaosPredictor test...")
    
    # Try to use real LLM if API key is available
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    llm_instance = None
    
    try:
        if os.getenv("GEMINI_API_KEY"):
            print("Using REAL Gemini API for predictions...")
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
                return json.dumps({
                    "7 Days": "Mock Prediction: You will feel a bit confused.",
                    "30 Days": "Mock Prediction: You will be very annoyed.",
                    "60 Days": "Mock Prediction: You will quit."
                })
        llm_instance = MockLLM()
        
    predictor = ChaosPredictor(llm=llm_instance)
    
    # Load real data if available
    from memory.chat_memory import ChatMemory
    from memory.emotion_log import EmotionLog
    
    chat_memory = ChatMemory()
    emotion_log = EmotionLog()
    user_id = "test_user"
    
    real_chat_history = chat_memory.get_recent_context(user_id, limit=20)
    real_logs = emotion_log.get_recent_logs(user_id, days=7)
    
    if real_chat_history:
        print(f"Using REAL chat history ({len(real_chat_history)} messages)...")
        sample_chat_history = real_chat_history
        sample_logs = real_logs
    else:
        print("No real data found. Using HARDCODED sample data...")
        # Sample data
        sample_chat_history = [
            {"role": "user", "content": "I love this!"},
            {"role": "assistant", "content": "That's great."},
            {"role": "user", "content": "Actually I hate it now."},
            {"role": "assistant", "content": "Oh, why?"},
            {"role": "user", "content": "It's amazing again!"},
            {"role": "assistant", "content": "You seem conflicted."},
            {"role": "user", "content": "No I'm sad."},
        ]
        
        sample_logs = [
            {"raw_text": "I love this!", "emotion_tags": ["joy"]},
            {"raw_text": "Actually I hate it now.", "emotion_tags": ["anger"]},
            {"raw_text": "It's amazing again!", "emotion_tags": ["excitement"]},
            {"raw_text": "No I'm sad.", "emotion_tags": ["sadness"]},
        ]
    
    score, reason = predictor.compute_chaos(sample_chat_history, sample_logs)
    print(f"Chaos Score: {score}")
    print(f"Reason: {reason}")
    
    print("\n--- Future Predictions ---")
    predictions = predictor.predict_impact(score, reason, sample_chat_history)
    for timeframe, prediction in predictions.items():
        print(f"[{timeframe}]: {prediction}")
