from huggingface_hub import InferenceClient
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
import os

model = InferenceClient(
    repo_id="meta-llama/Llama-3.1-70B-Instruct",
    token=os.getenv("HF_TOKEN")
)

class AnalyzedEmotionOutput(BaseModel):
    """
    This is the output of the analyze_emotion_chain.
    It is a dictionary with the following keys:
    - intent: The intent of the user. Should be one of the following:
        - "release meditation"
        - "sleep meditation"
        - "workout meditation"
        - "mindfulness meditation"
    - is_crisis: Whether the user is in a crisis.
    - selected_emotion: The emotion that the user wants to release.
    """
    intent: str
    is_crisis: bool
    selected_emotion: str

prompt = """
    You are a helpful assistant that analyzes the emotion of a user's intent.
    You will be given a user's chat message.
    You will need to deduce the intent from the user's message.
    You must pick the most likely intent from the following list:
    - "release meditation"
    - "sleep meditation"
    - "workout meditation"
    - "mindfulness meditation"
    
    If you identify that the intent is release meditation, 
    you will need to select the emotion that the user wants to release.
    The selected emotion should be one of the following:
    - "anger"
    - "sadness"
    - "fear"
    - "guilt"
    - "grief"
    - "desire"

    You will also need to determine if the user is in a crisis.
    If the user is in a crisis, you will need to return "crisis meditation" as the intent and is_crisis as true.

    You will need to return the intent, is_crisis, and selected_emotion in the following JSON format:
    
    {{
        "intent": "your_selected_intent",
        "is_crisis": true/false,
        "selected_emotion": "your_selected_emotion"
    }}

    Example 1:
    User: I feel angry but can't express it
    You: {{
        "intent": "release meditation",
        "is_crisis": false,
        "selected_emotion": "anger"
    }}
    Example 2:
    User: I'm feeling really anxious about my presentation tomorrow. I would love to feel more confident.
    You: {{
        "intent": "sleep meditation",
        "is_crisis": false,
        "selected_emotion": None
    }}
    Example 3:
    User: I'm having a panic attack
    You: {{
        "intent": "crisis meditation",
        "is_crisis": true,
        "selected_emotion": None
    }}
"""

messages = ChatPromptTemplate.from_messages([
    ("system", prompt),
    ("user", "{input}")
])

analyze_emotion_chain = messages | model.with_structured_output(AnalyzedEmotionOutput)








