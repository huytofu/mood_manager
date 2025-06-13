"""
HABIT MANAGER INTERNAL ARCHITECTURE INTEGRATION
=============================================

This file integrates the LLM "brain" architecture specialized for habit management
with the existing FastAPI/MCP server setup.

The integration approach:
1. Keep existing app.py FastAPI/MCP configuration 
2. Add habit brain router that exposes intelligent habit management
3. Brain orchestrates habit tracking, formation, and behavioral change tools
4. Coordinates with mood manager for emotional-behavioral synergy
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient
import os
from datetime import datetime, timedelta

# Option 1: LangChain React Agent
try:
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain.tools import Tool
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Option 2: HuggingFace CodeAgent  
try:
    import yaml
    from smolagents import CodeAgent, HfApiModel, Tool as SmolAgentTool
    SMOLAGENTS_AVAILABLE = True
except ImportError:
    SMOLAGENTS_AVAILABLE = False

# Import tools from new modular structure
from .habit_basic_tools import (
    main_habit_operations,
    modify_habit_parameters,
    pause_resume_habit,
    habit_notes_operations,
)
from .habit_execution_tools import (
    daily_execution_operations,
    progress_tracking_operations,
    final_habit_answer,
)
from .habit_analytics_tools import (
    analyze_underperforming_habits,
    analyze_lagging_epic_progress,
    analyze_habit_interactions,
    analyze_mood_habit_correlation,
    generate_habit_insights,
    recommend_mood_supporting_habits,
)
from .habit_manager_prompts import HABIT_MANAGER_SYSTEM_PROMPT, get_habit_user_prompt_template, generate_habit_tools_documentation

# =============================================================================
# MANAGER REQUEST/RESPONSE FORMATS
# =============================================================================

class HabitManagerRequest(BaseModel):
    """Standardized request format for habit management"""
    user_id: str = Field(..., description="Unique identifier for the user", example="user123")
    intent: str = Field(..., description="Request from master manager in natural language", 
                        example="User wants to build a consistent meditation routine and break their social media addiction")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context information",
                        example={
                            "mood_coordination": True,
                            "current_stress_level": 7,
                            "available_time_slots": ["morning", "evening"],
                            "existing_routines": ["coffee at 7am", "gym 3x/week"],
                            "duration_preference": "short_term_wins"
                        })
    user_data: Dict[str, Any] = Field(default_factory=dict, description="Additional user data",
                            example={
                            "user_name": "John Doe",
                            "current_habits": ["social media 3hrs/day", "irregular sleep"],
                            "desired_habits": ["daily meditation", "consistent sleep schedule"],
                            "habit_failures": ["tried meditation apps 3 times"],
                            "motivation_level": 6,
                            "accountability_preference": "app_based",
                            "user_text_input": "I want to meditate daily but keep failing after 3 days"
                            })
    priority: str = Field(default="normal", description="Request priority level",
                        enum=["low", "normal", "high", "addiction_recovery"], example="high")

class HabitManagerResponse(BaseModel):
    """Standardized response format for habit management"""
    success: bool = Field(..., description="Whether the request was processed successfully")
    habit_plan: Optional[Dict[str, Any]] = Field(default=None, description="Comprehensive habit formation/breaking plan") 
    analysis: Optional[Dict[str, Any]] = Field(default=None, description="Habit analysis and insights")
    metadata: Dict[str, Any] = Field(..., description="Processing metadata and diagnostics")
    recommendations: Optional[List[str]] = Field(default=None, description="Suggested follow-up actions")

# =============================================================================
# HABIT MANAGER BRAIN
# =============================================================================

class HabitManagerBrain:
    """
    LLM-Powered Brain specialized for habit management and behavioral change
    
    Supports multiple agent implementations:
    - LangChain React Agent (Option 1)
    - HuggingFace CodeAgent (Option 2)  
    - Custom React Agent (Fallback)
    """
    
    def __init__(self, agent_type: str = "auto", hf_token: str = None):
        """
        Initialize HabitManagerBrain with specified agent type
        
        Args:
            agent_type: "langchain", "smolagents", "custom", or "auto"
            hf_token: HuggingFace API token for model access
        """
        if hf_token:
            self.hf_token = hf_token
        else:
            self.hf_token = os.getenv("HF_TOKEN")
        
        # Available tools for the LLM to use (habit formation and behavioral analysis)
        self.tools = [
            main_habit_operations,
            daily_execution_operations,
            progress_tracking_operations,
            # NEW BASIC OPERATIONS
            modify_habit_parameters,
            pause_resume_habit,
            habit_notes_operations,
            final_habit_answer,
            analyze_underperforming_habits,
            analyze_lagging_epic_progress,
            analyze_habit_interactions,
            analyze_mood_habit_correlation,
            generate_habit_insights,
            recommend_mood_supporting_habits
        ]
        
        # Generate dynamic tools documentation
        tools_documentation = generate_habit_tools_documentation(self.tools)
        
        # System prompt for the LLM with dynamic tools documentation
        self.system_prompt = HABIT_MANAGER_SYSTEM_PROMPT.format(tools_documentation=tools_documentation)
        self.context_memory = {}
        
        # Determine and initialize the agent in one step
        self.agent_type = self._determine_and_initialize_agent(agent_type)
    
    def _determine_and_initialize_agent(self, agent_type: str) -> str:
        """Determine which agent type to use and initialize it - LLM-powered agents only"""
        # Determine agent type based on availability
        if agent_type == "auto":
            if LANGCHAIN_AVAILABLE:
                selected_type = "langchain"
            elif SMOLAGENTS_AVAILABLE:
                selected_type = "smolagents"
            else:
                raise RuntimeError("No LLM-powered agent libraries available. Install langchain or smolagents.")
        elif agent_type == "langchain" and not LANGCHAIN_AVAILABLE:
            raise RuntimeError("LangChain not available. Install langchain or use smolagents.")
        elif agent_type == "smolagents" and not SMOLAGENTS_AVAILABLE:
            raise RuntimeError("SmolagentS not available. Install smolagents or use langchain.")
        else:
            selected_type = agent_type
        
        # Initialize the selected agent (LLM-powered only)
        print(f"Initializing {selected_type} habit agent...")
        
        if selected_type == "langchain":
            self._init_langchain_agent()
        elif selected_type == "smolagents":
            self._init_smolagents_agent()
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}. Use 'langchain', 'smolagents', or 'auto'.")
        
        return selected_type
    
    def _init_langchain_agent(self):
        """Initialize LangChain React Agent for habits"""
        try:
            # Create LangChain tools from our functions
            self.langchain_tools = []
            for tool_func in self.tools:
                lc_tool = Tool(
                    name=tool_func.__name__,
                    description=tool_func.__doc__ or f"Habit management tool: {tool_func.__name__}",
                    func=tool_func
                )
                self.langchain_tools.append(lc_tool)
            
            # Initialize LLM
            self.llm = InferenceClient(
                model="microsoft/DialoGPT-large",
                token=self.hf_token,
                model_kwargs={"temperature": 0.7, "max_length": 1500}
            )
            
            # Create React agent using system prompt
            self.prompt = PromptTemplate.from_template(self.system_prompt + "\n\nUser Request: {input}\n\n{agent_scratchpad}")
            
            # Create React agent
            self.agent = create_react_agent(self.llm, self.langchain_tools, self.prompt)
            self.agent_executor = AgentExecutor(
                agent=self.agent, 
                tools=self.langchain_tools, 
                verbose=True,
                max_iterations=10,
                handle_parsing_errors=True
            )
            
            print("✅ LangChain habit agent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize LangChain habit agent: {e}")
            raise RuntimeError(f"LangChain habit agent initialization failed: {str(e)}")
    
    def _init_smolagents_agent(self):
        """Initialize HuggingFace CodeAgent for habits"""
        try:
            # Create model
            self.model = HfApiModel(
                model_id="Qwen/Qwen2.5-Coder-32B-Instruct",
                token=self.hf_token
            )
            
            # Convert tools to smolagents format if needed
            smolagents_tools = []
            for tool in self.tools:
                try:
                    smolagents_tools.append(SmolAgentTool.from_langchain_tool(tool))
                except Exception:
                    # Fallback for tools that don't convert easily
                    pass
            
            # Create CodeAgent
            self.agent = CodeAgent(
                tools=smolagents_tools,
                model=self.model,
                max_iterations=10
            )
            
            print("✅ HuggingFace habit CodeAgent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize CodeAgent: {e}")
            raise RuntimeError(f"Smolagents habit agent initialization failed: {str(e)}")
    

    
    async def _call_llm_with_tools(self, prompt: str, request: HabitManagerRequest) -> Dict[str, Any]:
        """
        Call LLM and execute tools based on agent type - LLM-powered agents only
        """
        try:
            if self.agent_type == "langchain":
                return await self._call_langchain_agent(prompt, request)
            elif self.agent_type == "smolagents":
                return await self._call_smolagents_agent(prompt, request)
            else:
                raise ValueError(f"Unsupported agent type: {self.agent_type}")
            
        except Exception as e:
            return {
                "intervention_type": "error",
                "error": f"LLM habit agent execution error: {str(e)}",
                "llm_reasoning": f"Failed to process with {self.agent_type} agent: {str(e)}",
                "tools_used": [],
                "steps": []
            }
    
    async def _call_langchain_agent(self, agent_input: str, request: HabitManagerRequest) -> Dict[str, Any]:
        """Execute LangChain React Agent"""
        try:
            # Run the agent
            result = await self.agent_executor.ainvoke({"input": agent_input})
            
            # Extract information from LangChain result
            return {
                "llm_reasoning": result.get("output", ""),
                "intervention_type": "habit_creation",
                "tools_used": [step.tool for step in result.get("intermediate_steps", [])],
                "steps": [
                    {
                        "thought": step.log,
                        "action": step.tool,
                        "input": step.tool_input,
                        "observation": step.observation
                    }
                    for step in result.get("intermediate_steps", [])
                ],
                "final_result": {"intervention_completed": True, "method": "langchain"},
                "agent_type": "langchain"
            }
            
        except Exception as e:
            print(f"LangChain habit agent error: {e}")
            raise RuntimeError(f"LangChain habit agent failed: {str(e)}")
    
    async def _call_smolagents_agent(self, agent_input: str, request: HabitManagerRequest) -> Dict[str, Any]:
        """Execute HuggingFace CodeAgent"""
        try:
            # Run the agent
            result = self.agent.run(agent_input)
            
            # Extract information from smolagents result
            return {
                "llm_reasoning": str(result),
                "intervention_type": "habit_creation", 
                "tools_used": getattr(self.agent, "tool_calls", []),
                "steps": getattr(self.agent, "logs", []),
                "final_result": {"intervention_completed": True, "method": "smolagents"},
                "agent_type": "smolagents"
            }
            
        except Exception as e:
            print(f"CodeAgent habit error: {e}")
            raise RuntimeError(f"Smolagents habit agent failed: {str(e)}")
    


    async def _process_request(self, request: HabitManagerRequest) -> HabitManagerResponse:
        """
        LLM-powered processing using available tools
        """
        try:
            # Create the prompt for the LLM using the updated template with React pattern
            user_prompt = get_habit_user_prompt_template(
                user_id=request.user_id,
                intent=request.intent,
                context=request.context,
                user_data=request.user_data,
                priority=request.priority
            )
            
            # Get LLM response with tool usage
            llm_response = await self._call_llm_with_tools(user_prompt, request)
            
            # Parse the LLM response and extract results
            return await self._synthesize_response(request, llm_response)
            
        except Exception as e:
            return HabitManagerResponse(
                success=False,
                habit_plan={"is_created": False, "plan_id": None},
                analysis=None,
                metadata={"is_error": True, "error_type": "llm_brain_error", "intervention_type": None, "processing_method": "llm_powered"},
                recommendations=["retry_request", "contact_support", "simplify_habit_goals"]
            )
    
    async def _synthesize_response(self, request: HabitManagerRequest, llm_results: Dict) -> HabitManagerResponse:
        """
        Synthesize final response from LLM tool usage results using final_habit_answer output
        
        Expected input from final_habit_answer tool (FinalHabitAnswerOutput):
        - habit_plan: Optional[HabitOutput] with is_created, habit_id, plan_id
        - analysis: Optional[Dict[str, Any]] - combined analytics results
        - recommendations: List[str] - actionable suggestions
        - intervention_type: str - habit_creation/habit_analysis/habit_modification/error
        - error_type: Optional[str] - error classification
        - insights: Optional[List[str]] - behavioral insights
        - patterns: Optional[Dict[str, Any]] - behavioral patterns
        - integrated_analysis: Optional[Dict[str, Any]] - integrated analysis
        - analysis_sources: Optional[Dict[str, Any]] - analysis sources
        - underperforming_habits: Optional[List[Dict]] - underperformance data
        - epic_progress_data: Optional[Dict] - epic progress data  
        - habit_interactions: Optional[Dict] - interaction data
        - mood_correlations: Optional[Dict] - mood correlation data
        - daily_plan: Optional[Dict] - daily planning data
        - progress_data: Optional[Dict] - progress tracking data
        """
        try:
            # Extract standardized response from final_habit_answer tool (FinalHabitAnswerOutput Pydantic model)
            final_response = llm_results.get("final_response")
            
            if final_response:
                # Handle FinalHabitAnswerOutput Pydantic model
                intervention_type = final_response.intervention_type
                success = intervention_type != "error"
                
                # Convert HabitOutput to dict format for HabitManagerResponse
                habit_plan_data = None
                if final_response.habit_plan:
                    habit_plan_data = {
                        "is_created": final_response.habit_plan.is_created,
                        "habit_id": final_response.habit_plan.habit_id,
                        "plan_id": final_response.habit_plan.plan_id
                    }
                
                # Comprehensive analysis data combining all analytics results
                analysis_data = {}
                
                # Include basic analysis if available
                if final_response.analysis:
                    analysis_data.update(final_response.analysis)
                
                # Include advanced analytics fields
                if final_response.insights:
                    analysis_data["insights"] = final_response.insights
                if final_response.patterns:
                    analysis_data["patterns"] = final_response.patterns
                if final_response.integrated_analysis:
                    analysis_data["integrated_analysis"] = final_response.integrated_analysis
                if final_response.analysis_sources:
                    analysis_data["analysis_sources"] = final_response.analysis_sources
                
                # Include individual analytics results
                if final_response.underperforming_habits:
                    analysis_data["underperforming_habits"] = final_response.underperforming_habits
                if final_response.epic_progress_data:
                    analysis_data["epic_progress_data"] = final_response.epic_progress_data
                if final_response.habit_interactions:
                    analysis_data["habit_interactions"] = final_response.habit_interactions
                if final_response.mood_correlations:
                    analysis_data["mood_correlations"] = final_response.mood_correlations
                if final_response.daily_plan:
                    analysis_data["daily_plan"] = final_response.daily_plan
                if final_response.progress_data:
                    analysis_data["progress_data"] = final_response.progress_data
                
                # Handle recommendations (List[str])
                recommendations_data = final_response.recommendations if final_response.recommendations else []
                
                return HabitManagerResponse(
                    success=success,
                    habit_plan=habit_plan_data,
                    analysis=analysis_data if analysis_data else None,
                    metadata={
                        "is_error": not success,
                        "error_type": final_response.error_type,
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered",
                        "tools_used": llm_results.get("tools_used", []),
                        "agent_type": llm_results.get("agent_type", "unknown"),
                        "analytics_included": {
                            "insights": final_response.insights is not None,
                            "patterns": final_response.patterns is not None,
                            "integrated_analysis": final_response.integrated_analysis is not None,
                            "underperforming_habits": final_response.underperforming_habits is not None,
                            "epic_progress": final_response.epic_progress_data is not None,
                            "habit_interactions": final_response.habit_interactions is not None,
                            "mood_correlations": final_response.mood_correlations is not None,
                            "daily_plan": final_response.daily_plan is not None,
                            "progress_data": final_response.progress_data is not None
                        }
                    },
                    recommendations=recommendations_data
                )
            else:
                # Fallback if no final_response available - this should not happen with proper LLM execution
                intervention_type = llm_results.get("intervention_type", "error")
                return HabitManagerResponse(
                    success=False,
                    habit_plan={"is_created": False, "habit_id": None, "plan_id": None},
                    analysis=None,
                    metadata={
                        "is_error": True,
                        "error_type": "missing_final_response",
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered",
                        "failure_reason": "LLM did not call final_habit_answer tool"
                    },
                    recommendations=["retry_request", "contact_support", "verify_llm_tool_usage"]
                )
                
        except Exception as e:
            # Fallback for unexpected errors during response synthesis
            return HabitManagerResponse(
                success=False,
                habit_plan={"is_created": False, "habit_id": None, "plan_id": None},
                analysis=None,
                metadata={
                    "is_error": True,
                    "error_type": "response_synthesis_error",
                    "intervention_type": "error",
                    "priority": request.priority,
                    "processing_method": "llm_powered",
                    "failure_reason": f"Synthesis error: {str(e)}"
                },
                recommendations=["retry_request", "contact_support", "check_final_response_format"]
            )

    async def process_request(self, request: HabitManagerRequest) -> HabitManagerResponse:
        """
        Public method to process habit management requests
        """
        return await self._process_request(request) 