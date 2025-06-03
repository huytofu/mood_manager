# Install required packages first:
# pip install TTS soundfile numpy redis pymongo

from TTS.api import TTS
from fastapi import FastAPI, HTTPException
from meditation_utils import get_user_emotion_embedding, get_meditation_text
from user_utils import get_user_tier, get_user_voice_path
from background import generate_background_music, generate_brainwave, combine_audio
from cache_manager import cache_manager

app = FastAPI()

# 1. Load the pre-trained multi-speaker TTS model
MODEL_NAME = "tts_models/multilingual/multi-dataset/your_tts"
tts = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=True)

@app.post("/cache_user_voice")
async def cache_user_voice(user_id: str):
    """Generate and cache speaker embedding for a user."""
    try:
        user_voice_path = get_user_voice_path(user_id)
        speaker_embedding = tts.get_speaker_embedding(user_voice_path)
        
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

@app.get("/cache_status/{user_id}")
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

@app.delete("/clear_user_cache/{user_id}")
async def clear_user_cache(user_id: str):
    """Clear cached speaker embedding for a user."""
    deleted = cache_manager.delete_speaker_embedding(user_id)
    return {
        "status": "success" if deleted else "not_found",
        "message": f"Speaker embedding {'cleared' if deleted else 'not found'} for user {user_id}"
    }

@app.post("/cleanup_cache")
async def cleanup_expired_cache():
    """Manually cleanup expired cache entries (MongoDB only)."""
    cleaned = cache_manager.cleanup_expired()
    return {
        "status": "success",
        "cleaned_entries": cleaned,
        "message": f"Cleaned up {cleaned} expired entries"
    }

def generate_meditation_audio(user_id: str, task: str, selected_emotion: str, selected_tone: str, min_length: int, background_options: dict):
    # 1. Get cached speaker embedding
    speaker_embedding = cache_manager.get_cached_speaker_embedding(user_id)

    # 2. Load pre-defined emotion embedding (these should be precomputed & saved as .npy files)
    emotion_embedding = get_user_emotion_embedding(selected_tone)
    is_premium = get_user_tier(user_id) == "premium"
    if task == "release":
        if selected_tone in [None, "None", "none"]:
            selected_tone = "passionate"
        text = get_meditation_text("release", selected_emotion, selected_tone, min_length, is_premium)
    elif task == "sleep":
        text = get_meditation_text("sleep", selected_emotion, selected_tone, min_length, is_premium)
    elif task == "mindfulness":
        text = get_meditation_text("mindfulness", selected_emotion, selected_tone, min_length, is_premium)
    elif task == "workout":
        if selected_tone in [None, "None", "none"]:
            selected_tone = "energetic"
        text = get_meditation_text("workout", selected_emotion, selected_tone, min_length, is_premium)

    emotion_embedding = get_user_emotion_embedding(selected_tone)
    
    # 4. Generate the emotional, speaker-cloned audio
    output_path = f"output_{task}_meditation_{user_id}.wav"
    tts.tts_to_file(
        text=text,
        speaker_embedding=speaker_embedding,
        style_wav=None,  # Optional: could be an emotional style reference instead of embedding
        emotion_embedding=emotion_embedding,  # Only works if the model supports it
        file_path=output_path
    )

    return output_path
    

@app.post("/generate_release_meditation_audio")
async def generate_release_meditation_audio(user_id: str, selected_emotion: str, selected_tone: str, min_length: int, background_options: dict):
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, "release", selected_emotion, selected_tone, min_length, background_options)

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

    return {"status": "success", "audio_path": combined_audio_path}

@app.post("/generate_sleep_meditation_audio")
async def generate_sleep_meditation_audio(user_id: str, min_length: int, background_options: dict):
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, "sleep", None, "calm", min_length, background_options)

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

    return {"status": "success", "audio_path": combined_audio_path}

@app.post("/generate_mindfulness_meditation_audio")
async def generate_mindfulness_meditation_audio(user_id: str, min_length: int, background_options: dict):
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, "mindfulness", None, "calm", min_length, background_options)

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

    return {"status": "success", "audio_path": combined_audio_path}

@app.post("/generate_workout_meditation_audio")
async def generate_workout_meditation_audio(user_id: str, selected_tone: str, min_length: int, background_options: dict, **kwargs):
    # Generate the emotional, speaker-cloned audio
    output_path = generate_meditation_audio(user_id, "workout", None, selected_tone, min_length, background_options)

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

    return {"status": "success", "audio_path": combined_audio_path}

