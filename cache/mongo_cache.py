from pymongo import MongoClient
import os
from typing import Optional, Any
from datetime import datetime, timedelta
from cache_utils import serialize_embedding, deserialize_embedding

class MongoCache:
    def __init__(self):
        self.client = None
        self.collection = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection."""
        try:
            connection_string = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017/")
            database_name = os.getenv("MONGO_DATABASE", "meditation_app")
            
            self.client = MongoClient(connection_string)
            db = self.client[database_name]
            self.collection = db["speaker_embeddings"]
            
            # Test connection and create indexes
            self.client.admin.command('ismaster')
            self.collection.create_index("user_id", unique=True)
            self.collection.create_index("expires_at", expireAfterSeconds=0)
            
            self.connected = True
            print("✅ Connected to MongoDB successfully")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected and self.client is not None
    
    def set_speaker_embedding(self, user_id: str, embedding, expiration_seconds: int = 2592000) -> bool:
        if not self.is_connected():
            return False
        try:
            document = {
                "user_id": user_id,
                "embedding_data": serialize_embedding(embedding),
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=expiration_seconds)
            }
            self.collection.replace_one({"user_id": user_id}, document, upsert=True)
            return True
        except Exception as e:
            print(f"MongoDB set failed: {e}")
            return False
    
    def get_speaker_embedding(self, user_id: str) -> Optional[Any]:
        if not self.is_connected():
            return None
        try:
            document = self.collection.find_one({"user_id": user_id})
            if document and "embedding_data" in document:
                # Check if expired
                if document.get("expires_at") and document["expires_at"] < datetime.utcnow():
                    self.delete_speaker_embedding(user_id)
                    return None
                return deserialize_embedding(document["embedding_data"])
            return None
        except Exception as e:
            print(f"MongoDB get failed: {e}")
            return None
    
    def delete_speaker_embedding(self, user_id: str) -> bool:
        if not self.is_connected():
            return False
        try:
            result = self.collection.delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"MongoDB delete failed: {e}")
            return False
    
    def exists_speaker_embedding(self, user_id: str) -> bool:
        if not self.is_connected():
            return False
        try:
            document = self.collection.find_one({"user_id": user_id}, {"expires_at": 1})
            if document:
                # Check if expired
                if document.get("expires_at") and document["expires_at"] < datetime.utcnow():
                    self.delete_speaker_embedding(user_id)
                    return False
                return True
            return False
        except Exception:
            return False
    
    def cleanup_expired(self) -> int:
        """Manually cleanup expired embeddings."""
        if not self.is_connected():
            return 0
        try:
            result = self.collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
            return result.deleted_count
        except Exception:
            return 0 