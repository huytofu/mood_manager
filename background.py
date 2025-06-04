import numpy as np
import random
from user_utils import get_user_tier
from pydub import AudioSegment
from audiocraft.models import musicgen
from audiocraft.data.audio import audio_write

def generate_brainwave(user_id, wave_type, volume_magnitude: str = "low", duration_sec=120, sample_rate=44100):
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
    is_premium = get_user_tier(user_id) == "premium"
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
    final_segment.export(f"brainwave_{user_id}.wav", format="wav")
    return f"brainwave_{user_id}.wav"

def generate_background_music(user_id, task, music_style, duration_sec=120):
    # generate background music
    # return background music path
    is_premium = get_user_tier(user_id) == "premium"
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

    audio_write(f"background_music_{user_id}", wav[0].cpu(), model.sample_rate, strategy="loudness")

    return f"background_music_{user_id}.wav"

def combine_audio(user_id, emotional_audio_path, background_music_path, brain_waves_path):
    # combine emotional audio, background music, and brain waves
    # return combined audio path
    # Load all components
    voice = AudioSegment.from_wav(emotional_audio_path)
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

    # Export final result
    final_mix.export(f"final_meditation_mix_{user_id}.wav", format="wav")

    return f"final_meditation_{user_id}.wav"
