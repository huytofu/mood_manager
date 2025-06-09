from fastapi import APIRouter, Depends
from utils.meditation_utils import generate_meditation_audio, generate_meditation_audio_advanced
from utils.background_utils import generate_background_music, generate_brainwave, combine_audio
from utils.dependencies import get_tts_model
from typing import Any

router = APIRouter(tags=["audio"])

async def _generate_release_meditation_audio(user_id: str, selected_emotion: str, selected_tone: str, min_length: int, background_options: dict, tts_model: Any, use_advanced_tts: bool = True):
    # Generate the emotional, speaker-cloned audio with advanced controls
    if use_advanced_tts:
        output_path, output_uuid = generate_meditation_audio_advanced(user_id, tts_model, "release", selected_emotion, selected_tone, min_length, use_advanced_control=True)
    else:
        output_path, output_uuid = generate_meditation_audio(user_id, tts_model, "release", selected_emotion, selected_tone, min_length)

    background_music_path = None
    brain_waves_path = None
    background_music_uuid = None
    brain_waves_uuid = None

    # 5. Generate background music
    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]
    
    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    brain_waves_type = background_options["brain_waves_type"]
    volume_magnitude = background_options["volume_magnitude"]

    if should_generate_background_music:
        background_music_path, background_music_uuid = generate_background_music(user_id, "release", music_style)

    if should_generate_brain_waves:
        brain_waves_path, brain_waves_uuid = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path, combined_audio_uuid = combine_audio(user_id, "release", output_path, background_music_path, brain_waves_path, output_uuid, background_music_uuid, brain_waves_uuid)

    return {"status": "success", "output_audio_path": combined_audio_path, "output_audio_uuid": combined_audio_uuid}

async def _generate_sleep_meditation_audio(user_id: str, min_length: int, background_options: dict, tts_model: Any, use_advanced_tts: bool = True):
    # Generate the emotional, speaker-cloned audio with advanced controls
    if use_advanced_tts:
        output_path, output_uuid = generate_meditation_audio_advanced(user_id, tts_model, "sleep", None, "calm", min_length, use_advanced_control=True)
    else:
        output_path, output_uuid = generate_meditation_audio(user_id, tts_model, "sleep", None, "calm", min_length)

    background_music_path = None
    brain_waves_path = None
    background_music_uuid = None
    brain_waves_uuid = None
    
    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path, background_music_uuid = generate_background_music(user_id, "sleep", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "theta" #Suitable for sleep
        volume_magnitude = "low" #Suitable for sleep
        brain_waves_path, brain_waves_uuid = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path, combined_audio_uuid = combine_audio(user_id, "sleep", output_path, background_music_path, brain_waves_path, output_uuid, background_music_uuid, brain_waves_uuid)

    return {"status": "success", "output_audio_path": combined_audio_path, "output_audio_uuid": combined_audio_uuid}

async def _generate_mindfulness_meditation_audio(user_id: str, min_length: int, background_options: dict, tts_model: Any, use_advanced_tts: bool = True):
    # Generate the emotional, speaker-cloned audio with advanced controls
    if use_advanced_tts:
        output_path, output_uuid = generate_meditation_audio_advanced(user_id, tts_model, "mindfulness", None, "calm", min_length, use_advanced_control=True)
    else:
        output_path, output_uuid = generate_meditation_audio(user_id, tts_model, "mindfulness", None, "calm", min_length)

    background_music_path = None
    brain_waves_path = None
    background_music_uuid = None
    brain_waves_uuid = None

    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path, background_music_uuid = generate_background_music(user_id, "mindfulness", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "alpha" #Suitable for mindfulness
        volume_magnitude = "low" #Suitable for mindfulness
        brain_waves_path, brain_waves_uuid = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path, combined_audio_uuid = combine_audio(user_id, "mindfulness", output_path, background_music_path, brain_waves_path, output_uuid, background_music_uuid, brain_waves_uuid)

    return {"status": "success", "output_audio_path": combined_audio_path, "output_audio_uuid": combined_audio_uuid}

async def _generate_workout_meditation_audio(user_id: str, selected_tone: str, min_length: int, background_options: dict, tts_model: Any, use_advanced_tts: bool = True):
    # Generate the emotional, speaker-cloned audio with advanced controls
    if use_advanced_tts:
        output_path, output_uuid = generate_meditation_audio_advanced(user_id, tts_model, "workout", None, selected_tone, min_length, use_advanced_control=True)
    else:
        output_path, output_uuid = generate_meditation_audio(user_id, tts_model, "workout", None, selected_tone, min_length)

    background_music_path = None
    brain_waves_path = None
    background_music_uuid = None
    brain_waves_uuid = None

    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path, background_music_uuid = generate_background_music(user_id, "workout", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "beta" #Suitable for workout
        volume_magnitude = background_options["volume_magnitude"] or "high" #Suitable for workout
        brain_waves_path, brain_waves_uuid = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    # 6. Combine the emotional, speaker-cloned audio with the background music and brain waves
    combined_audio_path, combined_audio_uuid = combine_audio(user_id, "workout", output_path, background_music_path, brain_waves_path, output_uuid, background_music_uuid, brain_waves_uuid)

    return {"status": "success", "output_audio_path": combined_audio_path, "output_audio_uuid": combined_audio_uuid}

async def _generate_crisis_meditation_audio(user_id: str, selected_tone: str, min_length: int, background_options: dict, tts_model: Any, use_advanced_tts: bool = True):
    # Generate the emotional, speaker-cloned audio with advanced controls
    if use_advanced_tts:
        output_path, output_uuid = generate_meditation_audio_advanced(user_id, tts_model, "crisis", None, selected_tone, min_length, use_advanced_control=True)
    else:
        output_path, output_uuid = generate_meditation_audio(user_id, tts_model, "crisis", None, selected_tone, min_length)

    background_music_path = None
    brain_waves_path = None
    background_music_uuid = None
    brain_waves_uuid = None

    should_generate_background_music = background_options["should_generate_background_music"]
    music_style = background_options["music_style"]

    if should_generate_background_music:
        background_music_path, background_music_uuid = generate_background_music(user_id, "crisis", music_style)

    should_generate_brain_waves = background_options["should_generate_brain_waves"]
    if should_generate_brain_waves:
        brain_waves_type = "alpha" #Suitable for crisis
        volume_magnitude = "low" #Suitable for crisis
        brain_waves_path, brain_waves_uuid = generate_brainwave(user_id, brain_waves_type, volume_magnitude)

    combined_audio_path, combined_audio_uuid = combine_audio(user_id, "crisis", output_path, background_music_path, brain_waves_path, output_uuid, background_music_uuid, brain_waves_uuid)
    return {"status": "success", "output_audio_path": combined_audio_path, "output_audio_uuid": combined_audio_uuid}

@router.post("/generate_release_meditation_audio",
        operation_id="generate_release_meditation_audio",
        description='''
        Generate a release meditation audio with AI-generated strategic pauses and optional speed/temperature control.
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
            use_advanced_tts: bool (optional, default True - enables speed and temperature control for more natural pacing)
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_release_meditation_audio(user_id: str, selected_emotion: str, selected_tone: str, min_length: int, background_options: dict, use_advanced_tts: bool = True, tts_model=Depends(get_tts_model)):
    """Generate a release meditation audio with AI-generated pauses and optional advanced TTS controls."""
    return await _generate_release_meditation_audio(user_id, selected_emotion, selected_tone, min_length, background_options, tts_model, use_advanced_tts)

@router.post("/generate_sleep_meditation_audio",
        operation_id="generate_sleep_meditation_audio",
        description='''
        Generate a sleep meditation audio with AI-generated strategic pauses and optional speed/temperature control.
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
            use_advanced_tts: bool (optional, default True - enables slower speech rate for better sleep meditation)
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_sleep_meditation_audio(user_id: str, min_length: int, background_options: dict, use_advanced_tts: bool = True, tts_model=Depends(get_tts_model)):
    """Generate a sleep meditation audio with AI-generated pauses and optional advanced TTS controls."""
    return await _generate_sleep_meditation_audio(user_id, min_length, background_options, tts_model, use_advanced_tts)

@router.post("/generate_mindfulness_meditation_audio",
        operation_id="generate_mindfulness_meditation_audio",
        description='''
        Generate a mindfulness meditation audio with AI-generated pauses and optional advanced TTS controls.
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
            use_advanced_tts: bool (optional, default True - enables speed and temperature control for more natural pacing)
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_mindfulness_meditation_audio(user_id: str, min_length: int, background_options: dict, use_advanced_tts: bool = True, tts_model=Depends(get_tts_model)):
    """Generate a mindfulness meditation audio with AI-generated pauses and optional advanced TTS controls."""
    return await _generate_mindfulness_meditation_audio(user_id, min_length, background_options, tts_model, use_advanced_tts)

@router.post("/generate_workout_meditation_audio",
        operation_id="generate_workout_meditation_audio",
        description='''
        Generate a workout meditation audio with AI-generated pauses and optional advanced TTS controls.
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
            use_advanced_tts: bool (optional, default True - enables speed and temperature control for more natural pacing)
        Returns:
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_workout_meditation_audio(user_id: str, selected_tone: str, min_length: int, background_options: dict, use_advanced_tts: bool = True, tts_model=Depends(get_tts_model)):
    """Generate a workout meditation audio with AI-generated pauses and optional advanced TTS controls."""
    return await _generate_workout_meditation_audio(user_id, selected_tone, min_length, background_options, tts_model, use_advanced_tts)

@router.post("/generate_crisis_meditation_audio",
        operation_id="generate_crisis_meditation_audio",
        description='''
        Generate a crisis meditation audio with AI-generated pauses and optional advanced TTS controls.
        Args:
            user_id: str
            selected_tone: str (user-selected tone for message)
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
            use_advanced_tts: bool (optional, default True - enables speed and temperature control for more natural pacing)
        Returns:    
            a dictionary with properties `status`, `output_audio_path`
        ''',
        response_description="a dictionary with properties `status`, `output_audio_path` if successful, or an error message if not")
async def generate_crisis_meditation_audio(user_id: str, selected_tone: str, min_length: int, background_options: dict, use_advanced_tts: bool = True, tts_model=Depends(get_tts_model)):
    """Generate a crisis meditation audio with AI-generated pauses and optional advanced TTS controls."""
    return await _generate_crisis_meditation_audio(user_id, selected_tone, min_length, background_options, tts_model, use_advanced_tts)