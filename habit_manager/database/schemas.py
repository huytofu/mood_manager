"""
Habit Manager Database Schema Models
===================================
Pydantic models for validating MongoDB documents before database operations.
Provides client-side validation to complement server-side MongoDB schema validation.
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any, List

# HABIT MANAGER SCHEMAS

class MicroHabitDocument(BaseModel):
    """Schema for micro_habits collection."""
    habit_id: str = Field(..., description="Unique habit identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    name: str = Field(..., description="Habit name", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Habit description", max_length=1000)
    category: str = Field(..., description="Habit category")
    period: str = Field(..., description="Habit frequency period")
    intrinsic_score: int = Field(..., description="Intrinsic motivation score", ge=1, le=4)
    difficulty_level: str = Field(default="easy", description="Difficulty level for progressive overload")
    habit_type: str = Field(..., description="Type of habit")
    status: str = Field(default="active", description="Habit status")
    current_streak: int = Field(default=0, description="Current streak count", ge=0)
    best_streak: int = Field(default=0, description="Best streak achieved", ge=0)
    total_completions: int = Field(default=0, description="Total completions", ge=0)
    weekly_days: Optional[List[str]] = Field(None, description="Days of week for weekly habits")
    specific_dates: Optional[List[str]] = Field(None, description="Specific dates for scheduled habits")
    daily_timing: Optional[str] = Field(None, description="Preferred timing for daily habits")
    is_meditation: Optional[bool] = Field(None, description="Whether this is a meditation habit")
    epic_habit_id: Optional[str] = Field(None, description="Associated epic habit ID")
    priority_within_epic: Optional[str] = Field(None, description="Priority within epic habit")
    created_date: str = Field(..., description="Creation date ISO string")
    
    @validator('category')
    def validate_category(cls, v):
        valid_categories = ["health", "productivity", "social", "financial", "mental_health", "spiritual", "creative", "other"]
        if v not in valid_categories:
            raise ValueError(f"category must be one of: {valid_categories}")
        return v
    
    @validator('period')
    def validate_period(cls, v):
        valid_periods = ["daily", "weekly", "specific_dates"]
        if v not in valid_periods:
            raise ValueError(f"period must be one of: {valid_periods}")
        return v
    
    @validator('difficulty_level')
    def validate_difficulty_level(cls, v):
        valid_difficulties = ["easy", "medium", "hard"]
        if v not in valid_difficulties:
            raise ValueError(f"difficulty_level must be one of: {valid_difficulties}")
        return v
    
    @validator('habit_type')
    def validate_habit_type(cls, v):
        valid_types = ["formation", "breaking"]
        if v not in valid_types:
            raise ValueError(f"habit_type must be one of: {valid_types}")
        return v
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["active", "paused", "completed", "archived"]
        if v not in valid_statuses:
            raise ValueError(f"status must be one of: {valid_statuses}")
        return v
    
    @validator('priority_within_epic')
    def validate_priority_within_epic(cls, v):
        if v is not None:
            valid_priorities = ["high", "low"]
            if v not in valid_priorities:
                raise ValueError(f"priority_within_epic must be one of: {valid_priorities}")
        return v


class EpicHabitDocument(BaseModel):
    """Schema for epic_habits collection."""
    epic_id: str = Field(..., description="Unique epic habit identifier", min_length=1)
    user_id: str = Field(..., description="User identifier", min_length=1)
    name: str = Field(..., description="Epic habit name", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Epic habit description", max_length=1000)
    category: str = Field(..., description="Epic habit category")
    priority: int = Field(..., description="Priority level", ge=1, le=10)
    target_completion_date: str = Field(..., description="Target completion date", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    success_criteria: Optional[List[str]] = Field(None, description="Success criteria list")
    current_progress: float = Field(default=0.0, description="Current progress percentage", ge=0, le=100)
    high_priority_micro_habits: List[str] = Field(default_factory=list, description="High priority micro habit IDs")
    low_priority_micro_habits: List[str] = Field(default_factory=list, description="Low priority micro habit IDs")
    created_date: str = Field(..., description="Creation date ISO string")
    
    @validator('category')
    def validate_category(cls, v):
        valid_categories = ["health", "productivity", "social", "financial", "mental_health", "spiritual", "creative", "other"]
        if v not in valid_categories:
            raise ValueError(f"category must be one of: {valid_categories}")
        return v


class HabitCompletionDocument(BaseModel):
    """Schema for habit_completions collection."""
    user_id: str = Field(..., description="User identifier", min_length=1)
    habit_id: str = Field(..., description="Habit identifier", min_length=1)
    date: str = Field(..., description="Completion date", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    completion_score: int = Field(..., description="Completion score", ge=0, le=4)
    actual_timing: Optional[str] = Field(None, description="Actual completion timing")
    notes: Optional[str] = Field(None, description="Completion notes", max_length=500)
    recorded_at: str = Field(..., description="Recording timestamp ISO string")


class DateRecordDocument(BaseModel):
    """Schema for dates collection."""
    user_id: str = Field(..., description="User identifier", min_length=1)
    date: str = Field(..., description="Date", regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    habits_scheduled: Optional[List[str]] = Field(default_factory=list, description="Scheduled habit IDs")
    habits_completed: Optional[List[str]] = Field(default_factory=list, description="Completed habit IDs")
    mood_score: Optional[int] = Field(None, description="Daily mood score", ge=1, le=10)
    is_crisis: Optional[bool] = Field(None, description="Whether this was a crisis day")
    is_depressed: Optional[bool] = Field(None, description="Whether user felt depressed")
    mood_notes: Optional[str] = Field(None, description="Mood notes")
    created_at: str = Field(..., description="Creation timestamp ISO string")


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
        # Get field names from schema
        schema_fields = schema_class.__fields__.keys()
        
        # Only validate fields that exist in both update_data and schema
        validated_updates = {}
        for field_name, field_value in update_data.items():
            if field_name in schema_fields:
                # Get field info for validation
                field_info = schema_class.__fields__[field_name]
                
                # Perform basic validation on individual fields
                if field_value is not None:
                    # For enum fields, check if validators exist and apply them
                    if hasattr(schema_class, f'validate_{field_name}'):
                        validator_method = getattr(schema_class, f'validate_{field_name}')
                        try:
                            validated_value = validator_method(field_value)
                            validated_updates[field_name] = validated_value
                        except ValueError as e:
                            raise ValueError(f"Field '{field_name}' validation failed: {e}")
                    else:
                        validated_updates[field_name] = field_value
                else:
                    validated_updates[field_name] = field_value
            else:
                # Field not in schema - pass through (might be MongoDB specific field)
                validated_updates[field_name] = field_value
        
        return validated_updates
        
    except Exception as e:
        raise ValueError(f"Update validation failed for {schema_class.__name__}: {e}")


def validate_habit_creation_data(habit_data: Dict) -> Dict:
    """
    Special validation helper for habit creation with automatic defaults.
    
    Args:
        habit_data: Raw habit data dictionary
        
    Returns:
        Validated habit data with defaults applied
    """
    try:
        # Add default values for creation
        habit_data.setdefault("status", "active")
        habit_data.setdefault("current_streak", 0)
        habit_data.setdefault("best_streak", 0)
        habit_data.setdefault("total_completions", 0)
        habit_data.setdefault("created_date", datetime.now().isoformat())
        
        # Validate using MicroHabitDocument schema
        return validate_and_convert_to_dict(habit_data, MicroHabitDocument)
        
    except Exception as e:
        raise ValueError(f"Habit creation validation failed: {e}")


def validate_epic_creation_data(epic_data: Dict) -> Dict:
    """
    Special validation helper for epic habit creation with automatic defaults.
    
    Args:
        epic_data: Raw epic habit data dictionary
        
    Returns:
        Validated epic habit data with defaults applied
    """
    try:
        # Add default values for creation
        epic_data.setdefault("current_progress", 0.0)
        epic_data.setdefault("high_priority_micro_habits", [])
        epic_data.setdefault("low_priority_micro_habits", [])
        epic_data.setdefault("created_date", datetime.now().isoformat())
        
        # Validate using EpicHabitDocument schema
        return validate_and_convert_to_dict(epic_data, EpicHabitDocument)
        
    except Exception as e:
        raise ValueError(f"Epic habit creation validation failed: {e}")


def validate_completion_data(completion_data: Dict) -> Dict:
    """
    Special validation helper for habit completion recording.
    
    Args:
        completion_data: Raw completion data dictionary
        
    Returns:
        Validated completion data with defaults applied
    """
    try:
        # Add recording timestamp if not present
        completion_data.setdefault("recorded_at", datetime.now().isoformat())
        
        # Validate using HabitCompletionDocument schema
        return validate_and_convert_to_dict(completion_data, HabitCompletionDocument)
        
    except Exception as e:
        raise ValueError(f"Completion data validation failed: {e}")
