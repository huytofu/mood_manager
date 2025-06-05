import numpy as np
import random
import uuid
import os
from mongo_user_manager import mongo_user_manager
from pydub import AudioSegment
from audiocraft.models import musicgen
from audiocraft.data.audio import audio_write
from mongo_audio_manager import mongo_audio_manager


def generate_brainwave(user_id, wave_type, volume_magnitude: str = "low", duration_sec=120, sample_rate=44100):
    # check if brainwave audio path exists in database for this user and wave type and volume magnitude
    doc = mongo_audio_manager.get_brainwave_audio(user_id, wave_type, volume_magnitude)
    if doc and doc.get("file_exists", False):
        return doc["audio_path"]
    
    wave_frequencies = {
        "alpha": 8.0,
        "beta": 12.0,
        "delta": 0.5,
        "theta": 4.0,
        "gamma": 30.0
    }
    volume_magnitudes = {
        "low": -20,
        "medium": -10,
        "high": 0
    }
    frequency = wave_frequencies.get(wave_type)
    volume = volume_magnitudes.get(volume_magnitude)
    is_premium = mongo_user_manager.get_user_tier(user_id) == "premium"
    if is_premium:
        duration_sec = 600
    else:
        duration_sec = 120
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    wave = np.sin(2 * np.pi * frequency * t)

    # Convert to 16-bit audio
    audio = np.int16(wave * 32767)
    segment = AudioSegment(audio.tobytes(), frame_rate=sample_rate, sample_width=2, channels=1)
    final_segment = segment + volume

    if not os.path.exists(f"assets/{user_id}"):
        os.makedirs(f"assets/{user_id}")

    uuid_id = str(uuid.uuid4())[:8]
    output_path = f"assets/{user_id}/brainwave_{wave_type}_{volume_magnitude}_{uuid_id}.wav"
    final_segment.export(output_path, format="wav")
    
    mongo_audio_manager.store_brainwave_audio(user_id, uuid_id, wave_type, volume_magnitude, output_path)

    return output_path, uuid_id

def generate_background_music(user_id, task, music_style, duration_sec=120):
    """Generate background music and store metadata in MongoDB."""
    is_premium = mongo_user_manager.get_user_tier(user_id) == "premium"
    if is_premium:
        model = musicgen.MusicGen.get_pretrained('large')  # use 'small' for faster generation
        duration_sec = 600
    else:
        model = musicgen.MusicGen.get_pretrained('medium')  # use 'small' for faster generation
        duration_sec = 120

    model.set_generation_params(duration=duration_sec)  # 60 seconds of music

    if task == "release":
        instrument_choices = {
            0: "soft flutes",
            1: "piano",
            2: "violin",
            3: "cello",
            4: "string guitar",
            5: "harp"  
        }
    elif task == "sleep":
        instrument_choices = {
            1: "piano",
            2: "harp",
        }
    elif task == "workout":
        instrument_choices = {
            0: "electric guitar",
            1: "drums",
            2: "bass",
            3: "saxophone",
            4: "edm"
        }
    elif task == "mindfulness":
        instrument_choices = {
            0: "soft flutes",
            1: "piano",
            2: "violin",
            3: "cello",
            4: "harp"
        }

    instruments = []
    for mix in range(2,4):
        instrument = instrument_choices.get(random.randint(0, len(instrument_choices) - 1))
        instruments.append(instrument)

    prompt = f"calm ambient meditation instrumental music with pads and a mix of {', '.join(instruments)} in the style of {music_style}"
    wav = model.generate([prompt])  # returns list of np arrays

    if not os.path.exists(f"assets/{user_id}"):
        os.makedirs(f"assets/{user_id}")

    uuid_id = str(uuid.uuid4())[:8]
    output_path = f"assets/{user_id}/background_music_{task}_{uuid_id}.wav"
    audio_write(output_path, wav[0].cpu(), model.sample_rate, strategy="loudness")

    mongo_audio_manager.store_music_audio(user_id, uuid_id, task, music_style, output_path)
    
    return output_path, uuid_id

def combine_audio(user_id, task, output_path, background_music_path, brain_waves_path, output_uuid, background_music_uuid, brain_waves_uuid):
    """Combine audio components and create session record."""
    # Load all components
    voice = AudioSegment.from_wav(output_path)
    music = AudioSegment.from_wav(background_music_path)
    brainwave = AudioSegment.from_wav(brain_waves_path)

    # Settings
    voice_duration = len(voice)  # in ms
    fade_duration = 6000         # 6 seconds fade out

    # Trim music and brainwave to voice length + fade
    max_duration = voice_duration + fade_duration
    music = music[:max_duration]
    brainwave = brainwave[:max_duration]

    # Apply fade out to music and brainwave
    music = music.fade_out(fade_duration)
    brainwave = brainwave.fade_out(fade_duration)

    # Mix music and brainwave first (background)
    background = music.overlay(brainwave - 10)  # reduce brainwave volume a bit

    # Overlay voice at the beginning
    final_mix = background.overlay(voice, position=0)

    if not os.path.exists(f"assets/{user_id}"):
        os.makedirs(f"assets/{user_id}")

    uuid_id = str(uuid.uuid4())[:8]
    final_mix_path = f"assets/{user_id}/final_meditation_mix_{task}_{uuid_id}.wav"
    final_mix.export(final_mix_path, format="wav")

    # Store final audio metadata
    components = {
        "message_audio_id": output_uuid,
        "background_music_id": background_music_uuid,
        "brain_waves_id": brain_waves_uuid,
        "emotional_audio_path": output_path,
        "background_music_path": background_music_path,
        "brain_waves_path": brain_waves_path
    }
    mongo_audio_manager.store_final_audio(user_id, uuid_id, task, components, final_mix_path)
    
    return final_mix_path, uuid_id
