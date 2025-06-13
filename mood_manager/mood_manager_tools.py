from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import json

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
# Import mood recording utilities
from utils.mood_recording_utils import (
    _record_daily_mood,
    _get_mood_stats,
    _record_daily_mood_notes,
    _record_daily_emotion,
    _record_daily_emotion_notes,
    _analyze_mood_trend,
    _analyze_emotion_trend
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

class MoodRecordingInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    mood_score: int = Field(..., ge=1, le=10, description="Daily mood score 1-10")
    is_crisis: bool = Field(default=False, description="Whether user is in crisis/stress state")
    is_depressed: bool = Field(default=False, description="Whether user is in depressed state")
    notes: Optional[str] = Field(default=None, description="Optional mood notes")

class MoodAnalysisInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(default="monthly", description="Analysis period: weekly, monthly, or custom")
    start_date: Optional[str] = Field(default=None, description="Start date for custom period")
    end_date: Optional[str] = Field(default=None, description="End date for custom period")

class MoodHistoryInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    start_date: Optional[str] = Field(default=None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(default=None, description="End date in YYYY-MM-DD format")
    limit: int = Field(default=50, description="Maximum number of mood records to retrieve", ge=1, le=200)

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

@tool("get_user_mood_history", args_schema=MoodHistoryInput)
async def get_user_mood_history(
    user_id: str, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Tool Purpose: Retrieve mood history records for intelligent analysis and recommendations.
    
    This tool provides comprehensive mood data for correlation analysis:
    - Fetches mood scores, crisis flags, depression markers
    - Includes emotional diary notes for qualitative insights
    - Returns chronological data for trend analysis
    - Essential for generating evidence-based recommendations
    
    Use Cases:
    - Before generating recommendations, check recent mood patterns
    - Identify if user has recurring crisis periods needing special attention
    - Correlate mood drops with specific time periods or notes
    - Adjust intervention intensity based on mood history stability
    """
    try:
        result = await _get_mood_stats(
            user_id=user_id, 
            start_date=start_date, 
            end_date=end_date, 
            limit=limit
        )
        return result
        
    except Exception as e:
        print(f"Error in get_user_mood_history: {str(e)}")
        return {
            "success": False,
            "mood_records": [],
            "total_records": 0,
            "date_range": "",
            "error": f"Failed to retrieve mood history: {str(e)}"
        }

# =============================================================================
# ENHANCED MOOD AND EMOTION RECORDING TOOLS (Phase 1 & 2)
# =============================================================================

class MoodRecordingInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    mood_score: Optional[int] = Field(default=None, ge=1, le=10, description="Optional daily mood score 1-10")
    mood_notes: Optional[str] = Field(default=None, description="Optional emotional diary notes")
    is_crisis: bool = Field(default=False, description="Whether user is in crisis/stress state")
    is_depressed: bool = Field(default=False, description="Whether user is in depressed state")

class MoodNotesInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    mood_notes: str = Field(..., description="Emotional diary entry")

class EmotionRecordingInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    emotion_type: str = Field(..., description="Type of emotion (e.g., anxiety, joy, anger)")
    emotion_score: int = Field(..., ge=1, le=10, description="Emotion intensity score 1-10")
    triggers: Optional[List[str]] = Field(default=None, description="Optional list of triggers")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context information")

class EmotionNotesInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    emotion_type: str = Field(..., description="Type of emotion")
    emotion_notes: str = Field(..., description="Notes about this emotion")
    triggers: Optional[List[str]] = Field(default=None, description="Optional list of triggers")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context information")

class MoodTrendAnalysisInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(default="monthly", description="Analysis period: weekly or monthly")
    include_note_analysis: bool = Field(default=True, description="Whether to analyze mood notes")

class EmotionTrendAnalysisInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    emotions: Union[str, List[str]] = Field(..., description="Single emotion, list of emotions, or 'all'")
    time_period: str = Field(default="monthly", description="Analysis period: weekly or monthly")
    include_note_analysis: bool = Field(default=True, description="Whether to analyze emotion notes")

@tool("record_daily_mood", args_schema=MoodRecordingInput)
async def record_daily_mood_tool(
    user_id: str,
    date: str,
    mood_score: int = None,
    mood_notes: str = None,
    is_crisis: bool = False,
    is_depressed: bool = False
) -> str:
    """
    Record daily mood with optional score and emotional diary notes.
    Consolidated tool that combines mood score recording with emotional diary functionality.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
        mood_score: Optional mood score 1-10
        mood_notes: Optional emotional diary entry
        is_crisis: Whether user is in crisis
        is_depressed: Whether user is depressed
        
    Returns:
        JSON string with recording result and recommendations
    """
    try:
        result = await _record_daily_mood(
            user_id=user_id,
            date=date,
            mood_score=mood_score,
            mood_notes=mood_notes,
            is_crisis=is_crisis,
            is_depressed=is_depressed
        )
        
        if result["success"]:
            return json.dumps({
                "status": "success",
                "mood_record_id": result["mood_record_id"],
                "date": result["date"],
                "mood_score": result.get("mood_score"),
                "mood_notes": result.get("mood_notes"),
                "crisis_trigger": result["crisis_trigger"],
                "correlation_trigger": result["correlation_trigger"],
                "recommendations": result["recommendations"],
                "tool_name": "record_daily_mood"
            })
        else:
            return json.dumps({
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "tool_name": "record_daily_mood"
            })
            
    except Exception as e:
        return json.dumps({
            "status": "error", 
            "error": f"Mood recording failed: {str(e)}",
            "tool_name": "record_daily_mood"
        })

@tool("record_daily_mood_notes", args_schema=MoodNotesInput)
async def record_daily_mood_notes_tool(
    user_id: str, 
    date: str, 
    mood_notes: str
) -> Dict[str, Any]:
    """
    Tool Purpose: Record daily emotional diary notes - implementing your excellent emotional diary idea!
    
    This tool enables rich emotional journaling and self-reflection:
    - Records detailed emotional experiences and thoughts
    - Supports sentiment analysis and pattern recognition
    - Integrates with mood scores for comprehensive tracking
    - Enables therapeutic insights from qualitative data
    
    Args:
    - user_id (str): User identifier
    - date (str): Date in YYYY-MM-DD format
    - mood_notes (str): Emotional diary entry
    
    Returns:
    - Dict containing: success (bool), message (str), date (str), note_length (int)
    """
    try:
        result = await _record_daily_mood_notes(
            user_id=user_id,
            date=date,
            mood_notes=mood_notes
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "date": result["date"],
                "note_length": result["note_length"],
                "tool_name": "record_mood_diary_notes"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to record mood notes"),
                "tool_name": "record_mood_diary_notes"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool_name": "record_mood_diary_notes"
        }

@tool("record_daily_emotion", args_schema=EmotionRecordingInput)
async def record_daily_emotion_tool(
    user_id: str, 
    date: str, 
    emotion_type: str, 
    emotion_score: int,
    triggers: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tool Purpose: Record specific emotions with granular tracking and contextual information.
    
    Enables multi-dimensional emotional awareness:
    - Tracks specific emotion types (anxiety, joy, anger, etc.)
    - Records intensity scores for each emotion
    - Captures triggers and environmental context
    - Supports multiple emotions per day for comprehensive tracking
    - Enables emotion-specific therapeutic interventions
    
    Args:
    - user_id (str): User identifier
    - date (str): Date in YYYY-MM-DD format
    - emotion_type (str): Type of emotion (e.g., anxiety, joy, anger)
    - emotion_score (int): Emotion intensity score 1-10
    - triggers (Optional[List[str]]): Optional list of triggers
    - context (Optional[Dict[str, Any]]): Optional context information
    
    Returns:
    - Dict containing: success (bool), emotion_record_id (str), emotion_type (str), 
      emotion_score (int), date (str), triggers (List[str]), context (Dict), recommendations (List[str])
    """
    try:
        result = await _record_daily_emotion(
            user_id=user_id,
            date=date,
            emotion_type=emotion_type,
            emotion_score=emotion_score,
            triggers=triggers or [],
            context=context or {}
        )
        
        if result["success"]:
            return {
                "success": True,
                "emotion_record_id": result["emotion_record_id"],
                "emotion_type": result["emotion_type"],
                "emotion_score": result["emotion_score"],
                "date": result["date"],
                "triggers": result["triggers"],
                "context": result["context"],
                "recommendations": result["recommendations"],
                "tool_name": "record_specific_emotion"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to record emotion"),
                "tool_name": "record_specific_emotion"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool_name": "record_specific_emotion"
        }

@tool("record_daily_emotion_notes", args_schema=EmotionNotesInput)
async def record_daily_emotion_notes_tool(
    user_id: str, 
    date: str, 
    emotion_type: str, 
    emotion_notes: str,
    triggers: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tool Purpose: Record detailed contextual notes for specific emotions with triggers and environmental factors.
    
    Enhances emotion tracking with rich qualitative data:
    - Links specific situations to emotional responses
    - Captures detailed triggers and environmental context
    - Enables pattern recognition in emotional reactions
    - Supports targeted therapeutic interventions
    - Facilitates emotion-specific journaling and reflection
    
    Args:
    - user_id (str): User identifier
    - date (str): Date in YYYY-MM-DD format
    - emotion_type (str): Type of emotion
    - emotion_notes (str): Detailed notes about this emotion
    - triggers (Optional[List[str]]): Optional list of triggers
    - context (Optional[Dict[str, Any]]): Optional context information
    
    Returns:
    - Dict containing: success (bool), message (str), emotion_type (str), date (str), note_length (int)
    """
    try:
        result = await _record_daily_emotion_notes(
            user_id=user_id,
            date=date,
            emotion_type=emotion_type,
            emotion_notes=emotion_notes,
            triggers=triggers,
            context=context
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "emotion_type": result["emotion_type"],
                "date": result["date"],
                "note_length": result["note_length"],
                "tool_name": "record_emotion_context_notes"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to record emotion notes"),
                "tool_name": "record_emotion_context_notes"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool_name": "record_emotion_context_notes"
        }

@tool("analyze_mood_trends", args_schema=MoodTrendAnalysisInput)
async def analyze_mood_trends_tool(
    user_id: str, 
    time_period: str = "monthly",
    include_note_analysis: bool = True
) -> Dict[str, Any]:
    """
    Tool Purpose: Enhanced mood trend analysis with sentiment analysis of diary notes and comprehensive insights.
    
    Provides sophisticated mood pattern analysis:
    - Statistical analysis of mood scores and trends
    - NLP sentiment analysis of emotional diary notes
    - Integration of quantitative and qualitative insights
    - Crisis pattern identification and early warning systems
    - Therapeutic recommendations based on comprehensive data analysis
    
    Args:
    - user_id (str): User identifier
    - time_period (str): Analysis period (weekly or monthly)
    - include_note_analysis (bool): Whether to analyze sentiment of mood notes
    
    Returns:
    - Dict containing: success (bool), analysis_period (str), date_range (str), total_records (int),
      average_mood (float), mood_trend (str), crisis_days (int), depressed_days (int), 
      low_mood_days (int), high_mood_days (int), mood_stability (str), note_insights (List[str]), 
      recommendations (List[str])
    """
    try:
        result = await _analyze_mood_trend(
            user_id=user_id,
            time_period=time_period,
            include_note_analysis=include_note_analysis
        )
        
        if result["success"]:
            return {
                "success": True,
                "analysis_period": result["analysis_period"],
                "date_range": result["date_range"],
                "total_records": result["total_records"],
                "average_mood": result["average_mood"],
                "mood_trend": result["mood_trend"],
                "crisis_days": result["crisis_days"],
                "depressed_days": result["depressed_days"],
                "low_mood_days": result["low_mood_days"],
                "high_mood_days": result["high_mood_days"],
                "mood_stability": result["mood_stability"],
                "note_insights": result["note_insights"],
                "recommendations": result["recommendations"],
                "tool_name": "analyze_mood_trends_enhanced"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to analyze mood trends"),
                "tool_name": "analyze_mood_trends_enhanced"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool_name": "analyze_mood_trends_enhanced"
        }

@tool("analyze_emotion_trends", args_schema=EmotionTrendAnalysisInput)
async def analyze_emotion_trends_tool(
    user_id: str, 
    emotions: Union[str, List[str]], 
    time_period: str = "monthly",
    include_note_analysis: bool = True
) -> Dict[str, Any]:
    """
    Tool Purpose: Advanced emotion trend analysis supporting your vision for sophisticated emotional intelligence.
    
    Supports multiple analysis modes:
    - Single emotion: Deep dive into specific emotion patterns and triggers
    - Multiple emotions: Correlation analysis between different emotional states
    - All emotions: Comprehensive emotional landscape and interaction analysis
    - Multi-emotion correlation detection for therapeutic insights
    - Trigger pattern recognition and intervention recommendations
    
    Args:
    - user_id (str): User identifier
    - emotions (Union[str, List[str]]): Single emotion, list of emotions, or "all"
    - time_period (str): Analysis period (weekly or monthly)
    - include_note_analysis (bool): Whether to analyze emotion notes
    
    Returns:
    - Dict containing: success (bool), analysis_type (str), emotion_type (str), date_range (str),
      total_records (int), average_intensity (float), intensity_trend (str), emotion_breakdown (Dict),
      emotion_correlations (Dict), common_triggers (List[Dict]), note_insights (List[str]), 
      recommendations (List[str])
    """
    try:
        result = await _analyze_emotion_trend(
            user_id=user_id,
            emotions=emotions,
            time_period=time_period,
            include_note_analysis=include_note_analysis
        )
        
        if result["success"]:
            return {
                "success": True,
                "analysis_type": result.get("analysis_type"),
                "emotion_type": result.get("emotion_type"),
                "date_range": result.get("date_range"),
                "total_records": result.get("total_records", 0),
                "average_intensity": result.get("average_intensity"),
                "intensity_trend": result.get("intensity_trend"),
                "emotion_breakdown": result.get("emotion_breakdown"),
                "emotion_correlations": result.get("emotion_correlations"),
                "common_triggers": result.get("common_triggers", []),
                "note_insights": result.get("note_insights", []),
                "recommendations": result.get("recommendations", []),
                "tool_name": "analyze_emotion_patterns"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to analyze emotion patterns"),
                "tool_name": "analyze_emotion_patterns"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool_name": "analyze_emotion_patterns"
        }