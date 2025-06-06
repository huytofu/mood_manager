# Mood Manager Brain - Modular Architecture

This directory contains the LLM-powered mood manager brain with a clean, modular architecture.

## File Structure

```
mood_manager/
├── mood_manager_brain.py      # Main brain orchestration & API endpoints
├── mood_manager_tools.py      # LangChain tools for therapeutic interventions  
├── mood_manager_prompts.py    # LLM system prompts and templates
└── README_BRAIN_ARCHITECTURE.md
```

## Components

### 1. `mood_manager_brain.py` - Core Brain
- **Purpose**: Main orchestration layer and FastAPI endpoints
- **Contains**: 
  - `MoodManagerBrain` class with HuggingFace LLM integration
  - Request/Response data models (`MoodManagerRequest`, `MoodManagerResponse`)
  - REST API endpoints (`/process`, `/capabilities`, `/tools`, `/analyze-emotion`, `/schema/request`)
- **Dependencies**: Imports tools and prompts from separate files

### 2. `mood_manager_tools.py` - Tool Layer
- **Purpose**: Specialized therapeutic tools for LLM to orchestrate
- **Contains**:
  - 7 LangChain tools with detailed schemas and documentation
  - Tool implementations with router function calls
  - Input/output validation for each tool
- **Tools Available**:
  1. `analyze_emotional_state` - Detect emotions, intensity, crisis indicators
  2. `plan_intervention` - Choose therapeutic strategy  
  3. `prepare_audio_params` - Generate audio parameters based on emotion
  4. `call_audio_endpoint` - Execute audio generation
  5. `call_cache_endpoint` - Manage voice caching operations
  6. `generate_recommendations` - Create evidence-based action plans
  7. `handle_crisis` - Specialized crisis intervention protocols

### 3. `mood_manager_prompts.py` - Prompt Layer
- **Purpose**: LLM prompts and templates for consistent AI behavior
- **Contains**:
  - `MOOD_MANAGER_SYSTEM_PROMPT` - Core system instructions for the LLM
  - `get_user_prompt_template()` - Function to generate user-specific prompts
- **Features**: Includes expertise, capabilities, process flow, and safety priorities

## API Endpoints

### **`POST /brain/process`** - Main LLM-Powered Processing
- **Purpose**: Full therapeutic intervention with LLM orchestration
- **Input**: `MoodManagerRequest` with user intent and context
- **Output**: `MoodManagerResponse` with audio, recommendations, crisis protocols
- **LLM Flow**: analyze → plan → execute → recommend

### **`GET /brain/capabilities`** - Therapeutic Capabilities
- **Purpose**: Describes what the mood manager can actually do therapeutically
- **Output**: Core interventions, emotional intelligence, audio capabilities

### **`GET /brain/tools`** - LLM Agent Tool Inventory  
- **Purpose**: Shows available tools the LLM can orchestrate
- **Output**: Tool descriptions, inputs/outputs, orchestration flow, agent benefits

### **`POST /brain/analyze-emotion`** - Emotion Analysis Only
- **Purpose**: Quick emotional analysis without full intervention
- **Input**: `user_input` (str) and optional `context` (dict)
- **Output**: Emotional analysis + recommended intervention plan
- **Updated**: Now uses modular tools directly

### **`GET /brain/schema/request`** - Request Schema
- **Purpose**: Schema for external AI models to structure requests
- **Output**: JSON schema + example for `MoodManagerRequest`

## Architecture Benefits

### ✅ **Modularity**
- Clean separation of concerns (orchestration, tools, prompts)
- Easy to maintain and update individual components
- Clear dependencies and imports

### ✅ **Extensibility** 
- Add new tools by creating functions in `mood_manager_tools.py`
- Update LLM behavior by modifying `mood_manager_prompts.py`
- Core brain remains stable

### ✅ **Testability**
- Each tool can be tested independently
- Prompts can be version-controlled and A/B tested
- Brain orchestration logic is isolated

### ✅ **Reusability**
- Tools can be imported by other components
- Prompts can be shared across different AI agents
- Clear interfaces for integration

### ✅ **LLM Agent Benefits**
- **Real Intelligence**: LLM reasoning replaces hardcoded if/else logic
- **Transparency**: Tool usage logging shows LLM decision-making process
- **Extensibility**: Add new tools without changing core brain logic
- **Focused Responsibilities**: Each tool has single, well-defined purpose

## Integration

The brain integrates with existing FastAPI app via:
```python
# In app.py
from mood_manager.mood_manager_brain import brain_router
app.include_router(brain_router, prefix="/brain", tags=["mood-brain"])
```

## Usage Example

```python
# Process a mood management request
request = MoodManagerRequest(
    user_id="user123",
    intent="I'm feeling anxious about tomorrow's meeting", 
    context={"stress_level": 8, "time_of_day": "evening"},
    priority="high"
)

response = await brain.process_request(request)
# Returns: audio meditation, recommendations, crisis protocols if needed
```

## Endpoint Updates for LLM Agent Architecture

### ✅ **Fixed `/analyze-emotion` Endpoint**
- **Problem**: Was calling non-existent `_analyze_emotional_state()` and `_plan_intervention()` methods
- **Solution**: Updated to use imported tools `analyze_emotional_state()` and `plan_intervention()` directly
- **Benefit**: Now properly uses the modular tool architecture

### ✅ **Added `/tools` Endpoint**  
- **Purpose**: Exposes the complete tool inventory that the LLM agent orchestrates
- **Benefit**: Provides transparency into agent capabilities and tool workflow
- **Content**: Tool descriptions, input/output specs, orchestration flow, agent benefits 