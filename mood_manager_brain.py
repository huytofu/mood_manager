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

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient

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
    from smolagents import CodeAgent, HfApiModel
    SMOLAGENTS_AVAILABLE = True
except ImportError:
    SMOLAGENTS_AVAILABLE = False

# Import tools and prompts from separate files
from .mood_manager_tools import (
    plan_intervention, 
    prepare_audio_params,
    call_audio_endpoint,
    call_cache_endpoint,
    generate_recommendations,
    handle_crisis
)
from .mood_manager_prompts import MOOD_MANAGER_SYSTEM_PROMPT, get_user_prompt_template, get_react_format_reminder

# =============================================================================
# MANAGER REQUEST/RESPONSE FORMATS
# =============================================================================

class MoodManagerRequest(BaseModel):
    """Standardized request format for mood management"""
    user_id: str = Field(..., description="Unique identifier for the user", example="user123")
    intent: str = Field(..., description="Request from master manager in natural language", 
                        example="User is anxious about his presentation tomorrow. Please help to generate a meditation audio to help him.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context information",
                        example={
                            "stress_level": 8,
                            "selected_tone": "calm",
                            "use_user_voice": True,
                            "should_use_background_music": True,
                            "should_use_brain_waves": True,
                            "music_style": "natural sounds",
                            "duration": 10,
                        })
    user_data: Dict[str, Any] = Field(default_factory=dict, description="Additional user data",
                            example={
                            "user_name": "John Doe",
                            "user_crisis_level": 8,
                            "user_age": 30,
                            "user_gender": "male",
                            "user_text_input": "I am feeling anxious about my presentation tomorrow. Please help me to relax."
                            })
    priority: str = Field(default="normal", description="Request priority level",
                        enum=["low", "normal", "high"], example="high")

# TO REVIEW:
class MoodManagerResponse(BaseModel):
    """Standardized response format for mood management"""
    success: bool = Field(..., description="Whether the request was processed successfully")
    audio: Optional[Dict[str, Any]] = Field(default=None, description="Audio file metadata with fields like is_created, audio_id, task_type, file_path, etc.") 
    metadata: Dict[str, Any] = Field(..., description="Processing metadata and diagnostics")
    recommendations: Optional[List[str]] = Field(default=None, description="Suggested follow-up actions")

# =============================================================================
# MOOD MANAGER BRAIN
# =============================================================================

class MoodManagerBrain:
    """
    LLM-Powered Brain specialized for mood management
    
    Supports multiple agent implementations:
    - LangChain React Agent (Option 1)
    - HuggingFace CodeAgent (Option 2)  
    - Custom React Agent (Fallback)
    """
    
    def __init__(self, agent_type: str = "auto", hf_token: str = None):
        """
        Initialize MoodManagerBrain with specified agent type
        
        Args:
            agent_type: "langchain", "smolagents", "custom", or "auto"
            hf_token: HuggingFace API token for model access
        """
        self.hf_token = hf_token
        
        # Available tools for the LLM to use (emotional analysis now handled by Master Manager)
        self.tools = [
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
        
        # Determine and initialize the agent in one step
        self.agent_type = self._determine_and_initialize_agent(agent_type)
    
    def _determine_and_initialize_agent(self, agent_type: str) -> str:
        """Determine which agent type to use and initialize it"""
        # Determine agent type based on availability
        if agent_type == "auto":
            if LANGCHAIN_AVAILABLE:
                selected_type = "langchain"
            elif SMOLAGENTS_AVAILABLE:
                selected_type = "smolagents"
            else:
                selected_type = "custom"
        elif agent_type == "langchain" and not LANGCHAIN_AVAILABLE:
            print("LangChain not available, falling back to custom implementation")
            selected_type = "custom"
        elif agent_type == "smolagents" and not SMOLAGENTS_AVAILABLE:
            print("SmolagentS not available, falling back to custom implementation")
            selected_type = "custom"
        else:
            selected_type = agent_type
        
        # Initialize the selected agent
        print(f"Initializing {selected_type} agent...")
        
        if selected_type == "langchain":
            self._init_langchain_agent()
        elif selected_type == "smolagents":
            self._init_smolagents_agent()
        else:
            self._init_custom_agent()
        
        return selected_type
    
    def _init_langchain_agent(self):
        """Initialize LangChain React Agent"""
        try:
            # Create LangChain tools from our functions
            self.langchain_tools = []
            for tool_func in self.tools:
                lc_tool = Tool(
                    name=tool_func.__name__,
                    description=tool_func.__doc__ or f"Mood management tool: {tool_func.__name__}",
                    func=tool_func
                )
                self.langchain_tools.append(lc_tool)
            
            # Initialize LLM
            self.llm = InferenceClient(
                model="microsoft/DialoGPT-large",
                token=self.hf_token,
                model_kwargs={"temperature": 0.7, "max_length": 1500}
            )
            
            # Load React prompt template
            with open("prompts/mood_manager_prompt.txt", "r") as f:
                template = f.read()
            
            self.prompt = PromptTemplate.from_template(template)
            
            # Create React agent
            self.agent = create_react_agent(self.llm, self.langchain_tools, self.prompt)
            self.agent_executor = AgentExecutor(
                agent=self.agent, 
                tools=self.langchain_tools, 
                verbose=True,
                max_iterations=10,
                handle_parsing_errors=True
            )
            
            print("✅ LangChain React Agent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize LangChain agent: {e}")
            print("Falling back to custom implementation...")
            self.agent_type = "custom"
            self._init_custom_agent()
    
    def _init_smolagents_agent(self):
        """Initialize HuggingFace CodeAgent"""
        try:
            # Create model
            self.model = HfApiModel(
                model_id="microsoft/DialoGPT-large",
                token=self.hf_token
            )
            
            # Convert our tools to smolagents format
            # Note: smolagents expects tools to be classes or have specific format
            # This might need adjustment based on your tool implementations
            
            # Create CodeAgent  
            self.agent = CodeAgent(
                tools=self.tools,
                model=self.model,
                max_iterations=10
            )
            
            print("✅ HuggingFace CodeAgent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize CodeAgent: {e}")
            print("Falling back to custom implementation...")
            self.agent_type = "custom"
            self._init_custom_agent()
    
    def _init_custom_agent(self):
        """Initialize simplified fallback implementation"""
        # No LLM client needed for direct tool execution
        print("✅ Simplified fallback agent initialized successfully")
    
    async def _call_llm_with_tools(self, prompt: str, request: MoodManagerRequest) -> Dict[str, Any]:
        """
        Call LLM and execute tools based on agent type
        """
        # Format input for agent
        agent_input = f"""
        User ID: {request.user_id}
        Intent: {request.intent}
        Context: {request.context}
        Priority: {request.priority}
        
        Please help this user with their emotional state using your available tools.
        """
        
        try:
            if self.agent_type == "langchain":
                return await self._call_langchain_agent(agent_input, request)
            elif self.agent_type == "smolagents":
                return await self._call_smolagents_agent(agent_input, request)
            else:
                return await self._call_custom_agent(prompt, request)
                
        except Exception as e:
            return {
                "intervention_type": "error",
                "error": f"Agent execution error: {str(e)}",
                "llm_reasoning": f"Failed to process with {self.agent_type} agent: {str(e)}",
                "tools_used": [],
                "steps": []
            }
    
    async def _call_langchain_agent(self, agent_input: str, request: MoodManagerRequest) -> Dict[str, Any]:
        """Execute LangChain React Agent"""
        try:
            # Run the agent
            result = await self.agent_executor.ainvoke({"input": agent_input})
            
            # Extract information from LangChain result
            return {
                "llm_reasoning": result.get("output", ""),
                "intervention_type": "standard",
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
            print(f"LangChain agent error: {e}")
            # Fallback to custom implementation
            return await self._call_custom_agent("", request)
    
    async def _call_smolagents_agent(self, agent_input: str, request: MoodManagerRequest) -> Dict[str, Any]:
        """Execute HuggingFace CodeAgent"""
        try:
            # Run the agent
            result = self.agent.run(agent_input)
            
            # Extract information from smolagents result
            return {
                "llm_reasoning": str(result),
                "intervention_type": "standard", 
                "tools_used": getattr(self.agent, "tool_calls", []),
                "steps": getattr(self.agent, "logs", []),
                "final_result": {"intervention_completed": True, "method": "smolagents"},
                "agent_type": "smolagents"
            }
            
        except Exception as e:
            print(f"CodeAgent error: {e}")
            # Fallback to custom implementation  
            return await self._call_custom_agent("", request)
    
    async def _call_custom_agent(self, prompt: str, request: MoodManagerRequest) -> Dict[str, Any]:
        """Execute simplified fallback implementation using direct tool calls"""
        print("Using simplified fallback agent (no LLM reasoning)")
        
        # Create tool mapping for easy access
        tool_map = {tool.__name__: tool for tool in self.tools}
        
        # Initialize results storage
        results = {
            "steps": [],
            "final_result": {},
            "llm_reasoning": "Simplified fallback - direct tool execution without LLM reasoning",
            "tools_used": [],
            "agent_type": "custom_fallback"
        }
        
        try:
            # Execute tools in standard mood management sequence following React pattern
            # 1. Plan intervention (emotional analysis comes from Master Manager via user_data)
            intervention_plan = plan_intervention(
                intent=request.intent,
                context=request.context,
                user_data=request.user_data
            )
            results["intervention_plan"] = intervention_plan
            results["tools_used"].append("plan_intervention")
            results["steps"].append({
                "thought": "I need to plan therapeutic intervention based on Master Manager's analysis and user data",
                "action": "plan_intervention", 
                "input": {"intent": request.intent, "context": request.context, "user_data": request.user_data},
                "observation": intervention_plan
            })
            
            # 2. Check for crisis
            if intervention_plan.get("crisis_protocol", False):
                crisis_response = handle_crisis(request=request.dict())
                results["crisis_response"] = crisis_response
                results["intervention_type"] = "crisis"
                results["tools_used"].append("handle_crisis")
                results["steps"].append({
                    "thought": "Crisis detected in intervention plan. I must activate emergency protocols immediately.",
                    "action": "handle_crisis",
                    "input": {"request": request.dict()},
                    "observation": crisis_response
                })
            else:
                # 3. Prepare audio parameters
                audio_params = prepare_audio_params(
                    request=request.dict(),
                    audio_type=intervention_plan.get("audio_type", "mindfulness_meditation")
                )
                results["tools_used"].append("prepare_audio_params")
                results["steps"].append({
                    "thought": f"No crisis detected. I need to prepare audio parameters for {intervention_plan.get('audio_type')} intervention.",
                    "action": "prepare_audio_params",
                    "input": {"request": request.dict(), "audio_type": intervention_plan.get("audio_type")},
                    "observation": audio_params
                })
                
                # 4. Generate audio
                audio_result = call_audio_endpoint(
                    audio_type=intervention_plan.get("audio_type", "mindfulness_meditation"),
                    params=audio_params
                )
                results["audio"] = audio_result
                results["tools_used"].append("call_audio_endpoint")
                results["steps"].append({
                    "thought": "Now I will generate the therapeutic audio using the prepared parameters.",
                    "action": "call_audio_endpoint",
                    "input": {"audio_type": intervention_plan.get("audio_type"), "params": audio_params},
                    "observation": audio_result
                })
            
            # 5. Generate recommendations
            recommendations = generate_recommendations(
                request=request.dict(),
                results=results.get("audio", None)
            )
            results["recommendations"] = recommendations
            results["tools_used"].append("generate_recommendations")
            results["steps"].append({
                "thought": "Finally, I need to generate personalized recommendations to help the user with immediate and follow-up actions.",
                "action": "generate_recommendations",
                "input": {"request": request.dict(), "results": results.get("audio", None)},
                "observation": recommendations
            })
            
            results["final_result"] = {
                "intervention_completed": True, 
                "method": "custom_fallback",
                "total_tools_executed": len(results["tools_used"])
            }
            
            return results
            
        except Exception as e:
            return {
                "intervention_type": "error",
                "error": f"Fallback agent error: {str(e)}",
                "llm_reasoning": f"Failed to execute fallback agent: {str(e)}",
                "tools_used": results.get("tools_used", []),
                "steps": results.get("steps", []),
                "agent_type": "custom_fallback"
            }

    async def _process_request(self, request: MoodManagerRequest) -> MoodManagerResponse:
        """
        LLM-powered processing using available tools
        """
        try:
            # Create the prompt for the LLM using the updated template with React pattern
            user_prompt = get_user_prompt_template(
                user_id=request.user_id,
                intent=request.intent,
                context=request.context,
                user_data=request.user_data,
                priority=request.priority
            )
            
            # Add React format reminder for consistent formatting
            full_prompt = user_prompt + get_react_format_reminder()
            
            # Get LLM response with tool usage
            llm_response = await self._call_llm_with_tools(full_prompt, request)
            
            # Parse the LLM response and extract results
            return await self._synthesize_response(request, llm_response, {})
            
        except Exception as e:
            return MoodManagerResponse(
                success=False,
                audio={"is_created": False, "file_path": None},
                metadata={"is_error": True, "error_type": "llm_brain_error", "intervention_type": None, "processing_method": "llm_powered"},
                recommendations=["retry_request", "contact_support"]
            )
    
    async def _synthesize_response(self, request: MoodManagerRequest, llm_results: Dict) -> MoodManagerResponse:
        """
        Synthesize final response from LLM tool usage results
        """
        try:
            # Handle crisis response
            intervention_type = llm_results.get("intervention_type", "standard")
            if intervention_type == "crisis":
                llm_response = llm_results.get("response", {})
                return MoodManagerResponse(
                    success=True,
                    audio=llm_response.get("audio", {"is_created": False, "file_path": None}),
                    metadata={
                        "is_error": False,
                        "error_type": None,
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered"
                    },
                    recommendations=llm_response.get("recommendations", [
                        "seek_professional_help",
                        "contact_emergency_services_if_needed", 
                        "check_in_1_hour"
                    ])
                )
            
            # Handle error response
            elif llm_results.get("intervention_type") == "error":
                return MoodManagerResponse(
                    success=False,
                    audio={"is_created": False, "file_path": None},
                    metadata={
                        "is_error": True,
                        "error_type": llm_results.get("error_type", "llm_execution_error"),
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered"
                    },
                    recommendations=llm_results.get("recommendations", ["retry_request", "contact_support"])
                )
            
            # Handle standard intervention response
            else:
                audio = llm_results.get("audio", {"is_created": False, "file_path": None})
                recommendations = llm_results.get("recommendations", ["retry_request", "contact_support"])
                
                return MoodManagerResponse(
                    success=True,
                    audio=audio,
                    metadata={
                        "is_error": False,
                        "error_type": None,
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered"
                    },
                    recommendations=recommendations
                )
                
        except Exception as e:
            return MoodManagerResponse(
                success=False,
                audio={"is_created": False, "file_path": None},
                metadata={
                    "is_error": True,
                    "error_type": "response_synthesis_error",
                    "intervention_type": intervention_type,
                    "priority": request.priority,
                    "processing_method": "llm_powered"
                },
                recommendations=["retry_request", "contact_support"]
            )