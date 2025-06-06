from fastapi import APIRouter
from mood_manager_brain import MoodManagerBrain, MoodManagerRequest, MoodManagerResponse
from typing import Dict, Any

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
            }
        ],
        
        # Comprehensive intervention flow
        "intervention_flow": {
            "1. Intervention Planning": "Customized plan based on detected emotion and user context",
            "2. Audio Generation": "Personalized therapeutic audio with AI voice, background music, brain waves",
            "3. Recommendation Engine": "Evidence-based immediate and follow-up action suggestions",
            "4. Crisis Protocols": "Specialized handling for mental health emergencies"
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
            "tools_available": ["plan_intervention", "prepare_audio_params", "call_audio_endpoint", "call_cache_endpoint", "generate_recommendations", "handle_crisis"],
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