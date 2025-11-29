"""
Memory Consolidator Module

This module extracts durable, long-term facts (trauma, goals, fears, hobbies) from 
conversation transcripts and consolidates them into the user's profile.
It filters out ephemeral chatter and ensures PII safety.
"""

import json
import re
import datetime
from typing import List, Dict, Any, Optional
from memory.profile_memory import ProfileMemory
from core.llm_wrapper import GeminiWrapper

class MemoryConsolidator:
    """
    Extracts and stores key long-term memories from chat transcripts.
    """
    
    # Regex patterns for PII masking
    EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_REGEX = r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b'
    
    # Extraction Prompt Template
    EXTRACTION_PROMPT_TEMPLATE = """
You are an assistant that extracts ONLY permanent, durable facts from a user's conversation transcript. Output ONLY a JSON object with these keys (use empty arrays/strings when nothing to extract):

{
  "traumas": [ {"text": "<brief text>", "confidence": 0.0-1.0 } ],
  "major_events": [ {"text": "<brief text>", "confidence": 0.0-1.0 } ],
  "fears": [ {"text": "<brief text>", "confidence": 0.0-1.0 } ],
  "long_term_goals": [ {"text": "<brief text>", "confidence": 0.0-1.0 } ],
  "meaningful_hobbies": [ {"text": "<brief text>", "confidence": 0.0-1.0 } ],
  "notes": "<optional short sentence about why these were extracted>"
}

Rules:
- Do NOT extract casual or ephemeral items (like "I ate pizza today") — only extract identity-level facts, traumas, goals, fears and long-term hobbies.
- Do NOT extract or output phone numbers, emails, addresses, or other direct PII. If present, replace PII with "[REDACTED]" in the text fields.
- For each item include a confidence score (0.0-1.0). Only items with confidence >= {min_confidence} should be considered for storage.
- Keep each text field under 240 characters.
- Output only valid JSON — nothing else.

Transcript to Analyze:
{transcript_text}
"""

    def __init__(self, llm: GeminiWrapper, profile_mem: ProfileMemory, config: dict = None):
        """
        Initialize the MemoryConsolidator.
        
        Args:
            llm: Instance of GeminiWrapper.
            profile_mem: Instance of ProfileMemory.
            config: Optional configuration dictionary.
        """
        self.llm = llm
        self.profile_mem = profile_mem
        self.config = config or {}
        self.min_confidence = self.config.get("min_confidence", 0.6)
        self.mascot_asset = "/mnt/data/a9fa5d35-d685-49d5-9e50-ed648825b2c2.png"

    def _mask_pii(self, text: str) -> str:
        """Mask emails and phone numbers in text."""
        text = re.sub(self.EMAIL_REGEX, "[MASKED_EMAIL]", text)
        text = re.sub(self.PHONE_REGEX, "[MASKED_PHONE]", text)
        return text

    def extract_only(self, transcript_text: str) -> Dict[str, Any]:
        """
        Internal helper to call LLM and parse extraction result.
        """
        # Mask PII in input
        masked_transcript = self._mask_pii(transcript_text)
        
        prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(
            min_confidence=self.min_confidence,
            transcript_text=masked_transcript
        )
        
        try:
            response_text = self.llm.generate_response(prompt)
            
            # Clean markdown
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split('\n')
                cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            
            return json.loads(cleaned)
        except Exception as e:
            raise RuntimeError(f"Extraction failed: {str(e)}")

    def consolidate_from_transcript(self, user_id: str, transcript: List[dict], dry_run: bool = False) -> Dict[str, Any]:
        """
        Consolidate memories from a transcript into the user profile.
        
        Args:
            user_id: User ID.
            transcript: List of message dicts.
            dry_run: If True, returns result without updating profile.
            
        Returns:
            Summary dictionary of added/skipped items.
        """
        if not transcript:
            return {"added": [], "skipped": [], "error": "Empty transcript"}

        # Format transcript for LLM
        transcript_text = ""
        for msg in transcript:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            transcript_text += f"{role}: {content}\n"

        try:
            extracted_data = self.extract_only(transcript_text)
        except Exception as e:
            return {"added": [], "skipped": [], "error": str(e)}

        # Process extracted items
        added_items = []
        skipped_items = []
        
        # Map JSON keys to internal types
        category_map = {
            "traumas": "trauma",
            "major_events": "major_event",
            "fears": "fear",
            "long_term_goals": "goal",
            "meaningful_hobbies": "hobby"
        }
        
        # Get existing memories to check duplicates
        profile = self.profile_mem.get_profile(user_id)
        existing_memories = profile.get("important_memories", []) if profile else []
        existing_texts = {m.get("text", "").lower() for m in existing_memories}

        timestamp = datetime.datetime.now().isoformat()

        for json_key, item_type in category_map.items():
            items = extracted_data.get(json_key, [])
            for item in items:
                text = item.get("text", "").strip()
                confidence = item.get("confidence", 0.0)
                
                # Validation
                if not text or confidence < self.min_confidence:
                    skipped_items.append({"type": item_type, "text": text, "reason": "low_confidence"})
                    continue
                
                # Deduplication (simple text match)
                if text.lower() in existing_texts:
                    skipped_items.append({"type": item_type, "text": text, "reason": "duplicate"})
                    continue
                
                # PII Check (basic heuristic - if LLM failed to mask)
                if "[REDACTED]" in text or "[MASKED" in text:
                    # We accept redacted text, but flag it internally if needed
                    pass
                
                new_memory = {
                    "type": item_type,
                    "text": text,
                    "confidence": confidence,
                    "timestamp": timestamp
                }
                added_items.append(new_memory)
                existing_texts.add(text.lower()) # Prevent duplicates within same batch

        # Update Profile
        if not dry_run and added_items and profile:
            # Append to existing list
            updated_memories = existing_memories + added_items
            self.profile_mem.update_profile(user_id, {"important_memories": updated_memories})

        return {
            "added": added_items,
            "skipped": skipped_items,
            "mascot_asset": self.mascot_asset,
            "dry_run": dry_run
        }
