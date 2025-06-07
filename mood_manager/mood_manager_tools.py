from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Import router functions for direct calls
from routers.cache_router import (
    _cache_user_voice, 
    _get_cache_status, 
    _clear_user_cache
)
from routers.audio_router import (
    _generate_release_meditation_audio,
    _generate_sleep_meditation_audio, 
    _generate_mindfulness_meditation_audio,
    _generate_workout_meditation_audio,
    _generate_crisis_meditation_audio
)
# =============================================================================
# TOOL SCHEMAS
# =============================================================================

class InterventionPlanInput(BaseModel):
    intent: str = Field(..., description="Master Manager's intent/instruction for mood management")
    context: Dict[str, Any] = Field(..., description="Additional context including user preferences")
    user_data: Dict[str, Any] = Field(..., description="User data including emotional analysis from Master Manager")

class AudioParamsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    user_data: Dict[str, Any] = Field(..., description="User data including stress level, text input, etc.")
    context: Dict[str, Any] = Field(..., description="Context with preferences for audio generation")
    audio_type: str = Field(..., description="Type of audio intervention determined by plan_intervention")

class AudioEndpointInput(BaseModel):
    audio_type: str = Field(..., description="Type of meditation audio to generate")
    params: Dict[str, Any] = Field(..., description="Audio generation parameters from prepare_audio_params")

class CacheEndpointInput(BaseModel):
    endpoint: str = Field(..., description="Cache endpoint name: cache_user_voice, get_cache_status, clear_user_cache")
    params: Dict[str, Any] = Field(..., description="Parameters for the cache endpoint")

class RecommendationsInput(BaseModel):
    user_data: Dict[str, Any] = Field(..., description="User data including stress level, text input, etc.")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Intervention results (optional)")

class CrisisHandlingInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    user_data: Dict[str, Any] = Field(..., description="User data including stress level, text input, etc.")
    context: Dict[str, Any] = Field(..., description="Context with user preferences")

class FinalAnswerInput(BaseModel):
    intervention_type: str = Field(..., description="Type of intervention: 'standard', 'crisis', or 'error'")
    audio_result: Optional[Dict[str, Any]] = Field(default=None, description="Audio generation result from call_audio_endpoint")
    crisis_result: Optional[Dict[str, Any]] = Field(default=None, description="Crisis handling result from handle_crisis")
    recommendations: Optional[List[str]] = Field(default=None, description="Recommendations from generate_recommendations")
    error_message: Optional[str] = Field(default=None, description="Error message if intervention_type is 'error'")

class AudioOutput(BaseModel):
    is_created: bool = Field(..., description="Whether audio was successfully created")
    file_path: Optional[str] = Field(default=None, description="Path to the generated audio file")

class FinalAnswerOutput(BaseModel):
    audio: AudioOutput = Field(..., description="Audio generation results")
    recommendations: List[str] = Field(..., description="List of actionable recommendations for the user")
    intervention_type: str = Field(..., description="Type of intervention performed: 'standard', 'crisis', or 'error'")
    error_type: Optional[str] = Field(default=None, description="Error type if intervention failed, None otherwise")

# =============================================================================
# MOOD MANAGER TOOLS
# =============================================================================

@tool("plan_intervention", args_schema=InterventionPlanInput)
def plan_intervention(intent: str, context: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Plan therapeutic intervention strategy based on Master Manager's intent and user's emotional context.
    
    Args:
    - intent (str): Master Manager's intent/instruction for mood management
    - context (Dict[str, Any]): Additional context including user preferences
    - user_data (Dict[str, Any]): User data including emotional analysis from Master Manager
    
    Returns:
    - Dict containing: audio_type (str), voice_caching (bool), follow_up_actions (List[str]), 
      is_crisis (bool), intervention_type (str), priority_level (str)
    """
    # Extract data from user_data (based on MoodManagerRequest example structure)
    user_stress_level = user_data.get("user_stress_level", 0)
    user_text_input = user_data.get("user_text_input", "")
    
    intent_lower = intent.lower()
    user_input_lower = user_text_input.lower()
    
    # Determine intervention type based on intent
    intervention = {
        "audio_type": None,
        "voice_caching": False,
        "follow_up_actions": [],
        "intervention_type": "standard",
        "priority_level": "normal",
        "is_crisis": False
    }
    
    # Crisis detection based on stress level or crisis keywords
    crisis_keywords = ["suicide", "kill myself", "panic attack", "can't cope", "want to die", "end it all", "hopeless"]
    is_crisis = (user_stress_level >= 8 or 
                any(crisis_word in user_input_lower for crisis_word in crisis_keywords))
    
    if is_crisis:
        intervention.update({
            "audio_type": "crisis_meditation",
            "intervention_type": "crisis",
            "priority_level": "urgent",
            "is_crisis": True
        })
        return intervention
    
    # Sleep/self-esteem intervention
    sleep_keywords = ["sleep", "confidence", "self-worth", "believe in myself"]
    if (any(keyword in intent_lower for keyword in sleep_keywords) or 
        any(keyword in user_input_lower for keyword in sleep_keywords)):
        intervention["audio_type"] = "sleep_meditation"
        
    # Energy/workout intervention  
    elif (any(keyword in intent_lower for keyword in ["energy", "workout", "motivation", "gym", "exercise"]) or
          any(keyword in user_input_lower for keyword in ["energy", "workout", "motivation", "gym", "exercise"])):
        intervention["audio_type"] = "workout_meditation"
        
    # Mindfulness intervention
    elif (any(keyword in intent_lower for keyword in ["mindful", "present", "focus", "scattered", "distracted"]) or
          any(keyword in user_input_lower for keyword in ["mindful", "present", "focus", "scattered", "distracted"])):
        intervention["audio_type"] = "mindfulness_meditation"
        
    # Default to release meditation for emotional release
    else:
        intervention["audio_type"] = "release_meditation"
    
    intervention["voice_caching"] = True
        
    # Plan follow-up actions  
    if is_crisis or user_stress_level >= 7:
        intervention["follow_up_actions"] = ["Schedule check-in within 1 hour", "Track mood progress", "Keep emergency contacts accessible"]
    else:
        intervention["follow_up_actions"] = ["Provide optional feedback on intervention effectiveness"]
        
    return intervention

@tool("prepare_audio_params", args_schema=AudioParamsInput)
def prepare_audio_params(user_id: str, user_data: Dict[str, Any], context: Dict[str, Any], audio_type: str) -> Dict[str, Any]:
    """
    Tool Purpose: Prepare parameters for audio generation based on user's emotional context and intervention type.
    
    Args:
    - user_id (str): User identifier
    - user_data (Dict[str, Any]): User data including stress level, text input, etc.
    - context (Dict[str, Any]): Context with preferences for audio generation
    - audio_type (str): Type of audio intervention determined by plan_intervention
    
    Returns:
    - Dict containing: user_id (str), duration (int), selected_emotion (str), selected_tone (str), 
      should_generate_background_music (bool), should_generate_brain_waves (bool), music_style (str), 
      brain_waves_type (str), volume_magnitude (str)
    """
    # Extract data from user_data
    user_stress_level = user_data.get("user_stress_level", 0)
    user_selected_tone = user_data.get("user_selected_tone", "calm")
    user_text_input = user_data.get("user_text_input", "")
    
    # Base parameters matching _call_audio_endpoint format
    params = {
        "user_id": user_id,
        "duration": context.get("duration", 10),  # Get from context or default
        "should_generate_background_music": context.get("should_use_background_music", True),
        "should_generate_brain_waves": context.get("should_use_brain_waves", True),
        "music_style": context.get("music_style", "nature"),
        "volume_magnitude": "low"
    }
    
    # Infer emotion from user input text and stress level
    user_input_lower = user_text_input.lower()
    inferred_emotion = "fear"  # default
    
    if any(word in user_input_lower for word in ["angry", "mad", "frustrated", "annoyed"]):
        inferred_emotion = "anger"
    elif any(word in user_input_lower for word in ["sad", "depressed", "grief", "loss", "mourning"]):
        inferred_emotion = "grief"
    elif any(word in user_input_lower for word in ["guilty", "shame", "regret", "blame"]):
        inferred_emotion = "guilt"
    elif any(word in user_input_lower for word in ["desire", "want", "need", "crave"]):
        inferred_emotion = "desire"
    elif user_stress_level >= 6:
        inferred_emotion = "fear"  # High stress maps to fear
    
    # Customize parameters based on audio type
    if audio_type == "release_meditation":
        params.update({
            "selected_emotion": inferred_emotion,
            "selected_tone": user_selected_tone or "passionate",
            "brain_waves_type": "theta",
            "volume_magnitude": "low"
        })
    elif audio_type == "sleep_meditation":
        params.update({
            "duration": context.get("duration", 20),
            "selected_tone": user_selected_tone or "calm",
            "brain_waves_type": "theta", 
            "volume_magnitude": "low"
        })
    elif audio_type == "mindfulness_meditation":
        params.update({
            "selected_tone": user_selected_tone or "calm",
            "brain_waves_type": "alpha", 
            "volume_magnitude": "low"
        })
    elif audio_type == "workout_meditation":
        params.update({
            "duration": context.get("duration", 20),
            "selected_tone": user_selected_tone or "energetic",
            "brain_waves_type": "beta", 
            "volume_magnitude": "high"
        })
    elif audio_type == "crisis_meditation":
        params.update({
            "selected_tone": "compassionate",  # Override user tone for crisis
            "brain_waves_type": "alpha", 
            "volume_magnitude": "low"
        })
        
    return params

@tool("call_audio_endpoint", args_schema=AudioEndpointInput)
async def call_audio_endpoint(audio_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Generate therapeutic audio by calling appropriate audio generation functions with prepared parameters.
    
    Args:
    - audio_type (str): Type of meditation audio (release_meditation, sleep_meditation, mindfulness_meditation, workout_meditation, crisis_meditation)
    - params (Dict[str, Any]): Audio generation parameters from prepare_audio_params including user_id, duration, tones, brain_waves
    
    Returns:
    - Dict containing: success (bool), audio_file (str), audio_uuid (str), duration (int), 
      metadata (Dict), endpoint (str), method (str), error (str if failed)
    """
    try:
        # Get TTS model (would be cached in real implementation)
        from utils.dependencies import get_tts_model
        try:
            tts_model = await get_tts_model()
        except TypeError:
            tts_model = get_tts_model()
        
        # Extract parameters
        user_id = params.get("user_id")
        min_length = params.get("duration", 10)
        
        # Prepare background options
        background_options = {
            "should_generate_background_music": params.get("should_generate_background_music", True),
            "music_style": params.get("music_style", "nature"),
            "should_generate_brain_waves": params.get("should_generate_brain_waves", True),
            "brain_waves_type": params.get("brain_waves_type", "alpha"),
            "volume_magnitude": params.get("volume_magnitude", "medium")
        }
        
        # Call appropriate audio function
        if audio_type == "release_meditation":
            result = await _generate_release_meditation_audio(
                user_id=user_id,
                selected_emotion=params.get("selected_emotion", "fear"),
                selected_tone=params.get("selected_tone", "calm"),
                min_length=min_length,
                background_options=background_options,
                tts_model=tts_model
            )
        elif audio_type == "sleep_meditation":
            result = await _generate_sleep_meditation_audio(
                user_id=user_id, min_length=min_length,
                background_options=background_options, tts_model=tts_model
            )
        elif audio_type == "mindfulness_meditation":
            result = await _generate_mindfulness_meditation_audio(
                user_id=user_id, min_length=min_length,
                background_options=background_options, tts_model=tts_model
            )
        elif audio_type == "workout_meditation":
            result = await _generate_workout_meditation_audio(
                user_id=user_id, selected_tone=params.get("selected_tone", "energetic"),
                min_length=min_length, background_options=background_options, tts_model=tts_model
            )
        elif audio_type == "crisis_meditation":
            result = await _generate_crisis_meditation_audio(
                user_id=user_id, min_length=min_length,
                background_options=background_options, tts_model=tts_model
            )
        else:
            raise ValueError(f"Unknown audio type: {audio_type}")
        
        return {
            "success": True,
            "audio_file": result.get("output_audio_path"),
            "audio_uuid": result.get("output_audio_uuid"),
            "duration": min_length * 60,
            "metadata": {"background_options": background_options, "user_id": user_id},
            "intervention_type": audio_type 
        }
        
    except Exception as e:
        return {"success": False, "error": str(e), "endpoint": audio_type, "method": "direct_call"}

@tool("call_cache_endpoint", args_schema=CacheEndpointInput)
async def call_cache_endpoint(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Manage user voice caching operations including caching, status checking, and clearing cache.
    
    Args:
    - endpoint (str): Cache operation type (cache_user_voice, get_cache_status, clear_user_cache)
    - params (Dict[str, Any]): Parameters including user_id and voice_data for caching operations
    
    Returns:
    - Dict containing: success (bool), data (Any), endpoint (str), method (str), error (str if failed)
    """
    try:
        if endpoint == "cache_user_voice":
            from utils.dependencies import get_tts_model
            try:
                tts_model = await get_tts_model()
            except TypeError:
                tts_model = get_tts_model()
            result = await _cache_user_voice(user_id=params.get("user_id"), tts_model=tts_model)
        elif endpoint == "get_cache_status":
            result = await _get_cache_status(user_id=params.get("user_id"))
        elif endpoint == "clear_user_cache":
            result = await _clear_user_cache(user_id=params.get("user_id"))
        else:
            raise ValueError(f"Unknown cache endpoint: {endpoint}")
        
        return {"success": True, "data": result, "endpoint": endpoint, "method": "direct_call"}
    except Exception as e:
        return {"success": False, "error": str(e), "endpoint": endpoint, "method": "direct_call"}

@tool("generate_recommendations", args_schema=RecommendationsInput)
def generate_recommendations(user_data: Dict[str, Any], results: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Tool Purpose: Generate evidence-based immediate and follow-up recommendations based on user's emotional state and intervention results.
    
    Args:
    - user_data (Dict[str, Any]): User data including stress level, text input, etc.
    - results (Optional[Dict[str, Any]]): Intervention results including audio generation outcomes (optional)
    
    Returns:
    - List[str]: All recommendations (immediate actions and follow-up actions combined) as a flat list
    """
    # Extract data from user_data
    user_stress_level = user_data.get("user_stress_level", 0)
    user_text_input = user_data.get("user_text_input", "")
    
    # Infer primary emotion from user input text
    user_input_lower = user_text_input.lower()
    primary_emotion = "stress"  # default
    
    if any(word in user_input_lower for word in ["anxious", "nervous", "worried", "scared"]):
        primary_emotion = "anxiety"
    elif any(word in user_input_lower for word in ["angry", "mad", "frustrated"]):
        primary_emotion = "anger"
    elif any(word in user_input_lower for word in ["sad", "depressed", "down"]):
        primary_emotion = "sadness"
    elif any(word in user_input_lower for word in ["overwhelmed", "too much", "can't handle"]):
        primary_emotion = "overwhelmed"
    
    intensity = user_stress_level / 10.0 if user_stress_level else 0.5
    
    all_recommendations = []
    
    # Immediate actions based on emotional state
    if primary_emotion in ["anxiety", "fear"]:
        all_recommendations.extend([
            "Practice deep breathing exercises (4-7-8 technique)",
            "Try progressive muscle relaxation",
            "Use grounding techniques (5-4-3-2-1 method)",
            "Focus on present moment awareness"
        ])
    elif primary_emotion in ["stress", "overwhelmed"]:
        all_recommendations.extend([
            "Take 5-10 minute breaks from current activity",
            "Try gentle stretching or movement",
            "Practice mindful breathing",
            "Write down 3 things causing stress"
        ])
    elif primary_emotion in ["sadness", "grief"]:
        all_recommendations.extend([
            "Allow yourself to feel the emotion without judgment",
            "Practice self-compassion meditation",
            "Reach out to a trusted friend or family member",
            "Engage in gentle, nurturing activities"
        ])
    elif primary_emotion in ["anger", "frustration"]:
        all_recommendations.extend([
            "Take slow, deep breaths to calm your nervous system",
            "Count to 10 before responding to triggers",
            "Try physical release (walking, stretching)",
            "Practice the STOP technique (Stop, Take a breath, Observe, Proceed)"
        ])
    
    # High intensity actions
    if intensity > 0.7:
        all_recommendations.extend([
            "Consider speaking with a mental health professional",
            "Use crisis resources if needed",
            "Prioritize self-care and rest"
        ])
    
    # Follow-up actions
    all_recommendations.append("Track mood progress in journal")
    if intensity > 0.6:
        all_recommendations.extend([
            "Schedule daily check-in with yourself",
            "Repeat today's meditation session tomorrow",
            "Consider establishing regular mindfulness practice"
        ])
    else:
        all_recommendations.extend([
            "Optional weekly mood check-in",
            "Continue building emotional awareness skills"
        ])
    
    # Add follow-ups based on intervention results
    if results and results.get("audio"):
        all_recommendations.append("Save audio session for future use")
        
    return all_recommendations

@tool("handle_crisis", args_schema=CrisisHandlingInput)
async def handle_crisis(user_id: str, user_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Provide specialized crisis intervention for users showing high crisis indicators or suicidal ideation.
    
    Args:
    - user_id (str): User identifier
    - user_data (Dict[str, Any]): User data including stress level, text input, etc.
    - context (Dict[str, Any]): Context with user preferences
    
    Returns:
    - Dict containing: audio (Dict), is_crisis (bool), 
      recommendations (List[str]) with immediate resources and follow-up actions
    """
    # Prepare crisis meditation audio
    audio_params = prepare_audio_params(user_id, user_data, context, "crisis_meditation")
    audio_result = await call_audio_endpoint("crisis_meditation", audio_params)
    
    # Generate comprehensive crisis recommendations
    crisis_recommendations = [
        "Call National Suicide Prevention Lifeline: 988 immediately",
        "Text HOME to 741741 for Crisis Text Line support",
        "Contact Emergency Services: 911 if in immediate danger",
        "Reach out to a trusted friend, family member, or mental health professional",
        "Remove any means of self-harm from immediate environment",
        "Stay with someone or go to a safe public place",
        "Use the crisis meditation audio provided",
        "Schedule follow-up appointment with mental health professional within 24 hours",
        "Contact SAMHSA National Helpline: 1-800-662-4357 for ongoing support",
        "Check in with crisis counselor within 1 hour",
        "Keep emergency contact numbers easily accessible"
    ]
    
    crisis_response = {
        "audio": audio_result,
        "is_crisis": True,
        "recommendations": crisis_recommendations
    }
    
    return crisis_response

@tool("final_answer", args_schema=FinalAnswerInput)
def final_answer(
    intervention_type: str,
    audio_result: Optional[Dict[str, Any]] = None,
    crisis_result: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[str]] = None,
    error_message: Optional[str] = None
) -> FinalAnswerOutput:
    """
    Tool Purpose: Standardize the final response format for mood management interventions.
    
    Args:
    - intervention_type (str): Type of intervention: 'standard', 'crisis', or 'error'
    - audio_result (Optional[Dict]): Audio generation result from call_audio_endpoint
    - crisis_result (Optional[Dict]): Crisis handling result from handle_crisis
    - recommendations (Optional[List[str]]): Recommendations from generate_recommendations
    - error_message (Optional[str]): Error message if intervention_type is 'error'
    
    Returns:
    - FinalAnswerOutput: Validated Pydantic model with audio, recommendations, intervention_type, and error_type
    """
    # Initialize default values
    audio_output = AudioOutput(is_created=False, file_path=None)
    response_recommendations = []
    error_type = None
    
    if intervention_type == "error":
        error_type = "intervention_error"
        response_recommendations = ["retry_request", "contact_support"]
    
    elif intervention_type == "crisis":
        if crisis_result:
            # Extract audio from crisis result
            crisis_audio = crisis_result.get("audio", {})
            audio_output = AudioOutput(
                is_created=crisis_audio.get("success", False),
                file_path=crisis_audio.get("audio_file", None)
            )
            response_recommendations = crisis_result.get("recommendations", [
                "seek_professional_help",
                "contact_emergency_services_if_needed", 
                "check_in_1_hour"
            ])
    
    elif intervention_type == "standard":
        if audio_result:
            audio_output = AudioOutput(
                is_created=audio_result.get("success", False),
                file_path=audio_result.get("audio_file", None)
            )
        
        if recommendations:
            response_recommendations = recommendations
        else:
            response_recommendations = ["track_mood_progress", "optional_feedback"]
    
    return FinalAnswerOutput(
        audio=audio_output,
        recommendations=response_recommendations,
        intervention_type=intervention_type,
        error_type=error_type
    )