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
import os

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

# Import tools and prompts from separate files
from .mood_manager_tools import (
    plan_intervention, 
    prepare_audio_params,
    call_audio_endpoint,
    call_cache_endpoint,
    generate_recommendations,
    handle_crisis,
    final_answer,
    get_user_mood_history,
    record_daily_mood_tool,
    record_daily_mood_notes_tool,
    record_daily_emotion_tool,
    record_daily_emotion_notes_tool,
    analyze_mood_trends_tool,
    analyze_emotion_trends_tool
)
from .mood_manager_prompts import MOOD_MANAGER_SYSTEM_PROMPT, get_user_prompt_template, generate_tools_documentation

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
                            "should_use_user_voice": True,
                            "should_use_background_music": True,
                            "should_use_brain_waves": True,
                            "music_style": "natural sounds",
                            "duration": 10,
                        })
    user_data: Dict[str, Any] = Field(default_factory=dict, description="Additional user data",
                            example={
                            "user_name": "John Doe",
                            "user_selected_tone": "calm",
                            "user_stress_level": 8,
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
        if hf_token:
            self.hf_token = hf_token
        else:
            self.hf_token = os.getenv("HF_TOKEN")
        
        # Phase 1 & 2 Enhanced Tools (Your emotional diary & multi-emotion tracking idea!)
        self.tools = [
            plan_intervention,
            prepare_audio_params,
            call_audio_endpoint,
            call_cache_endpoint,
            generate_recommendations,
            handle_crisis,
            final_answer,
            get_user_mood_history,
            record_daily_mood_tool,
            record_daily_mood_notes_tool,
            record_daily_emotion_tool,
            record_daily_emotion_notes_tool,
            analyze_mood_trends_tool,
            analyze_emotion_trends_tool
        ]
        
        # Generate dynamic tools documentation
        tools_documentation = generate_tools_documentation(self.tools)
        
        # System prompt for the LLM with dynamic tools documentation
        self.system_prompt = MOOD_MANAGER_SYSTEM_PROMPT.format(tools_documentation=tools_documentation)
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
        print(f"Initializing {selected_type} mood agent...")
        
        if selected_type == "langchain":
            self._init_langchain_agent()
        elif selected_type == "smolagents":
            self._init_smolagents_agent()
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}. Use 'langchain', 'smolagents', or 'auto'.")
        
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
                model_id="Qwen/Qwen2.5-Coder-32B-Instruct",
                token=self.hf_token
            )
            
            # Convert our tools to smolagents format
            # Note: smolagents expects tools to be classes or have specific format
            # This might need adjustment based on your tool implementations
            
            # Transform langchain tools to smolagents format
            smolagents_tools = []
            for tool in self.tools:
                smolagents_tools.append(SmolAgentTool.from_langchain_tool(tool))
            
            with open("prompts/mood_manager_smolagents.yaml", "r") as f:
                prompt_templates = yaml.safe_load(f)
            
            # Create CodeAgent  
            self.agent = CodeAgent(
                tools=smolagents_tools,
                model=self.model,
                max_iterations=10,
                prompt_templates=prompt_templates
            )
            
            print("✅ HuggingFace CodeAgent initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize CodeAgent: {e}")
            print("Falling back to custom implementation...")
            self.agent_type = "custom"
            self._init_custom_agent()
    

    
    async def _call_llm_with_tools(self, prompt: str, request: MoodManagerRequest) -> Dict[str, Any]:
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
                "error": f"LLM agent execution error: {str(e)}",
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
            raise RuntimeError(f"LangChain agent failed: {str(e)}")
    
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
            raise RuntimeError(f"Smolagents agent failed: {str(e)}")
    


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
            
            # Get LLM response with tool usage
            llm_response = await self._call_llm_with_tools(user_prompt, request)
            
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
        Synthesize final response from LLM tool usage results using standardized final_response
        """
        try:
            # Extract standardized response from final_answer tool (Pydantic model)
            final_response = llm_results.get("final_response")
            
            if final_response:
                # Handle Pydantic model
                intervention_type = final_response.intervention_type
                success = intervention_type != "error"
                
                return MoodManagerResponse(
                    success=success,
                    audio={
                        "is_created": final_response.audio.is_created,
                        "file_path": final_response.audio.file_path
                    },
                    metadata={
                        "is_error": not success,
                        "error_type": final_response.error_type,
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered"
                    },
                    recommendations=final_response.recommendations
                )
            else:
                # Fallback if no final_response available
                intervention_type = llm_results.get("intervention_type", "error")
                return MoodManagerResponse(
                    success=False,
                    audio={"is_created": False, "file_path": None},
                    metadata={
                        "is_error": True,
                        "error_type": "missing_final_response",
                        "intervention_type": intervention_type,
                        "priority": request.priority,
                        "processing_method": "llm_powered"
                    },
                    recommendations=["retry_request", "contact_support"]
                )
                
        except Exception as e:
            # Fallback if final_response is missing or malformed
            return MoodManagerResponse(
                success=False,
                audio={"is_created": False, "file_path": None},
                metadata={
                    "is_error": True,
                    "error_type": "response_synthesis_error",
                    "intervention_type": "error",
                    "priority": request.priority,
                    "processing_method": "llm_powered"
                },
                recommendations=["retry_request", "contact_support"]
            )