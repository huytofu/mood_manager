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
            self.client = MongoClient(
                host=self.connection_string,
                username=os.getenv("MONGO_USERNAME"),
                password=os.getenv("MONGO_PASSWORD"),
                database=os.getenv("MONGO_DATABASE")
            )
            self.db = self.client[os.getenv("MONGO_DATABASE")]
            
            # Test connection
            self.client.admin.command('ismaster')
            
            # Initialize collections
            self.users = self.db["users"]
            self.user_voices = self.db["user_voices"]
            self.user_sessions = self.db["user_sessions"]
            
            # Create indexes for better performance
            self._create_indexes()
            
            # Create schema validation for collections
            self._create_schema_validation()
            
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
    
    def _create_schema_validation(self):
        """Create schema validation for MongoDB collections to ensure data integrity."""
        try:
            # USERS Schema Validation
            users_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "subscription_tier", "is_active"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "email": {"bsonType": ["string", "null"], "pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                        "subscription_tier": {"bsonType": "string", "enum": ["free", "premium", "enterprise"]},
                        "voice_path": {"bsonType": ["string", "null"]},
                        "is_active": {"bsonType": "bool"},
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"},
                        "profile": {
                            "bsonType": "object",
                            "properties": {
                                "preferences": {"bsonType": "object"},
                                "settings": {"bsonType": "object"},
                                "metadata": {"bsonType": "object"}
                            }
                        }
                    }
                }
            }
            
            # USER VOICES Schema Validation
            user_voices_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "voice_path", "is_active"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "voice_path": {"bsonType": "string", "minLength": 1},
                        "file_size_bytes": {"bsonType": ["number", "null"], "minimum": 0},
                        "duration_seconds": {"bsonType": ["number", "null"], "minimum": 0},
                        "quality_score": {"bsonType": ["number", "null"], "minimum": 0, "maximum": 100},
                        "is_active": {"bsonType": "bool"},
                        "created_at": {"bsonType": "date"},
                        "last_used": {"bsonType": ["date", "null"]}
                    }
                }
            }
            
            # USER SESSIONS Schema Validation
            user_sessions_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "session_date"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "session_date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "session_type": {"bsonType": ["string", "null"], "enum": ["meditation", "crisis", "habit_tracking", "mood_check", "null"]},
                        "duration_minutes": {"bsonType": ["number", "null"], "minimum": 0},
                        "activity_count": {"bsonType": ["int", "null"], "minimum": 0},
                        "mood_before": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 10},
                        "mood_after": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 10},
                        "created_at": {"bsonType": "date"}
                    }
                }
            }
            
            # Apply validation to collections
            validation_configs = [
                ("users", users_schema),
                ("user_voices", user_voices_schema),
                ("user_sessions", user_sessions_schema)
            ]
            
            for collection_name, schema in validation_configs:
                try:
                    # Check if collection exists and has validation
                    collection_info = self.db.list_collections(filter={"name": collection_name})
                    collection_exists = len(list(collection_info)) > 0
                    
                    if collection_exists:
                        # Modify existing collection validation
                        self.db.command("collMod", collection_name, validator=schema, validationLevel="moderate")
                        print(f"✅ Updated schema validation for {collection_name}")
                    else:
                        # Create collection with validation
                        self.db.create_collection(collection_name, validator=schema, validationLevel="moderate")
                        print(f"✅ Created {collection_name} with schema validation")
                        
                except Exception as e:
                    print(f"⚠️ Could not set validation for {collection_name}: {e}")
            
        except Exception as e:
            print(f"Warning: Error during schema validation setup: {e}")
    
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