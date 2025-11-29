"""
ChaosSynth - Modern AI Mental Health Companion
Beautiful dark-themed interface with sidebar navigation and integrated chat
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path so we can import modules when running from /app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Load environment variables FIRST
load_dotenv()

# Import ChaosSynth components
from memory.profile_memory import ProfileMemory
from memory.emotion_log import EmotionLog
from core.prediction import Predictor
from core.llm_wrapper import GeminiWrapper
from core.suggestion import SuggestionEngine
from services.feedback_loop import FeedbackLoop
from memory.chat_memory import ChatMemory
from core.chaos import ChaosPredictor

# --- Page Config ---
st.set_page_config(
    page_title="ChaosSynth",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Modern Dark Theme ---
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f1e 0%, #1a1a2e 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Sidebar icon buttons */
    .nav-button {
        display: flex;
        align-items: center;
        padding: 16px 20px;
        margin: 8px 0;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        cursor: pointer;
        transition: all 0.3s ease;
        color: #a0a0b0;
        text-decoration: none;
        font-weight: 500;
    }
    
    .nav-button:hover {
        background: rgba(139, 92, 246, 0.15);
        border-color: rgba(139, 92, 246, 0.3);
        color: #e0e0ff;
        transform: translateX(4px);
    }
    
    .nav-button.active {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(59, 130, 246, 0.2));
        border-color: rgba(139, 92, 246, 0.5);
        color: #fff;
    }
    
    /* Cards */
    .profile-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border-radius: 20px;
        padding: 32px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin-bottom: 24px;
    }
    
    /* Avatar */
    .avatar-container {
        display: flex;
        justify-content: center;
        margin-bottom: 24px;
    }
    
    .avatar {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 48px;
        color: white;
        border: 4px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
    }
    
    /* Input fields */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #e0e0e0 !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(139, 92, 246, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Labels */
    .stTextInput label, .stTextArea label, .stNumberInput label {
        color: #a0a0b0 !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        margin-bottom: 8px !important;
    }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Stats */
    .stat-box {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .stat-value {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    
    .stat-label {
        font-size: 12px;
        color: #808090;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 12px 16px;
        border-radius: 16px;
        margin: 8px 0;
        max-width: 80%;
        animation: fadeIn 0.3s ease;
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        margin-left: auto;
        color: white;
    }
    
    .chat-message.assistant {
        background: rgba(255, 255, 255, 0.05);
        margin-right: auto;
        color: #e0e0e0;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.02);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #a0a0b0;
        font-weight: 500;
        padding: 12px 24px;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(139, 92, 246, 0.2);
        color: #e0e0ff;
    }
    
    /* Suggestion cards */
    .suggestion-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    
    .suggestion-card:hover {
        border-color: rgba(139, 92, 246, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.02);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(139, 92, 246, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(139, 92, 246, 0.5);
    }
    
    /* Title styling */
    h1, h2, h3 {
        color: #e0e0ff !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #667eea !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Components ---
# Removed @st.cache_resource to ensure updates to modules are reflected immediately
def init_components():
    """Initialize all ChaosSynth components"""
    try:
        profile_mem = ProfileMemory()
        emotion_log = EmotionLog()
        chat_memory = ChatMemory()
        
        # Initialize LLM
        try:
            llm = GeminiWrapper()
        except Exception as e:
            print(f"Failed to initialize LLM: {e}")
            llm = None
        
        predictor = Predictor(profile_mem, emotion_log, llm)
        feedback_loop = FeedbackLoop()
        suggestion_engine = SuggestionEngine(profile_mem, emotion_log, predictor, llm, feedback_loop)
        chaos_predictor = ChaosPredictor(llm)
        
        return {
            'profile': profile_mem,
            'emotion': emotion_log,
            'chat': chat_memory,
            'llm': llm,
            'predictor': predictor,
            'feedback': feedback_loop,
            'suggestions': suggestion_engine,
            'chaos': chaos_predictor
        }
    except Exception as e:
        st.error(f"⚠️ Failed to initialize components: {e}")
        st.info("💡 Make sure your GEMINI_API_KEY is set in the .env file")
        return None

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = 'default_user'
if 'page' not in st.session_state:
    st.session_state.page = 'User Profile'
if 'components' not in st.session_state:
    st.session_state.components = init_components()

components_dict = st.session_state.components

# Check if components initialized successfully
if components_dict is None:
    st.stop()

# --- Sidebar Navigation ---
def render_sidebar():
    with st.sidebar:
        # Header
        st.markdown('<div style="text-align: center; padding: 20px 0;">', unsafe_allow_html=True)
        st.markdown('<h2 style="margin: 0; color: #667eea;">ChaosSynth</h2>', unsafe_allow_html=True)
        st.markdown('<p style="margin: 0; color: #808090; font-size: 12px;">Mental Health AI Companion</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('---')
        
        # Navigation buttons
        pages = {
            '👤 User Profile': 'User Profile',
            '💡 Suggestions': 'Suggestions',
            '🌀 Chaos Prediction': 'Chaos Prediction',
            '💬 Chat with AI': 'Chat with AI'
        }
        
        for icon_label, page_name in pages.items():
            if st.button(icon_label, key=page_name, use_container_width=True):
                st.session_state.page = page_name
                st.rerun()
        
        st.markdown('---')
        
        # User info
        st.markdown(f'<p style="color: #808090; font-size: 12px; text-align: center;">User: {st.session_state.user_id}</p>', unsafe_allow_html=True)

# --- Page: User Profile ---
def render_user_profile():
    profile_mem = components_dict['profile']
    user_id = st.session_state.user_id
    
    # Load or create profile
    profile = profile_mem.get_profile(user_id)
    if profile is None:
        profile_mem.create_profile(user_id, {})
        profile = profile_mem.get_profile(user_id)
    
    # Tabs
    tab1, tab2 = st.tabs(['User Profile', 'Personal Settings'])
    
    with tab1:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        
        # Avatar
        st.markdown('''
            <div class="avatar-container">
                <div class="avatar">👤</div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Name
        col1, col2 = st.columns([2, 1])
        with col1:
            name = st.text_input('Name', value=profile.get('name', ''), placeholder='Enter your name')
        with col2:
            age = st.number_input('Age', value=profile.get('age') or 25, min_value=13, max_value=120)
        
        # Stats
        st.markdown('<div style="margin: 32px 0;">', unsafe_allow_html=True)
        st.markdown('<p style="color: #a0a0b0; font-size: 13px; font-weight: 600; margin-bottom: 16px;">STATS</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-value">{len(profile.get('hobbies', []))}</div>
                    <div class="stat-label">Hobbies</div>
                </div>
            ''', unsafe_allow_html=True)
        with col2:
            emotion_log = components_dict['emotion']
            logs = emotion_log.get_recent_logs(user_id, days=30)
            st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-value">{len(logs)}</div>
                    <div class="stat-label">Logs</div>
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Detailed Information
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        
        # Hobbies
        st.markdown('### 🎨 Hobbies')
        hobbies_text = st.text_area('Enter your hobbies (one per line)', 
                                     value='\n'.join(profile.get('hobbies', [])),
                                     height=100)
        
        # Fears/Triggers
        st.markdown('### ⚠️ Stress Triggers')
        fears_text = st.text_area('What triggers stress for you? (one per line)', 
                                   value='\n'.join(profile.get('fears', [])),
                                   height=100)
        
        # Personality Traits
        st.markdown('### 🧠 Personality Traits')
        traits_text = st.text_area('Describe your personality (one trait per line)', 
                                    value='\n'.join(profile.get('personality_traits', [])),
                                    height=80)
        
        # Personal Notes
        st.markdown('### 📝 Personal Notes')
        notes = st.text_area('Any additional notes about yourself', 
                              value=profile.get('personal_notes', ''),
                              height=100)
        
        # Save button
        if st.button('💾 Save Profile', use_container_width=True):
            updated_profile = {
                'name': name,
                'age': age,
                'hobbies': [h.strip() for h in hobbies_text.split('\n') if h.strip()],
                'fears': [f.strip() for f in fears_text.split('\n') if f.strip()],
                'personality_traits': [t.strip() for t in traits_text.split('\n') if t.strip()],
                'personal_notes': notes
            }
            profile_mem.update_profile(user_id, updated_profile)
            st.success('✅ Profile saved successfully!')
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown('### ⚙️ Account Settings')
        
        new_user_id = st.text_input('User ID', value=st.session_state.user_id)
        if st.button('Switch User'):
            st.session_state.user_id = new_user_id
            st.success(f'Switched to user: {new_user_id}')
            st.rerun()
        
        st.markdown('---')
        
        if st.button('🗑️ Clear Chat History', use_container_width=True):
            components_dict['chat'].clear_history(user_id)
            st.success('Chat history cleared!')
        
        if st.button('🗑️ Delete Profile', use_container_width=True, type='secondary'):
            st.warning('This will delete all your data!')
            
        st.markdown('</div>', unsafe_allow_html=True)

# --- Page: Suggestions ---
def render_suggestions():
    user_id = st.session_state.user_id
    suggestion_engine = components_dict['suggestions']
    
    st.markdown('# ✨ AI Suggestions')
    st.markdown('<p style="color: #808090;">Personalized recommendations based on your emotional state</p>', unsafe_allow_html=True)
    
    if st.button('🔄 Generate New Suggestions', use_container_width=True):
        with st.spinner('Analyzing your state...'):
            result = suggestion_engine.suggest_for_user(user_id, num=3)
            st.session_state.suggestion_result = result
    
    if 'suggestion_result' in st.session_state:
        result = st.session_state.suggestion_result
        
        # Phase indicator
        phase = result.get('phase', 'STABLE')
        phase_colors = {
            'STABLE': '#10b981',
            'AT_RISK': '#f59e0b',
            'HURT': '#f97316',
            'CRISIS': '#ef4444'
        }
        phase_color = phase_colors.get(phase, '#808090')
        
        st.markdown(f'''
            <div style="background: rgba(255,255,255,0.05); padding: 16px; border-radius: 12px; margin: 20px 0; border-left: 4px solid {phase_color};">
                <p style="margin: 0; color: #a0a0b0; font-size: 13px;">CURRENT PHASE</p>
                <h2 style="margin: 8px 0 0 0; color: {phase_color};">{phase}</h2>
            </div>
        ''', unsafe_allow_html=True)
        
        # Predictions
        col1, col2, col3 = st.columns(3)
        predictions = result.get('predictions', {})
        
        with col1:
            st.metric('😰 Stress', f"{predictions.get('stress', 0)}%")
        with col2:
            st.metric('🔥 Burnout', f"{predictions.get('burnout', 0)}%")
        with col3:
            st.metric('⚠️ Danger', f"{predictions.get('danger', 0)}%")
        
        st.markdown('---')
        
        # Suggestions
        suggestions = result.get('suggestions', [])
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f'''
                <div class="suggestion-card">
                    <h3 style="margin-top: 0; color: #e0e0ff;">{i}. {suggestion.get('text', '')}</h3>
                    <p style="color: #a0a0b0; margin: 12px 0;">{suggestion.get('reason', '')}</p>
                    <div style="display: flex; gap: 12px; margin-top: 16px; font-size: 12px;">
                        <span style="background: rgba(139, 92, 246, 0.2); padding: 6px 12px; border-radius: 8px; color: #c4b5fd;">
                            {suggestion.get('difficulty', 'N/A').upper()}
                        </span>
                        <span style="background: rgba(59, 130, 246, 0.2); padding: 6px 12px; border-radius: 8px; color: #93c5fd;">
                            {suggestion.get('category', 'N/A').upper()}
                        </span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)

# --- Page: Chaos Prediction ---
def render_chaos_prediction():
    user_id = st.session_state.user_id
    chaos_predictor = components_dict['chaos']
    chat_memory = components_dict['chat']
    emotion_log = components_dict['emotion']
    
    st.markdown('# 🌀 Chaos Prediction')
    st.markdown('<p style="color: #808090;">Analyze conversational and emotional volatility</p>', unsafe_allow_html=True)
    
    if st.button('🔮 Analyze Chaos Score', use_container_width=True):
        with st.spinner('Analyzing patterns...'):
            # Get chat history and recent logs
            chat_history = chat_memory.get_recent_context(user_id, limit=20)
            recent_logs = emotion_log.get_recent_logs(user_id, days=7)
            
            if len(chat_history) < 4:
                st.warning('Not enough conversation data. Chat with the AI first!')
            else:
                score, reason = chaos_predictor.compute_chaos(chat_history, recent_logs)
                predictions = chaos_predictor.predict_impact(score, reason, chat_history)
                
                st.session_state.chaos_result = {
                    'score': score,
                    'reason': reason,
                    'predictions': predictions
                }
    
    if 'chaos_result' in st.session_state:
        result = st.session_state.chaos_result
        score = result['score']
        
        # Chaos score display
        score_color = '#10b981' if score < 40 else '#f59e0b' if score < 70 else '#ef4444'
        
        st.markdown(f'''
            <div style="background: rgba(255,255,255,0.05); padding: 32px; border-radius: 20px; margin: 20px 0; text-align: center;">
                <p style="margin: 0; color: #a0a0b0; font-size: 13px;">CHAOS SCORE</p>
                <h1 style="font-size: 72px; margin: 16px 0; color: {score_color};">{score}</h1>
                <p style="margin: 0; color: #c0c0d0; font-size: 16px;">{result['reason']}</p>
            </div>
        ''', unsafe_allow_html=True)
        
        # Predictions
        st.markdown('### 🔮 Future Impact Predictions')
        
        predictions = result['predictions']
        timeframes = ['7 Days', '30 Days', '60 Days']
        icons = ['🌱', '🌿', '🌳']
        
        cols = st.columns(3)
        for i, (timeframe, icon) in enumerate(zip(timeframes, icons)):
            prediction = predictions.get(timeframe, 'N/A')
            with cols[i]:
                st.markdown(f'''
                    <div class="suggestion-card" style="height: 100%; min-height: 200px;">
                        <h3 style="margin-top: 0; color: #e0e0ff; font-size: 18px;">{icon} {timeframe}</h3>
                        <p style="color: #c0c0d0; margin: 0; font-size: 14px;">{prediction}</p>
                    </div>
                ''', unsafe_allow_html=True)

# --- Page: Chat ---
def render_chat():
    user_id = st.session_state.user_id
    chat_memory = components_dict['chat']
    emotion_log = components_dict['emotion']
    llm = components_dict['llm']
    
    st.markdown('# 💬 Chat with AI')
    st.markdown('<p style="color: #808090;">Your personal mental health companion</p>', unsafe_allow_html=True)
    
    # Load chat history
    history = chat_memory.get_recent_context(user_id, limit=50)
    
    # Chat container
    chat_container = st.container(height=500)
    
    with chat_container:
        if not history:
            st.info('👋 Hi! I\'m here to listen. How are you feeling today?')
        
        for msg in history:
            role = msg.get('role')
            content = msg.get('content', '')
            
            if role == 'user':
                st.markdown(f'<div class="chat-message user">{content}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant">{content}</div>', unsafe_allow_html=True)
    
    # Input handling
    def handle_input():
        if st.session_state.chat_input and llm:
            user_input = st.session_state.chat_input
            
            # Add user message
            chat_memory.add_turn(user_id, 'user', user_input)
            
            # Analyze emotion
            emotion_log.add_log(user_id, user_input)
            
            # Get AI response
            try:
                # Build context
                recent_history = chat_memory.get_recent_context(user_id, limit=10)
                context = '\n'.join([f"{m['role']}: {m['content']}" for m in recent_history[-5:]])
                
                prompt = f"""You are a compassionate mental health AI companion. Respond empathetically and supportively.

Recent conversation:
{context}

Respond in a warm, understanding way. Keep responses concise (2-3 sentences)."""
                
                response = llm.generate_response(prompt)
                
                # Add assistant message
                chat_memory.add_turn(user_id, 'assistant', response)
            except Exception as e:
                st.error(f"Error generating response: {e}")
            
            # Clear input
            st.session_state.chat_input = ''

    st.text_input('Type your message...', key='chat_input', on_change=handle_input, label_visibility='collapsed')
    
    # Send button (optional, as Enter works with text_input)
    if st.button('Send', use_container_width=True):
        handle_input()
        st.rerun()

# --- Main App ---
def main():
    render_sidebar()
    
    # Render selected page
    page = st.session_state.page
    
    if page == 'User Profile':
        render_user_profile()
    elif page == 'Suggestions':
        render_suggestions()
    elif page == 'Chaos Prediction':
        render_chaos_prediction()
    elif page == 'Chat with AI':
        render_chat()

if __name__ == '__main__':
    main()
