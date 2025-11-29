import json
from typing import Dict, Any, Optional
from core.llm_wrapper import GeminiWrapper

class SessionManager:
    """
    Manages the "Session Report" - a live summary of the current conversation.
    It maintains a structured state of the conversation for each user, 
    updating it after every turn to capture topics, emotions, and needs.
    """
    
    def __init__(self, llm: GeminiWrapper):
        self.llm = llm
        # In-memory storage for active sessions: {user_id: report_dict}
        self.reports: Dict[str, Dict[str, Any]] = {}

    def get_report(self, user_id: str) -> Dict[str, Any]:
        """Get the current report for a user, initializing if necessary."""
        if user_id not in self.reports:
            self.reports[user_id] = {
                "topics": [],
                "emotional_trajectory": "Starting conversation",
                "key_insights": [],
                "immediate_needs": []
            }
        return self.reports[user_id]

    def update_report(self, user_id: str, last_message: str, last_response: str) -> Dict[str, Any]:
        """
        Updates the session report based on the latest interaction.
        """
        current_report = self.get_report(user_id)
        
        prompt = f"""
        Update the following Session Report based on the new interaction.
        
        Current Report:
        {json.dumps(current_report, indent=2)}
        
        New Interaction:
        User: {last_message}
        AI: {last_response}
        
        Return ONLY a JSON object with the updated report structure:
        {{
            "topics": ["list", "of", "CURRENTly", "relevant", "topics", "(remove stale ones)"],
            "emotional_trajectory": "Brief description of emotional shift",
            "key_insights": ["list", "of", "new", "insights"],
            "immediate_needs": ["list", "of", "user", "needs"]
        }}
        
        Guidelines:
        - Topics: Keep this list short (max 3-5 items). Remove topics that are no longer relevant to the CURRENT conversation flow.
        - Immediate Needs: Focus on what the user needs RIGHT NOW (e.g., "Crisis Intervention", "Validation").
        """
        
        try:
            response = self.llm.generate_response(prompt)
            
            # Clean and parse JSON
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            
            updated_report = json.loads(cleaned)
            
            # Validate structure (basic check)
            if "topics" in updated_report:
                self.reports[user_id] = updated_report
                return updated_report
            else:
                print("Warning: LLM returned invalid report structure.")
                return current_report
                
        except Exception as e:
            print(f"Error updating session report: {e}")
            return current_report
