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
    request: Dict[str, Any] = Field(..., description="MoodManagerRequest data as dict containing user_data with emotional analysis")
    audio_type: str = Field(..., description="Type of audio intervention determined by plan_intervention")

class AudioEndpointInput(BaseModel):
    audio_type: str = Field(..., description="Type of meditation audio to generate")
    params: Dict[str, Any] = Field(..., description="Audio generation parameters from prepare_audio_params")

class CacheEndpointInput(BaseModel):
    endpoint: str = Field(..., description="Cache endpoint name: cache_user_voice, get_cache_status, clear_user_cache")
    params: Dict[str, Any] = Field(..., description="Parameters for the cache endpoint")

class RecommendationsInput(BaseModel):
    request: Dict[str, Any] = Field(..., description="MoodManagerRequest data as dict containing user_data with emotional analysis")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Intervention results (optional)")

class CrisisHandlingInput(BaseModel):
    request: Dict[str, Any] = Field(..., description="MoodManagerRequest data as dict containing user_data with emotional analysis")

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
      crisis_protocol (bool), intervention_type (str), priority_level (str)
    """
    # Extract emotional analysis from user_data
    emotional_analysis = user_data.get("emotional_analysis", {})
    user_crisis_level = user_data.get("user_crisis_level", 0)
    user_text_input = user_data.get("user_text_input", "")
    
    intent_lower = intent.lower()
    user_input_lower = user_text_input.lower()
    
    # Determine intervention type based on intent
    intervention = {
        "audio_type": None,
        "voice_caching": False,
        "follow_up_actions": [],
        "crisis_protocol": False,
        "intervention_type": "standard",
        "priority_level": "normal"
    }
    
    # Crisis detection based on crisis level or emotional analysis
    is_crisis = (user_crisis_level >= 8 or 
                emotional_analysis.get("is_crisis", False) or
                any(crisis_word in user_input_lower for crisis_word in ["suicide", "kill myself", "panic attack", "can't cope"]))
    
    if is_crisis:
        intervention.update({
            "audio_type": "crisis_meditation",
            "crisis_protocol": True,
            "intervention_type": "crisis",
            "priority_level": "urgent"
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
    if emotional_analysis.get("is_crisis", False):
        intervention["follow_up_actions"] = ["schedule_check_in", "track_mood"]
    else:
        intervention["follow_up_actions"] = ["optional_feedback"]
        
    return intervention

@tool("prepare_audio_params", args_schema=AudioParamsInput)
def prepare_audio_params(request: Dict[str, Any], audio_type: str) -> Dict[str, Any]:
    """
    Tool Purpose: Prepare parameters for audio generation based on user's emotional context and intervention type.
    
    Args:
    - request (Dict[str, Any]): MoodManagerRequest data containing user_id, context, and user_data with emotional analysis
    - audio_type (str): Type of audio intervention determined by plan_intervention
    
    Returns:
    - Dict containing: user_id (str), duration (int), selected_emotion (str), selected_tone (str), 
      should_generate_background_music (bool), should_generate_brain_waves (bool), music_style (str), 
      brain_waves_type (str), volume_magnitude (str)
    """
    # Extract data from request
    user_data = request.get("user_data", {})
    emotional_analysis = user_data.get("emotional_analysis", {})
    selected_emotion = emotional_analysis.get("selected_emotion", "fear")
    context = request.get("context", {})
    
    # Base parameters matching _call_audio_endpoint format
    params = {
        "user_id": request.get("user_id"),
        "duration": 10,  # Default duration in minutes
        "should_generate_background_music": context.get("background_music", True),
        "should_generate_brain_waves": context.get("brain_waves", True),
        "music_style": context.get("background_music_preference", "nature"),
        "volume_magnitude": "low"
    }
    
    # Map emotions to supported values: guilt, fear, grief, anger, desire
    emotion_mapping = {
        "stress": "fear", "anxiety": "fear", "sadness": "grief", "depression": "grief",
        "frustration": "anger", "worry": "fear", "overwhelmed": "fear", "shame": "guilt",
        "loss": "grief", "hatred": "anger", "jealousy": "desire", "envy": "desire",
        "lust": "desire", "annoyance": "anger", "disappointment": "anger", "disgust": "anger",
    }
    
    mapped_emotion = emotion_mapping.get(selected_emotion, selected_emotion)
    supported_emotions = ["guilt", "fear", "grief", "anger", "desire", "lust"]
    if mapped_emotion not in supported_emotions:
        mapped_emotion = "fear"
    
    # Customize parameters based on audio type
    if audio_type == "release_meditation":
        params.update({
            "selected_emotion": mapped_emotion,
            "duration": 10,
            "selected_tone": "passionate",
            "brain_waves_type": "theta",
            "volume_magnitude": "low"
        })
    elif audio_type == "sleep_meditation":
        params.update({
            "duration": 20, "selected_tone": "calm",
            "brain_waves_type": "theta", "volume_magnitude": "low"
        })
    elif audio_type == "mindfulness_meditation":
        params.update({
            "duration": 10, "selected_tone": "calm",
            "brain_waves_type": "alpha", "volume_magnitude": "low"
        })
    elif audio_type == "workout_meditation":
        params.update({
            "duration": 20, "selected_tone": "energetic",
            "brain_waves_type": "beta", "volume_magnitude": "high"
        })
    elif audio_type == "crisis_meditation":
        params.update({
            "duration": 10, "selected_tone": "compassionate",
            "brain_waves_type": "alpha", "volume_magnitude": "low"
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
            "metadata": {"audio_type": audio_type, "background_options": background_options, "parameters": params},
            "endpoint": audio_type, "method": "direct_call"
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
def generate_recommendations(request: Dict[str, Any], results: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
    """
    Tool Purpose: Generate evidence-based immediate and follow-up recommendations based on user's emotional state and intervention results.
    
    Args:
    - request (Dict[str, Any]): MoodManagerRequest data containing user_data with emotional analysis from Master Manager
    - results (Optional[Dict[str, Any]]): Intervention results including audio generation outcomes (optional)
    
    Returns:
    - Dict containing: immediate_actions (List[str]) and follow_up_actions (List[str]) with specific recommendations
    """
    # Extract emotional analysis from user_data
    user_data = request.get("user_data", {})
    emotion_analysis = user_data.get("emotional_analysis", {})
    user_crisis_level = user_data.get("user_crisis_level", 0)
    
    primary_emotion = emotion_analysis.get("primary_emotion", "stress")
    intensity = emotion_analysis.get("intensity", user_crisis_level / 10.0 if user_crisis_level else 0.5)
    
    recommendations = {"immediate_actions": [], "follow_up_actions": []}
    
    # Immediate actions based on emotional state
    if primary_emotion in ["anxiety", "fear"]:
        recommendations["immediate_actions"].extend([
            "Practice deep breathing exercises (4-7-8 technique)",
            "Try progressive muscle relaxation", "Use grounding techniques (5-4-3-2-1 method)",
            "Focus on present moment awareness"
        ])
    elif primary_emotion in ["stress", "overwhelmed"]:
        recommendations["immediate_actions"].extend([
            "Take 5-10 minute breaks from current activity", "Try gentle stretching or movement",
            "Practice mindful breathing", "Write down 3 things causing stress"
        ])
    elif primary_emotion in ["sadness", "grief"]:
        recommendations["immediate_actions"].extend([
            "Allow yourself to feel the emotion without judgment", "Practice self-compassion meditation",
            "Reach out to a trusted friend or family member", "Engage in gentle, nurturing activities"
        ])
    elif primary_emotion in ["anger", "frustration"]:
        recommendations["immediate_actions"].extend([
            "Take slow, deep breaths to calm your nervous system", "Count to 10 before responding to triggers",
            "Try physical release (walking, stretching)", "Practice the STOP technique (Stop, Take a breath, Observe, Proceed)"
        ])
    
    # High intensity actions
    if intensity > 0.7:
        recommendations["immediate_actions"].extend([
            "Consider speaking with a mental health professional",
            "Use crisis resources if needed", "Prioritize self-care and rest"
        ])
    
    # Follow-up actions
    recommendations["follow_up_actions"].append("Track mood progress in journal")
    if intensity > 0.6:
        recommendations["follow_up_actions"].extend([
            "Schedule daily check-in with yourself", "Repeat today's meditation session tomorrow",
            "Consider establishing regular mindfulness practice"
        ])
    else:
        recommendations["follow_up_actions"].extend([
            "Optional weekly mood check-in", "Continue building emotional awareness skills"
        ])
    
    # Add follow-ups based on intervention results
    if results and results.get("audio"):
        recommendations["follow_up_actions"].append("Save audio session for future use")
        
    return recommendations

@tool("handle_crisis", args_schema=CrisisHandlingInput)
async def handle_crisis(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Provide specialized crisis intervention for users showing high crisis indicators or suicidal ideation.
    
    Args:
    - request (Dict[str, Any]): MoodManagerRequest data containing user_id, context, and user_data with emotional analysis
    
    Returns:
    - Dict containing: immediate_resources (List[str]), audio (Dict), follow_up_scheduled (bool), 
      crisis_protocol_activated (bool), emergency_contacts (List[str])
    """
    # Prepare crisis meditation audio
    audio_params = prepare_audio_params(request, "crisis_meditation")
    audio_result = await call_audio_endpoint("crisis_meditation", audio_params)
    
    crisis_response = {
        "immediate_resources": [
            "National Suicide Prevention Lifeline: 988",
            "Crisis Text Line: Text HOME to 741741",
            "Emergency Services: 911"
        ],
        "audio": audio_result,
        "follow_up_scheduled": True,
        "crisis_protocol_activated": True,
        "emergency_contacts": [
            "National Suicide Prevention Lifeline: 988",
            "Crisis Text Line: 741741",
            "SAMHSA National Helpline: 1-800-662-4357"
        ]
    }
    
    return crisis_response