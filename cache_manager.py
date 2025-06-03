import os
from typing import Optional, Any
from cache.redis_cache import RedisCache
from cache.mongo_cache import MongoCache
from fastapi import HTTPException

class CacheManager:
    def __init__(self):
        self.cache_backend = os.getenv("CACHE_BACKEND", "redis").lower()
        self.cache = None
        self.fallback_cache = {}  # Simple in-memory fallback
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize cache backend with simple fallback."""
        backends = {
            "redis": RedisCache,
            "mongodb": MongoCache,
            "mongo": MongoCache
        }
        
        # Try primary backend
        primary_class = backends.get(self.cache_backend, RedisCache)
        self.cache = primary_class()
        
        if not self.cache.is_connected():
            print(f"⚠️ {self.cache_backend} failed, trying alternative...")
            # Try alternative backend
            alternative = MongoCache() if self.cache_backend == "redis" else RedisCache()
            if alternative.is_connected():
                self.cache = alternative
                print(f"✅ Using alternative cache: {type(alternative).__name__}")
            else:
                print("❌ All databases failed. Using in-memory cache.")
                self.cache = None
    
    def set_speaker_embedding(self, user_id: str, embedding, expiration_seconds: int = 2592000) -> bool:
        # Try database cache first
        if self.cache and self.cache.is_connected():
            if self.cache.set_speaker_embedding(user_id, embedding, expiration_seconds):
                return True
        
        # Fallback to memory
        self.fallback_cache[user_id] = embedding
        return True
    
    def get_speaker_embedding(self, user_id: str) -> Optional[Any]:
        # Try database cache first
        if self.cache and self.cache.is_connected():
            embedding = self.cache.get_speaker_embedding(user_id)
            if embedding is not None:
                return embedding
        
        # Try fallback cache
        return self.fallback_cache.get(user_id)
    
    def delete_speaker_embedding(self, user_id: str) -> bool:
        deleted = False
        
        # Delete from database cache
        if self.cache and self.cache.is_connected():
            deleted = self.cache.delete_speaker_embedding(user_id)
        
        # Delete from fallback
        if user_id in self.fallback_cache:
            del self.fallback_cache[user_id]
            deleted = True
        
        return deleted
    
    def exists_speaker_embedding(self, user_id: str) -> bool:
        # Check database cache
        if self.cache and self.cache.is_connected():
            if self.cache.exists_speaker_embedding(user_id):
                return True
        
        # Check fallback
        return user_id in self.fallback_cache
    
    def get_cache_info(self) -> dict:
        cache_type = "in-memory"
        if self.cache:
            cache_type = "redis" if "Redis" in type(self.cache).__name__ else "mongodb"
        
        return {
            "configured_backend": self.cache_backend,
            "active_backend": cache_type,
            "status": "connected" if (self.cache and self.cache.is_connected()) else "fallback_only",
            "fallback_entries": len(self.fallback_cache)
        }
    
    def cleanup_expired(self) -> int:
        if self.cache and hasattr(self.cache, 'cleanup_expired'):
            return self.cache.cleanup_expired()
        return 0
    
    def get_cached_speaker_embedding(self, user_id: str):
        """Retrieve cached speaker embedding or raise HTTPException if not found."""
        embedding = self.get_speaker_embedding(user_id)
        if embedding is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Speaker embedding not found for user {user_id}. Please call /cache_user_voice first."
            )
        return embedding

# Global cache manager instance
cache_manager = CacheManager() 