from fastapi import APIRouter, HTTPException
from mood_manager_brain import MoodManagerBrain, MoodManagerRequest, MoodManagerResponse
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

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
# PYDANTIC MODELS FOR MOOD RECORDING
# =============================================================================

class MoodRecordRequest(BaseModel):
    """Request model for recording daily mood"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    mood_score: int = Field(..., description="Mood score from 1-10", ge=1, le=10)
    is_crisis: bool = Field(default=False, description="Whether user is in crisis")
    is_depressed: bool = Field(default=False, description="Whether user feels depressed")
    notes: Optional[str] = Field(None, description="Optional mood notes", max_length=1000)

class MoodRecordResponse(BaseModel):
    """Response model for mood recording"""
    success: bool
    mood_record_id: str
    crisis_trigger: bool
    correlation_trigger: bool
    recommendations: List[str]
    error: Optional[str] = None

class MoodAnalysisRequest(BaseModel):
    """Request model for mood pattern analysis with enhanced features"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    time_period: str = Field(default="monthly", description="Analysis period: weekly, monthly, or custom")
    include_note_analysis: bool = Field(default=True, description="Whether to analyze mood notes")

class MoodAnalysisResponse(BaseModel):
    """Response model for mood pattern analysis with enhanced features"""
    success: bool
    analysis_period: Optional[str] = None
    date_range: Optional[str] = None
    total_records: int = 0
    average_mood: Optional[float] = None
    mood_trend: Optional[str] = None
    crisis_days: int = 0
    depressed_days: int = 0
    low_mood_days: int = 0
    high_mood_days: int = 0
    mood_stability: Optional[str] = None
    note_insights: List[str] = []
    recommendations: List[str] = []
    error: Optional[str] = None

class MoodHistoryResponse(BaseModel):
    """Response model for mood history retrieval"""
    success: bool
    mood_records: List[Dict[str, Any]]
    total_records: int
    date_range: str
    error: Optional[str] = None

# =============================================================================
# ENHANCED PYDANTIC MODELS FOR PHASE 1 & 2
# =============================================================================

class EnhancedMoodRecordRequest(BaseModel):
    """Request model for enhanced daily mood recording with notes"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date in YYYY-MM-DD format", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    mood_score: Optional[int] = Field(None, description="Optional mood score from 1-10", ge=1, le=10)
    mood_notes: Optional[str] = Field(None, description="Optional emotional diary notes", max_length=2000)
    is_crisis: bool = Field(default=False, description="Whether user is in crisis")
    is_depressed: bool = Field(default=False, description="Whether user feels depressed")

class MoodNotesRequest(BaseModel):
    """Request model for recording daily mood notes (emotional diary)"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date in YYYY-MM-DD format", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    mood_notes: str = Field(..., description="Emotional diary entry", min_length=1, max_length=2000)

class EmotionRecordRequest(BaseModel):
    """Request model for recording specific emotions"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date in YYYY-MM-DD format", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    emotion_type: str = Field(..., description="Type of emotion", min_length=1, max_length=50)
    emotion_score: int = Field(..., description="Emotion intensity from 1-10", ge=1, le=10)
    triggers: Optional[List[str]] = Field(default_factory=list, description="Optional list of triggers")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional context information")

class EmotionNotesRequest(BaseModel):
    """Request model for recording emotion-specific notes"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date in YYYY-MM-DD format", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    emotion_type: str = Field(..., description="Type of emotion", min_length=1, max_length=50)
    emotion_notes: str = Field(..., description="Notes about this emotion", min_length=1, max_length=1500)
    triggers: Optional[List[str]] = Field(default_factory=list, description="Optional list of triggers")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional context information")

class EmotionTrendRequest(BaseModel):
    """Request model for emotion trend analysis"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    emotions: Union[str, List[str]] = Field(..., description="Single emotion, list of emotions, or 'all'")
    time_period: str = Field(default="monthly", description="Analysis period: weekly, monthly, or custom")
    include_note_analysis: bool = Field(default=True, description="Whether to include note analysis")

# Response models
class EnhancedMoodRecordResponse(BaseModel):
    """Response model for enhanced mood recording"""
    success: bool
    mood_record_id: Optional[str] = None
    date: Optional[str] = None
    mood_score: Optional[int] = None
    mood_notes: Optional[str] = None
    crisis_trigger: bool = False
    correlation_trigger: bool = False
    recommendations: List[str] = []
    error: Optional[str] = None

class MoodNotesResponse(BaseModel):
    """Response model for mood notes recording"""
    success: bool
    message: Optional[str] = None
    date: Optional[str] = None
    note_length: int = 0
    error: Optional[str] = None

class EmotionRecordResponse(BaseModel):
    """Response model for emotion recording"""
    success: bool
    emotion_record_id: Optional[str] = None
    emotion_type: Optional[str] = None
    emotion_score: Optional[int] = None
    date: Optional[str] = None
    triggers: List[str] = []
    context: Dict[str, Any] = {}
    recommendations: List[str] = []
    error: Optional[str] = None

class EmotionNotesResponse(BaseModel):
    """Response model for emotion notes recording"""
    success: bool
    message: Optional[str] = None
    emotion_type: Optional[str] = None
    date: Optional[str] = None
    note_length: int = 0
    error: Optional[str] = None

class EmotionTrendResponse(BaseModel):
    """Response model for emotion trend analysis"""
    success: bool
    analysis_type: Optional[str] = None
    emotion_type: Optional[str] = None
    date_range: Optional[str] = None
    total_records: int = 0
    average_intensity: Optional[float] = None
    intensity_trend: Optional[str] = None
    emotion_breakdown: Optional[Dict[str, Any]] = None
    emotion_correlations: Optional[Dict[str, float]] = None
    common_triggers: List[Dict[str, Any]] = []
    note_insights: List[str] = []
    recommendations: List[str] = []
    error: Optional[str] = None

# =============================================================================
# BRAIN ROUTER INTEGRATION
# =============================================================================

# Create the brain instance with auto-detection of available agent types
mood_brain = MoodManagerBrain(agent_type="smolagents")

# Create router for brain endpoints
brain_router = APIRouter(prefix="/brain", tags=["mood-brain"])

@brain_router.post("/process", response_model=MoodManagerResponse,
                   operation_id="process_mood_request",
                   description='''Main endpoint for intelligent mood management
                   Args:
                   - request: MoodManagerRequest object. Please check the schema for the request object by calling the /brain/schema/request endpoint.
                   Returns:
                   - MoodManagerResponse object. Please check the schema for the response object by calling the /brain/schema/response endpoint.
                   ''',
                   )
async def process_mood_request(request: MoodManagerRequest) -> MoodManagerResponse:
    """
    Main endpoint for intelligent mood management
    
    This endpoint uses the mood brain to:
    1. Plan appropriate intervention  
    2. Execute intervention using existing tools
    3. Generate a meditation audio if necessary
    4. Generate comprehensive response with recommendations (immediate and follow-ups) for the user
    """
    return await mood_brain._process_request(request)

@brain_router.get("/capabilities",
                  operation_id="get_brain_capabilities",
                  description='''Get mood manager brain capabilities
                  Args:
                  - None
                  Returns:
                  - Dictionary containing brain capabilities
                  ''',
                  response_description='''Dictionary containing brain capabilities
                  ''',
                  response_model=Dict[str, Any],
                  tags=["mood-brain"]
                )
async def get_brain_capabilities():
    """Get mood manager brain capabilities - what it can DO, not how it does it"""
    return {
        "manager": "Mood Manager",
        "version": "2.0",
        "description": "AI-powered emotional support, therapeutic audio generation, and comprehensive mood tracking specialist",
        
        # Core therapeutic interventions the mood manager can perform
        "core_interventions": [
            {
                "name": "Suppressed Emotion Release",
                "description": "Detect suppressed emotions from user inputs and generate release meditation audio",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male",
                    "user_crisis_level": 8,
                    "user_text_input": "I am feeling anxious about my presentation tomorrow. Please help me to relax."
                },
                "output": "Personalized release meditation with passionate tone targeting specific emotion (supported emotions: guilt, fear, grief, anger, desire)"
            },
            {
                "name": "Self-Belief & Esteem Enhancement", 
                "description": "Detect intent for self-improvement and prepare positive reinforcement audio for sleep",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male",
                    "user_crisis_level": 8,
                    "user_text_input": "I don't believe in myself. Sometimes I feel worthless. I need confidence."
                },
                "output": "Sleep meditation with calm tone and theta brain waves for subconscious reinforcement."
            },
            {
                "name": "Workout Motivation",
                "description": "Detect intent to feel energized during exercise and prepare motivation audio",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male",
                    "user_crisis_level": 8,
                    "user_text_input": "I need energy for my workout. I feel lazy to exercise. Motivate me!"
                },
                "output": "Energetic workout meditation with beta brain waves and high volume."
            },
            {
                "name": "Mindfulness & Present Moment",
                "description": "Detect intent to be more present and prepare mindfulness meditation",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male",
                    "user_crisis_level": 8,
                    "user_text_input": "My mind is scattered. I'm always distracted."
                },
                "output": "Mindfulness meditation with calm tone and alpha brain waves."
            },
            {
                "name": "Crisis & Stress Management",
                "description": "Detect emotional crisis and high stress, provide immediate calming intervention",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male",
                    "user_crisis_level": 8,
                    "user_text_input": "I'm having a panic attack. I can't cope anymore. I feel suicidal."
                },
                "output": "Crisis meditation with compassionate tone, alpha brain waves, plus emergency resources."
            },
            {
                "name": "Comprehensive Mood & Emotion Tracking",
                "description": "Record and analyze mood patterns, emotional diary entries, and specific emotion tracking with correlation analysis",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male", 
                    "user_crisis_level": 6,
                    "user_text_input": "I had a really tough day. My mood was around 3/10 and I felt pretty depressed. Can you track this for me and analyze my patterns?"
                },
                "output": "Comprehensive mood recording with pattern analysis, crisis detection, therapeutic recommendations, and correlation analysis with granular emotion tracking."
            }
        ],
        
        # Comprehensive intervention flow
        "intervention_flow": {
            "1. Intervention Planning": "Customized plan based on detected emotion and user context",
            "2. Mood & Emotion Recording": "Enhanced tracking with diary notes, specific emotions, triggers, and context",
            "3. Audio Generation": "Personalized therapeutic audio with AI voice, background music, brain waves",
            "4. Pattern Analysis": "Advanced mood and emotion trend analysis with correlation insights",
            "5. Recommendation Engine": "Evidence-based immediate and follow-up action suggestions",
            "6. Crisis Protocols": "Specialized handling for mental health emergencies"
        },
        
        # Enhanced API endpoints available
        "api_endpoints": {
            "brain_endpoints": {
                "/brain/process": "Main intelligent mood management endpoint",
                "/brain/capabilities": "Get brain capabilities (this endpoint)",
                "/brain/tools": "Get available tools for LLM orchestration",
                "/brain/schema/request": "Get request schema for external integration",
                "/brain/schema/response": "Get response schema for external integration"
            },
            "mood_recording_endpoints": {
                "/mood/history/{user_id}": "Get mood history with flexible date range support",
                "/mood/record": "Enhanced daily mood recording with optional score and diary notes",
                "/mood/notes": "Record daily emotional diary notes",
                "/mood/analyze": "Comprehensive mood pattern analysis with note insights",
                "/emotion/record": "Record specific emotions with intensity and context",
                "/emotion/notes": "Record detailed notes for specific emotions",
                "/emotion/analyze": "Advanced emotion trend analysis with correlation insights"
            }
        },
        
        # Audio personalization features
        "audio_capabilities": {
            "meditation_audio_types": {
                "release_meditation": "For suppressed emotions (passionate tone, theta waves)",
                "sleep_meditation": "For self-improvement during sleep (calm tone, theta waves)",
                "workout_meditation": "For energy and motivation (energetic tone, beta waves)",
                "mindfulness_meditation": "For present moment awareness (calm tone, alpha waves)",
                "crisis_meditation": "For immediate calming (compassionate tone, alpha waves)"
            },
            "audio_customization": [
                "Emotion-specific content targeting guilt, fear, grief, anger, desire",
                "Intensity-based duration (10-20 minutes)",
                "Brain wave optimization (alpha, beta, theta)",
                "Background music selection with randomization of instruments",
                "Volume adjustment based on emotional state"
            ]
        },
        
        # Enhanced mood tracking features
        "mood_tracking_capabilities": {
            "mood_recording": {
                "basic_mood_scores": "1-10 daily mood rating with crisis/depression flags",
                "emotional_diary": "Rich qualitative journaling with sentiment analysis",
                "combined_recording": "Consolidated recording supporting both score and notes"
            },
            "emotion_tracking": {
                "granular_emotions": "Track specific emotions (anxiety, joy, anger, etc.) with intensity scores",
                "contextual_notes": "Detailed notes with triggers and environmental context",
                "multi_emotion_support": "Multiple emotions per day for comprehensive tracking"
            },
            "analysis_features": {
                "mood_trends": "Statistical analysis with sentiment analysis of diary notes",
                "emotion_correlations": "Advanced correlation analysis between different emotions",
                "pattern_recognition": "Crisis pattern identification and early warning systems",
                "trigger_analysis": "Common trigger identification and intervention recommendations"
            },
            "flexible_querying": {
                "date_ranges": "Query mood/emotion data with flexible start/end dates",
                "time_periods": "Support for weekly, monthly, or custom time periods",
                "record_limits": "Configurable limits for data retrieval (1-200 records)"
            }
        },
        
        # Integration for external AI models
        "integration": {
            "brain_tools_available": 13,
            "mood_tracking_tools": 7,
            "tools_details_endpoint": "/brain/tools",
            "input_format": "MoodManagerRequest",
            "output_format": "MoodManagerResponse",
            "input_schema_endpoint": "/brain/schema/request",
            "output_schema_endpoint": "/brain/schema/response",
            "example_usage": "Send user's emotional state assessment and details, receive personalized audio + comprehensive recommendations",
            "response_format": "Structured intervention with audio file, recommendations (immediate and follow-ups), and mood tracking integration"
        }
    }

@brain_router.get("/tools",
                  operation_id="get_available_tools",
                  description='''Get list of available tools that the LLM agent can orchestrate
                  Args:
                  - None
                  Returns:
                  - Dictionary containing tool inventory and orchestration flow
                  ''',
                  response_description='''Dictionary containing detailed tool specifications including:
                  - Tool descriptions and purposes
                  - Input/output parameters for each tool
                  - Tool orchestration flow sequence
                  - Total number of available tools
                  ''',
                  response_model=Dict[str, Any],
                  tags=["mood-brain"]
                )
async def get_available_tools():
    """Get list of available tools that the LLM agent can orchestrate"""
    return {
        "description": "LLM Agent Tool Inventory - The mood manager brain orchestrates these specialized tools",
        "total_tools": 13,
        "tools": [
            {
                "name": "plan_intervention", 
                "purpose": "Plan therapeutic intervention strategy based on Master Manager's intent and user emotional context",
                "inputs": ["intent (str)", "context (dict)", "user_data (dict with emotional_analysis)"],
                "outputs": ["audio_type", "voice_caching", "crisis_protocol", "intervention_type", "priority_level"]
            },
            {
                "name": "prepare_audio_params",
                "purpose": "Generate audio parameters based on user data and audio type",
                "inputs": ["user_id (str)", "user_data (dict)", "context (dict)", "audio_type (str)"],
                "outputs": ["user_id", "duration", "selected_emotion", "selected_tone", "brain_waves_type", "music_style"]
            },
            {
                "name": "call_audio_endpoint",
                "purpose": "Execute audio generation with prepared parameters",
                "inputs": ["audio_type (str)", "params (dict)"],
                "outputs": ["success", "audio_file", "audio_uuid", "duration", "metadata"]
            },
            {
                "name": "call_cache_endpoint",
                "purpose": "Manage voice caching operations",
                "inputs": ["endpoint (str)", "params (dict)"],
                "outputs": ["success", "data", "endpoint", "method"]
            },
            {
                "name": "generate_recommendations",
                "purpose": "Create evidence-based immediate and follow-up actions",
                "inputs": ["user_data (dict)", "results (optional dict)"],
                "outputs": ["immediate_actions (list)", "follow_up_actions (list)"]
            },
            {
                "name": "handle_crisis",
                "purpose": "Provide specialized crisis intervention protocols",
                "inputs": ["user_id (str)", "user_data (dict)", "context (dict)"],
                "outputs": ["immediate_resources", "audio", "crisis_protocol_activated", "emergency_contacts"]
            },
            {
                "name": "final_answer",
                "purpose": "Standardize the final response format for mood management interventions",
                "inputs": ["intervention_type (str)", "audio_result (optional dict)", "crisis_result (optional dict)", "recommendations (optional list)", "error_message (optional str)"],
                "outputs": ["audio (AudioOutput)", "recommendations (list)", "intervention_type (str)", "error_type (optional str)"]
            },
            {
                "name": "get_user_mood_history", 
                "purpose": "Retrieve mood history records for intelligent analysis and recommendations with flexible date ranges",
                "inputs": ["user_id (str)", "start_date (optional str)", "end_date (optional str)", "limit (int, default: 50)"],
                "outputs": ["success (bool)", "mood_records (list)", "total_records (int)", "date_range (str)", "statistics (dict)"]
            },
            {
                "name": "record_daily_mood",
                "purpose": "Consolidated daily mood recording with optional score and diary notes - combines basic mood recording with emotional diary functionality",
                "inputs": ["user_id (str)", "date (str)", "mood_score (optional int 1-10)", "mood_notes (optional str)", "is_crisis (bool)", "is_depressed (bool)"],
                "outputs": ["success (bool)", "mood_record_id (str)", "crisis_trigger (bool)", "correlation_trigger (bool)", "recommendations (list)"]
            },
            {
                "name": "record_daily_mood_notes",
                "purpose": "Record daily emotional diary notes - implementing emotional diary functionality",
                "inputs": ["user_id (str)", "date (str)", "mood_notes (str)"],
                "outputs": ["success (bool)", "message (str)", "date (str)", "note_length (int)"]
            },
            {
                "name": "record_daily_emotion",
                "purpose": "Record specific emotions with granular tracking and contextual information",
                "inputs": ["user_id (str)", "date (str)", "emotion_type (str)", "emotion_score (int 1-10)", "triggers (optional list)", "context (optional dict)"],
                "outputs": ["success (bool)", "emotion_record_id (str)", "emotion_type (str)", "triggers (list)", "context (dict)", "recommendations (list)"]
            },
            {
                "name": "record_daily_emotion_notes",
                "purpose": "Record detailed contextual notes for specific emotions with triggers and environmental factors",
                "inputs": ["user_id (str)", "date (str)", "emotion_type (str)", "emotion_notes (str)", "triggers (optional list)", "context (optional dict)"],
                "outputs": ["success (bool)", "message (str)", "emotion_type (str)", "date (str)", "note_length (int)"]
            },
            {
                "name": "analyze_mood_trends",
                "purpose": "Enhanced mood trend analysis with sentiment analysis of diary notes and comprehensive insights including crisis detection",
                "inputs": ["user_id (str)", "time_period (str)", "include_note_analysis (bool)"],
                "outputs": ["success (bool)", "analysis_period (str)", "average_mood (float)", "mood_trend (str)", "note_insights (list)", "date_range (str)", "mood_stability (str)", "recommendations (list)"]
            },
            {
                "name": "analyze_emotion_trends",
                "purpose": "Advanced emotion trend analysis supporting single emotion, multiple emotions, or all emotions correlation analysis",
                "inputs": ["user_id (str)", "emotions (str or list)", "time_period (str)", "include_note_analysis (bool)"],
                "outputs": ["success (bool)", "analysis_type (str)", "emotion_breakdown (dict)", "emotion_correlations (dict)", "common_triggers (list)", "recommendations (list)"]
            }
        ],
        "tool_orchestration_flow": [
            "1. Receive Master Manager's intent and user_data (containing emotional analysis)",
            "2. plan_intervention → Choose optimal therapeutic approach based on user's emotional state", 
            "3a. handle_crisis → If crisis detected, activate emergency protocols",
            "3b. Standard intervention → If crisis not detected, proceed with audio generation",
            "4a. prepare_audio_params → Generate parameters for therapeutic audio using user_data",
            "4b. Optional: if audio needs to be in user's voice, then call_cache_endpoint for voice management",
            "5. call_audio_endpoint → Execute audio generation",
            "6. generate_recommendations → Provide actionable guidance based on user_data and results",
            "7. final_answer → Standardize response format with audio, recommendations, and intervention type"
        ],
        "mood_tracking_tools": {
            "description": "Enhanced mood and emotion tracking capabilities",
            "tools": [
                "record_daily_mood: Consolidated mood recording with optional score and diary notes",
                "record_daily_mood_notes: Emotional diary functionality for rich qualitative tracking",
                "record_daily_emotion: Granular emotion tracking with intensity and context",
                "record_daily_emotion_notes: Detailed contextual notes for specific emotions",
                "get_user_mood_history: Flexible mood history retrieval with date range support",
                "analyze_mood_trends: Comprehensive mood pattern analysis with note sentiment analysis",
                "analyze_emotion_trends: Advanced emotion correlation and trigger pattern analysis"
            ]
        }
    }

@brain_router.get("/schema/request",
                  operation_id="get_request_schema",
                  description='''Get the exact schema for MoodManagerRequest - useful for external AI models
                  Args:
                  - None
                  Returns:
                  - Dictionary containing request schema, example, and description
                  ''',
                  response_description='''Dictionary containing complete request schema including:
                  - JSON schema specification for MoodManagerRequest
                  - Practical example with all required fields
                  - Usage description for external AI model integration
                  ''',
                  response_model=Dict[str, Any],
                  tags=["mood-brain", "schema"]
                )
async def get_request_schema():
    """Get the exact schema for MoodManagerRequest - useful for external AI models"""
    return {
        "schema": MoodManagerRequest.model_json_schema(),
        "example": {
            "user_id": "user123",
            "intent": "I'm feeling really anxious about my presentation tomorrow",
            "context": {
                "time_of_day": "evening",
                "stress_level": 8,
                "voice_preference": "calm_female",
                "background_music": True,
                "brain_waves": True,
                "background_music_preference": "nature"
            },
            "priority": "high"
        },
        "description": "External AI models can use this schema to structure requests to /brain/process"
    }

@brain_router.get("/schema/response",
                  operation_id="get_response_schema", 
                  description='''Get the exact schema for MoodManagerResponse - useful for external AI models
                  Args:
                  - None
                  Returns:
                  - Dictionary containing response schema, example, and description
                  ''',
                  response_description='''Dictionary containing complete response schema including:
                  - JSON schema specification for MoodManagerResponse
                  - Practical example with all response fields
                  - Usage description for external AI model integration
                  ''',
                  response_model=Dict[str, Any],
                  tags=["mood-brain", "schema"]
                )
async def get_response_schema():
    """Get the exact schema for MoodManagerResponse - useful for external AI models"""
    return {
        "schema": MoodManagerResponse.model_json_schema(),
        "example": {
            "success": True,
            "audio": {"is_created": True, "file_path": "path/to/audio.mp3"},
            "metadata": {
                "is_error": False,
                "error_type": None,
                "intervention_type": "standard",
                "priority": "high",
                "processing_method": "llm_powered"
            },
            "recommendations": ["seek_professional_help", "contact_emergency_services_if_needed", "check_in_1_hour"]
        },
        "description": "External AI models can use this schema to structure responses from /brain/process"
    }

# =============================================================================
# MOOD RECORDING API ENDPOINTS
# =============================================================================

# Create router for mood recording endpoints
mood_router = APIRouter(prefix="/mood", tags=["mood-recording"])

@mood_router.get("/history/{user_id}", response_model=MoodHistoryResponse,
                 operation_id="get_mood_history",
                 description='''Get mood history for a specific user
                 Args:
                 - user_id: User identifier
                 - start_date: Optional start date (YYYY-MM-DD format)
                 - end_date: Optional end date (YYYY-MM-DD format)
                 - limit: Optional limit for number of records (default: 50)
                 Returns:
                 - MoodHistoryResponse with mood records, total count, and date range
                 ''')
async def get_mood_history_endpoint(
    user_id: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    limit: int = 50
) -> MoodHistoryResponse:
    """
    Get mood history records for a specific user within a date range
    
    This endpoint:
    1. Retrieves mood records for the specified user within the date range
    2. Returns records in chronological order (newest first)
    3. Includes mood scores, crisis/depression flags, and notes
    4. Provides date range and total record count
    5. Useful for correlation analysis with other behavioral data
    """
    try:
        # Call the mood history utility function with updated signature
        result = await _get_mood_stats(
            user_id=user_id, 
            start_date=start_date, 
            end_date=end_date, 
            limit=limit
        )
        
        if not result["success"]:
            return MoodHistoryResponse(
                success=False,
                mood_records=[],
                total_records=0,
                date_range="",
                error=result.get("error", "Unknown error occurred")
            )
        
        return MoodHistoryResponse(
            success=True,
            mood_records=result["mood_records"],
            total_records=result["total_records"],
            date_range=result["date_range"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mood history retrieval failed: {str(e)}")

# =============================================================================
# ENHANCED MOOD AND EMOTION RECORDING ENDPOINTS (Phase 1 & 2)
# =============================================================================

@mood_router.post("mood/record", response_model=EnhancedMoodRecordResponse,
                  operation_id="record_daily_mood",
                  description='''Record daily mood with crisis/depression flags and pattern analysis''')
async def record_daily_mood_endpoint(request: EnhancedMoodRecordRequest) -> EnhancedMoodRecordResponse:
    """Record enhanced daily mood with optional score and notes."""
    result = await _record_daily_mood(
        user_id=request.user_id,
        date=request.date,
        mood_score=request.mood_score,
        mood_notes=request.mood_notes,
        is_crisis=request.is_crisis,
        is_depressed=request.is_depressed
    )
    return EnhancedMoodRecordResponse(**result)

@mood_router.post("mood/notes", response_model=MoodNotesResponse,
                  operation_id="record_daily_mood_notes",
                  description='''Record daily emotional diary notes''')
async def record_daily_mood_notes_endpoint(request: MoodNotesRequest) -> MoodNotesResponse:
    """Record daily emotional diary notes - your excellent emotional diary idea!"""
    try:
        result = await _record_daily_mood_notes(
            user_id=request.user_id, date=request.date, mood_notes=request.mood_notes
        )
        
        if not result["success"]:
            return MoodNotesResponse(success=False, error=result.get("error", "Unknown error"))
        
        return MoodNotesResponse(
            success=True, message=result["message"], date=result["date"], note_length=result["note_length"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mood notes recording failed: {str(e)}")

@mood_router.post("/emotion/record", response_model=EmotionRecordResponse,
                  operation_id="record_daily_emotion",
                  description='''Record specific emotion with intensity and context''')
async def record_daily_emotion_endpoint(request: EmotionRecordRequest) -> EmotionRecordResponse:
    """Record specific emotions with granular tracking and context."""
    try:
        result = await _record_daily_emotion(
            user_id=request.user_id, date=request.date, emotion_type=request.emotion_type,
            emotion_score=request.emotion_score, triggers=request.triggers, context=request.context
        )
        
        if not result["success"]:
            return EmotionRecordResponse(success=False, error=result.get("error", "Unknown error"))
        
        return EmotionRecordResponse(
            success=True, emotion_record_id=result["emotion_record_id"],
            emotion_type=result["emotion_type"], emotion_score=result["emotion_score"],
            date=result["date"], triggers=result["triggers"],
            context=result["context"], recommendations=result["recommendations"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion recording failed: {str(e)}")

@mood_router.post("/emotion/notes", response_model=EmotionNotesResponse,
                  operation_id="record_daily_emotion_notes",
                  description='''Record notes for a specific emotion''')
async def record_daily_emotion_notes_endpoint(request: EmotionNotesRequest) -> EmotionNotesResponse:
    """Record detailed notes for specific emotions with contextual information."""
    try:
        result = await _record_daily_emotion_notes(
            user_id=request.user_id, date=request.date, emotion_type=request.emotion_type,
            emotion_notes=request.emotion_notes, triggers=request.triggers, context=request.context
        )
        
        if not result["success"]:
            return EmotionNotesResponse(success=False, error=result.get("error", "Unknown error"))
        
        return EmotionNotesResponse(
            success=True, message=result["message"], emotion_type=result["emotion_type"],
            date=result["date"], note_length=result["note_length"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion notes recording failed: {str(e)}")

@mood_router.post("mood/analyze", response_model=MoodAnalysisResponse,
                  operation_id="analyze_mood_trends",
                  description='''Consolidated mood pattern analysis with enhanced note insights and comprehensive metrics''')
async def analyze_mood_trend_endpoint(request: MoodAnalysisRequest) -> MoodAnalysisResponse:
    """Enhanced mood trend analysis including sentiment analysis of diary notes."""
    try:
        result = await _analyze_mood_trend(
            user_id=request.user_id, time_period=request.time_period,
            include_note_analysis=request.include_note_analysis
        )
        
        if not result["success"]:
            return MoodAnalysisResponse(success=False, error=result.get("error", "Unknown error"))
        
        return MoodAnalysisResponse(
            success=True, analysis_period=result["analysis_period"], date_range=result["date_range"],
            total_records=result["total_records"], average_mood=result["average_mood"],
            mood_trend=result["mood_trend"], crisis_days=result["crisis_days"],
            depressed_days=result["depressed_days"], low_mood_days=result["low_mood_days"],
            high_mood_days=result["high_mood_days"], mood_stability=result["mood_stability"],
            note_insights=result["note_insights"], recommendations=result["recommendations"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced mood analysis failed: {str(e)}")

@mood_router.post("/emotion/analyze", response_model=EmotionTrendResponse,
                  operation_id="analyze_emotion_trend",
                  description='''Analyze specific emotion trends with correlation analysis''')
async def analyze_emotion_trend_endpoint(request: EmotionTrendRequest) -> EmotionTrendResponse:
    """Analyze trends for specific emotions with multi-emotion correlation analysis."""
    try:
        result = await _analyze_emotion_trend(
            user_id=request.user_id, emotions=request.emotions,
            time_period=request.time_period, include_note_analysis=request.include_note_analysis
        )
        
        if not result["success"]:
            return EmotionTrendResponse(success=False, error=result.get("error", "Unknown error"))
        
        return EmotionTrendResponse(
            success=True, analysis_type=result.get("analysis_type"),
            emotion_type=result.get("emotion_type"), date_range=result.get("date_range"),
            total_records=result.get("total_records", 0), average_intensity=result.get("average_intensity"),
            intensity_trend=result.get("intensity_trend"), emotion_breakdown=result.get("emotion_breakdown"),
            emotion_correlations=result.get("emotion_correlations"), common_triggers=result.get("common_triggers", []),
            note_insights=result.get("note_insights", []), recommendations=result.get("recommendations", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion trend analysis failed: {str(e)}")

# =============================================================================
# MCP TOOLS FOR EXTERNAL INTEGRATION
# =============================================================================

    """Get MCP tool capabilities for external integration"""
    return {
        "service": "Mood Manager MCP Tools",
        "version": "1.0",
        "description": "MCP tools for direct mood recording and analysis",
        
        "tools": [
            {
                "name": "mcp_mood_record",
                "description": "Record daily mood with crisis detection and recommendations",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "mood_score": {"type": "integer", "required": True, "description": "Mood score 1-10", "min": 1, "max": 10},
                    "is_crisis": {"type": "boolean", "required": False, "default": False, "description": "Crisis flag"},
                    "is_depressed": {"type": "boolean", "required": False, "default": False, "description": "Depression flag"},
                    "notes": {"type": "string", "required": False, "description": "Optional mood notes"}
                },
                "outputs": {
                    "mood_record_id": "string",
                    "crisis_trigger": "boolean",
                    "correlation_trigger": "boolean", 
                    "recommendations": "array of strings"
                },
                "endpoint": "/mood/record"
            },
            {
                "name": "mcp_mood_analyze",
                "description": "Analyze mood patterns over time periods",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "time_period": {"type": "string", "required": False, "default": "monthly", "description": "weekly, monthly, or custom"},
                    "start_date": {"type": "string", "required": False, "description": "Start date for custom period (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "required": False, "description": "End date for custom period (YYYY-MM-DD)"}
                },
                "outputs": {
                    "analysis_period": "string",
                    "total_records": "integer",
                    "average_mood": "float",
                    "mood_trend": "string",
                    "crisis_days": "integer",
                    "depressed_days": "integer",
                    "mood_stability": "string",
                    "recommendations": "array of strings"
                },
                "endpoint": "/mood/analyze"
            },
            {
                "name": "mcp_mood_history",
                "description": "Get mood history records for correlation analysis",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "limit": {"type": "integer", "required": False, "default": 50, "description": "Number of records to return"}
                },
                "outputs": {
                    "mood_records": "array of mood record objects",
                    "total_records": "integer",
                    "date_range": "string"
                },
                "endpoint": "/mood/history/{user_id}"
            },
            {
                "name": "mcp_mood_record_enhanced",
                "description": "Enhanced daily mood recording with optional score and diary notes",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "date": {"type": "string", "required": True, "description": "Date in YYYY-MM-DD format"},
                    "mood_score": {"type": "integer", "required": False, "description": "Optional mood score 1-10", "min": 1, "max": 10},
                    "mood_notes": {"type": "string", "required": False, "description": "Optional emotional diary notes"},
                    "is_crisis": {"type": "boolean", "required": False, "default": False, "description": "Crisis flag"},
                    "is_depressed": {"type": "boolean", "required": False, "default": False, "description": "Depression flag"}
                },
                "outputs": {
                    "mood_record_id": "string",
                    "date": "string",
                    "mood_score": "integer",
                    "mood_notes": "string",
                    "crisis_trigger": "boolean",
                    "correlation_trigger": "boolean",
                    "recommendations": "array of strings"
                },
                "endpoint": "/mood/record/enhanced"
            },
            {
                "name": "mcp_mood_diary_notes",
                "description": "Record daily emotional diary notes",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "date": {"type": "string", "required": True, "description": "Date in YYYY-MM-DD format"},
                    "mood_notes": {"type": "string", "required": True, "description": "Emotional diary entry"}
                },
                "outputs": {
                    "message": "string",
                    "date": "string",
                    "note_length": "integer"
                },
                "endpoint": "/mood/notes"
            },
            {
                "name": "mcp_emotion_record",
                "description": "Record specific emotions with intensity and context",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "date": {"type": "string", "required": True, "description": "Date in YYYY-MM-DD format"},
                    "emotion_type": {"type": "string", "required": True, "description": "Type of emotion"},
                    "emotion_score": {"type": "integer", "required": True, "description": "Emotion intensity 1-10", "min": 1, "max": 10},
                    "triggers": {"type": "array", "required": False, "description": "Optional list of triggers"},
                    "context": {"type": "object", "required": False, "description": "Optional context information"}
                },
                "outputs": {
                    "emotion_record_id": "string",
                    "emotion_type": "string",
                    "emotion_score": "integer",
                    "triggers": "array",
                    "context": "object",
                    "recommendations": "array of strings"
                },
                "endpoint": "/mood/emotion/record"
            },
            {
                "name": "mcp_emotion_notes",
                "description": "Record notes for specific emotions",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "date": {"type": "string", "required": True, "description": "Date in YYYY-MM-DD format"},
                    "emotion_type": {"type": "string", "required": True, "description": "Type of emotion"},
                    "emotion_notes": {"type": "string", "required": True, "description": "Notes about this emotion"},
                    "triggers": {"type": "array", "required": False, "description": "Optional list of triggers"},
                    "context": {"type": "object", "required": False, "description": "Optional context information"}
                },
                "outputs": {
                    "message": "string",
                    "emotion_type": "string",
                    "date": "string",
                    "note_length": "integer"
                },
                "endpoint": "/mood/emotion/notes"
            },
            {
                "name": "mcp_mood_analyze_enhanced",
                "description": "Enhanced mood pattern analysis with note insights",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "time_period": {"type": "string", "required": False, "default": "monthly", "description": "weekly or monthly"},
                    "include_note_analysis": {"type": "boolean", "required": False, "default": True, "description": "Whether to analyze mood notes"}
                },
                "outputs": {
                    "analysis_period": "string",
                    "date_range": "string",
                    "total_records": "integer",
                    "average_mood": "float",
                    "mood_trend": "string",
                    "note_insights": "array of strings",
                    "recommendations": "array of strings"
                },
                "endpoint": "/mood/analyze/enhanced"
            },
            {
                "name": "mcp_emotion_analyze",
                "description": "Analyze emotion trends with correlation analysis",
                "inputs": {
                    "user_id": {"type": "string", "required": True, "description": "User identifier"},
                    "emotions": {"type": "string or array", "required": True, "description": "Single emotion, list of emotions, or 'all'"},
                    "time_period": {"type": "string", "required": False, "default": "monthly", "description": "weekly or monthly"},
                    "include_note_analysis": {"type": "boolean", "required": False, "default": True, "description": "Whether to analyze emotion notes"}
                },
                "outputs": {
                    "analysis_type": "string",
                    "emotion_breakdown": "object",
                    "emotion_correlations": "object",
                    "common_triggers": "array of objects",
                    "note_insights": "array of strings",
                    "recommendations": "array of strings"
                },
                "endpoint": "/mood/emotion/analyze"
            }
        ],
        
        "integration_guide": {
            "base_url": "/mood",
            "authentication": "Include user authentication as needed",
            "rate_limits": "Standard API rate limits apply",
            "error_handling": "All endpoints return error field in response for error cases",
            "correlation_use_case": "Use mood history endpoint to correlate mood data with habit/behavior tracking from other managers",
            "mcp_server_integration": "These endpoints can be exposed as MCP tools for external AI agents to call directly"
        }
    }