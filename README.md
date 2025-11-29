# ChaosSynth 2.0

**AI-powered mental health companion with chaos prediction and emotional analysis.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

- 💬 **Empathetic AI Chat** - Compassionate conversation powered by Google Gemini
- 🌀 **Chaos Score** - Analyze conversational and emotional volatility
- 📊 **Emotional Tracking** - Log and visualize emotional patterns over time
- ✨ **Smart Suggestions** - Personalized recommendations based on your state
- 🔒 **Privacy-Focused** - All data stored locally in JSON format

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ChaosSynth-2.0.git
   cd ChaosSynth-2.0
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

5. **Run the application**
   ```bash
   streamlit run app/streamlit_app.py
   ```

The app will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
ChaosSynth-2.0/
├── app/                    # Application entry points
│   ├── streamlit_app.py    # Main Streamlit UI
│   ├── main.py             # Backend server
│   └── terminal_test.py    # CLI test runner
├── core/                   # Core AI logic
│   ├── llm_wrapper.py      # LLM provider wrapper
│   ├── chaos.py            # Chaos prediction
│   ├── prediction.py       # Prediction engine
│   └── suggestion.py       # Suggestion engine
├── memory/                 # Memory system
│   ├── profile_memory.py   # User profiles
│   ├── chat_memory.py      # Chat history
│   ├── emotion_log.py      # Emotion tracking
│   └── memory_consolidator.py
├── services/               # Service layer
│   ├── chat_engine.py      # Chat pipeline
│   ├── session_manager.py  # Session management
│   ├── feedback_loop.py    # Feedback system
│   └── fallback_library.py # Fallback responses
└── data/                   # User data (gitignored)
```

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **AI**: Google Gemini API
- **Storage**: JSON-based local storage
- **Language**: Python 3.8+

## 📖 Usage

### Streamlit UI

The main interface provides:
- **User Profile**: Set up your profile with hobbies, stress triggers, and personality traits
- **Chat**: Talk with the AI companion
- **Chaos Prediction**: Analyze conversation volatility
- **Suggestions**: Get personalized recommendations

### Terminal Test

For testing without the UI:
```bash
python app/terminal_test.py
```

## ⚠️ Important Notes

- **Privacy**: All data is stored locally in the `data/` directory
- **API Usage**: This app uses the Google Gemini API (free tier available)
- **Not a Replacement**: This is NOT a replacement for professional mental health care

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io)
- Powered by [Google Gemini](https://deepmind.google/technologies/gemini/)

## ⚡ Support

If you encounter any issues or have questions:
- Open an [issue](https://github.com/yourusername/ChaosSynth-2.0/issues)
- Check the [documentation](docs/)

---

**⚠️ Disclaimer**: ChaosSynth is an experimental AI companion and should not be used as a substitute for professional mental health services. If you're experiencing a mental health crisis, please contact a qualified professional or crisis hotline immediately.
