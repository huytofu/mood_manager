from fastapi import APIRouter
from ..habit_manager_brain import HabitManagerBrain, HabitManagerRequest, HabitManagerResponse
from typing import Dict, Any

# =============================================================================
# BRAIN ROUTER INTEGRATION
# =============================================================================

# Create the brain instance with auto-detection of available agent types
habit_brain = HabitManagerBrain(agent_type="auto")

# Create router for brain endpoints
brain_router = APIRouter(prefix="/brain", tags=["habit-brain"])

@brain_router.post("/process", response_model=HabitManagerResponse,
                   operation_id="process_habit_request",
                   description='''Main endpoint for intelligent habit management
                   Args:
                   - request: HabitManagerRequest object. Please check the schema for the request object by calling the /brain/schema/request endpoint.
                   Returns:
                   - HabitManagerResponse object. Please check the schema for the response object by calling the /brain/schema/response endpoint.
                   ''',
                   )
async def process_habit_request(request: HabitManagerRequest) -> HabitManagerResponse:
    """
    Main endpoint for intelligent habit management
    
    This endpoint uses the habit brain to:
    1. Analyze user's habit goals and behavioral patterns
    2. Create comprehensive habit formation/breaking plans
    3. Execute advanced analytics for struggling habits
    4. Generate adaptive recommendations based on mood coordination
    5. Provide evidence-based behavioral change strategies
    """
    return await habit_brain.process_request(request)

@brain_router.get("/capabilities",
                  operation_id="get_brain_capabilities",
                  description='''Get habit manager brain capabilities
                  Args:
                  - None
                  Returns:
                  - Dictionary containing brain capabilities
                  ''',
                  response_description='''Dictionary containing brain capabilities
                  ''',
                  response_model=Dict[str, Any],
                  tags=["habit-brain"]
                )
async def get_brain_capabilities():
    """Get habit manager brain capabilities - what it can DO, not how it does it"""
    return {
        "manager": "Habit Manager",
        "version": "1.0",
        "description": "AI-powered behavioral change specialist for habit formation, breaking bad habits, and addiction recovery. Uses LLM knowledge for general recommendations, specialized tools for crisis mood support.",
        
        # Core behavioral interventions the habit manager can perform
        "core_interventions": [
            {
                "name": "Habit Formation Planning",
                "description": "Create comprehensive plans for building new positive habits using behavioral science",
                "input_examples": {
                    "user_id": "user123",
                    "intent": "I want to meditate daily but keep failing after 3 days",
                    "desired_habits": ["daily meditation", "consistent sleep schedule"],
                    "motivation_level": 6,
                    "available_time_slots": ["morning", "evening"]
                },
                "output": "Epic habit goals with micro-habits, scheduling, tracking system, and progressive complexity"
            },
            {
                "name": "Bad Habit Breaking & Addiction Recovery", 
                "description": "Design strategies to break destructive patterns and support addiction recovery",
                "input_examples": {
                    "user_id": "user123",
                    "intent": "I need to quit social media addiction and reduce screen time",
                    "current_habits": ["social media 3hrs/day", "binge watching"],
                    "habit_failures": ["tried digital detox 3 times"],
                    "priority": "addiction_recovery"
                },
                "output": "Replacement behaviors, environment design, harm reduction protocols, and relapse prevention"
            },
            {
                "name": "Underperforming Habit Analysis",
                "description": "Analyze struggling habits and provide actionable improvement recommendations",
                "input_examples": {
                    "user_id": "user123",
                    "intent": "I'm struggling with consistency in my habits, need analysis of what's going wrong",
                    "time_period": "monthly"
                },
                "output": "Completion rate analysis, bottleneck identification, timing optimization, and corrective strategies"
            },
            {
                "name": "Epic Goal Progress Tracking",
                "description": "Monitor progress toward major life goals and detect when they're falling behind",
                "input_examples": {
                    "user_id": "user123",
                    "intent": "Check if my fitness transformation goal is on track",
                    "epic_habit_id": "epic_123",
                    "target_completion_date": "2024-06-01"
                },
                "output": "Weighted progress calculation, micro-habit performance analysis, schedule adjustments"
            },
            {
                "name": "Mood-Habit Coordination",
                "description": "Adapt habit strategies based on emotional state and crisis levels",
                "input_examples": {
                    "user_id": "user123",
                    "intent": "I'm in a depressive episode, how should I adjust my habits?",
                    "current_stress_level": 8,
                    "mood_coordination": True,
                    "is_crisis": True
                },
                "output": "Crisis-adapted habits, minimum viable routines, mood-supporting recommendations"
            },
            {
                "name": "Behavioral Pattern Analysis",
                "description": "Detect habit interactions, timing patterns, and behavioral insights",
                "input_examples": {
                    "user_id": "user123",
                    "intent": "Find patterns in my habit performance and mood correlations",
                    "time_period": "monthly"
                },
                "output": "Synergistic/antagonistic habit pairs, optimal timing windows, mood correlation insights"
            }
        ],
        
        # Comprehensive intervention flow
        "intervention_flow": {
            "1. Behavioral Analysis": "Assess current patterns, failures, and motivational context",
            "2. Goal Decomposition": "Break large goals into micro-habits and epic habits",
            "3. Scientific Planning": "Apply cue-routine-reward loops, habit stacking, environment design",
            "4. Mood Integration": "Coordinate with emotional state for crisis-adaptive strategies",
            "5. Tracking & Analytics": "Monitor performance and provide data-driven adjustments",
            "6. Recovery Protocols": "Build in forgiveness mechanisms and restart strategies"
        },
        
        # Behavioral science principles
        "behavioral_science": {
            "habit_formation_principles": [
                "Start Small (2-minute rule)",
                "Environment Design (obvious cues, invisible friction)",
                "Identity Alignment (be someone who...)",
                "Progressive Overload (gradual complexity increase)",
                "Habit Stacking (link to existing routines)"
            ],
            "breaking_bad_habits": [
                "Replacement Behaviors (substitute positive actions)",
                "Environmental Modification (remove triggers)",
                "Implementation Intentions (when X happens, I will Y)",
                "Social Accountability (leverage relationships)",
                "Harm Reduction (gradual vs cold turkey approaches)"
            ],
            "addiction_recovery": [
                "Relapse Prevention Planning",
                "Trigger Identification and Management",
                "Recovery-Supporting Habit Networks",
                "Emotional Regulation Skills",
                "Crisis Protocol Activation"
            ]
        },
        
        # Mood coordination features
        "mood_coordination": {
            "crisis_adaptation": {
                "level_8_plus": "Survival habits only (eating, sleeping, hygiene)",
                "level_5_to_7": "Simplified habits, reduced complexity by 50%",
                "level_below_5": "Normal habit complexity with mood optimization"
            },
            "emotional_states": {
                "depression": "Very small achievable habits, social connection focus",
                "anxiety": "Stress-reducing habits, mindfulness integration",
                "high_energy": "Capitalize on motivation for challenging habits",
                "low_motivation": "Minimum viable habits, environmental support"
            }
        },
        
        # Integration for external AI models
        "integration": {
            "tool_architecture": {
                "basic_operations": {
                    "count": 3,
                    "tools": ["main_habit_operations", "daily_execution_operations", "progress_tracking_operations"],
                    "purpose": "Core habit CRUD and daily workflow operations"
                },
                "advanced_analytics": {
                    "count": 5,
                    "tools": ["analyze_underperforming_habits", "analyze_lagging_epic_progress", "analyze_habit_interactions", "analyze_mood_habit_correlation", "generate_habit_insights"],
                    "purpose": "Behavioral pattern analysis ending with comprehensive insights"
                },
                "mood_integration": {
                    "count": 1,
                    "tools": ["recommend_mood_supporting_habits"],
                    "purpose": "Crisis-adaptive recommendations for stress/depression only"
                },
                "response_formatting": {
                    "count": 1,
                    "tools": ["final_habit_answer"],
                    "purpose": "Standardized output with fixed Pydantic schema"
                }
            },
            "tools_details_endpoint": "/brain/tools",
            "input_format": "HabitManagerRequest",
            "output_format": "HabitManagerResponse",
            "input_schema_endpoint": "/brain/schema/request",
            "output_schema_endpoint": "/brain/schema/response",
            "example_usage": "Send user's habit goals and constraints, receive comprehensive behavioral change plan",
            "response_format": "Structured intervention with habit plans, analytics, and adaptive recommendations",
            "workflow_patterns": {
                "habit_creation": "main_habit_operations → LLM recommendations → mood_support (if crisis) → final_habit_answer",
                "habit_analysis": "analytics_tools → generate_habit_insights → LLM recommendations → mood_support (if crisis) → final_habit_answer",
                "daily_execution": "daily_execution_operations → progress_tracking_operations → LLM optimization → final_habit_answer"
            },
            "key_principle": "LLM generates behavioral science recommendations from knowledge, recommend_mood_supporting_habits only extends for crisis situations"
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
                  tags=["habit-brain"]
                )
async def get_available_tools():
    """Get list of available tools that the LLM agent can orchestrate"""
    return {
        "description": "LLM Agent Tool Inventory - The habit manager brain orchestrates these specialized tools. LLM generates general recommendations from behavioral science knowledge, then extends with recommend_mood_supporting_habits only for crisis situations (stress/depression).",
        "total_tools": 10,
        "tool_architecture": {
            "basic_operations": {
                "count": 3,
                "purpose": "Core CRUD operations for habit creation, daily execution, and progress tracking",
                "tools": ["main_habit_operations", "daily_execution_operations", "progress_tracking_operations"]
            },
            "advanced_analytics": {
                "count": 5,
                "purpose": "Behavioral pattern analysis and insights generation (step 1 for analytics)",
                "tools": ["analyze_underperforming_habits", "analyze_lagging_epic_progress", "analyze_habit_interactions", "analyze_mood_habit_correlation", "generate_habit_insights"]
            },
            "mood_integration": {
                "count": 1,
                "purpose": "Crisis-adaptive recommendations for stress/depression only",
                "tools": ["recommend_mood_supporting_habits"]
            },
            "response_formatting": {
                "count": 1,
                "purpose": "Standardized output format with fixed schema",
                "tools": ["final_habit_answer"]
            }
        },
        "tools": [
            {
                "name": "main_habit_operations", 
                "category": "basic_operations",
                "purpose": "Execute core habit creation and epic goal management",
                "inputs": ["operation: str", "params: dict"],
                "outputs": ["success: bool", "data: dict", "operation: str", "error: str"],
                "operations": ["create_micro_habit", "create_epic_habit", "assign_micro_to_epic"],
                "usage": "Primary tool for habit formation and goal structure creation"
            },
            {
                "name": "daily_execution_operations",
                "category": "basic_operations",
                "purpose": "Handle daily habit execution, mood tracking, and flexible scheduling",
                "inputs": ["operation: str", "params: dict"],
                "outputs": ["success: bool", "data: dict", "operation: str", "error: str"],
                "operations": ["record_mood", "get_daily_habits", "plan_flexible_habits"],
                "usage": "Daily workflow operations and mood coordination"
            },
            {
                "name": "progress_tracking_operations",
                "category": "basic_operations", 
                "purpose": "Track habit completion and calculate progress metrics",
                "inputs": ["operation: str", "params: dict"],
                "outputs": ["success: bool", "data: dict", "operation: str", "error: str"],
                "operations": ["track_completion", "calculate_trends", "calculate_epic_progress"],
                "usage": "Performance monitoring and progress analytics"
            },
            {
                "name": "analyze_underperforming_habits",
                "category": "advanced_analytics",
                "purpose": "Identify habits with poor completion rates and generate actionable fixes (step 1)",
                "inputs": ["user_id: str", "time_period: str", "threshold: float"],
                "outputs": ["underperforming_habits: list", "analysis: dict", "recommendations: list"],
                "usage": "Diagnose struggling habits and provide corrective strategies"
            },
            {
                "name": "analyze_lagging_epic_progress", 
                "category": "advanced_analytics",
                "purpose": "Detect epic goals behind schedule and suggest corrective actions (step 1)",
                "inputs": ["epic_habit_id: str", "target_progress_rate: float"],
                "outputs": ["epic_analysis: dict", "bottleneck_habits: list", "corrective_actions: list"],
                "usage": "Monitor epic goal progress and identify bottlenecks"
            },
            {
                "name": "analyze_habit_interactions",
                "category": "advanced_analytics",
                "purpose": "Find synergistic and antagonistic patterns between habits (step 1)",
                "inputs": ["user_id: str", "time_period: str", "interaction_type: str"],
                "outputs": ["synchronous_pairs: list", "antagonistic_pairs: list", "insights: list"],
                "usage": "Detect habit interference and synergy patterns"
            },
            {
                "name": "analyze_mood_habit_correlation",
                "category": "advanced_analytics",
                "purpose": "Calculate statistical relationships between mood and habit performance (step 1)",
                "inputs": ["user_id: str", "habit_id: str", "time_period: str"],
                "outputs": ["correlations: dict", "insights: list", "recommendations: list"],
                "usage": "Understand emotional impact on habit completion"
            },
            {
                "name": "generate_habit_insights",
                "category": "advanced_analytics",
                "purpose": "Comprehensive behavioral analysis and optimization insights (ALWAYS FINAL STEP)",
                "inputs": ["user_id: str", "habit_id: str", "insight_type: str"],
                "outputs": ["insights: list", "patterns: dict", "recommendations: list"],
                "usage": "Final comprehensive analysis combining all behavioral patterns"
            },
            {
                "name": "recommend_mood_supporting_habits",
                "category": "mood_integration",
                "purpose": "Suggest crisis-adaptive habits for stress/depression ONLY",
                "inputs": ["mood_state: str", "is_crisis: bool", "is_depressed: bool", "crisis_level: int"],
                "outputs": ["mood_supporting_habits: list"],
                "usage": "Crisis intervention: extends LLM recommendations with hard-coded mood support",
                "restriction": "Only use for stress (crisis_level ≥ 5) or depression states"
            },
            {
                "name": "final_habit_answer",
                "category": "response_formatting",
                "purpose": "Format standardized response with fixed output schema",
                "inputs": ["intervention_type: str", "habit_plan: dict", "analysis: dict", "recommendations: list", "error_message: str"],
                "outputs": ["FinalHabitAnswerOutput: Pydantic model"],
                "usage": "Required final step - standardizes all responses for Master Manager",
                "schema": {
                    "habit_plan": "HabitOutput (is_created, habit_id, plan_id)",
                    "analysis": "Optional[Dict] - analytics results",
                    "recommendations": "List[str] - actionable suggestions",
                    "intervention_type": "str - habit_creation/habit_analysis/habit_modification/error",
                    "error_type": "Optional[str] - error classification"
                }
            }
        ],
        "orchestration_patterns": {
            "habit_creation": [
                "1. main_habit_operations → create epic and micro habits",
                "2. LLM generates behavioral science recommendations",
                "3. recommend_mood_supporting_habits (if crisis detected)",
                "4. final_habit_answer → standardized output"
            ],
            "habit_analysis": [
                "1. analytics tools (step 1) → analyze patterns/issues",
                "2. generate_habit_insights → comprehensive analysis (FINAL STEP)",
                "3. LLM generates improvement recommendations",
                "4. recommend_mood_supporting_habits (if crisis detected)",
                "5. final_habit_answer → standardized output"
            ],
            "daily_execution": [
                "1. daily_execution_operations → mood tracking, get habits",
                "2. progress_tracking_operations → track completions",
                "3. LLM generates daily optimization suggestions",
                "4. final_habit_answer → standardized output"
            ]
        },
        "analytics_workflow": {
            "pattern": "Unidirectional flow ending with generate_habit_insights",
            "step_1_tools": ["analyze_underperforming_habits", "analyze_lagging_epic_progress", "analyze_habit_interactions", "analyze_mood_habit_correlation"],
            "final_step_tool": "generate_habit_insights",
            "rule": "LLM should always arrive at generate_habit_insights as the final analytical step"
        },
        "crisis_adaptation": {
            "trigger_conditions": {
                "high_crisis": "crisis_level ≥ 8 or severe stress/depression",
                "medium_crisis": "crisis_level ≥ 5 or moderate stress",
                "depression": "is_depressed = true"
            },
            "adaptation_strategy": {
                "high_crisis": "Survival habits only (eating, sleeping, hygiene)",
                "medium_crisis": "Simplified habits, reduced complexity by 50%",
                "depression": "Very small achievable habits, social connection focus"
            }
        }
    }

@brain_router.get("/schema/request",
                  operation_id="get_request_schema",
                  description='''Get the exact schema for HabitManagerRequest - useful for external AI models
                  Args:
                  - None
                  Returns:
                  - Dictionary containing request schema, example, and description
                  ''',
                  response_description='''Dictionary containing complete request schema including:
                  - JSON schema specification for HabitManagerRequest
                  - Practical example with all required fields
                  - Usage description for external AI model integration
                  ''',
                  response_model=Dict[str, Any],
                  tags=["habit-brain", "schema"]
                )
async def get_request_schema():
    """Get the exact schema for HabitManagerRequest - useful for external AI models"""
    return {
        "schema": HabitManagerRequest.model_json_schema(),
        "example": {
            "user_id": "user123",
            "intent": "User wants to build a consistent meditation routine and break their social media addiction",
            "context": {
                "mood_coordination": True,
                "current_stress_level": 7,
                "available_time_slots": ["morning", "evening"],
                "existing_routines": ["coffee at 7am", "gym 3x/week"],
                "duration_preference": "short_term_wins"
            },
            "user_data": {
                "user_name": "John Doe",
                "current_habits": ["social media 3hrs/day", "irregular sleep"],
                "desired_habits": ["daily meditation", "consistent sleep schedule"],
                "habit_failures": ["tried meditation apps 3 times"],
                "motivation_level": 6,
                "accountability_preference": "app_based",
                "user_text_input": "I want to meditate daily but keep failing after 3 days"
            },
            "priority": "high"
        },
        "description": "External AI models can use this schema to structure requests to /brain/process"
    }

@brain_router.get("/schema/response",
                  operation_id="get_response_schema", 
                  description='''Get the exact schema for HabitManagerResponse - useful for external AI models
                  Args:
                  - None
                  Returns:
                  - Dictionary containing response schema, example, and description
                  ''',
                  response_description='''Dictionary containing complete response schema including:
                  - JSON schema specification for HabitManagerResponse
                  - Practical example with all response fields
                  - Usage description for external AI model integration
                  ''',
                  response_model=Dict[str, Any],
                  tags=["habit-brain", "schema"]
                )
async def get_response_schema():
    """Get the exact schema for HabitManagerResponse - useful for external AI models"""
    return {
        "schema": HabitManagerResponse.model_json_schema(),
        "example": {
            "success": True,
            "habit_plan": {
                "is_created": True,
                "habit_id": "epic_habit_123",
                "plan_id": "plan_456"
            },
            "analysis": {
                "underperforming_habits": [
                    {
                        "habit_id": "habit_789",
                        "habit_name": "Daily Meditation",
                        "completion_rate": 0.25,
                        "issues": ["timing_conflicts", "too_ambitious"]
                    }
                ],
                "recommendations": ["simplify_to_2_minute_breathing", "link_to_coffee_routine"]
            },
            "metadata": {
                "is_error": False,
                "error_type": None,
                "intervention_type": "habit_creation",
                "priority": "high",
                "processing_method": "llm_powered"
            },
            "recommendations": [
                "start_with_smallest_habit",
                "track_daily_progress", 
                "be_patient_with_formation",
                "use_habit_stacking_with_coffee",
                "celebrate_2_day_streaks"
            ]
        },
        "description": "External AI models can use this schema to interpret responses from /brain/process"
    } 