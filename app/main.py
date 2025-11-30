"""
ChaosSynth API Main Module

This module exposes the core functionality of the ChaosSynth application via a FastAPI interface.
It connects the frontend to the backend logic for profile management, emotion logging,
predictions, and suggestions.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Import core modules
from memory.profile_memory import ProfileMemory
from memory.emotion_log import EmotionLog
from core.llm_wrapper import GeminiWrapper
from core.prediction import Predictor
from core.suggestion import SuggestionEngine

from memory.chat_memory import ChatMemory
from services.feedback_loop import FeedbackLoop
from services.chat_engine import ChatEngine
from memory.memory_consolidator import MemoryConsolidator

# --- App Initialization ---
app = FastAPI(
    title="ChaosSynth API",
    description="Backend API for the ChaosSynth Mental Health Companion",
    version="2.3.0"
)

# CORS Middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Initialization ---
# Initialize singletons for the application
# --- Dependency Initialization ---
# Initialize singletons for the application
profile_memory = None
chat_memory = None
feedback_loop = None
llm_wrapper = None
emotion_log = None
predictor = None
suggestion_engine = None
chat_engine = None
memory_consolidator = None

# 1. Initialize Safe Modules (File I/O only)
try:
    profile_memory = ProfileMemory()
    chat_memory = ChatMemory()
    feedback_loop = FeedbackLoop()
    print("Safe modules initialized.")
except Exception as e:
    print(f"Error initializing safe modules: {e}")

# 2. Initialize LLM (Risky - might fail if no key)
try:
    llm_wrapper = GeminiWrapper()
    print("LLM initialized.")
except Exception as e:
    print(f"Warning: LLM failed to initialize (Check API Key): {e}")

# 3. Initialize Dependent Modules
try:
    emotion_log = EmotionLog() 
    
    if profile_memory and emotion_log and llm_wrapper:
        predictor = Predictor(profile_memory, emotion_log, llm_wrapper)
        suggestion_engine = SuggestionEngine(profile_memory, emotion_log, predictor, llm_wrapper, feedback_loop, chat_memory)
        
        chat_engine = ChatEngine(
            profile_memory, 
            emotion_log, 
            chat_memory, 
            predictor, 
            suggestion_engine, 
            llm_wrapper,
            efficient_mode=True
        )
        
        memory_consolidator = MemoryConsolidator(llm_wrapper, profile_memory)
        print("All core engines initialized.")
    else:
        print("Skipping core engines due to missing dependencies (LLM or Profile).")

except Exception as e:
    print(f"Error initializing core engines: {e}")

def check_init():
    # We only strictly need profile_memory and chat_memory for basic ops.
    # But for chat_interact, we need chat_engine.
    if not chat_engine:
        raise HTTPException(status_code=503, detail="AI Engine not available (Check API Key).")

# --- Pydantic Models ---

class ProfileCreate(BaseModel):
    name: str
    age: Optional[int] = None
    hobbies: List[str] = []
    likes: List[str] = []
    dislikes: List[str] = []
    goals: List[str] = []
    personal_notes: str = ""
    fears: List[str] = []
    personality_traits: List[str] = []

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    hobbies: Optional[List[str]] = None
    likes: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    personal_notes: Optional[str] = None
    fears: Optional[List[str]] = None
    personality_traits: Optional[List[str]] = None

class LogEntryRequest(BaseModel):
    text: str

class ChatMessageRequest(BaseModel):
    role: str  # 'user' or 'system'
    content: str
    metadata: Optional[Dict[str, Any]] = {}

class InteractRequest(BaseModel):
    message: str

class FeedbackRequest(BaseModel):
    suggestion_id: str
    action: str # 'accepted', 'rejected', 'completed', 'dismissed'
    rating: Optional[int] = None
    meta: Optional[Dict[str, Any]] = {}

# --- Endpoints ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "ChaosSynth API is running"}

# --- Profile Endpoints ---

@app.post("/profile/{user_id}")
async def create_user_profile(user_id: str, profile: ProfileCreate):
    """Create a new user profile."""
    try:
        profile_memory.create_profile(user_id, profile.dict())
        return {"message": "Profile created successfully", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get a user's profile."""
    profile = profile_memory.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.patch("/profile/{user_id}")
async def update_user_profile(user_id: str, profile_update: ProfileUpdate):
    """
    Update a user's profile.
    Note: List fields will append new unique items, not replace.
    """
    # Filter out None values
    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    
    if not update_data:
        return {"message": "No data provided for update"}
        
    try:
        updated_profile = profile_memory.update_profile(user_id, update_data)
        return updated_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Emotion Log Endpoints ---

@app.post("/log/{user_id}")
async def add_emotion_log(user_id: str, log_request: LogEntryRequest):
    """
    Add a new emotion log entry.
    Analyzes the text for emotion, severity, and stability.
    """
    if not profile_memory.profile_exists(user_id):
        raise HTTPException(status_code=404, detail="User profile not found. Create profile first.")
        
    try:
        result = emotion_log.add_log(user_id, log_request.text)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to analyze and save log.")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/log/{user_id}")
async def get_logs(user_id: str, days: int = 30):
    """Get recent emotion logs."""
    return emotion_log.get_recent_logs(user_id, days)

# --- Prediction & Suggestion Endpoints ---

@app.get("/predict/{user_id}")
async def get_predictions(user_id: str):
    """
    Get stress, burnout, and danger predictions based on recent logs.
    """
    if not profile_memory.profile_exists(user_id):
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return predictor.predict_all(user_id)

@app.get("/suggest/{user_id}")
async def get_suggestions(user_id: str, num: int = 3):
    """
    Get personalized suggestions based on current emotional state.
    """
    if not profile_memory.profile_exists(user_id):
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return suggestion_engine.suggest_for_user(user_id, num)

# --- Chat & Feedback Endpoints ---

@app.get("/chat/{user_id}")
async def get_chat_history(user_id: str, limit: int = 20):
    """Get recent chat history."""
    return chat_memory.get_recent_context(user_id, limit)

@app.post("/chat/interact/{user_id}")
async def chat_interact(user_id: str, request: InteractRequest):
    """
    Full chat interaction:
    1. Saves user message
    2. Analyzes emotion
    3. Checks predictions
    4. Generates AI response
    """
    check_init()
    if not profile_memory.profile_exists(user_id):
        raise HTTPException(status_code=404, detail="Profile not found")
        
    try:
        return chat_engine.process_message(user_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback/{user_id}")
async def log_feedback(user_id: str, feedback: FeedbackRequest):
    """Log user interaction with a suggestion."""
    return feedback_loop.log_interaction(
        user_id, 
        feedback.suggestion_id, 
        feedback.action, 
        feedback.meta, 
        feedback.rating
    )

# --- Memory Consolidation Endpoints ---

@app.post("/memory/consolidate/{user_id}")
async def consolidate_memory(user_id: str):
    """
    Trigger memory consolidation.
    Extracts long-term facts from recent chat history and updates the profile.
    """
    if not profile_memory.profile_exists(user_id):
        raise HTTPException(status_code=404, detail="Profile not found")
        
    # Get recent chat history (e.g., last 50 messages)
    transcript = chat_memory.get_recent_context(user_id, limit=50)
    
    if not transcript:
        return {"message": "No recent chat history to consolidate."}
        
    try:
        result = memory_consolidator.consolidate_from_transcript(user_id, transcript)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/stats/{user_id}")
async def get_feedback_stats(user_id: str):
    """Get feedback statistics and user preferences."""
    # check_init() # Feedback loop is safe, no need to check chat_engine
    return feedback_loop.get_user_preferences(user_id)

class ApiKeyRequest(BaseModel):
    api_key: str

@app.post("/config/api_key")
async def set_api_key(request: ApiKeyRequest):
    """Set the Gemini API Key dynamically."""
    global llm_wrapper, predictor, suggestion_engine, chat_engine, memory_consolidator, emotion_log
    
    clean_key = request.api_key.strip()
    if not clean_key:
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")

    try:
        print(f"Attempting to set API Key (length: {len(clean_key)})...")
        # Re-initialize LLM with new key
        llm_wrapper = GeminiWrapper(api_key=clean_key)
        
        # Re-initialize dependents
        if not emotion_log: emotion_log = EmotionLog()
        
        predictor = Predictor(profile_memory, emotion_log, llm_wrapper)
        suggestion_engine = SuggestionEngine(profile_memory, emotion_log, predictor, llm_wrapper, feedback_loop)
        
        chat_engine = ChatEngine(
            profile_memory, 
            emotion_log, 
            chat_memory, 
            predictor, 
            suggestion_engine, 
            llm_wrapper,
            efficient_mode=True
        )
        
        memory_consolidator = MemoryConsolidator(llm_wrapper, profile_memory)
        
        print("API Key updated successfully.")
        return {"message": "API Key updated and engines re-initialized."}
    except Exception as e:
        print(f"Error setting API Key: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to initialize with provided key: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
