from fastapi import APIRouter, HTTPException
from mood_manager_brain import MoodManagerBrain, MoodManagerRequest, MoodManagerResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Import mood recording utilities
from utils.mood_recording_utils import _record_daily_mood, _analyze_mood_patterns, _get_mood_records

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
    """Request model for mood pattern analysis"""
    user_id: str = Field(..., description="User identifier", min_length=1)
    time_period: str = Field(default="monthly", description="Analysis period: weekly, monthly, or custom")
    start_date: Optional[str] = Field(None, description="Start date for custom period (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date for custom period (YYYY-MM-DD)")

class MoodAnalysisResponse(BaseModel):
    """Response model for mood pattern analysis"""
    success: bool
    analysis_period: str
    total_records: int
    average_mood: float
    mood_trend: str
    crisis_days: int
    depressed_days: int
    low_mood_days: int
    high_mood_days: int
    mood_stability: str
    recommendations: List[str]
    error: Optional[str] = None

class MoodHistoryResponse(BaseModel):
    """Response model for mood history retrieval"""
    success: bool
    mood_records: List[Dict[str, Any]]
    total_records: int
    date_range: str
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
        "version": "1.0",
        "description": "AI-powered emotional support and therapeutic audio generation specialist",
        
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
                "name": "Daily Mood Recording & Analysis",
                "description": "Record daily mood scores with crisis/depression flags and analyze mood patterns for insights",
                "input_examples": {
                    "user_age": 30,
                    "user_gender": "male", 
                    "user_crisis_level": 6,
                    "user_text_input": "I had a really tough day. My mood was around 3/10 and I felt pretty depressed. Can you track this for me?"
                },
                "output": "Mood recorded with pattern analysis, crisis detection, therapeutic recommendations, and habit correlation triggers."
            }
        ],
        
        # Comprehensive intervention flow
        "intervention_flow": {
            "1. Intervention Planning": "Customized plan based on detected emotion and user context",
            "2. Mood Recording": "Daily mood tracking with crisis/depression flags and pattern analysis",
            "3. Audio Generation": "Personalized therapeutic audio with AI voice, background music, brain waves",
            "4. Pattern Analysis": "Mood trend analysis and correlation with behavioral data",
            "5. Recommendation Engine": "Evidence-based immediate and follow-up action suggestions",
            "6. Crisis Protocols": "Specialized handling for mental health emergencies"
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
        
        # Integration for external AI models
        "integration": {
            "tools_available": ["plan_intervention", "prepare_audio_params", "call_audio_endpoint", "call_cache_endpoint", "generate_recommendations", "handle_crisis", "record_mood", "analyze_mood_patterns_tool", "get_user_mood_history"],
            "tools_details_endpoint": "/brain/tools",
            "input_format": "MoodManagerRequest",
            "output_format": "MoodManagerResponse",
            "input_schema_endpoint": "/brain/schema/request",
            "output_schema_endpoint": "/brain/schema/response",
            "example_usage": "Send user's emotional state assesment and user details (including message), receive personalized audio + recommendations",
            "response_format": "Structured intervention with audio file and recommendations (immediate and follow-ups actions)"
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
        "total_tools": len(mood_brain.tools),
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
                "inputs": ["request (dict with user_data)", "audio_type (str)"],
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
                "inputs": ["request (dict with user_data)", "results (optional dict)"],
                "outputs": ["immediate_actions (list)", "follow_up_actions (list)"]
            },
            {
                "name": "handle_crisis",
                "purpose": "Provide specialized crisis intervention protocols",
                "inputs": ["request (dict with user_data)"],
                "outputs": ["immediate_resources", "audio", "crisis_protocol_activated", "emergency_contacts"]
            },
            {
                "name": "record_mood",
                "purpose": "Record daily mood score with crisis/depression flags and therapeutic recommendations",
                "inputs": ["user_id (str)", "mood_score (int 1-10)", "is_crisis (bool)", "is_depressed (bool)", "notes (str)"],
                "outputs": ["success", "mood_record_id", "crisis_trigger", "correlation_trigger", "recommendations"]
            },
            {
                "name": "analyze_mood_patterns_tool",
                "purpose": "Analyze mood patterns for trends, stability, crisis detection over time periods",
                "inputs": ["user_id (str)", "time_period (str)", "start_date (optional str)", "end_date (optional str)"],
                "outputs": ["average_mood", "trend", "crisis_days", "stability_metrics", "pattern_recommendations"]
            },
            {
                "name": "get_user_mood_history", 
                "purpose": "Retrieve recent mood history records for context-aware therapeutic recommendations and correlation analysis",
                "inputs": ["user_id (str)", "limit (int, default: 50)"],
                "outputs": ["success (bool)", "mood_records (list)", "total_records (int)", "date_range (str)", "error (optional str)"]
            }
        ],
        "tool_orchestration_flow": [
            "1. Receive Master Manager's intent and user_data (containing emotional analysis)",
            "2. Plan_intervention → Choose optimal therapeutic approach based on user's emotional state", 
            "3a. Handle_crisis → If crisis detected, activate emergency protocols",
            "3b. Standard intervention → If crisis not detected, proceed with audio generation",
            "4a. Prepare_audio_params → Generate parameters for therapeutic audio using user_data",
            "4b. Optional: if audio needs to be in user's voice, then call_cache_endpoint for voice management",
            "5. Call_audio_endpoint → Execute audio generation",
            "6. Generate_recommendations → Provide actionable guidance based on user_data and results",
        ],
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

@mood_router.post("/record", response_model=MoodRecordResponse,
                  operation_id="record_daily_mood",
                  description='''Record daily mood with crisis/depression flags and pattern analysis
                  Args:
                  - request: MoodRecordRequest object with mood_score (1-10), crisis/depression flags, and optional notes
                  Returns:
                  - MoodRecordResponse with mood record ID, triggers, and recommendations
                  ''')
async def record_daily_mood_endpoint(request: MoodRecordRequest) -> MoodRecordResponse:
    """
    Record daily mood with crisis/depression flags and automatic pattern analysis
    
    This endpoint:
    1. Records mood score with crisis and depression indicators
    2. Checks for crisis triggers (mood <= 4 or crisis flag)
    3. Checks for correlation triggers (mood <= 5 or pattern changes)
    4. Provides therapeutic recommendations
    5. Returns mood record ID for tracking
    """
    try:
        # Call the mood recording utility function
        result = _record_daily_mood(
            user_id=request.user_id,
            mood_score=request.mood_score,
            is_crisis=request.is_crisis,
            is_depressed=request.is_depressed,
            notes=request.notes or ""
        )
        
        if not result["success"]:
            return MoodRecordResponse(
                success=False,
                mood_record_id="",
                crisis_trigger=False,
                correlation_trigger=False,
                recommendations=[],
                error=result.get("error", "Unknown error occurred")
            )
        
        return MoodRecordResponse(
            success=True,
            mood_record_id=result["mood_record_id"],
            crisis_trigger=result["crisis_trigger"],
            correlation_trigger=result["correlation_trigger"],
            recommendations=result["recommendations"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mood recording failed: {str(e)}")

@mood_router.post("/analyze", response_model=MoodAnalysisResponse,
                  operation_id="analyze_mood_patterns",
                  description='''Analyze mood patterns over specified time period
                  Args:
                  - request: MoodAnalysisRequest with user_id, time_period (weekly/monthly/custom), and optional date range
                  Returns:
                  - MoodAnalysisResponse with comprehensive mood pattern analysis and recommendations
                  ''')
async def analyze_mood_patterns_endpoint(request: MoodAnalysisRequest) -> MoodAnalysisResponse:
    """
    Analyze mood patterns and trends over a specified time period
    
    This endpoint:
    1. Analyzes mood data over the specified time period
    2. Calculates average mood, trend, and stability
    3. Counts crisis, depressed, low, and high mood days
    4. Provides pattern-based therapeutic recommendations
    5. Identifies concerning trends for intervention
    """
    try:
        # Call the mood analysis utility function
        result = _analyze_mood_patterns(
            user_id=request.user_id,
            time_period=request.time_period,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if not result["success"]:
            return MoodAnalysisResponse(
                success=False,
                analysis_period="",
                total_records=0,
                average_mood=0.0,
                mood_trend="",
                crisis_days=0,
                depressed_days=0,
                low_mood_days=0,
                high_mood_days=0,
                mood_stability="",
                recommendations=[],
                error=result.get("error", "Unknown error occurred")
            )
        
        return MoodAnalysisResponse(
            success=True,
            analysis_period=result["analysis_period"],
            total_records=result["total_records"],
            average_mood=result["average_mood"],
            mood_trend=result["mood_trend"],
            crisis_days=result["crisis_days"],
            depressed_days=result["depressed_days"],
            low_mood_days=result["low_mood_days"],
            high_mood_days=result["high_mood_days"],
            mood_stability=result["mood_stability"],
            recommendations=result["recommendations"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mood analysis failed: {str(e)}")

@mood_router.get("/history/{user_id}", response_model=MoodHistoryResponse,
                 operation_id="get_mood_history",
                 description='''Get mood history for a specific user
                 Args:
                 - user_id: User identifier
                 - limit: Optional limit for number of records (default: 50)
                 Returns:
                 - MoodHistoryResponse with mood records, total count, and date range
                 ''')
async def get_mood_history_endpoint(user_id: str, limit: int = 50) -> MoodHistoryResponse:
    """
    Get mood history records for a specific user
    
    This endpoint:
    1. Retrieves mood records for the specified user
    2. Returns records in chronological order (newest first)
    3. Includes mood scores, crisis/depression flags, and notes
    4. Provides date range and total record count
    5. Useful for correlation analysis with other behavioral data
    """
    try:
        # Call the mood history utility function
        result = _get_mood_records(user_id=user_id, limit=limit)
        
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
# MCP TOOLS FOR EXTERNAL INTEGRATION
# =============================================================================

@mood_router.get("/mcp/capabilities",
                 operation_id="get_mcp_mood_capabilities",
                 description='''Get MCP tool capabilities for mood recording
                 Args:
                 - None
                 Returns:
                 - Dictionary containing MCP tool specifications
                 ''',
                 response_model=Dict[str, Any],
                 tags=["mcp-tools"])
async def get_mcp_mood_capabilities():
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