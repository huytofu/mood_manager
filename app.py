# Install required packages first:
# pip install TTS soundfile numpy redis pymongo

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from routers.cache_router import router as cache_router
from routers.audio_router import router as audio_router

app = FastAPI()
mcp = FastApiMCP(
    app,
    name="mood_management_mc",
    description="Mood Management Microservice",
    version="1.0.0",
    exclude_operations=["cleanup_expired_cache"],
    include_operations=[
        "cache_user_voice", 
        "get_cache_status", 
        "clear_user_cache", 
        "generate_release_meditation_audio", 
        "generate_sleep_meditation_audio", 
        "generate_mindfulness_meditation_audio", 
        "generate_workout_meditation_audio"
    ],
    describe_all_responses=True,
    describe_full_response_schema=True,
)
mcp.mount()

# Include routers
app.include_router(cache_router)
app.include_router(audio_router)

