# Install required packages first:
# pip install TTS soundfile numpy redis pymongo

from TTS.api import TTS
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP
from meditation_utils import generate_meditation_audio
from user_utils import get_user_voice_path
from background import generate_background_music, generate_brainwave, combine_audio
from cache_manager import cache_manager

# 1. Load the pre-trained multi-speaker TTS model
MODEL_NAME = "tts_models/multilingual/multi-dataset/your_tts"
tts_model = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=True)

app = FastAPI()
mcp = FastApiMCP(
    app,
    name="mood_management_mc",
    description="Mood Management Microservice",
    version="1.0.0",
    exclude_operations=["cleanup_expired_cache"],
    include_operations=[
        "cache_user_voice", 
        "get_cache_status", 
        "clear_user_cache", 
        "generate_release_meditation_audio", 
        "generate_sleep_meditation_audio", 
        "generate_mindfulness_meditation_audio", 
        "generate_workout_meditation_audio"
    ],
    describe_all_responses=True,
    describe_full_response_schema=True,
)
mcp.mount()

# CACHE MANAGEMENT ENDPOINTS
@app.post("/cache_user_voice", 
        operation_id="cache_user_voice", 
        description='''
        Generate and cache speaker embedding for a user.
        Args:
            user_id: str
        Returns:
            a dictionary with properties `status`, `message`, and `cache_backend`
        ''',
        response_description="a dictionary with properties `status`, `message`, and `cache_backend` if successful, or an error message if not")
async def cache_user_voice(user_id: str):
    """Generate and cache speaker embedding for a user."""
    try:
        user_voice_path = get_user_voice_path(user_id)
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

@app.get("/cache_status/{user_id}", 
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

@app.delete("/clear_user_cache/{user_id}",
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

@app.post("/cleanup_cache",
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
    
# AUDIO GENERATION ENDPOINTS
@app.post("/generate_release_meditation_audio",
        operation_id="generate_release_meditation_audio",
        description='''
        Generate a release meditation audio.
        Args:
            user_id: str
            selected_emotion: str (user-selected emotion for release)
            selected_tone: str (user-selected tone for message)
            min_length: int (minimum length of the audio in minutes)
            background_options: dict (options for background music and brain waves - should have 5 keys. Example:
                {
                    "should_generate_background_music": True,
                    "music_style": "classical",
                    "should_generate_brain_waves": True,
                    "brain_waves_type": "theta",
                    "volume_magnitude": "high"
                }
            )
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_release_meditation_audio(user_id: str, selected_emotion: str, selected_tone: str, min_length: int, background_options: dict):
    """Generate a release meditation audio."""
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, tts_model, "release", selected_emotion, selected_tone, min_length, background_options)

    background_music_path = None
    brain_waves_path = None
    # 5. Generate background music
    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]
    
    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    brain_waves_type = background_options["brain_waves_type"]
    volume_magnitude = background_options["volume_magnitude"]

    if should_generate_background_music:
        background_music_path = generate_background_music(user_id, "release", music_style)

    if should_generate_brain_waves:
        brain_waves_path = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path = combine_audio(output_path, background_music_path, brain_waves_path)

    return {"status": "success", "output_audio_path": combined_audio_path}

@app.post("/generate_sleep_meditation_audio",
        operation_id="generate_sleep_meditation_audio",
        description='''
        Generate a sleep meditation audio.
        Args:
            user_id: str
            min_length: int (minimum length of the audio in minutes)
            background_options: dict (options for background music and brain waves - should have 5 keys. Example:
                {
                    "should_generate_background_music": True,
                    "music_style": "classical",
                    "should_generate_brain_waves": True,
                    "brain_waves_type": "theta",
                    "volume_magnitude": "low"
                }
            )
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_sleep_meditation_audio(user_id: str, min_length: int, background_options: dict):
    """Generate a sleep meditation audio."""
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, tts_model, "sleep", None, "calm", min_length, background_options)

    background_music_path = None
    brain_waves_path = None
    
    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path = generate_background_music(user_id, "sleep", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "theta" #Suitable for sleep
        volume_magnitude = "low" #Suitable for sleep
        brain_waves_path = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path = combine_audio(output_path, background_music_path, brain_waves_path)

    return {"status": "success", "output_audio_path": combined_audio_path}

@app.post("/generate_mindfulness_meditation_audio",
        operation_id="generate_mindfulness_meditation_audio",
        description='''
        Generate a mindfulness meditation audio.
        Args:
            user_id: str
            min_length: int (minimum length of the audio in minutes)
            background_options: dict (options for background music and brain waves - should have 5 keys. Example:
                {
                    "should_generate_background_music": True,
                    "music_style": "classical",
                    "should_generate_brain_waves": True,
                    "brain_waves_type": "alpha",
                    "volume_magnitude": "low"
                }
            )
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_mindfulness_meditation_audio(user_id: str, min_length: int, background_options: dict):
    """Generate a mindfulness meditation audio."""
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, tts_model, "mindfulness", None, "calm", min_length, background_options)

    background_music_path = None
    brain_waves_path = None

    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path = generate_background_music(user_id, "mindfulness", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "alpha" #Suitable for mindfulness
        volume_magnitude = "low" #Suitable for mindfulness
        brain_waves_path = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path = combine_audio(output_path, background_music_path, brain_waves_path)

    return {"status": "success", "output_audio_path": combined_audio_path}

@app.post("/generate_workout_meditation_audio",
        operation_id="generate_workout_meditation_audio",
        description='''
        Generate a workout meditation audio.
        Args:
            user_id: str
            selected_tone: str (user-selected tone for message)
            min_length: int (minimum length of the audio in minutes)
            background_options: dict (options for background music and brain waves - should have 5 keys. Example:
                {
                    "should_generate_background_music": True,
                    "music_style": "classical",
                    "should_generate_brain_waves": True,
                    "brain_waves_type": "beta",
                    "volume_magnitude": "high"
                }
            )
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_workout_meditation_audio(user_id: str, selected_tone: str, min_length: int, background_options: dict, **kwargs):
    """Generate a workout meditation audio."""
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, tts_model, "workout", None, selected_tone, min_length, background_options)

    background_music_path = None
    brain_waves_path = None

    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path = generate_background_music(user_id, "workout", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "beta" #Suitable for workout
        volume_magnitude = background_options["volume_magnitude"] or "high" #Suitable for workout
        brain_waves_path = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path = combine_audio(output_path, background_music_path, brain_waves_path)

    return {"status": "success", "output_audio_path": combined_audio_path}

