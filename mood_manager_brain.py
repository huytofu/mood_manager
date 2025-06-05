"""
MOOD MANAGER INTERNAL ARCHITECTURE INTEGRATION
=============================================

This file shows how to integrate the LLM "brain" architecture with the existing 
FastAPI/MCP server setup in app.py.

The integration approach:
1. Keep existing app.py FastAPI/MCP configuration 
2. Add brain router that exposes intelligent mood management
3. Brain orchestrates existing cache and audio tools
4. Existing routers become the "tools" layer
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from huggingface_hub import InferenceClient
import json

# Import tools and prompts from separate files
from .mood_manager_tools import (
    analyze_emotional_state,
    plan_intervention, 
    prepare_audio_params,
    call_audio_endpoint,
    call_cache_endpoint,
    generate_recommendations,
    handle_crisis
)
from .mood_manager_prompts import MOOD_MANAGER_SYSTEM_PROMPT, get_user_prompt_template

# =============================================================================
# MANAGER REQUEST/RESPONSE FORMATS
# =============================================================================

class MoodManagerRequest(BaseModel):
    """Standardized request format for mood management"""
    user_id: str = Field(..., description="Unique identifier for the user", example="user123")
    intent: str = Field(..., description="User's emotional state or request in natural language", 
                       example="I'm feeling really anxious about my presentation tomorrow")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context information",
                                  example={
                                      "time_of_day": "evening",
                                      "stress_level": 8,
                                      "voice_preference": "calm_female",
                                      "background_music": True,
                                      "brain_waves": True,
                                      "background_music_preference": "nature"
                                  })
    priority: str = Field(default="normal", description="Request priority level",
                         enum=["low", "normal", "high", "urgent"], example="high")

class MoodManagerResponse(BaseModel):
    """Standardized response format for mood management"""
    success: bool = Field(..., description="Whether the request was processed successfully")
    result: Any = Field(..., description="Main result data including intervention details")
    metadata: Dict[str, Any] = Field(..., description="Processing metadata and diagnostics")
    follow_up_suggestions: Optional[List[str]] = Field(default=None, description="Suggested follow-up actions")
    emotional_assessment: Optional[Dict[str, Any]] = Field(default=None, description="Analyzed emotional state")

# =============================================================================
# MOOD MANAGER BRAIN
# =============================================================================

class MoodManagerBrain:
    """
    LLM-Powered Brain specialized for mood management
    
    Uses HuggingFace InferenceClient to power intelligent decision making
    and orchestrates specialized tools for therapeutic interventions.
    """
    
    def __init__(self):
        # Initialize HuggingFace LLM client
        self.llm_client = InferenceClient(
            model="microsoft/DialoGPT-large",  # You can change to your preferred model
            token=None  # Add your HF token if needed
        )
        
        # Available tools for the LLM to use
        self.tools = [
            analyze_emotional_state,
            plan_intervention, 
            prepare_audio_params,
            call_audio_endpoint,
            call_cache_endpoint,
            generate_recommendations,
            handle_crisis
        ]
        
        # System prompt for the LLM (imported from prompts file)
        self.system_prompt = MOOD_MANAGER_SYSTEM_PROMPT
        
        self.context_memory = {}
    
    async def _process_request(self, request: MoodManagerRequest) -> MoodManagerResponse:
        """
        LLM-powered processing using available tools
        """
        try:
            # Create the prompt for the LLM using the template
            user_prompt = get_user_prompt_template(
                user_id=request.user_id,
                intent=request.intent,
                context=request.context,
                priority=request.priority
            )
            
            # Get LLM response with tool usage
            llm_response = await self._call_llm_with_tools(user_prompt, request)
            
            # Parse the LLM response and extract results
            return await self._synthesize_response(request, llm_response, {})
            
        except Exception as e:
            return MoodManagerResponse(
                success=False,
                result={"error": str(e)},
                metadata={"error_type": "llm_brain_error", "processing_method": "llm_powered"},
                follow_up_suggestions=["retry_request", "contact_support"]
            )
    
    async def _call_llm_with_tools(self, prompt: str, request: MoodManagerRequest) -> Dict[str, Any]:
        """
        Call LLM and execute tools based on its decisions
        """
        try:
            # For now, we'll simulate LLM tool calling by following the standard process
            # In a full implementation, you'd use a proper tool-calling LLM
            
            # Step 1: Analyze emotional state
            emotional_analysis = analyze_emotional_state(
                intent=request.intent,
                context=request.context
            )
            
            # Step 2: Check for crisis
            if emotional_analysis.get("crisis_level", 0) > 0.7:
                crisis_response = await handle_crisis(
                    request=request.dict(),
                    emotional_analysis=emotional_analysis
                )
                return {
                    "intervention_type": "crisis",
                    "emotional_analysis": emotional_analysis,
                    "crisis_response": crisis_response,
                    "llm_reasoning": "Crisis detected - activating emergency protocols"
                }
            
            # Step 3: Plan intervention
            intervention_plan = plan_intervention(
                intent=request.intent,
                context={"emotion_analysis": emotional_analysis, **request.context}
            )
            
            # Step 4: Prepare and generate audio
            audio_type = intervention_plan.get("audio_type")
            audio_result = None
            if audio_type:
                audio_params = prepare_audio_params(
                    request=request.dict(),
                    emotional_analysis=emotional_analysis,
                    audio_type=audio_type
                )
                audio_result = await call_audio_endpoint(
                    audio_type=audio_type,
                    params=audio_params
                )
            
            # Step 5: Generate recommendations
            recommendations = generate_recommendations(
                emotion_analysis=emotional_analysis,
                results={"audio": audio_result} if audio_result else None
            )
            
            return {
                "intervention_type": "standard",
                "emotional_analysis": emotional_analysis,
                "intervention_plan": intervention_plan,
                "audio": audio_result,
                "recommendations": recommendations,
                "llm_reasoning": f"Detected {emotional_analysis.get('primary_emotion')} with intensity {emotional_analysis.get('intensity')} - generated {audio_type} with personalized recommendations"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "intervention_type": "error",
                "llm_reasoning": "Failed to process request with tools"
            } 

    async def _synthesize_response(self, request: MoodManagerRequest, llm_results: Dict, 
                                 emotional_analysis: Dict) -> MoodManagerResponse:
        """
        Synthesize final response from LLM tool usage results
        """
        try:
            # Handle crisis response
            if llm_results.get("intervention_type") == "crisis":
                crisis_response = llm_results.get("crisis_response", {})
                return MoodManagerResponse(
                    success=True,
                    result=crisis_response,
                    metadata={
                        "intervention_type": "crisis",
                        "priority": "urgent",
                        "llm_reasoning": llm_results.get("llm_reasoning"),
                        "processing_method": "llm_powered"
                    },
                    follow_up_suggestions=[
                        "seek_professional_help",
                        "contact_emergency_services_if_needed", 
                        "check_in_1_hour"
                    ],
                    emotional_assessment=llm_results.get("emotional_analysis")
                )
            
            # Handle error response
            elif llm_results.get("intervention_type") == "error":
                return MoodManagerResponse(
                    success=False,
                    result={"error": llm_results.get("error")},
                    metadata={
                        "error_type": "tool_execution_error",
                        "llm_reasoning": llm_results.get("llm_reasoning"),
                        "processing_method": "llm_powered"
                    },
                    follow_up_suggestions=["retry_request", "contact_support"]
                )
            
            # Handle standard intervention response
            else:
                emotional_analysis = llm_results.get("emotional_analysis", {})
                audio = llm_results.get("audio", {})
                recommendations = llm_results.get("recommendations", {"immediate_actions": [], "follow_up_actions": []})
                
                return MoodManagerResponse(
                    success=True,
                    result={
                        "intervention_completed": True,
                        "audio_generated": audio.get("success", False),
                        "audio": audio,
                        "personalized_recommendations": recommendations
                    },
                    metadata={
                        "intervention_type": "standard",
                        "processing_method": "llm_powered",
                        "llm_reasoning": llm_results.get("llm_reasoning"),
                        "tools_used": ["analyze_emotional_state", "plan_intervention", "prepare_audio_params", "call_audio_endpoint", "generate_recommendations"]
                    },
                    follow_up_suggestions=recommendations.get("follow_up_actions", []),
                    emotional_assessment=emotional_analysis
                )
                
        except Exception as e:
            return MoodManagerResponse(
                success=False,
                result={"error": str(e)},
                metadata={"error_type": "response_synthesis_error", "processing_method": "llm_powered"},
                follow_up_suggestions=["retry_request"]
            )
        
# =============================================================================
# BRAIN ROUTER INTEGRATION
# =============================================================================

# Create the brain instance
mood_brain = MoodManagerBrain()

# Create router for brain endpoints
brain_router = APIRouter(prefix="/brain", tags=["mood-brain"])

@brain_router.post("/process", response_model=MoodManagerResponse,
                   operation_id="process_mood_request",
                   description='''Main endpoint for intelligent mood management
                   Args:
                   - request: MoodManagerRequest object
                   Returns:
                   - MoodManagerResponse object
                   ''',
                   )
async def process_mood_request(request: MoodManagerRequest) -> MoodManagerResponse:
    """
    Main endpoint for intelligent mood management
    
    This endpoint uses the mood brain to:
    1. Analyze emotional state
    2. Plan appropriate intervention  
    3. Execute intervention using existing tools
    4. Provide comprehensive response with follow-ups
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
                "trigger_examples": ["I feel angry but can't express it", "I'm holding back tears", "I feel numb"],
                "output": "Personalized release meditation with passionate tone targeting specific emotion (guilt, fear, grief, anger, desire)"
            },
            {
                "name": "Self-Belief & Esteem Enhancement", 
                "description": "Detect intent for self-improvement and prepare positive reinforcement audio for sleep",
                "trigger_examples": ["I don't believe in myself", "I feel worthless", "I need confidence"],
                "output": "Sleep meditation with calm tone and theta brain waves for subconscious reinforcement"
            },
            {
                "name": "Workout Motivation",
                "description": "Detect intent to feel energized during exercise and prepare motivation audio",
                "trigger_examples": ["I need energy for my workout", "I feel lazy to exercise", "Motivate me for gym"],
                "output": "Energetic workout meditation with beta brain waves and high volume"
            },
            {
                "name": "Mindfulness & Present Moment",
                "description": "Detect intent to be more present and prepare mindfulness meditation",
                "trigger_examples": ["My mind is scattered", "I want to be more mindful", "I'm always distracted"],
                "output": "Mindfulness meditation with calm tone and alpha brain waves"
            },
            {
                "name": "Crisis & Stress Management",
                "description": "Detect emotional crisis and high stress, provide immediate calming intervention",
                "trigger_examples": ["I'm having a panic attack", "I can't cope anymore", "I feel suicidal"],
                "output": "Crisis meditation with compassionate tone, alpha brain waves, plus emergency resources"
            }
        ],
        
        # Advanced emotional processing capabilities
        "emotional_intelligence": {
            "detection_capabilities": [
                "Suppressed emotion identification",
                "Self-esteem and confidence levels",
                "Energy and motivation states", 
                "Mindfulness and presence awareness",
                "Crisis and stress intensity"
            ],
            "supported_emotions": {
                "core_emotions": ["guilt", "fear", "grief", "anger", "desire", "lust"],
                "complex_states": ["suppressed_anger", "hidden_grief", "low_self_worth", "lack_of_motivation", "mental_scattered", "crisis_overwhelm"],
                "intensity_levels": ["low", "medium", "high", "crisis"]
            }
        },
        
        # Comprehensive intervention system
        "intervention_system": {
            "emotional_analysis": "Deep analysis of user's emotional state and suppressed feelings",
            "intervention_planning": "Customized plan based on detected emotion and user context",
            "audio_generation": "Personalized therapeutic audio with AI voice, background music, brain waves",
            "recommendation_engine": "Evidence-based immediate and follow-up action suggestions",
            "crisis_protocols": "Specialized handling for mental health emergencies"
        },
        
        # Audio personalization features
        "audio_capabilities": {
            "meditation_types": {
                "release_meditation": "For suppressed emotions (passionate tone, theta waves)",
                "sleep_meditation": "For self-improvement during sleep (calm tone, theta waves)",
                "workout_meditation": "For energy and motivation (energetic tone, beta waves)",
                "mindfulness_meditation": "For present moment awareness (calm tone, alpha waves)",
                "crisis_meditation": "For immediate calming (compassionate tone, alpha waves)"
            },
            "personalization": [
                "Emotion-specific content targeting guilt, fear, grief, anger, desire",
                "Intensity-based duration (10-20 minutes)",
                "Brain wave optimization (alpha, beta, theta)",
                "Background music selection",
                "Volume adjustment based on emotional state"
            ]
        },
        
        # Integration for external AI models
        "integration": {
            "input_format": "Natural language emotional expression via MoodManagerRequest",
            "schema_endpoint": "/brain/schema/request",
            "example_usage": "Send user's emotional state, receive personalized audio + recommendations",
            "response_format": "Structured intervention with audio file, emotional assessment, action plans"
        }
    }

@brain_router.post("/analyze-emotion")
async def analyze_emotion_only(user_input: str, context: Dict[str, Any] = None):
    """Analyze emotional state without full intervention - uses the modular tools"""
    if context is None:
        context = {}
        
    # Use the imported tools directly
    analysis = analyze_emotional_state(intent=user_input, context=context)
    intervention_plan = plan_intervention(intent=user_input, context={"emotion_analysis": analysis})
    
    return {
        "emotional_analysis": analysis,
        "recommended_intervention": intervention_plan,
        "metadata": {
            "tools_used": ["analyze_emotional_state", "plan_intervention"],
            "processing_method": "direct_tool_calls"
        }
    }

@brain_router.get("/tools")
async def get_available_tools():
    """Get list of available tools that the LLM agent can orchestrate"""
    return {
        "description": "LLM Agent Tool Inventory - The mood manager brain orchestrates these specialized tools",
        "total_tools": len(mood_brain.tools),
        "tools": [
            {
                "name": "analyze_emotional_state",
                "purpose": "Analyze user's emotional state from their intent and context",
                "inputs": ["intent (str)", "context (dict)"],
                "outputs": ["primary_emotion", "intensity", "crisis_level", "core_emotions", "confidence_level"]
            },
            {
                "name": "plan_intervention", 
                "purpose": "Plan therapeutic intervention strategy based on emotional context",
                "inputs": ["intent (str)", "context (dict)"],
                "outputs": ["audio_type", "voice_caching", "crisis_protocol", "intervention_type", "priority_level"]
            },
            {
                "name": "prepare_audio_params",
                "purpose": "Generate audio parameters based on emotion and audio type",
                "inputs": ["request (dict)", "emotional_analysis (dict)", "audio_type (str)"],
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
                "inputs": ["emotion_analysis (dict)", "results (optional dict)"],
                "outputs": ["immediate_actions (list)", "follow_up_actions (list)"]
            },
            {
                "name": "handle_crisis",
                "purpose": "Provide specialized crisis intervention protocols",
                "inputs": ["request (dict)", "emotional_analysis (dict)"],
                "outputs": ["immediate_resources", "audio", "crisis_protocol_activated", "emergency_contacts"]
            }
        ],
        "orchestration_flow": [
            "1. analyze_emotional_state → Understand user's emotional state",
            "2. plan_intervention → Choose optimal therapeutic approach", 
            "3a. handle_crisis → If crisis detected, activate emergency protocols",
            "3b. prepare_audio_params → Generate parameters for therapeutic audio",
            "4. call_audio_endpoint → Execute audio generation",
            "5. generate_recommendations → Provide actionable guidance",
            "Optional: call_cache_endpoint for voice management"
        ],
        "agent_benefits": [
            "Real intelligence via LLM reasoning vs hardcoded logic",
            "Transparency through tool usage logging with LLM reasoning", 
            "Extensibility for adding new tools without core logic changes",
            "Focused tool responsibilities with detailed schemas"
        ]
    }

@brain_router.get("/schema/request")
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