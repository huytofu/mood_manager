import numpy as np
import uuid
from huggingface_hub import InferenceClient
from pymongo import MongoClient
from cache.cache_manager import cache_manager
from mongo_user_manager import mongo_user_manager
from mongo_audio_manager import mongo_audio_manager

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

def get_meditation_text(task, emotion, tone, min_length, is_premium=True):
    # get meditation text from meditation_texts folder
    # return meditation text
    if is_premium:
        return get_ai_meditation_text(emotion, tone, task, min_length)
    else:
        return get_default_meditation_text(emotion, tone, task)

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

    # 2. Load pre-defined emotion embedding (these should be precomputed & saved as .npy files)
    emotion_embedding = get_user_emotion_embedding(selected_tone)
    is_premium = mongo_user_manager.get_user_tier(user_id) == "premium"
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
    output_uuid = str(uuid.uuid4())
    output_path = f"assets/{user_id}/output_{task}_meditation_{output_uuid}.wav"
    tts_model.tts_to_file(
        text=text,
        speaker_embedding=speaker_embedding,
        style_wav=None,  # Optional: could be an emotional style reference instead of embedding
        emotion_embedding=emotion_embedding,  # Only works if the model supports it
        file_path=output_path
    )
    _, __ = mongo_audio_manager.store_message_audio(user_id, output_uuid, task, min_length, selected_tone, selected_emotion, output_path)

    return output_path, output_uuid