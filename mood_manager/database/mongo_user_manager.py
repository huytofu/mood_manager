"""
MongoDB User Manager
===================
Manages user data collections:
1. users - User profiles with voice paths and subscription tiers
2. user_voices - User voice file metadata
3. user_sessions - User activity sessions
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os

class MongoUserManager:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.users = None
        self.user_voices = None
        self.user_sessions = None
        self.connected = False
        
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection and initialize collections."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client["meditation_app"]
            
            # Test connection
            self.client.admin.command('ismaster')
            
            # Initialize collections
            self.users = self.db["users"]
            self.user_voices = self.db["user_voices"]
            self.user_sessions = self.db["user_sessions"]
            
            # Create indexes for better performance
            self._create_indexes()
            
            self.connected = True
            print("✅ Connected to MongoDB User Manager successfully")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB User Manager: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected and self.client is not None
    
    def _create_indexes(self):
        """Create indexes for efficient querying if they don't already exist."""
        try:
            # Helper function to safely create index
            def safe_create_index(collection, index_spec, index_name=None):
                try:
                    existing_indexes = collection.list_indexes()
                    existing_names = [idx["name"] for idx in existing_indexes]
                    
                    if index_name and index_name in existing_names:
                        return
                    
                    if isinstance(index_spec, list):
                        # Compound index
                        collection.create_index(index_spec)
                    else:
                        # Single field index
                        collection.create_index(index_spec)
                except Exception as e:
                    print(f"Warning: Could not create index {index_spec}: {e}")
            
            # Users collection indexes
            safe_create_index(self.users, "user_id", "user_id_1")
            safe_create_index(self.users, "email")
            safe_create_index(self.users, "subscription_tier")
            safe_create_index(self.users, "created_at")
            
            # User voices collection indexes
            safe_create_index(self.user_voices, "user_id", "voice_user_id_1")
            safe_create_index(self.user_voices, "created_at")
            safe_create_index(self.user_voices, "is_active")
            
            # User sessions collection indexes
            safe_create_index(self.user_sessions, [("user_id", 1), ("session_date", -1)])
            safe_create_index(self.user_sessions, "created_at")
            
        except Exception as e:
            print(f"Warning: Error during index creation: {e}")
    
    def get_user_tier(self, user_id: str) -> str:
        """
        Get user subscription tier.
        Returns: "free", "premium", or "enterprise". Defaults to "free" if user not found.
        """
        if not self.is_connected():
            return "free"
        
        try:
            user = self.users.find_one({"user_id": user_id})
            if user:
                return user.get("subscription_tier", "free")
            else:
                # Create user with free tier if doesn't exist
                self._create_user(user_id, subscription_tier="free")
                return "free"
        except Exception as e:
            print(f"❌ Error getting user tier for {user_id}: {e}")
            return "free"
    
    def get_user_voice_path(self, user_id: str) -> str:
        """
        Get user's voice file path.
        Returns the voice file path or creates a default path if user doesn't exist.
        """
        if not self.is_connected():
            # Fallback to default path structure
            return f"assets/{user_id}/user_voice.wav"
        
        try:
            user = self.users.find_one({"user_id": user_id})
            if user and user.get("voice_path"):
                voice_path = user["voice_path"]
                # Verify file exists, otherwise return default
                if os.path.exists(voice_path):
                    return voice_path
            
            # If no voice path or file doesn't exist, create default structure
            default_path = f"assets/{user_id}/user_voice.wav"
            
            # Ensure user exists and update with default voice path
            self._create_user(user_id, voice_path=default_path)
            
            return default_path
        except Exception as e:
            print(f"❌ Error getting voice path for {user_id}: {e}")
            return f"assets/{user_id}/user_voice.wav"
    
    def _create_user(self, user_id: str, email: str = None, subscription_tier: str = "free", 
                   voice_path: str = None) -> bool:
        """Create a new user profile."""
        if not self.is_connected():
            return False
        
        # Check if user already exists
        existing_user = self.users.find_one({"user_id": user_id})
        if existing_user:
            return True  # User already exists
        
        user_document = {
            "user_id": user_id,
            "email": email,
            "subscription_tier": subscription_tier,  # "free", "premium", "enterprise"
            "voice_path": voice_path,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "profile": {
                "preferences": {},
                "settings": {},
                "metadata": {}
            }
        }
        
        try:
            self.users.insert_one(user_document)
            print(f"✅ Created new user: {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error creating user {user_id}: {e}")
            return False
    
    def update_user_tier(self, user_id: str, new_tier: str) -> bool:
        """Update user subscription tier."""
        if not self.is_connected():
            return False
        
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "subscription_tier": new_tier,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"❌ Error updating user tier for {user_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics for all collections."""
        if not self.is_connected():
            return {}
        
        return {
            "users": self.users.count_documents({}),
            "active_users": self.users.count_documents({"is_active": True}),
            "premium_users": self.users.count_documents({"subscription_tier": "premium"}),
            "user_voices": self.user_voices.count_documents({}),
            "user_sessions": self.user_sessions.count_documents({})
        }

# Global instance
mongo_user_manager = MongoUserManager() 