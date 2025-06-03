import redis
import os
from typing import Optional, Any
from cache_utils import serialize_embedding, deserialize_embedding

class RedisCache:
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                password=os.getenv("REDIS_PASSWORD", None),
                decode_responses=False
            )
            self.client.ping()
            self.connected = True
            print("✅ Connected to Redis successfully")
        except redis.ConnectionError as e:
            print(f"❌ Failed to connect to Redis: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected and self.client is not None
    
    def set_speaker_embedding(self, user_id: str, embedding, expiration_seconds: int = 2592000) -> bool:
        if not self.is_connected():
            return False
        try:
            data = serialize_embedding(embedding)
            return bool(self.client.setex(f"speaker_embedding:{user_id}", expiration_seconds, data))
        except Exception as e:
            print(f"Redis set failed: {e}")
            return False
    
    def get_speaker_embedding(self, user_id: str) -> Optional[Any]:
        if not self.is_connected():
            return None
        try:
            data = self.client.get(f"speaker_embedding:{user_id}")
            return deserialize_embedding(data) if data else None
        except Exception as e:
            print(f"Redis get failed: {e}")
            return None
    
    def delete_speaker_embedding(self, user_id: str) -> bool:
        if not self.is_connected():
            return False
        try:
            return bool(self.client.delete(f"speaker_embedding:{user_id}"))
        except Exception as e:
            print(f"Redis delete failed: {e}")
            return False
    
    def exists_speaker_embedding(self, user_id: str) -> bool:
        if not self.is_connected():
            return False
        try:
            return bool(self.client.exists(f"speaker_embedding:{user_id}"))
        except Exception as e:
            return False
    
    def get_cache_info(self) -> dict:
        """Get Redis cache information."""
        if not self.is_connected():
            return {"status": "disconnected", "type": "redis"}
        
        try:
            info = self.client.info()
            return {
                "status": "connected",
                "type": "redis",
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "keyspace": info.get("db0", {})
            }
        except Exception as e:
            return {"status": "error", "type": "redis", "error": str(e)}