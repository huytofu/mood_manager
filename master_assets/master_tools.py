from master_chains.analyze_emotion_chain import analyze_emotion_chain
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Dict, Any

class EmotionalAnalysisInput(BaseModel):
    message: str = Field(..., description="User's emotional expression or intent in natural language")

# =============================================================================
# MASTER TOOLS
# =============================================================================

@tool("analyze_emotional_state", args_schema=EmotionalAnalysisInput)
def analyze_emotional_state(message: str) -> Dict[str, Any]:
    """
    Tool Purpose: Analyze user's emotional state from their intent and context to detect emotions, intensity, and crisis indicators.
    
    Args:
    - message (str): User's emotional expression or request in natural language (e.g., "I feel angry but can't express it")
    
    Returns:
    - Dict containing: intent (str), is_crisis (bool), selected_emotion (str)
    This can be values to the emotional_analysis field in the InterventionPlanInput, AudioParamsInput, CrisisHandlingInput and RecommendationsInput schemas.
    """
    message_lowered = message.lower()
    
    detections = analyze_emotion_chain.invoke(message_lowered)

    intent = detections.intent
    is_crisis = detections.is_crisis
    selected_emotion = detections.selected_emotion
    
    return {
        "intent": intent,
        "is_crisis": is_crisis,
        "selected_emotion": selected_emotion,
    }