import os
import sys
import asyncio
from typing import Optional

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

def load_env_file():
    """Manually load .env file if it exists."""
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
        print(f"Loading environment from {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

from memory.profile_memory import ProfileMemory
from memory.emotion_log import EmotionLog
from core.llm_wrapper import GeminiWrapper
from core.prediction import Predictor
from core.suggestion import SuggestionEngine
from memory.chat_memory import ChatMemory
from services.feedback_loop import FeedbackLoop
from services.chat_engine import ChatEngine
from memory.memory_consolidator import MemoryConsolidator

def init_components(api_key: Optional[str] = None):
    print("Initializing components...")
    
    try:
        profile_memory = ProfileMemory()
        chat_memory = ChatMemory()
        feedback_loop = FeedbackLoop()
        print("Safe modules initialized.")
    except Exception as e:
        print(f"Error initializing safe modules: {e}")
        return None

    try:
        llm_wrapper = GeminiWrapper(api_key=api_key)
        print("LLM initialized.")
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        print("Please ensure GEMINI_API_KEY is set or passed.")
        return None

    try:
        emotion_log = EmotionLog()
        predictor = Predictor(profile_memory, emotion_log, llm_wrapper)
        suggestion_engine = SuggestionEngine(profile_memory, emotion_log, predictor, llm_wrapper, feedback_loop, chat_memory)
        
        chat_engine = ChatEngine(
            profile_memory, 
            emotion_log, 
            chat_memory, 
            predictor, 
            suggestion_engine, 
            llm_wrapper,
            efficient_mode=True  # Optimize API usage
        )
        
        memory_consolidator = MemoryConsolidator(llm_wrapper, profile_memory)
        print("All core engines initialized.")
        
        return chat_engine, profile_memory
    except Exception as e:
        print(f"Error initializing core engines: {e}")
        return None

def main():
    print("--- ChaosSynth Terminal Test ---")
    
    load_env_file()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = input("Enter Gemini API Key: ").strip()
        if not api_key:
            print("API Key is required.")
            return

    components = init_components(api_key)
    if not components:
        print("Failed to initialize components. Exiting.")
        return

    chat_engine, profile_memory = components
    
    user_id = "test_user"
    
    # Ensure profile exists
    if not profile_memory.profile_exists(user_id):
        print(f"Creating profile for {user_id}...")
        profile_memory.create_profile(user_id, {
            "name": "Test User",
            "age": 30,
            "hobbies": ["coding", "testing"],
            "likes": ["python", "ai"],
            "dislikes": ["bugs"],
            "goals": ["stable system"],
            "personal_notes": "Testing the system via terminal."
        })
    
    print(f"\nChatting as {user_id}. Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            
            if not user_input.strip():
                continue
                
            print("ChaosSynth is thinking...", end="\r")
            
            response_data = chat_engine.process_message(user_id, user_input)
            
            response_text = response_data.get("response", "No response")
            phase = response_data.get("phase", "Unknown")
            emotion = response_data.get("emotion_data", {}).get("summary", "Unknown")
            
            print(f"ChaosSynth: {response_text}")
            
            report = response_data.get("session_report", {})
            topics = ", ".join(report.get("topics", []))
            print(f"[Debug] Phase: {phase}, Emotion: {emotion}")
            print(f"[Report] Topics: {topics} | Needs: {', '.join(report.get('immediate_needs', []))}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError during chat: {e}")

if __name__ == "__main__":
    main()
