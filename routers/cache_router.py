from fastapi import APIRouter, HTTPException, Depends
from cache.cache_manager import cache_manager
from mongo_user_manager import mongo_user_manager
from dependencies import get_tts_model

router = APIRouter(tags=["cache"])

@router.post("/cache_user_voice", 
        operation_id="cache_user_voice", 
        description='''
        Generate and cache speaker embedding for a user.
        Args:
            user_id: str
        Returns:
            a dictionary with properties `status`, `message`, and `cache_backend`
        ''',
        response_description="a dictionary with properties `status`, `message`, and `cache_backend` if successful, or an error message if not")
async def cache_user_voice(user_id: str, tts_model=Depends(get_tts_model)):
    """Generate and cache speaker embedding for a user."""
    try:
        user_voice_path = mongo_user_manager.get_user_voice_path(user_id)
        speaker_embedding = tts_model.get_speaker_embedding(user_voice_path)
        
        success = cache_manager.set_speaker_embedding(user_id, speaker_embedding)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cache speaker embedding")
        
        cache_info = cache_manager.get_cache_info()
        return {
            "status": "success", 
            "message": f"Speaker embedding cached for user {user_id}",
            "cache_backend": cache_info["active_backend"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cache speaker embedding: {str(e)}")

@router.get("/cache_status/{user_id}", 
        operation_id="get_cache_status", 
        description='''
        Check cache status for a user with system info.
        Args:
            user_id: str
        Returns:
            a dictionary with properties `user_id`, `cached`, `message`, and cached information
        ''',
        response_description="a dictionary with properties `user_id`, `cached`, `message`, and cached information if successful, or an error message if not")
async def get_cache_status(user_id: str):
    """Check cache status for a user with system info."""
    exists = cache_manager.exists_speaker_embedding(user_id)
    cache_info = cache_manager.get_cache_info()
    
    return {
        "user_id": user_id,
        "cached": exists,
        "message": "Speaker embedding found" if exists else "Speaker embedding not found. Call /cache_user_voice first.",
        **cache_info
    }

@router.delete("/clear_user_cache/{user_id}",
        operation_id="clear_user_cache",
        description='''
        Clear cached speaker embedding for a user.
        Args:
            user_id: str
        Returns:
            a dictionary with properties `status`, `message`
        ''',
        response_description="a dictionary with properties `status`, `message` if successful, or an error message if not")
async def clear_user_cache(user_id: str):
    """Clear cached speaker embedding for a user."""
    deleted = cache_manager.delete_speaker_embedding(user_id)
    return {
        "status": "success" if deleted else "not_found",
        "message": f"Speaker embedding {'cleared' if deleted else 'not found'} for user {user_id}"
    }

@router.post("/cleanup_cache",
        operation_id="cleanup_expired_cache",
        description='''
        Manually cleanup expired cache entries (MongoDB only).
        Args:
            None
        Returns:
            a dictionary with properties `status`, `message`
        ''',
        response_description="a dictionary with properties `status`, `message` if successful, or an error message if not")
async def cleanup_expired_cache():
    """Manually cleanup expired cache entries (MongoDB only)."""
    cleaned = cache_manager.cleanup_expired()
    return {
        "status": "success",
        "cleaned_entries": cleaned,
        "message": f"Cleaned up {cleaned} expired entries"
    } 