from pymongo import MongoClient
import os
from typing import Optional, Any
from datetime import datetime, timedelta
from cache.cache_utils import serialize_embedding, deserialize_embedding

class MongoCache:
    def __init__(self):
        self.client = None
        self.collection = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection and initialize collections."""
        try:
            connection_string = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017/")
            
            self.client = MongoClient(
                host=connection_string,
                username=os.getenv("MONGO_USERNAME"),
                password=os.getenv("MONGO_PASSWORD"),
                database=os.getenv("MONGO_DATABASE")
            )
            db = self.client[os.getenv("MONGO_DATABASE")]
            self.collection = db["speaker_embeddings"]
            
            # Test connection
            self.client.admin.command('ismaster')
            
            # Create indexes for better performance
            self._create_indexes()
            
            self.connected = True
            print("✅ Connected to MongoDB Cache successfully")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB Cache: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """Create indexes for efficient querying if they don't already exist."""
        try:
            # Helper function to safely create index
            def safe_create_index(collection, index_spec, **kwargs):
                try:
                    existing_indexes = collection.list_indexes()
                    existing_names = [idx["name"] for idx in existing_indexes]
                    
                    # Generate expected index name
                    if isinstance(index_spec, str):
                        expected_name = f"{index_spec}_1"
                    else:
                        expected_name = "_".join([f"{field}_{direction}" for field, direction in index_spec])
                    
                    if expected_name in existing_names:
                        return
                    
                    collection.create_index(index_spec, **kwargs)
                except Exception as e:
                    print(f"Warning: Could not create index {index_spec}: {e}")
            
            # Speaker embeddings indexes
            safe_create_index(self.collection, "user_id", unique=True)
            safe_create_index(self.collection, "expires_at", expireAfterSeconds=0)
            
        except Exception as e:
            print(f"Warning: Error during index creation: {e}")
    
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