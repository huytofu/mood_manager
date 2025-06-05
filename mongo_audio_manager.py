"""
MongoDB Audio Manager
====================
Manages 5 collections for audio metadata:
1. brainwave_audios - Brainwave audio files with properties
2. music_audios - Background music audio files  
3. message_audios - Voice message audio files
4. final_audios - Final mixed audio files with component references
5. sessions - User sessions linking to final audios
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os

class MongoAudioManager:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(connection_string)
        self.db = self.client["meditation_app"]
        
        # 5 main collections for audio metadata
        self.brainwave_audios = self.db["brainwave_audios"]
        self.music_audios = self.db["music_audios"]
        self.message_audios = self.db["message_audios"]
        self.final_audios = self.db["final_audios"]
        self.sessions = self.db["sessions"]
        
        # Create indexes for better performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for efficient querying."""
        # Brainwave audios indexes
        self.brainwave_audios.create_index([("user_id", 1), ("wave_type", 1), ("volume_magnitude", 1)])
        self.brainwave_audios.create_index("created_at")
        
        # Music audios indexes
        self.music_audios.create_index([("user_id", 1), ("task", 1)])
        self.music_audios.create_index("created_at")
        
        # Message audios indexes
        self.message_audios.create_index([("user_id", 1)])
        self.message_audios.create_index("created_at")
        
        # Final audios indexes
        self.final_audios.create_index([("user_id", 1), ("task", 1)])
        self.final_audios.create_index("created_at")
        
        # Sessions indexes
        self.sessions.create_index([("user_id", 1)])
        self.sessions.create_index("created_at")
    
    # BRAINWAVE AUDIOS COLLECTION
    def store_brainwave_audio(self, user_id: str, uuid_id: str, wave_type: str, 
                             volume_magnitude: str, audio_path: str) -> bool:
        """Store brainwave audio metadata."""
        document = {
            "uuid_id": uuid_id,
            "user_id": user_id,
            "wave_type": wave_type,
            "volume_magnitude": volume_magnitude,
            "audio_path": audio_path,
            "file_exists": os.path.exists(audio_path),
            "created_at": datetime.now(datetime.UTC)
        }
        
        try:
            self.brainwave_audios.insert_one(document)
            return True
        except Exception as e:
            print(f"Error storing brainwave audio: {e}")
            return False
    
    def get_brainwave_audio(self, user_id: str, wave_type: str, 
                           volume_magnitude: str) -> Optional[Dict]:
        """Get brainwave audio by user and properties."""
        return self.brainwave_audios.find_one({
            "user_id": user_id,
            "wave_type": wave_type,
            "volume_magnitude": volume_magnitude
        })
    
    # MUSIC AUDIOS COLLECTION
    def store_music_audio(self, user_id: str, uuid_id: str, task: str, 
                         music_style: str, audio_path: str) -> bool:
        """Store background music audio metadata."""
        document = {
            "uuid_id": uuid_id,
            "user_id": user_id,
            "task": task,
            "music_style": music_style,
            "audio_path": audio_path,
            "file_exists": os.path.exists(audio_path),
            "created_at": datetime.now(datetime.UTC)
        }
        
        try:
            self.music_audios.insert_one(document)
            return True
        except Exception as e:
            print(f"Error storing music audio: {e}")
            return False
    
    def get_music_audio(self, user_id: str, task: str) -> Optional[Dict]:
        """Get most recent music audio for user and task."""
        return self.music_audios.find_one(
            {"user_id": user_id, "task": task},
            sort=[("created_at", -1)]
        )
    
    # MESSAGE AUDIOS COLLECTION
    def store_message_audio(self, user_id: str, uuid_id: str, task: str, duration_sec: float, 
                           selected_tone: str, selected_emotion: str, audio_path: str) -> bool:
        """Store voice message audio metadata."""
        document = {
            "uuid_id": uuid_id,
            "user_id": user_id,
            "task": task,
            "duration_sec": duration_sec,
            "selected_tone": selected_tone,
            "selected_emotion": selected_emotion or None,
            "audio_path": audio_path,
            "file_exists": os.path.exists(audio_path),
            "created_at": datetime.now(datetime.UTC)
        }
        
        try:
            self.message_audios.insert_one(document)
            return True
        except Exception as e:
            print(f"Error storing message audio: {e}")
            return False
    
    def get_message_audio(self, uuid_id: str) -> Optional[Dict]:
        """Get message audio by UUID."""
        return self.message_audios.find_one({"uuid_id": uuid_id})
    
    # FINAL AUDIOS COLLECTION
    def store_final_audio(self, user_id: str, uuid_id: str, task: str, 
                        components: Dict, audio_path: str) -> bool:
        """
        Store final mixed audio with component references.
        components should contain: message_audio_id, music_audio_id, brainwave_audio_id
        """
        document = {
            "uuid_id": uuid_id,
            "user_id": user_id,
            "task": task,
            "components": {
                "message_audio_id": components.get("message_audio_id"),
                "music_audio_id": components.get("music_audio_id"),
                "brainwave_audio_id": components.get("brainwave_audio_id")
            },
            "component_paths": {
                "emotional_audio_path": components.get("emotional_audio_path"),
                "background_music_path": components.get("background_music_path"),
                "brain_waves_path": components.get("brain_waves_path")
            },
            "audio_path": audio_path,
            "file_exists": os.path.exists(audio_path),
            "created_at": datetime.now(datetime.UTC)
        }
        
        try:
            self.final_audios.insert_one(document)
            return True
        except Exception as e:
            print(f"Error storing final audio: {e}")
            return False
    
    def get_final_audio(self, uuid_id: str) -> Optional[Dict]:
        """Get final audio by UUID."""
        return self.final_audios.find_one({"uuid_id": uuid_id})
    
    # SESSIONS COLLECTION
    def create_session(self, user_id: str, session_id: str, final_audio_id: str,
                      task: str, session_type: str, schedule_id: str) -> bool:
        """Create a user session linking to final audio."""
        document = {
            "session_id": session_id,
            "user_id": user_id,
            "task": task,
            "session_type": session_type,
            "final_audio_id": final_audio_id,
            "schedule_id": schedule_id,
            "created_at": datetime.now(datetime.UTC)
        }
        
        try:
            self.sessions.insert_one(document)
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's recent sessions."""
        return list(self.sessions.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit))
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        return self.sessions.find_one({"session_id": session_id})
    
    # CLEANUP METHODS
    def cleanup_old_files(self, days_old: int = 30):
        """Clean up old audio files and metadata."""
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days_old)
        
        collections = [
            self.brainwave_audios,
            self.music_audios, 
            self.message_audios,
            self.final_audios
        ]
        
        for collection in collections:
            old_docs = collection.find({"created_at": {"$lt": cutoff_date}})
            
            for doc in old_docs:
                # Delete file if exists
                if "audio_path" in doc and os.path.exists(doc["audio_path"]):
                    try:
                        os.remove(doc["audio_path"])
                    except Exception as e:
                        print(f"Error deleting file {doc['audio_path']}: {e}")
                
                # Delete document
                collection.delete_one({"_id": doc["_id"]})
        
        # Clean up old sessions
        self.sessions.delete_many({"created_at": {"$lt": cutoff_date}})
    
    def get_collection_stats(self) -> Dict:
        """Get statistics for all collections."""
        return {
            "brainwave_audios": self.brainwave_audios.count_documents({}),
            "music_audios": self.music_audios.count_documents({}),
            "message_audios": self.message_audios.count_documents({}),
            "final_audios": self.final_audios.count_documents({}),
            "sessions": self.sessions.count_documents({})
        }

# Global instance
mongo_audio_manager = MongoAudioManager()