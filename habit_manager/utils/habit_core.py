"""
Habit Core Operations
====================
Core schemas and functions for habit creation, modification, and basic management.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel, Field, field_validator
from database.mongo_habit_manager import mongo_habit_manager
from database.mongo_user_manager import mongo_user_manager
import os

# =============================================================================
# PREMIUM TIER MANAGEMENT
# =============================================================================

def _get_user_habit_limits(user_id: str) -> Dict[str, Any]:
    """Get habit limits and capabilities based on user tier."""
    is_premium = mongo_user_manager.get_user_tier(user_id) == "premium"
    
    if is_premium:
        return {
            "max_active_habits": 50,
            "max_epic_habits": 10,
            "analytics_period_limit": "unlimited",  # custom periods allowed
            "advanced_scheduling": True,  # Now available for all users
            "mood_correlation": True,
            "ai_insights": True,
            "habit_interaction_analysis": True,
            "epic_habit_creation": True,
            "epic_progress_calculation": True,  # Premium can calculate epic progress
            "trend_analysis_days": 365,  # 1 year
            "can_use_custom_periods": True  # Now available for all users
        }
    else:
        return {
            "max_active_habits": 10,
            "max_epic_habits": 0,  # Free users can't create epic habits
            "analytics_period_limit": "unlimited",  # Now available for all users
            "advanced_scheduling": True,  # Now available for all users
            "mood_correlation": False,  # Basic mood recording only (no correlation analysis)
            "ai_insights": False,  # Basic insights only (no AI-generated recommendations)
            "habit_interaction_analysis": False,  # No synergy/conflict analysis
            "epic_habit_creation": False,
            "epic_progress_calculation": False,  # Can't calculate progress on epics they can't create
            "trend_analysis_days": 30,  # 1 month max
            "can_use_custom_periods": True  # Now available for all users
        }

def check_habit_creation_limits(user_id: str, habit_type: str = "micro") -> Dict[str, Any]:
    """Check if user can create more habits based on their tier limits."""
    limits = _get_user_habit_limits(user_id)
    
    if habit_type == "epic" and not limits["epic_habit_creation"]:
        return {
            "can_create": False,
            "reason": "Epic habit creation requires premium plan",
            "upgrade_message": "Upgrade to premium to create epic habits with multiple micro-habit tracking"
        }
    
    # Count current active habits
    current_habits = mongo_habit_manager.get_user_micro_habits(user_id, "active")
    current_epics = mongo_habit_manager.get_user_epic_habits(user_id) if habit_type == "epic" else []
    
    if habit_type == "micro" and len(current_habits) >= limits["max_active_habits"]:
        return {
            "can_create": False, 
            "reason": f"Reached maximum active habits limit ({limits['max_active_habits']})",
            "upgrade_message": "Upgrade to premium for up to 50 active habits",
            "current_count": len(current_habits),
            "limit": limits["max_active_habits"]
        }
    elif habit_type == "epic" and len(current_epics) >= limits["max_epic_habits"]:
        return {
            "can_create": False,
            "reason": f"Reached maximum epic habits limit ({limits['max_epic_habits']})", 
            "upgrade_message": "Premium users can create up to 10 epic habits",
            "current_count": len(current_epics),
            "limit": limits["max_epic_habits"]
        }
    
    return {"can_create": True}

# =============================================================================
# CORE HABIT SCHEMAS
# =============================================================================

# NEW SCHEMAS FOR BASIC OPERATIONS
class ModifyHabitParametersInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    timing_type: Optional[str] = Field(default=None, description="specific_time, entire_day, or time_range")
    daily_timing: Optional[str] = Field(default=None, description="Fixed time like 07:00 or after_coffee")
    start_time: Optional[str] = Field(default=None, description="Start time for time_range habits (HH:MM format)")
    end_time: Optional[str] = Field(default=None, description="End time for time_range habits (HH:MM format)")
    difficulty_level: Optional[str] = Field(default=None, description="Difficulty level: easy, medium, hard")
    intrinsic_score: Optional[int] = Field(default=None, ge=1, le=4, description="Importance score 1-4")

    @field_validator('timing_type')
    def validate_timing_type(cls, v):
        if v is not None:
            valid_timing_types = ["specific_time", "entire_day", "time_range"]
            if v not in valid_timing_types:
                raise ValueError(f"timing_type must be one of: {valid_timing_types}")
        return v

    @field_validator('difficulty_level')
    def validate_difficulty_level(cls, v):
        if v is not None:
            valid_levels = ["easy", "medium", "hard"]
            if v not in valid_levels:
                raise ValueError(f"difficulty_level must be one of: {valid_levels}")
        return v

class PauseResumeHabitInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    action: str = Field(..., description="pause or resume")
    reason: Optional[str] = Field(default=None, description="Reason for pausing/resuming")
    pause_until: Optional[str] = Field(default=None, description="Resume date for temporary pause (YYYY-MM-DD)")

    @field_validator('action')
    def validate_action(cls, v):
        valid_actions = ["pause", "resume"]
        if v not in valid_actions:
            raise ValueError(f"action must be one of: {valid_actions}")
        return v

class AddHabitNoteInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    date: str = Field(..., description="Date for the note in YYYY-MM-DD format")
    note_type: str = Field(..., description="trigger, difficulty, learning, reflection, or general")
    content: str = Field(..., description="Note content - thoughts, learnings, triggers faced, etc.")
    mood_context: Optional[int] = Field(default=None, ge=1, le=10, description="Mood score at time of note")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorizing notes")

    @field_validator('note_type')
    def validate_note_type(cls, v):
        valid_types = ["trigger", "difficulty", "learning", "reflection", "general"]
        if v not in valid_types:
            raise ValueError(f"note_type must be one of: {valid_types}")
        return v

class GetHabitNotesInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    start_date: Optional[str] = Field(default=None, description="Start date for notes query (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date for notes query (YYYY-MM-DD)")
    note_type: Optional[str] = Field(default=None, description="Filter by note type")
    limit: Optional[int] = Field(default=50, description="Maximum number of notes to return")

# HABIT CREATION SCHEMAS
class CreateMicroHabitInput(BaseModel):
    name: str = Field(..., description="Habit name")
    description: str = Field(..., description="Detailed habit description")
    category: str = Field(..., description="Habit category: health, productivity, social, financial, etc.")
    period: str = Field(..., description="daily, weekly, or specific_dates")
    frequency: Optional[str] = Field(default=None, description="For weekly: 3x_week, every_2_days, etc.")
    weekly_days: Optional[List[str]] = Field(default=None, description="For weekly habits: [monday, wednesday, friday]")
    specific_dates: Optional[List[str]] = Field(default=None, description="For specific_dates period")
    timing_type: str = Field(default="specific_time", description="specific_time, entire_day, or time_range")
    daily_timing: Optional[str] = Field(default=None, description="Fixed time like 07:00 or after_coffee, None for flexible (only for specific_time)")
    start_time: Optional[str] = Field(default=None, description="Start time for time_range habits (HH:MM format)")
    end_time: Optional[str] = Field(default=None, description="End time for time_range habits (HH:MM format)")
    intrinsic_score: int = Field(..., ge=1, le=4, description="Importance score 1-4, used as weight")
    difficulty_level: str = Field(default="easy", description="Difficulty level: easy, medium, hard")
    is_meditation: bool = Field(default=False, description="Whether this is a meditation habit requiring audio asset")
    meditation_audio_id: Optional[str] = Field(default=None, description="Required if is_meditation=True")
    habit_type: str = Field(..., description="formation (good habits to build) or breaking (bad habits to avoid)")

    @field_validator('timing_type')
    def validate_timing_type(cls, v):
        valid_timing_types = ["specific_time", "entire_day", "time_range"]
        if v not in valid_timing_types:
            raise ValueError(f"timing_type must be one of: {valid_timing_types}")
        return v
    
    @field_validator('habit_type')
    def validate_habit_type(cls, v):
        valid_types = ["formation", "breaking"]
        if v not in valid_types:
            raise ValueError(f"habit_type must be one of: {valid_types}")
        return v

class CreateEpicHabitInput(BaseModel):
    name: str = Field(..., description="Epic habit name like 'Achieve 15% body fat'")
    description: str = Field(..., description="Detailed description of the epic goal")
    category: str = Field(..., description="Category: health, productivity, mental_health, etc.")
    priority: int = Field(..., ge=1, le=10, description="Overall priority across all epic habits")
    target_completion_date: str = Field(..., description="Target date in YYYY-MM-DD format")
    success_criteria: List[str] = Field(..., description="Measurable outcomes for success")

class AssignMicroToEpicInput(BaseModel):
    micro_habit_id: str = Field(..., description="ID of micro habit to assign")
    epic_habit_id: str = Field(..., description="ID of epic habit to assign to")
    priority_within_epic: str = Field(..., description="high or low priority within this epic")

# =============================================================================
# CORE HABIT OPERATIONS
# =============================================================================

async def _create_micro_habit_record(
    user_id: str, name: str, description: str, category: str, period: str, intrinsic_score: int, 
    habit_type: str, timing_type: str = "specific_time", frequency: Optional[str] = None, weekly_days: Optional[List[str]] = None,
    specific_dates: Optional[List[str]] = None, daily_timing: Optional[str] = None,
    start_time: Optional[str] = None, end_time: Optional[str] = None,
    difficulty_level: str = "easy", is_meditation: bool = False, meditation_audio_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a micro habit record in database with validation."""
    try:
        # Check user limits
        limits_check = check_habit_creation_limits(user_id, "micro")
        if not limits_check["can_create"]:
            return {"success": False, "error": limits_check["reason"]}
        
        # Generate unique habit ID
        habit_id = str(uuid.uuid4())
        
        # Validate meditation requirements
        if is_meditation and not meditation_audio_id:
            return {"success": False, "error": "meditation_audio_id is required for meditation habits"}
        
        # Prepare habit record
        habit_record = {
            "habit_id": habit_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "category": category,
            "period": period,
            "intrinsic_score": intrinsic_score,
            "difficulty_level": difficulty_level,
            "habit_type": habit_type,
            "timing_type": timing_type,
            "status": "active",
            "current_streak": 0,
            "best_streak": 0,
            "total_completions": 0,
            "created_date": datetime.now().isoformat()
        }
        
        # Add scheduling fields based on period and timing
        if period == "weekly" and weekly_days:
            habit_record["weekly_days"] = weekly_days
        if period == "specific_dates" and specific_dates:
            habit_record["specific_dates"] = specific_dates
        if timing_type == "specific_time" and daily_timing:
            habit_record["daily_timing"] = daily_timing
        if timing_type == "time_range" and start_time and end_time:
            habit_record["start_time"] = start_time
            habit_record["end_time"] = end_time
        
        # Add frequency for weekly habits
        if frequency:
            habit_record["frequency"] = frequency
        
        # Add meditation fields
        if is_meditation:
            habit_record["is_meditation"] = True
            habit_record["meditation_audio_id"] = meditation_audio_id
        
        # Store in database
        success = mongo_habit_manager.create_micro_habit(habit_record)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully created {habit_type} habit: {name}",
                "habit_id": habit_id,
                "details": {
                    "name": name,
                    "category": category,
                    "timing_type": timing_type,
                    "intrinsic_score": intrinsic_score,
                    "difficulty_level": difficulty_level
                }
            }
        else:
            return {"success": False, "error": "Failed to create habit in database"}
            
    except Exception as e:
        return {"success": False, "error": f"Error creating habit: {str(e)}"}

async def _create_epic_habit_record(
    user_id: str, name: str, description: str, category: str, priority: int,
    target_completion_date: str, success_criteria: List[str]
) -> Dict[str, Any]:
    """Create an epic habit record in database with validation."""
    try:
        # Check user limits
        limits_check = check_habit_creation_limits(user_id, "epic")
        if not limits_check["can_create"]:
            return {"success": False, "error": limits_check["reason"]}
        
        # Generate unique epic ID
        epic_id = str(uuid.uuid4())
        
        # Validate target date format
        try:
            target_date = datetime.strptime(target_completion_date, "%Y-%m-%d")
            if target_date <= datetime.now():
                return {"success": False, "error": "Target completion date must be in the future"}
        except ValueError:
            return {"success": False, "error": "Invalid target completion date format. Use YYYY-MM-DD"}
        
        # Prepare epic habit record
        epic_record = {
            "epic_id": epic_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "category": category,
            "priority": priority,
            "target_completion_date": target_completion_date,
            "success_criteria": success_criteria,
            "current_progress": 0.0,
            "high_priority_micro_habits": [],
            "low_priority_micro_habits": [],
            "created_date": datetime.now().isoformat()
        }
        
        # Store in database
        success = mongo_habit_manager.create_epic_habit(epic_record)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully created epic habit: {name}",
                "epic_id": epic_id,
                "details": {
                    "name": name,
                    "category": category,
                    "priority": priority,
                    "target_completion_date": target_completion_date,
                    "success_criteria": success_criteria
                }
            }
        else:
            return {"success": False, "error": "Failed to create epic habit in database"}
            
    except Exception as e:
        return {"success": False, "error": f"Error creating epic habit: {str(e)}"}

async def _assign_micro_to_epic_record(micro_habit_id: str, epic_habit_id: str, priority_within_epic: str) -> Dict[str, Any]:
    """Assign a micro habit to an epic habit with priority level."""
    try:
        # Validate priority level
        if priority_within_epic not in ["high", "low"]:
            return {"success": False, "error": "priority_within_epic must be 'high' or 'low'"}
        
        # Assign in database
        success = mongo_habit_manager.assign_micro_to_epic(micro_habit_id, epic_habit_id, priority_within_epic)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully assigned micro habit to epic with {priority_within_epic} priority",
                "micro_habit_id": micro_habit_id,
                "epic_habit_id": epic_habit_id,
                "priority": priority_within_epic
            }
        else:
            return {"success": False, "error": "Failed to assign micro habit to epic"}
            
    except Exception as e:
        return {"success": False, "error": f"Error assigning habit: {str(e)}"}

async def _modify_habit_parameters(
    habit_id: str, timing_type: Optional[str] = None, daily_timing: Optional[str] = None,
    start_time: Optional[str] = None, end_time: Optional[str] = None,
    difficulty_level: Optional[str] = None, intrinsic_score: Optional[int] = None
) -> Dict[str, Any]:
    """Modify habit parameters like timing, difficulty, and importance."""
    try:
        # Get existing habit
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        # Build update data
        update_data = {}
        
        if timing_type is not None:
            update_data["timing_type"] = timing_type
            # Clear conflicting timing fields
            if timing_type == "specific_time":
                update_data["start_time"] = None
                update_data["end_time"] = None
            elif timing_type == "entire_day":
                update_data["daily_timing"] = None
                update_data["start_time"] = None
                update_data["end_time"] = None
            elif timing_type == "time_range":
                update_data["daily_timing"] = None
        
        if daily_timing is not None:
            update_data["daily_timing"] = daily_timing
        
        if start_time is not None:
            update_data["start_time"] = start_time
        
        if end_time is not None:
            update_data["end_time"] = end_time
        
        if difficulty_level is not None:
            update_data["difficulty_level"] = difficulty_level
        
        if intrinsic_score is not None:
            update_data["intrinsic_score"] = intrinsic_score
        
        if not update_data:
            return {"success": False, "error": "No parameters provided to modify"}
        
        # Add modification timestamp
        update_data["last_modified"] = datetime.now().isoformat()
        
        # Update in database
        result = mongo_habit_manager.update_habit_parameters(habit_id, update_data)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Habit parameters updated successfully",
                "habit_id": habit_id,
                "modified_fields": list(update_data.keys()),
                "habit_name": habit.get("name", "Unknown")
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to update habit parameters")}
            
    except Exception as e:
        return {"success": False, "error": f"Error modifying habit: {str(e)}"}

async def _pause_resume_habit(
    habit_id: str, action: str, reason: Optional[str] = None, pause_until: Optional[str] = None
) -> Dict[str, Any]:
    """Pause or resume a habit with optional reason and auto-resume date."""
    try:
        # Get current habit status
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        current_status = habit.get("status", "active")
        
        if action == "pause":
            if current_status == "paused":
                return {"success": False, "error": "Habit is already paused"}
            
            # Validate pause_until date if provided
            if pause_until:
                try:
                    pause_date = datetime.strptime(pause_until, "%Y-%m-%d")
                    if pause_date <= datetime.now():
                        return {"success": False, "error": "pause_until date must be in the future"}
                except ValueError:
                    return {"success": False, "error": "Invalid pause_until date format. Use YYYY-MM-DD"}
            
            update_data = {
                "status": "paused",
                "pause_reason": reason,
                "paused_at": datetime.now().isoformat(),
                "pause_until": pause_until,
                "last_modified": datetime.now().isoformat()
            }
            message = f"Habit paused successfully"
            if pause_until:
                message += f" until {pause_until}"
                
        elif action == "resume":
            if current_status != "paused":
                return {"success": False, "error": "Habit is not currently paused"}
            
            update_data = {
                "status": "active",
                "resume_reason": reason,
                "resumed_at": datetime.now().isoformat(),
                "pause_reason": None,
                "pause_until": None,
                "last_modified": datetime.now().isoformat()
            }
            message = "Habit resumed successfully"
        
        # Update in database
        result = mongo_habit_manager.update_habit_status(habit_id, update_data)
        
        if result["success"]:
            return {
                "success": True,
                "message": message,
                "action": action,
                "habit_id": habit_id,
                "new_status": update_data["status"]
            }
        else:
            return {"success": False, "error": result.get("error", f"Failed to {action} habit")}
            
    except Exception as e:
        return {"success": False, "error": f"Error {action}ing habit: {str(e)}"}

async def _add_habit_note(
    habit_id: str, date: str, note_type: str, content: str,
    mood_context: Optional[int] = None, tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Add a note/diary entry for a habit on a specific date."""
    try:
        # Validate habit exists
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Create note record
        note_record = {
            "note_id": str(uuid.uuid4()),
            "habit_id": habit_id,
            "user_id": habit["user_id"],
            "date": date,
            "note_type": note_type,
            "content": content,
            "mood_context": mood_context,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
        
        # Save to database
        result = mongo_habit_manager.add_habit_note(note_record)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Habit note added successfully",
                "note_id": note_record["note_id"],
                "habit_id": habit_id,
                "date": date,
                "note_type": note_type
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to add habit note")}
            
    except Exception as e:
        return {"success": False, "error": f"Error adding habit note: {str(e)}"}

async def _get_habit_notes(
    habit_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
    note_type: Optional[str] = None, limit: int = 50
) -> Dict[str, Any]:
    """Get habit notes with optional filtering by date range and note type."""
    try:
        # Validate habit exists
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        # Validate date formats if provided
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return {"success": False, "error": "Invalid start_date format. Use YYYY-MM-DD"}
        
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return {"success": False, "error": "Invalid end_date format. Use YYYY-MM-DD"}
        
        # Build query filters
        filters = {
            "habit_id": habit_id,
            "start_date": start_date,
            "end_date": end_date,
            "note_type": note_type,
            "limit": limit
        }
        
        # Get notes from database
        result = mongo_habit_manager.get_habit_notes(filters)
        
        if result["success"]:
            notes = result["notes"]
            return {
                "success": True,
                "notes": notes,
                "total_count": len(notes),
                "habit_id": habit_id,
                "filters_applied": {k: v for k, v in filters.items() if v is not None}
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to retrieve habit notes")}
            
    except Exception as e:
        return {"success": False, "error": f"Error retrieving habit notes: {str(e)}"}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def _get_habit_by_id(habit_id: str) -> Optional[Dict[str, Any]]:
    """Get habit by ID."""
    return mongo_habit_manager.get_micro_habit(habit_id)

async def _get_epic_habit_by_id(epic_id: str) -> Optional[Dict[str, Any]]:
    """Get epic habit by ID."""
    return mongo_habit_manager.get_epic_habit(epic_id)

async def _get_user_active_habits(user_id: str) -> List[Dict[str, Any]]:
    """Get all active habits for a user."""
    return mongo_habit_manager.get_user_micro_habits(user_id, "active") 