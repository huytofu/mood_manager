import numpy as np
import uuid
import re
import torch
import torchaudio
from huggingface_hub import InferenceClient
from pymongo import MongoClient
from cache.cache_manager import cache_manager
from database.mongo_user_manager import mongo_user_manager
from database.mongo_audio_manager import mongo_audio_manager

with open("prompts/release_prompt_template.txt", "r") as file:
    release_prompt_template = file.read()
with open("prompts/sleep_prompt_template.txt", "r") as file:
    sleep_prompt_template = file.read()
with open("prompts/workout_prompt_template.txt", "r") as file:
    workout_prompt_template = file.read()
with open("prompts/mindfulness_prompt_template.txt", "r") as file:
    mindfulness_prompt_template = file.read()

def get_user_emotion_embedding(emotion):
    # get user's selected emotion embedding from emotion_embeddings folder
    # return emotion embedding
    emotion_embeddings = {
    "happy": np.load("emotion_embeddings/happy.npy"),
    "sad": np.load("emotion_embeddings/sad.npy"),
    "angry": np.load("emotion_embeddings/angry.npy"),
    "calm": np.load("emotion_embeddings/calm.npy"),
    }
    emotion_embedding = emotion_embeddings[emotion]
    return emotion_embedding

def convert_pause_tags_to_xtts(text):
    """
    Convert AI-generated pause tags to XTTS-compatible pause markers.
    
    Args:
        text (str): Text with <pause:Xs> tags
        
    Returns:
        str: Text with XTTS-compatible pause markers
    """
    if not text:
        return text
    
    # Convert <pause:Xs> tags to multiple periods for natural pauses
    # XTTS interprets multiple periods as pauses of varying lengths
    def replace_pause_tag(match):
        duration = match.group(1)
        seconds = int(duration.replace('s', ''))
        
        # Convert seconds to period-based pauses that XTTS understands
        if seconds <= 1:
            return "."  # Brief pause
        elif seconds <= 2:
            return ".."  # Short pause
        elif seconds <= 3:
            return "..."  # Medium pause
        elif seconds <= 5:
            return "...."  # Long pause
        elif seconds <= 8:
            return "....."  # Extended pause
        else:
            return "......"  # Very long pause
    
    # Replace all <pause:Xs> patterns
    text = re.sub(r'<pause:(\d+s?)>', replace_pause_tag, text)
    
    return text

def enhance_meditation_text_with_pauses(text, task: str):
    """
    Enhance meditation text with pauses and timing markers for more natural meditation pacing.
    This function now works in combination with AI-generated pause tags.
    
    Args:
        text (str): The original meditation text (may already contain AI-generated pause tags)
        task (str): Type of meditation (release, sleep, workout, mindfulness, crisis)
    
    Returns:
        str: Enhanced text with pause markers
    """
    if not text:
        return text
    
    # First convert AI-generated pause tags to XTTS format
    text = convert_pause_tags_to_xtts(text)
    
    # Additional enhancements for cases where AI didn't add enough pauses
    # Only add these if the text doesn't already have sufficient pauses
    pause_count = text.count('.')
    word_count = len(text.split())
    pause_ratio = pause_count / word_count if word_count > 0 else 0
    
    # If pause ratio is low, add some basic enhancements
    if pause_ratio < 0.1:  # Less than 10% pause markers
        if task in ["sleep", "mindfulness"]:
            # Slower, more contemplative pacing
            text = text.replace('. ', '. ... ')  # Long pauses after sentences
            text = text.replace(', ', ', . ')     # Brief pauses after commas
            text = text.replace('\n\n', '\n\n..... \n\n')  # Extended pauses between paragraphs
            
        elif task == "crisis":
            # Gentle, compassionate pacing
            text = text.replace('. ', '. .. ')    # Medium pauses
            text = text.replace('\n\n', '\n\n.. \n\n')  # Gentle paragraph breaks
            
        elif task == "workout":
            # More energetic, but still allowing for breath
            text = text.replace('. ', '. . ')     # Short pauses
            text = text.replace('!', '! . ')      # Brief pause after exclamations
            
        elif task == "release":
            # Balanced pacing for emotional processing
            text = text.replace('. ', '. .. ')    # Medium pauses
            text = text.replace('...', '.... ')   # Extended contemplative pauses
    
    # Ensure proper opening and closing
    if not text.startswith('.'):
        text = f".. {text}"  # Add introductory pause
    
    if not text.endswith('.'):
        text = f"{text} ....."  # Add closing pause
    
    return text

def get_meditation_text_and_tone(task: str, selected_emotion: str, selected_tone: str, min_length: int, is_premium: bool = True):
    """
    Centralized function to get meditation text and normalize tone based on task type.
    
    Args:
        task (str): Type of meditation (release, sleep, workout, mindfulness, crisis)
        selected_emotion (str): User-selected emotion
        selected_tone (str): User-selected tone
        min_length (int): Minimum length in minutes
        is_premium (bool): Whether user has premium access
    
    Returns:
        tuple: (text, normalized_tone)
    """
    # Normalize tone based on task
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
    elif task == "crisis":
        if selected_tone in [None, "None", "none"]:
            selected_tone = "compassionate"
        text = get_meditation_text("crisis", selected_emotion, selected_tone, min_length, is_premium)
    else:
        text = "I love you 3000"
    
    return text, selected_tone

def get_meditation_text(task, emotion, tone, min_length, is_premium=True):
    # get meditation text from meditation_texts folder
    # return meditation text
    if is_premium:
        raw_text = get_ai_meditation_text(emotion, tone, task, min_length)
    else:
        raw_text = get_default_meditation_text(emotion, tone, task)
    
    # Enhance text with pauses for better meditation experience
    if raw_text:
        enhanced_text = enhance_meditation_text_with_pauses(raw_text, task)
        return enhanced_text
    
    return raw_text

def get_default_meditation_text(emotion, tone, task: str):
    # get from database the default meditation text for the emotion
    if task == "release":
        text = MongoClient.db.release_meditation_texts.find_one({"emotion": emotion, "tone": tone})
    elif task == "sleep":
        text = MongoClient.db.sleep_meditation_texts.find_one({"emotion": emotion, "tone": tone})
    elif task == "workout":
        text = MongoClient.db.workout_meditation_texts.find_one({"emotion": emotion, "tone": tone})
    elif task == "mindfulness":
        text = MongoClient.db.mindfulness_meditation_texts.find_one({"emotion": emotion, "tone": tone})
    else:
        text = None
    # return default meditation text
    return text

def get_ai_meditation_text(emotion, tone, task: str, min_length: int, **kwargs):
    if task == "release":
        prompt = release_prompt_template.format(emotion=emotion, tone=tone, minutes=min_length)
        messages = [{
            "role": "user",
            "content": prompt
        }]
        response = InferenceClient.chat_completion(
            model="deepseek-ai/DeepSeek-V3",
            messages=messages,
        )
        return response.choices[0].message.content
    elif task == "sleep":
        prompt = sleep_prompt_template.format(tone=tone, minutes=min_length)
        messages = [{
            "role": "user",
            "content": prompt
        }]
        response = InferenceClient.chat_completion(
            model="deepseek-ai/DeepSeek-V3",
            messages=messages,
        )
        return response.choices[0].message.content
    elif task == "mindfulness":
        prompt = mindfulness_prompt_template.format(tone=tone, minutes=min_length)
        messages = [{
            "role": "user",
            "content": prompt
        }]
        response = InferenceClient.chat_completion(
            model="deepseek-ai/DeepSeek-V3",
            messages=messages,
        )
        return response.choices[0].message.content
    elif task == "workout":
        if "person_style" in kwargs:
            person_style = kwargs["person_style"]
        else:
            person_style = "Bruce Lee"
        prompt = workout_prompt_template.format(person_style=person_style, tone=tone, minutes=min_length)
        messages = [{
            "role": "user",
            "content": prompt
        }]
        response = InferenceClient.chat_completion(
            model="deepseek-ai/DeepSeek-V3",
            messages=messages,
        )
        return response.choices[0].message.content
    else:
        return None

def generate_meditation_audio(user_id: str, tts_model, task: str, selected_emotion: str, selected_tone: str, min_length: int):
    # 1. Get cached speaker embedding
    speaker_embedding = cache_manager.get_cached_speaker_embedding(user_id)

    # 2. Get meditation text and normalized tone using centralized function
    is_premium = mongo_user_manager.get_user_tier(user_id) == "premium"
    text, selected_tone = get_meditation_text_and_tone(task, selected_emotion, selected_tone, min_length, is_premium)

    # 3. Load pre-defined emotion embedding
    emotion_embedding = get_user_emotion_embedding(selected_tone)
    
    # 4. Generate the emotional, speaker-cloned audio with XTTS parameters
    output_uuid = str(uuid.uuid4())
    output_path = f"assets/{user_id}/output_{task}_meditation_{output_uuid}.wav"
    
    # XTTS tts_to_file API parameters
    tts_kwargs = {
        "text": text,
        "file_path": output_path,
        "language": "en",
        "split_sentences": True  # Helps with pause interpretation
    }
    
    # Handle speaker embedding - XTTS API expects wav files, not embeddings
    # For now, we'll use a simpler approach compatible with XTTS API
    try:
        # Try to use speaker embedding if available as wav file path
        if isinstance(speaker_embedding, str):  # If it's a file path
            tts_kwargs["speaker_wav"] = [speaker_embedding]
        
        # Try to add emotion embedding if the model supports it
        # Note: This may not work with standard XTTS API, but we'll try
        if emotion_embedding is not None:
            tts_kwargs["emotion_embedding"] = emotion_embedding
            
        tts_model.tts_to_file(**tts_kwargs)
    except Exception as e:
        # Fallback to basic XTTS call if advanced features fail
        print(f"Warning: Advanced features failed, using basic XTTS: {e}")
        tts_model.tts_to_file(
            text=text,
            file_path=output_path,
            language="en",
            split_sentences=True
        )
    
    _, __ = mongo_audio_manager.store_message_audio(user_id, output_uuid, task, min_length, selected_tone, selected_emotion, output_path)

    return output_path, output_uuid

def generate_meditation_audio_advanced(user_id: str, tts_model, task: str, selected_emotion: str, selected_tone: str, min_length: int, use_advanced_control=True):
    """
    Advanced meditation audio generation with speed and temperature control using XTTS manual inference.
    
    Args:
        user_id (str): User identifier
        tts_model: The XTTS model instance
        task (str): Type of meditation
        selected_emotion (str): Selected emotion
        selected_tone (str): Selected tone
        min_length (int): Minimum length in minutes
        use_advanced_control (bool): Whether to use advanced speed/temperature control
    
    Returns:
        tuple: (output_path, output_uuid)
    """
    try:
        from TTS.tts.configs.xtts_config import XttsConfig
        from TTS.tts.models.xtts import Xtts
        
        # Get meditation text and normalized tone using centralized function
        is_premium = mongo_user_manager.get_user_tier(user_id) == "premium"
        text, selected_tone = get_meditation_text_and_tone(task, selected_emotion, selected_tone, min_length, is_premium)
        
        # Get emotion embedding
        emotion_embedding = get_user_emotion_embedding(selected_tone)
        
        # Get speaker reference (assuming we have a way to get the user's reference audio)
        user_voice_path = f"assets/{user_id}/user_voice.wav"  # This should be the cached user voice
        
        # Manual XTTS inference with advanced controls
        if hasattr(tts_model, 'get_conditioning_latents') and use_advanced_control:
            # Get conditioning latents from user voice
            gpt_cond_latent, speaker_embedding = tts_model.get_conditioning_latents(audio_path=[user_voice_path])
            
            # Set parameters based on meditation type
            if task in ["sleep", "mindfulness"]:
                temperature = 0.65  # More stable, calmer speech
                speed = 0.8         # Slower speech rate
            elif task == "workout":
                temperature = 0.85  # More dynamic speech
                speed = 1.1         # Slightly faster pace
            else:  # release, crisis
                temperature = 0.75  # Balanced
                speed = 0.9         # Slightly slower than normal
            
            # Generate audio with manual inference
            inference_kwargs = {
                "text": text,
                "language": "en",
                "gpt_cond_latent": gpt_cond_latent,
                "speaker_embedding": speaker_embedding,
                "temperature": temperature,
                "speed": speed,
                "enable_text_splitting": True
            }
            
            # Try to add emotion embedding if supported
            try:
                if emotion_embedding is not None:
                    inference_kwargs["emotion_embedding"] = emotion_embedding
            except:
                # Emotion embedding not supported in this version
                pass
            
            out = tts_model.inference(**inference_kwargs)
            
            # Save the audio
            output_uuid = str(uuid.uuid4())
            output_path = f"assets/{user_id}/output_{task}_meditation_{output_uuid}.wav"
            torchaudio.save(output_path, torch.tensor(out["wav"]).unsqueeze(0), 24000)
            
        else:
            # Fallback to regular generation
            return generate_meditation_audio(user_id, tts_model, task, selected_emotion, selected_tone, min_length)
        
        _, __ = mongo_audio_manager.store_message_audio(user_id, output_uuid, task, min_length, selected_tone, selected_emotion, output_path)
        return output_path, output_uuid
        
    except Exception as e:
        print(f"Advanced XTTS generation failed, falling back to standard method: {e}")
        return generate_meditation_audio(user_id, tts_model, task, selected_emotion, selected_tone, min_length)