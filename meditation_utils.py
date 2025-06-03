import numpy as np
from huggingface_hub import InferenceClient
from pymongo import MongoClient

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
