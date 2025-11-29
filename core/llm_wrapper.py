"""
LLM Wrapper Module for Gemini API Integration

This module provides a wrapper class for interacting with Google's Gemini API.
"""

import os
from typing import Optional
import google.generativeai as genai
import json


class GeminiWrapper:
    """
    A wrapper class for the Google Gemini API.
    
    This class handles initialization and communication with the Gemini API,
    providing a simple interface for generating text responses.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the GeminiWrapper with an API key.
        
        Args:
            api_key: Optional API key for Gemini. If not provided, 
                    will attempt to read from GEMINI_API_KEY environment variable.
        
        Raises:
            ValueError: If no API key is provided and GEMINI_API_KEY is not set.
        """
        # Get API key from parameter or environment variable
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "No API key provided. Please pass an API key to the constructor "
                "or set the GEMINI_API_KEY environment variable."
            )
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model (using gemini-2.0-flash-lite as default)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite-preview-02-05')
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic for rate limits.
        """
        import time
        import random
        
        max_retries = 5
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                # Check for common rate limit error indicators
                if "429" in error_str or "resource exhausted" in error_str or "quota" in error_str:
                    if attempt == max_retries - 1:
                        print(f"Max retries reached for API call. Error: {e}")
                        raise e
                    
                    # Exponential backoff with jitter
                    delay = (base_delay * (2 ** attempt)) + (random.random() * 1.0)
                    # print(f"API Quota hit (429). Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    # Not a rate limit error, raise immediately
                    raise e

    def generate_response(self, prompt: str) -> str:
        """
        Generate a text response from the Gemini API based on the provided prompt.
        
        Args:
            prompt: The input prompt to send to the Gemini model.
        
        Returns:
            The text response from the model.
        
        Raises:
            ValueError: If the prompt is empty or invalid.
            RuntimeError: If the API request fails or returns an error.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")
        
        try:
            # Define the API call to be retried
            def _api_call():
                return self.model.generate_content(prompt)

            # Execute with retry logic
            response = self._retry_with_backoff(_api_call)
            
            # Check if response has valid text
            if not response or not response.text:
                raise RuntimeError(
                    "API returned an empty response. The content may have been blocked "
                    "or the model failed to generate a response."
                )
            
            return response.text
            
        except ValueError as ve:
            # Handle validation errors
            raise ValueError(f"Invalid prompt or request: {str(ve)}")
        
        except Exception as e:
            # Handle all other API-related errors
            raise RuntimeError(
                f"Failed to generate response from Gemini API: {str(e)}"
            )
    
    def analyze_emotion(self, text: str) -> dict:
        """
        Analyze emotional content from user text.
        
        Extracts emotion tags, severity, stability, and a summary from the provided text.
        
        Args:
            text: The user's emotional message to analyze.
        
        Returns:
            Dictionary containing:
                - emotion_tags: List of emotion keywords (e.g., ["anxious", "stressed"])
                - severity: Float from 0-10 indicating emotional intensity
                - stability: Float from 0-10 indicating emotional stability (10 = very stable)
                - summary: Brief summary of the emotional state
        
        Raises:
            ValueError: If the text is empty or invalid.
            RuntimeError: If the API request fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty for emotion analysis.")
        
        # Create a structured prompt for emotion analysis
        prompt = f"""Analyze the following text for emotional content and return a JSON response with these exact fields:

Text to analyze: "{text}"

Return ONLY a valid JSON object with this structure (no markdown, no extra text):
{{
    "emotion_tags": ["list", "of", "emotion", "keywords"],
    "severity": 0.0,
    "stability": 0.0,
    "summary": "brief summary of emotional state"
}}

Guidelines:
- emotion_tags: List primary emotions (e.g., "anxious", "happy", "stressed", "sad", "angry", "suicidal", "self-harm", "hopeful")
- severity: Rate 0-10 (0=neutral, 10=extreme crisis)
- stability: Rate 0-10 (0=very unstable, 10=very stable/balanced)
- summary: One sentence describing the overall emotional state

Return ONLY the JSON object, nothing else."""

        try:
            # Get response from Gemini
            response_text = self.generate_response(prompt)
            
            # Try to parse JSON from response
            
            # Clean up response - remove markdown code blocks if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```"):
                # Remove markdown code blocks
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_response
                cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            emotion_data = json.loads(cleaned_response)
            
            # Validate required fields
            required_fields = ["emotion_tags", "severity", "stability", "summary"]
            for field in required_fields:
                if field not in emotion_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure types are correct
            if not isinstance(emotion_data["emotion_tags"], list):
                emotion_data["emotion_tags"] = [str(emotion_data["emotion_tags"])]
            
            emotion_data["severity"] = float(emotion_data["severity"])
            emotion_data["stability"] = float(emotion_data["stability"])
            emotion_data["summary"] = str(emotion_data["summary"])
            
            # Clamp values to valid ranges
            emotion_data["severity"] = max(0.0, min(10.0, emotion_data["severity"]))
            emotion_data["stability"] = max(0.0, min(10.0, emotion_data["stability"]))
            
            return emotion_data
            
        except json.JSONDecodeError as je:
            raise RuntimeError(f"Failed to parse emotion analysis response: {str(je)}")
        except ValueError as ve:
            raise ValueError(f"Invalid emotion analysis data: {str(ve)}")
        except Exception as e:
            raise RuntimeError(f"Failed to analyze emotion: {str(e)}")
