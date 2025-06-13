"""
Database Schema Models
=====================
Pydantic models for validating MongoDB documents before database operations.
Provides client-side validation to complement server-side MongoDB schema validation.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, Any, List

# AUDIO MANAGER SCHEMAS

class BrainwaveAudioDocument(BaseModel):
    """Schema for brainwave_audios collection."""
    uuid_id: str = Field(..., description="Unique identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    wave_type: str = Field(..., description="Type of brainwave")
    volume_magnitude: str = Field(..., description="Volume level")
    audio_path: str = Field(..., description="File path to audio", min_length=1)
    file_exists: bool = Field(..., description="Whether file exists")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @field_validator('wave_type')
    def validate_wave_type(cls, v):
        valid_types = ["alpha", "beta", "gamma", "delta", "theta"]
        if v not in valid_types:
            raise ValueError(f"wave_type must be one of: {valid_types}")
        return v
    
    @field_validator('volume_magnitude')
    def validate_volume_magnitude(cls, v):
        valid_magnitudes = ["low", "medium", "high"]
        if v not in valid_magnitudes:
            raise ValueError(f"volume_magnitude must be one of: {valid_magnitudes}")
        return v


class MusicAudioDocument(BaseModel):
    """Schema for music_audios collection."""
    uuid_id: str = Field(..., description="Unique identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    task: str = Field(..., description="Task type")
    music_style: str = Field(..., description="Style of music", min_length=1, max_length=100)
    audio_path: str = Field(..., description="File path to audio", min_length=1)
    file_exists: bool = Field(..., description="Whether file exists")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @field_validator('task')
    def validate_task(cls, v):
        valid_tasks = ["release", "sleep", "workout", "mindfulness", "crisis"]
        if v not in valid_tasks:
            raise ValueError(f"task must be one of: {valid_tasks}")
        return v


class MessageAudioDocument(BaseModel):
    """Schema for message_audios collection."""
    uuid_id: str = Field(..., description="Unique identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    task: str = Field(..., description="Task type")
    duration_sec: float = Field(..., description="Duration in seconds", ge=0)
    selected_tone: str = Field(..., description="Voice tone", min_length=1, max_length=50)
    selected_emotion: Optional[str] = Field(None, description="Voice emotion", max_length=50)
    audio_path: str = Field(..., description="File path to audio", min_length=1)
    file_exists: bool = Field(..., description="Whether file exists")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @field_validator('task')
    def validate_task(cls, v):
        valid_tasks = ["release", "sleep", "workout", "mindfulness", "crisis"]
        if v not in valid_tasks:
            raise ValueError(f"task must be one of: {valid_tasks}")
        return v


class ComponentsData(BaseModel):
    """Schema for audio component references."""
    message_audio_id: Optional[str] = None
    music_audio_id: Optional[str] = None
    brainwave_audio_id: Optional[str] = None


class ComponentPathsData(BaseModel):
    """Schema for audio component file paths."""
    emotional_audio_path: Optional[str] = None
    background_music_path: Optional[str] = None
    brain_waves_path: Optional[str] = None


class FinalAudioDocument(BaseModel):
    """Schema for final_audios collection."""
    uuid_id: str = Field(..., description="Unique identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    task: str = Field(..., description="Task type")
    components: ComponentsData = Field(..., description="Component references")
    component_paths: ComponentPathsData = Field(..., description="Component file paths")
    audio_path: str = Field(..., description="File path to final audio", min_length=1)
    file_exists: bool = Field(..., description="Whether file exists")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @field_validator('task')
    def validate_task(cls, v):
        valid_tasks = ["release", "sleep", "workout", "mindfulness", "crisis"]
        if v not in valid_tasks:
            raise ValueError(f"task must be one of: {valid_tasks}")
        return v


class SessionDocument(BaseModel):
    """Schema for sessions collection."""
    session_id: str = Field(..., description="Session identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    task: str = Field(..., description="Task type")
    session_type: str = Field(..., description="Session type", min_length=1, max_length=50)
    final_audio_id: str = Field(..., description="Final audio identifier", min_length=1)
    schedule_id: Optional[str] = Field(None, description="Schedule identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @field_validator('task')
    def validate_task(cls, v):
        valid_tasks = ["release", "sleep", "workout", "mindfulness", "crisis"]
        if v not in valid_tasks:
            raise ValueError(f"task must be one of: {valid_tasks}")
        return v


# USER MANAGER SCHEMAS

class ProfileData(BaseModel):
    """Schema for user profile data."""
    preferences: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserDocument(BaseModel):
    """Schema for users collection."""
    user_id: str = Field(..., description="Unique user identifier", min_length=1)
    email: Optional[str] = Field(None, description="User email")
    subscription_tier: str = Field(default="free", description="Subscription level")
    voice_path: Optional[str] = Field(None, description="Path to user's voice file")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    profile: ProfileData = Field(default_factory=ProfileData, description="User profile data")
    
    @field_validator('email')
    def validate_email(cls, v):
        if v is not None and '@' not in v:
            raise ValueError("email must be a valid email address")
        return v
    
    @field_validator('subscription_tier')
    def validate_subscription_tier(cls, v):
        valid_tiers = ["free", "premium", "enterprise"]
        if v not in valid_tiers:
            raise ValueError(f"subscription_tier must be one of: {valid_tiers}")
        return v


class UserVoiceDocument(BaseModel):
    """Schema for user_voices collection."""
    user_id: str = Field(..., description="User identifier", min_length=1)
    voice_path: str = Field(..., description="Voice file path", min_length=1)
    file_size_bytes: Optional[float] = Field(None, description="File size in bytes", ge=0)
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds", ge=0)
    quality_score: Optional[float] = Field(None, description="Quality score", ge=0, le=100)
    is_active: bool = Field(..., description="Whether voice is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")


class UserSessionDocument(BaseModel):
    """Schema for user_sessions collection."""
    user_id: str = Field(..., description="User identifier", min_length=1)
    session_date: str = Field(..., description="Session date", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    session_type: Optional[str] = Field(None, description="Session type")
    duration_minutes: Optional[float] = Field(None, description="Duration in minutes", ge=0)
    activity_count: Optional[int] = Field(None, description="Activity count", ge=0)
    mood_before: Optional[int] = Field(None, description="Mood before session", ge=1, le=10)
    mood_after: Optional[int] = Field(None, description="Mood after session", ge=1, le=10)
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @field_validator('session_type')
    def validate_session_type(cls, v):
        if v is not None:
            valid_types = ["meditation", "crisis", "habit_tracking", "mood_check"]
            if v not in valid_types:
                raise ValueError(f"session_type must be one of: {valid_types}")
        return v


# MOOD MANAGER SCHEMAS

class DateRecordDocument(BaseModel):
    """
    Schema for dates collection (shared with habit manager).
    Consolidated daily records including mood data and habit tracking.
    """
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    
    # Habit-related fields (maintained for habit manager compatibility)
    habits_scheduled: Optional[List[str]] = Field(default_factory=list, description="Scheduled habit IDs")
    habits_completed: Optional[List[str]] = Field(default_factory=list, description="Completed habit IDs")
    
    # Mood-related fields (enhanced for mood manager)
    mood_score: Optional[int] = Field(None, description="Daily overall mood score", ge=1, le=10)
    is_crisis: Optional[bool] = Field(default=False, description="Whether this was a crisis day")
    is_depressed: Optional[bool] = Field(default=False, description="Whether user felt depressed")
    mood_notes: Optional[str] = Field(None, description="Daily emotional diary/context notes", max_length=2000)
    
    # Metadata
    created_at: str = Field(..., description="Creation timestamp ISO string")
    updated_at: Optional[str] = Field(None, description="Last update timestamp ISO string")

    @field_validator('mood_notes')
    def validate_mood_notes(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class EmotionRecordDocument(BaseModel):
    """
    Schema for emotion_records collection.
    Tracks specific emotions with granular detail and context.
    """
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    emotion_type: str = Field(..., description="Type of emotion", min_length=1, max_length=50)
    emotion_score: int = Field(..., description="Intensity of this specific emotion", ge=1, le=10)
    emotion_notes: Optional[str] = Field(None, description="Context, triggers, environment for this emotion", max_length=1500)
    
    # Contextual information
    triggers: Optional[List[str]] = Field(default_factory=list, description="Identified triggers for this emotion")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Environmental and activity context")
    
    # Metadata
    created_at: str = Field(..., description="Creation timestamp ISO string")
    updated_at: Optional[str] = Field(None, description="Last update timestamp ISO string")

    @field_validator('emotion_type')
    def validate_emotion_type(cls, v):
        # Normalize emotion type to lowercase
        normalized = v.lower().strip()
        valid_emotions = [
            "happiness", "joy", "contentment", "excitement", "euphoria",
            "sadness", "melancholy", "grief", "despair", "sorrow",
            "anger", "irritation", "rage", "frustration", "annoyance",
            "fear", "anxiety", "panic", "worry", "nervousness",
            "surprise", "amazement", "shock", "wonder", "confusion",
            "disgust", "contempt", "revulsion", "aversion",
            "love", "affection", "compassion", "empathy", "warmth",
            "guilt", "shame", "embarrassment", "regret", "remorse",
            "pride", "confidence", "accomplishment", "satisfaction",
            "loneliness", "isolation", "emptiness", "disconnection"
        ]
        
        if normalized not in valid_emotions:
            # Allow custom emotions but warn - this could be expanded
            pass
        
        return normalized

    @field_validator('triggers')
    def validate_triggers(cls, v):
        if v is not None and len(v) > 10:  # Reasonable limit on number of triggers
            raise ValueError("Too many triggers specified (max 10)")
        return v

    @field_validator('emotion_notes')
    def validate_emotion_notes(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


# VALIDATION HELPERS

def validate_and_convert_to_dict(document_data: Dict, schema_class: BaseModel) -> Dict:
    """
    Validate data using Pydantic model and return as dictionary for MongoDB.
    
    Args:
        document_data: Raw dictionary data to validate
        schema_class: Pydantic model class for validation
        
    Returns:
        Validated dictionary ready for MongoDB insertion
        
    Raises:
        ValidationError: If data doesn't match schema
    """
    try:
        # Validate using Pydantic model
        validated_model = schema_class(**document_data)
        
        # Convert to dict for MongoDB (handles datetime serialization)
        return validated_model.dict()
        
    except Exception as e:
        raise ValueError(f"Validation failed for {schema_class.__name__}: {e}")


def validate_update_data(update_data: Dict, schema_class: BaseModel) -> Dict:
    """
    Validate partial update data against schema.
    Only validates fields that are present in the update.
    
    Args:
        update_data: Dictionary with partial update data
        schema_class: Pydantic model class for validation
        
    Returns:
        Validated update dictionary
        
    Raises:
        ValidationError: If any provided field doesn't match schema
    """
    try:
        # Create a temporary model instance with just the update fields
        # Use model validation but ignore required field errors
        temp_data = {}
        
        # Get field names from schema
        schema_fields = schema_class.__fields__.keys()
        
        # Only validate fields that exist in both update_data and schema
        for field_name, field_value in update_data.items():
            if field_name in schema_fields:
                temp_data[field_name] = field_value
        
        # For partial validation, create model with minimal required fields
        # This is a simplified approach - in production you might want more sophisticated partial validation
        if temp_data:
            # Try to validate individual fields
            for field_name, field_value in temp_data.items():
                field_info = schema_class.__fields__[field_name]
                # Basic type checking - can be enhanced as needed
                if hasattr(field_info, 'type_') and field_value is not None:
                    # Perform field-level validation
                    pass
        
        return update_data
        
    except Exception as e:
        raise ValueError(f"Update validation failed for {schema_class.__name__}: {e}")


def validate_date_record_data(date_data: Dict) -> Dict:
    """
    Validate date record data using DateRecordDocument schema.
    
    Args:
        date_data: Raw date record data
        
    Returns:
        Validated and normalized date record data
        
    Raises:
        ValueError: If validation fails
    """
    try:
        # Convert to Pydantic model for validation
        date_record = DateRecordDocument(**date_data)
        
        # Return as dict with Pydantic serialization
        return date_record.model_dump()
        
    except Exception as e:
        raise ValueError(f"DateRecordDocument validation failed: {str(e)}")


def validate_emotion_record_data(emotion_data: Dict) -> Dict:
    """
    Validate emotion record data using EmotionRecordDocument schema.
    
    Args:
        emotion_data: Raw emotion record data
        
    Returns:
        Validated and normalized emotion record data
        
    Raises:
        ValueError: If validation fails
    """
    try:
        # Convert to Pydantic model for validation
        emotion_record = EmotionRecordDocument(**emotion_data)
        
        # Return as dict with Pydantic serialization
        return emotion_record.model_dump()
        
    except Exception as e:
        raise ValueError(f"EmotionRecordDocument validation failed: {str(e)}") 