"""
Habit Basic Tools
================
Basic CRUD operations and core functionality tools for habit management.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from datetime import datetime, timedelta
import uuid

# Import basic habit functions for direct calls
from utils.habit_core import (
    _create_micro_habit_record,
    _create_epic_habit_record,
    _assign_micro_to_epic_record,
    _get_habit_by_id,
    _get_epic_habit_by_id,
    _get_user_habit_limits,
    _modify_habit_parameters,
    _pause_resume_habit,
    _add_habit_note,
    _get_habit_notes,
)

# =============================================================================
# BASIC TOOL SCHEMAS
# =============================================================================

class MainHabitOperationInput(BaseModel):
    operation: str = Field(..., description="Operation name: create_micro_habit, create_epic_habit, assign_micro_to_epic")
    params: Dict[str, Any] = Field(..., description="Parameters for the habit operation")

class ModifyHabitParametersInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    timing_type: Optional[str] = Field(default=None, description="specific_time, entire_day, or time_range")
    daily_timing: Optional[str] = Field(default=None, description="Fixed time like 07:00 or after_coffee")
    start_time: Optional[str] = Field(default=None, description="Start time for time_range habits (HH:MM format)")
    end_time: Optional[str] = Field(default=None, description="End time for time_range habits (HH:MM format)")
    difficulty_level: Optional[str] = Field(default=None, description="Difficulty level: easy, medium, hard")
    intrinsic_score: Optional[int] = Field(default=None, description="Importance score 1-4")

class PauseResumeHabitInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    action: str = Field(..., description="pause or resume")
    reason: Optional[str] = Field(default=None, description="Reason for pausing/resuming")
    pause_until: Optional[str] = Field(default=None, description="Resume date for temporary pause (YYYY-MM-DD)")

class HabitNotesOperationInput(BaseModel):
    operation: str = Field(..., description="Operation name: add_note, get_notes, get_insights")
    params: Dict[str, Any] = Field(..., description="Parameters for the habit notes operation")

class HabitOutput(BaseModel):
    is_created: bool = Field(..., description="Whether habit operation was successful")
    habit_id: Optional[str] = Field(default=None, description="ID of the created/modified habit")
    plan_id: Optional[str] = Field(default=None, description="ID of the created plan")

# =============================================================================
# BASIC HABIT OPERATION TOOLS
# =============================================================================

@tool("main_habit_operations", args_schema=MainHabitOperationInput)
async def main_habit_operations(operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Execute main habit operations (create habits, assign to epics).
    
    Args:
    - operation (str): Operation name (create_micro_habit, create_epic_habit, assign_micro_to_epic)
    - params (Dict[str, Any]): Parameters for the habit operation
    
    Returns:
    - Dict containing: success (bool), data (Any), operation (str), error (str if failed)
    """
    try:
        if operation == "create_micro_habit":
            result = await _create_micro_habit_record(
                user_id=params.get("user_id"),
                name=params.get("name"),
                description=params.get("description"),
                category=params.get("category"),
                period=params.get("period"),
                intrinsic_score=params.get("intrinsic_score", 1),
                habit_type=params.get("habit_type"),
                timing_type=params.get("timing_type", "specific_time"),
                frequency=params.get("frequency"),
                weekly_days=params.get("weekly_days"),
                specific_dates=params.get("specific_dates"),
                daily_timing=params.get("daily_timing"),
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
                difficulty_level=params.get("difficulty_level", "easy"),
                is_meditation=params.get("is_meditation", False),
                meditation_audio_id=params.get("meditation_audio_id")
            )
        elif operation == "create_epic_habit":
            result = await _create_epic_habit_record(
                user_id=params.get("user_id"),
                name=params.get("name"),
                description=params.get("description"),
                category=params.get("category"),
                priority=params.get("priority", 1),
                target_completion_date=params.get("target_completion_date"),
                success_criteria=params.get("success_criteria", [])
            )
        elif operation == "assign_micro_to_epic":
            result = await _assign_micro_to_epic_record(
                micro_habit_id=params.get("micro_habit_id"),
                epic_habit_id=params.get("epic_habit_id"),
                priority_within_epic=params.get("priority_within_epic")
            )
        else:
            raise ValueError(f"Unknown main habit operation: {operation}")
        
        return {
            "success": result.get("success", False),
            "data": result,
            "operation": operation,
            "error": result.get("error") if not result.get("success", False) else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "operation": operation,
            "error": f"Error executing {operation}: {str(e)}"
        }

@tool("modify_habit_parameters", args_schema=ModifyHabitParametersInput)
async def modify_habit_parameters(
    habit_id: str, timing_type: Optional[str] = None, daily_timing: Optional[str] = None,
    start_time: Optional[str] = None, end_time: Optional[str] = None,
    difficulty_level: Optional[str] = None, intrinsic_score: Optional[int] = None
) -> Dict[str, Any]:
    """
    Tool Purpose: Modify habit parameters like timing, difficulty, and importance.
    
    Args:
    - habit_id (str): Habit identifier
    - timing_type (Optional[str]): specific_time, entire_day, or time_range
    - daily_timing (Optional[str]): Fixed time like 07:00 or after_coffee
    - start_time (Optional[str]): Start time for time_range habits (HH:MM format)
    - end_time (Optional[str]): End time for time_range habits (HH:MM format)  
    - difficulty_level (Optional[str]): Difficulty level: easy, medium, hard
    - intrinsic_score (Optional[int]): Importance score 1-4
    
    Returns:
    - Dict containing: success (bool), message (str), details (dict), error (str if failed)
    """
    try:
        result = await _modify_habit_parameters(
            habit_id=habit_id,
            timing_type=timing_type,
            daily_timing=daily_timing,
            start_time=start_time,
            end_time=end_time,
            difficulty_level=difficulty_level,
            intrinsic_score=intrinsic_score
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "details": {
                "habit_id": habit_id,
                "modified_fields": result.get("modified_fields", []),
                "habit_name": result.get("habit_name", "Unknown")
            },
            "error": result.get("error") if not result.get("success", False) else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "",
            "details": {},
            "error": f"Error modifying habit parameters: {str(e)}"
        }

@tool("pause_resume_habit", args_schema=PauseResumeHabitInput)
async def pause_resume_habit(
    habit_id: str, action: str, reason: Optional[str] = None, pause_until: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool Purpose: Pause or resume a habit with optional reason and auto-resume date.
    
    Args:
    - habit_id (str): Habit identifier
    - action (str): pause or resume
    - reason (Optional[str]): Reason for pausing/resuming
    - pause_until (Optional[str]): Resume date for temporary pause (YYYY-MM-DD)
    
    Returns:
    - Dict containing: success (bool), message (str), details (dict), error (str if failed)
    """
    try:
        result = await _pause_resume_habit(
            habit_id=habit_id,
            action=action,
            reason=reason,
            pause_until=pause_until
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "details": {
                "habit_id": habit_id,
                "action": action,
                "new_status": result.get("new_status"),
                "reason": reason,
                "pause_until": pause_until
            },
            "error": result.get("error") if not result.get("success", False) else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "",
            "details": {},
            "error": f"Error {action}ing habit: {str(e)}"
        }

@tool("habit_notes_operations", args_schema=HabitNotesOperationInput)
async def habit_notes_operations(operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool Purpose: Handle habit notes operations (add, get notes, get insights).
    
    Args:
    - operation (str): Operation name (add_note, get_notes, get_insights)
    - params (Dict[str, Any]): Parameters for the notes operation
    
    Returns:
    - Dict containing: success (bool), data (Any), operation (str), error (str if failed)
    """
    try:
        if operation == "add_note":
            result = await _add_habit_note(
                habit_id=params.get("habit_id"),
                date=params.get("date"),
                note_type=params.get("note_type"),
                content=params.get("content"),
                mood_context=params.get("mood_context"),
                tags=params.get("tags")
            )
        elif operation == "get_notes":
            result = await _get_habit_notes(
                habit_id=params.get("habit_id"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                note_type=params.get("note_type"),
                limit=params.get("limit", 50)
            )
        elif operation == "get_insights":
            from utils.habit_analytics import _get_habit_insights_from_notes
            result = await _get_habit_insights_from_notes(
                habit_id=params.get("habit_id"),
                days=params.get("days", 30)
            )
        else:
            raise ValueError(f"Unknown habit notes operation: {operation}")
        
        return {
            "success": result.get("success", False),
            "data": result,
            "operation": operation,
            "error": result.get("error") if not result.get("success", False) else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "operation": operation,
            "error": f"Error executing {operation}: {str(e)}"
        } 