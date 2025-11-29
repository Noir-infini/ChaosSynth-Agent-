"""
Profile Memory Module

This module manages persistent user profile data stored as JSON files.
Each user has their own profile file containing personal information like
name, hobbies, likes/dislikes, goals, fears, and personality traits.
"""

import json
import os
from typing import Optional


class ProfileMemory:
    """
    Manages user profile data with persistent JSON storage.
    
    Each user profile is stored as a separate JSON file in the data/ directory.
    Provides methods to create, read, update, and check profile existence.
    """
    
    # Default profile structure
    DEFAULT_PROFILE = {
        "name": "",
        "age": None,
        "hobbies": [],
        "likes": [],
        "dislikes": [],
        "goals": [],
        "personal_notes": "",
        "fears": [],
        "personality_traits": []
    }
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the ProfileMemory manager.
        
        Args:
            data_dir: Directory path where profile JSON files will be stored.
        """
        self.data_dir = data_dir
        # Ensure the data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_profile_path(self, user_id: str) -> str:
        """
        Get the file path for a user's profile.
        
        Args:
            user_id: Unique identifier for the user.
            
        Returns:
            Full path to the user's profile JSON file.
        """
        return os.path.join(self.data_dir, f"{user_id}_profile.json")
    
    def _safe_write_json(self, filepath: str, data: dict) -> bool:
        """
        Safely write JSON data to a file using atomic write operation.
        
        Writes to a temporary file first, then renames to avoid data corruption.
        
        Args:
            filepath: Target file path.
            data: Dictionary to write as JSON.
            
        Returns:
            True if successful, False otherwise.
        """
        temp_filepath = filepath + ".tmp"
        try:
            # Write to temporary file
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Atomically rename temp file to target file
            os.replace(temp_filepath, filepath)
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass
            return False
    
    def _load_json(self, filepath: str) -> Optional[dict]:
        """
        Load JSON data from a file with error handling.
        
        Args:
            filepath: Path to the JSON file.
            
        Returns:
            Dictionary if successful, None if file doesn't exist or is corrupted.
        """
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError):
            # File is corrupted or unreadable
            return None
    
    def _merge_with_defaults(self, profile_data: dict) -> dict:
        """
        Merge provided profile data with default structure.
        
        Ensures all required fields exist in the profile.
        
        Args:
            profile_data: Partial or complete profile data.
            
        Returns:
            Complete profile with all required fields.
        """
        merged = self.DEFAULT_PROFILE.copy()
        merged.update(profile_data)
        return merged
    
    def create_profile(self, user_id: str, profile_data: dict) -> None:
        """
        Create a new profile for a user.
        
        Creates a JSON file with the provided profile data, filling in
        any missing fields with default values.
        
        Args:
            user_id: Unique identifier for the user.
            profile_data: Dictionary containing profile information.
        """
        # Merge with defaults to ensure all fields exist
        complete_profile = self._merge_with_defaults(profile_data)
        
        # Get the file path
        filepath = self._get_profile_path(user_id)
        
        # Write to file safely
        self._safe_write_json(filepath, complete_profile)
    
    def get_profile(self, user_id: str) -> Optional[dict]:
        """
        Retrieve a user's profile.
        
        Args:
            user_id: Unique identifier for the user.
            
        Returns:
            Profile dictionary if exists, or a new default profile if missing/corrupted.
            Returns None only if the profile doesn't exist.
        """
        filepath = self._get_profile_path(user_id)
        
        # Try to load existing profile
        profile = self._load_json(filepath)
        
        if profile is None:
            # File doesn't exist or is corrupted
            if os.path.exists(filepath):
                # File exists but is corrupted - recreate with defaults
                default_profile = self.DEFAULT_PROFILE.copy()
                self._safe_write_json(filepath, default_profile)
                return default_profile
            else:
                # File doesn't exist
                return None
        
        # Ensure profile has all required fields
        return self._merge_with_defaults(profile)
    
    def update_profile(self, user_id: str, new_data: dict) -> dict:
        """
        Update an existing user profile.
        
        Merges new data into the existing profile without deleting previous values.
        For list fields (hobbies, likes, etc.), appends unique items instead of replacing.
        
        Args:
            user_id: Unique identifier for the user.
            new_data: Dictionary containing fields to update.
            
        Returns:
            Updated profile dictionary.
        """
        # Load existing profile or create default
        existing_profile = self.get_profile(user_id)
        
        if existing_profile is None:
            # Profile doesn't exist, create it with new data
            existing_profile = self.DEFAULT_PROFILE.copy()
        
        # Merge new data into existing profile
        for key, value in new_data.items():
            if key in existing_profile:
                # Handle list fields - append unique items
                if isinstance(existing_profile[key], list) and isinstance(value, list):
                    # Add only unique items
                    for item in value:
                        if item not in existing_profile[key]:
                            existing_profile[key].append(item)
                else:
                    # For non-list fields, update directly
                    existing_profile[key] = value
            else:
                # New field not in default structure
                existing_profile[key] = value
        
        # Save updated profile
        filepath = self._get_profile_path(user_id)
        self._safe_write_json(filepath, existing_profile)
        
        return existing_profile
    
    def profile_exists(self, user_id: str) -> bool:
        """
        Check if a valid profile exists for a user.
        
        Args:
            user_id: Unique identifier for the user.
            
        Returns:
            True if profile file exists and is valid, False otherwise.
        """
        filepath = self._get_profile_path(user_id)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return False
        
        # Try to load and validate
        profile = self._load_json(filepath)
        
        # Profile exists and is valid if we can load it
        return profile is not None
