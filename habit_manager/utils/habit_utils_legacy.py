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
# BASIC OPERATION SCHEMAS (for utils functions and FastAPI endpoints)
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

# DAILY EXECUTION SCHEMAS
class PlanFlexibleHabitsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date to plan for in YYYY-MM-DD format")
    available_time_slots: List[str] = Field(..., description="Available timing options")
    energy_level: Optional[int] = Field(default=5, description="Current energy level 1-10")

# RateDailyMoodInput REMOVED: Mood recording moved to mood_manager

class GetDailyHabitListInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")

# PROGRESS TRACKING SCHEMAS
class TrackHabitCompletionInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    habit_id: str = Field(..., description="Habit identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    completion_score: int = Field(..., ge=0, le=4, description="0-4 for formation habits, 0-1 for breaking habits")
    habit_type: str = Field(..., description="formation or breaking")
    actual_timing: Optional[str] = Field(default=None, description="When habit actually happened")
    notes: Optional[str] = Field(default=None, description="Optional completion notes")

    @field_validator('completion_score')
    def validate_completion_score(cls, v, values):
        # Get habit_type from values context
        habit_type = values.data.get('habit_type') if hasattr(values, 'data') else values.get('habit_type')
        
        if habit_type == "breaking":
            # Bad habits: only 0 (relapsed) or 1 (stayed clean) are valid
            if v not in [0, 1]:
                raise ValueError("For breaking habits, completion_score must be 0 (relapsed) or 1 (stayed clean)")
        elif habit_type == "formation":
            # Good habits: 0-4 scale based on intrinsic_score
            if not (0 <= v <= 4):
                raise ValueError("For formation habits, completion_score must be between 0-4")
        
        return v

    @field_validator('habit_type')
    def validate_habit_type(cls, v):
        valid_types = ["formation", "breaking"]
        if v not in valid_types:
            raise ValueError(f"habit_type must be one of: {valid_types}")
        return v

class CalculateHabitTrendsInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    time_period: str = Field(..., description="weekly, monthly, or custom")
    start_date: Optional[str] = Field(default=None, description="Start date for custom period")
    end_date: Optional[str] = Field(default=None, description="End date for custom period")

class GenerateEpicProgressInput(BaseModel):
    epic_habit_id: str = Field(..., description="Epic habit identifier")
    time_period: str = Field(..., description="weekly, monthly, or all_time")

# =============================================================================
# MAIN HABIT OPERATIONS (for FastAPI endpoints and MCP tools)
# =============================================================================

async def _create_micro_habit_record(
    user_id: str, name: str, description: str, category: str, period: str, intrinsic_score: int, 
    habit_type: str, timing_type: str = "specific_time", frequency: Optional[str] = None, weekly_days: Optional[List[str]] = None,
    specific_dates: Optional[List[str]] = None, daily_timing: Optional[str] = None,
    start_time: Optional[str] = None, end_time: Optional[str] = None,
    difficulty_level: str = "easy", is_meditation: bool = False, meditation_audio_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new micro habit record with validation and premium tier checks."""
    validation_errors = []
    
    # Check premium tier limits first
    limits_check = check_habit_creation_limits(user_id, "micro")
    if not limits_check["can_create"]:
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": [limits_check["reason"]],
            "upgrade_required": True,
            "upgrade_message": limits_check["upgrade_message"],
            "tier_info": limits_check
        }
    
    # Get user limits for validation
    user_limits = _get_user_habit_limits(user_id)
    
    # Advanced scheduling is now available to all users - no validation needed
    
    # Validate difficulty level
    if difficulty_level not in ["easy", "medium", "hard"]:
        validation_errors.append("difficulty_level must be one of: easy, medium, hard")
    
    # Validate habit_type
    if habit_type not in ["formation", "breaking"]:
        validation_errors.append("habit_type must be one of: formation, breaking")
    
    # Validate timing_type
    if timing_type not in ["specific_time", "entire_day", "time_range"]:
        validation_errors.append("timing_type must be one of: specific_time, entire_day, time_range")
    
    # Validate timing fields based on timing_type
    if timing_type == "time_range":
        if not start_time or not end_time:
            validation_errors.append("time_range timing requires both start_time and end_time")
        elif start_time >= end_time:
            validation_errors.append("start_time must be before end_time")
    elif timing_type == "specific_time":
        # For specific_time, daily_timing is optional but should be validated if provided
        pass
    elif timing_type == "entire_day":
        # For entire_day habits, timing fields should be null
        if daily_timing or start_time or end_time:
            validation_errors.append("entire_day timing should not specify daily_timing, start_time, or end_time")
    
    # Validate meditation habit requirements
    if is_meditation and not meditation_audio_id:
        validation_errors.append("Meditation habit requires meditation_audio_id. Create meditation audio first.")
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": validation_errors
        }
    
    # Bad habits can't be meditation habits
    if habit_type == "breaking" and is_meditation:
        validation_errors.append("Breaking habits (bad habits) cannot be meditation habits")
    
    # Bad habits have different timing constraints
    if habit_type == "breaking" and timing_type == "specific_time":
        validation_errors.append("Breaking habits cannot use specific_time timing - use entire_day or time_range")
    
    # Validate weekly habit requirements  
    if period == "weekly" and not weekly_days:
        validation_errors.append("Weekly habits require weekly_days to be specified")
        
    # Validate specific dates requirements
    if period == "specific_dates" and not specific_dates:
        validation_errors.append("Specific dates period requires specific_dates list")
    
    if validation_errors:
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": validation_errors
        }
    
    # Generate habit ID
    habit_id = f"habit_{uuid.uuid4().hex[:8]}"
    
    # Create habit record
    habit_record = {
        "habit_id": habit_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "category": category,
        "period": period,
        "frequency": frequency,
        "weekly_days": weekly_days,
        "specific_dates": specific_dates,
        "timing_type": timing_type,
        "daily_timing": daily_timing,
        "start_time": start_time,
        "end_time": end_time,
        "intrinsic_score": intrinsic_score,
        "difficulty_level": difficulty_level,
        "habit_type": habit_type,
        "is_meditation": is_meditation,
        "assets": [meditation_audio_id] if meditation_audio_id else [],
        "status": "active",
        "current_streak": 0,
        "best_streak": 0,
        "total_completions": 0,
        "created_date": datetime.now().isoformat()
    }
    
    # Save to MongoDB
    db_success = mongo_habit_manager.create_micro_habit(habit_record)
    if not db_success:
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": ["Failed to save habit to database"]
        }
    
    # Generate schedule automatically
    schedule_generated = await _generate_habit_schedule_for_habit(habit_record)
    
    return {
        "success": True,
        "habit_id": habit_id,
        "habit_record": habit_record,
        "schedule_generated": schedule_generated,
        "validation_errors": []
    }

async def _create_epic_habit_record(
    user_id: str, name: str, description: str, category: str, priority: int,
    target_completion_date: str, success_criteria: List[str]
) -> Dict[str, Any]:
    """Create an epic habit record with premium tier validation."""
    # Check premium tier limits for epic habits
    limits_check = check_habit_creation_limits(user_id, "epic")
    if not limits_check["can_create"]:
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": [limits_check["reason"]],
            "upgrade_required": True,
            "upgrade_message": limits_check["upgrade_message"],
            "tier_info": limits_check
        }
    
    # Generate epic habit ID
    epic_id = f"epic_{uuid.uuid4().hex[:8]}"
    
    # Create epic habit record
    epic_record = {
        "epic_id": epic_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "category": category,
        "priority": priority,
        "target_completion_date": target_completion_date,
        "success_criteria": success_criteria,
        "high_priority_micro_habits": [],
        "low_priority_micro_habits": [],
        "current_progress": 0.0
    }
    
    # Save to MongoDB
    db_success = mongo_habit_manager.create_epic_habit(epic_record)
    if not db_success:
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": ["Failed to save epic habit to database"]
        }
    
    return {
        "success": True,
        "habit_id": epic_id,
        "epic_record": epic_record,
        "schedule_generated": True  # Epic habits don't need scheduling
    }

async def _assign_micro_to_epic_record(micro_habit_id: str, epic_habit_id: str, priority_within_epic: str) -> Dict[str, Any]:
    """Assign micro habit to epic habit with priority."""
    # Validate priority
    if priority_within_epic not in ["high", "low"]:
        return {"success": False, "error": "priority_within_epic must be 'high' or 'low'"}
    
    # Perform assignment in MongoDB
    assignment_success = mongo_habit_manager.assign_micro_to_epic(micro_habit_id, epic_habit_id, priority_within_epic)
    
    if not assignment_success:
        return {"success": False, "error": "Failed to assign micro habit to epic habit"}
    
    assignment_id = f"assign_{uuid.uuid4().hex[:8]}"
    
    return {
        "success": True,
        "assignment_id": assignment_id,
        "epic_progress_updated": True,
        "assignment_details": {
            "micro_habit_id": micro_habit_id,
            "epic_habit_id": epic_habit_id,
            "priority": priority_within_epic
        }
    }


# =============================================================================
# DAILY EXECUTION OPERATIONS
# =============================================================================

async def _plan_flexible_habits_timing(
    user_id: str, date: str, available_time_slots: List[str], energy_level: int = 5
) -> Dict[str, Any]:
    """Plan optimal timing for flexible habits with support for different timing types."""
    # Get habits that need timing for this date
    flexible_habits = await _get_flexible_habits_for_date(user_id, date)
    
    if not flexible_habits:
        return {
            "success": True,
            "date": date,
            "planned_habits": [],
            "scheduling_notes": ["No flexible timing habits found for this date"]
        }
    
    # Categorize habits by timing type
    specific_time_habits = []
    entire_day_habits = []
    time_range_habits = []
    
    for habit in flexible_habits:
        timing_type = habit.get("timing_type", "specific_time")
        
        if timing_type == "specific_time":
            specific_time_habits.append(habit)
        elif timing_type == "entire_day":
            entire_day_habits.append(habit)
        elif timing_type == "time_range":
            time_range_habits.append(habit)
    
    planned_habits = []
    scheduling_notes = []
    
    # Handle entire_day habits (these don't need specific timing)
    for habit in entire_day_habits:
        habit_type = habit.get("habit_type", "formation")
        
        if habit_type == "breaking":
            # Bad habits tracked all day - provide guidance
            planned_habits.append({
                "habit_id": habit["habit_id"],
                "habit_name": habit.get("name", "Unknown"),
                "habit_type": habit_type,
                "timing_type": "entire_day",
                "planned_timing": "all_day",
                "energy_requirement": "none",
                "guidance": f"Avoid {habit.get('name', 'this habit')} throughout the entire day",
                "success_metric": "staying_clean_all_day"
            })
        else:
            # Good habits that can be done anytime during the day
            planned_habits.append({
                "habit_id": habit["habit_id"],
                "habit_name": habit.get("name", "Unknown"),
                "habit_type": habit_type,
                "timing_type": "entire_day",
                "planned_timing": "flexible_anytime",
                "energy_requirement": _get_energy_requirement(habit),
                "guidance": f"Complete {habit.get('name', 'this habit')} anytime during the day",
                "success_metric": "completion_by_end_of_day"
            })
    
    # Handle time_range habits (habits that can only be done during specific windows)
    for habit in time_range_habits:
        start_time = habit.get("start_time")
        end_time = habit.get("end_time")
        habit_type = habit.get("habit_type", "formation")
        
        if start_time and end_time:
            if habit_type == "breaking":
                # Bad habits to avoid during specific time windows
                planned_habits.append({
                    "habit_id": habit["habit_id"],
                    "habit_name": habit.get("name", "Unknown"),
                    "habit_type": habit_type,
                    "timing_type": "time_range",
                    "planned_timing": f"avoid_during_{start_time}_to_{end_time}",
                    "time_window": f"{start_time} - {end_time}",
                    "energy_requirement": "vigilance",
                    "guidance": f"Extra vigilance needed: avoid {habit.get('name', 'this habit')} between {start_time} and {end_time}",
                    "success_metric": "staying_clean_during_window"
                })
                scheduling_notes.append(f"High-risk window: {start_time}-{end_time} for {habit.get('name', 'habit avoidance')}")
            else:
                # Good habits that must be done within specific time windows
                optimal_slot = _find_best_slot_in_range(available_time_slots, start_time, end_time, energy_level)
                
                planned_habits.append({
                    "habit_id": habit["habit_id"],
                    "habit_name": habit.get("name", "Unknown"),
                    "habit_type": habit_type,
                    "timing_type": "time_range",
                    "planned_timing": optimal_slot if optimal_slot else f"within_{start_time}_to_{end_time}",
                    "time_window": f"{start_time} - {end_time}",
                    "energy_requirement": _get_energy_requirement(habit),
                    "guidance": f"Complete {habit.get('name', 'this habit')} between {start_time} and {end_time}",
                    "success_metric": "completion_within_window"
                })
                
                if not optimal_slot:
                    scheduling_notes.append(f"No ideal slot found for {habit.get('name')} within {start_time}-{end_time} window")
    
    # Handle specific_time habits (traditional scheduling)
    available_slots = [slot for slot in available_time_slots]  # Copy to avoid modification
    
    # Sort specific_time habits by priority and energy requirements
    specific_time_habits.sort(key=lambda h: (
        h.get("intrinsic_score", 1),  # Higher intrinsic score first
        _get_energy_requirement_numeric(h)  # Higher energy requirements first when energy is high
    ), reverse=True)
    
    for habit in specific_time_habits:
        if not available_slots:
            scheduling_notes.append("No more available time slots for remaining habits")
            break
        
        # Find optimal slot based on energy requirements
        energy_req = _get_energy_requirement_numeric(habit)
        
        if energy_level >= 7 and energy_req >= 3:
            # High energy available, prioritize high-energy habits
            optimal_slot = available_slots[0]
        elif energy_level <= 4 and energy_req <= 2:
            # Low energy available, find easy habits
            optimal_slot = available_slots[-1]  # Use later slots for easier habits
        else:
            # Match energy level to habit requirements
            optimal_slot = available_slots[len(available_slots) // 2]
        
        planned_habits.append({
            "habit_id": habit["habit_id"],
            "habit_name": habit.get("name", "Unknown"),
            "habit_type": habit.get("habit_type", "formation"),
            "timing_type": "specific_time",
            "planned_timing": optimal_slot,
            "energy_requirement": _get_energy_requirement(habit),
            "priority_score": habit.get("intrinsic_score", 1),
            "guidance": f"Scheduled for {optimal_slot}",
            "success_metric": "completion_at_scheduled_time"
        })
        
        # Remove the used slot
        available_slots.remove(optimal_slot)
    
    # Add general scheduling notes
    if entire_day_habits:
        scheduling_notes.append(f"{len(entire_day_habits)} habits can be completed anytime during the day")
    if time_range_habits:
        scheduling_notes.append(f"{len(time_range_habits)} habits have specific time window requirements")
    if specific_time_habits:
        scheduling_notes.append(f"{len(specific_time_habits)} habits scheduled for specific times")
    
    return {
        "success": True,
        "date": date,
        "energy_level": energy_level,
        "planned_habits": planned_habits,
        "scheduling_summary": {
            "total_habits": len(planned_habits),
            "specific_time_count": len(specific_time_habits),
            "entire_day_count": len(entire_day_habits),
            "time_range_count": len(time_range_habits),
            "formation_habits": len([h for h in planned_habits if h["habit_type"] == "formation"]),
            "breaking_habits": len([h for h in planned_habits if h["habit_type"] == "breaking"])
        },
        "scheduling_notes": scheduling_notes
    }


def _get_energy_requirement(habit: Dict[str, Any]) -> str:
    """Get energy requirement description for a habit."""
    difficulty = habit.get("difficulty_level", "easy")
    habit_type = habit.get("habit_type", "formation")
    
    if habit_type == "breaking":
        return "vigilance"  # Bad habits require mental vigilance
    
    if difficulty == "hard":
        return "high"
    elif difficulty == "medium":
        return "medium"
    else:
        return "low"


def _get_energy_requirement_numeric(habit: Dict[str, Any]) -> int:
    """Get numeric energy requirement for sorting."""
    difficulty = habit.get("difficulty_level", "easy")
    
    if difficulty == "hard":
        return 3
    elif difficulty == "medium":
        return 2
    else:
        return 1


def _find_best_slot_in_range(available_slots: List[str], start_time: str, end_time: str, energy_level: int) -> Optional[str]:
    """Find the best available slot within a time range."""
    # Simple implementation - find first slot that falls within range
    for slot in available_slots:
        # This would need more sophisticated time parsing in a real implementation
        # For now, just return first available slot
        if slot:  # Basic check that slot exists
            return slot
    return None

async def _get_daily_habit_list_organized(user_id: str, date: str) -> Dict[str, Any]:
    """Get habits for a date organized by timing type."""
    # Get all active habits for user
    all_habits = await _get_user_active_habits(user_id)
    
    # Filter habits scheduled for this date
    scheduled_habits = await _filter_habits_by_date(all_habits, date)
    
    # Separate by timing type
    fixed_timing_habits = [h for h in scheduled_habits if h.get("daily_timing")]
    flexible_habits = [h for h in scheduled_habits if not h.get("daily_timing")]
    
    return {
        "date": date,
        "fixed_timing_habits": fixed_timing_habits,
        "flexible_habits": flexible_habits,
        "total_habits": len(scheduled_habits)
    }

# =============================================================================
# PROGRESS TRACKING OPERATIONS
# =============================================================================

async def _track_habit_completion_record(
    user_id: str, habit_id: str, date: str, completion_score: int,
    actual_timing: Optional[str] = None, notes: Optional[str] = None
) -> Dict[str, Any]:
    """Track habit completion with validation and streak updates."""
    # Get habit details to determine habit_type
    habit_details = await _get_habit_by_id(habit_id)
    if not habit_details:
        return {
            "success": False,
            "completion_recorded": False,
            "streak_updated": False,
            "validation_errors": [f"Habit {habit_id} not found"]
        }
    
    habit_type = habit_details.get("habit_type", "formation")
    intrinsic_score = habit_details.get("intrinsic_score", 4)
    
    # Validate completion score based on habit type
    validation_errors = []
    if habit_type == "breaking":
        # Bad habits: only 0 (relapsed) or 1 (stayed clean) are valid
        if completion_score not in [0, intrinsic_score]:
            validation_errors.append(f"For breaking habits, completion_score must be 0 (relapsed) or {intrinsic_score} (stayed clean). No partial scores are allowed.")
    elif habit_type == "formation":
        # Good habits: 0 to intrinsic_score range
        if not (0 <= completion_score <= intrinsic_score):
            validation_errors.append(f"For formation habits, completion_score must be between 0-{intrinsic_score}")
    
    if validation_errors:
        return {
            "success": False,
            "completion_recorded": False,
            "streak_updated": False,
            "validation_errors": validation_errors
        }
    
    # Create completion record with habit_type
    completion_record = {
        "user_id": user_id,
        "habit_id": habit_id,
        "date": date,
        "intrinsic_score": intrinsic_score,
        "completion_score": completion_score,
        "habit_type": habit_type,
        "actual_timing": actual_timing,
        "notes": notes,
        "recorded_at": datetime.now().isoformat()
    }
    
    # Save completion to MongoDB
    completion_success = mongo_habit_manager.record_habit_completion(completion_record)
    if not completion_success:
        return {
            "success": False,
            "completion_recorded": False,
            "streak_updated": False,
            "validation_errors": ["Failed to save completion to database"]
        }
    
    # Update streak based on habit type
    if habit_type == "breaking":
        # For bad habits: success is staying clean (score = full score), failure is relapse (score = 0)
        completed = (completion_score == intrinsic_score)
    else:
        # For good habits: success is any positive score
        completed = (completion_score > 0)
    
    streak_success = mongo_habit_manager._update_habit_streak(habit_id, completed)
    
    return {
        "success": True,
        "completion_recorded": True,
        "streak_updated": streak_success,
        "habit_type": habit_type,
        "completion_details": {
            "user_id": user_id,
            "habit_id": habit_id,
            "date": date,
            "completion_score": completion_score,
            "streak_maintained" if completed else "streak_broken": True
        }
    }

async def _calculate_basic_habit_trends(
    habit_id: str, time_period: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate habit trend analysis with formation/breaking habit support."""
    # Get habit details to determine habit type
    habit_details = await _get_habit_by_id(habit_id)
    if not habit_details:
        return {"success": False, "error": f"Habit {habit_id} not found"}
    
    habit_type = habit_details.get("habit_type", "formation")
    habit_name = habit_details.get("name", "Unknown")
    intrinsic_score = habit_details.get("intrinsic_score", 4)
    
    # Get completion records for the time period
    completion_records = await _get_completion_records(habit_id, start_date, end_date)
    
    if not completion_records:
        return {
            "success": True,
            "habit_id": habit_id,
            "habit_name": habit_name,
            "habit_type": habit_type,
            "time_period": time_period,
            "trends": {
                "overall_completion_rate": 0,
                "average_score": 0,
                "streak_info": {"current": 0, "best": 0},
                "trend_direction": "no_data",
                "consistency_score": 0
            },
            "insights": ["No completion data available for analysis"],
            "recommendations": ["Start tracking this habit to generate trends"]
        }
    
    # Calculate metrics based on habit type
    if habit_type == "breaking":
        # For bad habits: success = staying clean (score 1), failure = relapse (score 0)
        successful_days = [r for r in completion_records if r["completion_score"] == 1]
        completion_rate = len(successful_days) / len(completion_records)
        average_score = completion_rate  # Binary: either 1 or 0
        
        # Streak calculation for bad habits (consecutive clean days)
        current_streak = await _get_current_habit_streak(habit_id)
        best_streak = await _get_best_habit_streak(habit_id)
        
        insights = []
        recommendations = []
        
        if completion_rate >= 0.9:
            insights.append(f"Excellent abstinence from {habit_name} - {completion_rate*100:.1f}% clean days")
            recommendations.append("Maintain current strategies and identify triggers to avoid")
        elif completion_rate >= 0.7:
            insights.append(f"Good progress avoiding {habit_name} - {completion_rate*100:.1f}% clean days")
            recommendations.append("Strengthen relapse prevention strategies")
        elif completion_rate >= 0.5:
            insights.append(f"Moderate success avoiding {habit_name} - room for improvement")
            recommendations.append("Consider additional support or different avoidance strategies")
        else:
            insights.append(f"Frequent relapses detected - {(1-completion_rate)*100:.1f}% relapse rate")
            recommendations.append("Review triggers and consider professional support or intervention")
        
        # Streak insights for bad habits
        if current_streak >= 30:
            insights.append(f"Strong current streak: {current_streak} clean days")
        elif current_streak >= 7:
            insights.append(f"Building momentum: {current_streak} clean days")
        else:
            insights.append("Focus on building longer clean streaks")
            
    else:
        # For good habits: standard completion rate calculation
        successful_days = [r for r in completion_records if r["completion_score"] > 0]
        completion_rate = len(successful_days) / len(completion_records)
        
        # Calculate average score (weighted by intrinsic_score)
        total_score = sum(r["completion_score"] for r in completion_records)
        max_possible = len(completion_records) * intrinsic_score
        average_score = total_score / max_possible if max_possible > 0 else 0
        
        # Streak calculation for good habits
        current_streak = await _get_current_habit_streak(habit_id)
        best_streak = await _get_best_habit_streak(habit_id)
        
        insights = []
        recommendations = []
        
        if completion_rate >= 0.8:
            insights.append(f"Excellent consistency with {habit_name} - {completion_rate*100:.1f}% completion rate")
            recommendations.append("Maintain current routine and consider progressive difficulty increases")
        elif completion_rate >= 0.6:
            insights.append(f"Good progress with {habit_name} - room for improvement")
            recommendations.append("Identify barriers to more consistent completion")
        elif completion_rate >= 0.4:
            insights.append(f"Moderate completion rate - {habit_name} needs attention")
            recommendations.append("Simplify the habit or adjust timing for better success")
        else:
            insights.append(f"Low completion rate for {habit_name} - consider redesign")
            recommendations.append("Break down into smaller steps or pause this habit temporarily")
    
    # Calculate consistency score (variance in completion)
    scores = [r["completion_score"] for r in completion_records]
    if len(scores) > 1:
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        consistency_score = max(0, 1 - (variance / (intrinsic_score ** 2)))  # Normalize by max possible variance
    else:
        consistency_score = 1.0 if scores and scores[0] > 0 else 0.0
    
    # Determine trend direction (last 7 days vs previous 7 days)
    if len(completion_records) >= 14:
        recent_scores = [r["completion_score"] for r in completion_records[-7:]]
        previous_scores = [r["completion_score"] for r in completion_records[-14:-7]]
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        previous_avg = sum(previous_scores) / len(previous_scores)
        
        if recent_avg > previous_avg * 1.1:
            trend_direction = "improving"
        elif recent_avg < previous_avg * 0.9:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "insufficient_data"
    
    return {
        "success": True,
        "habit_id": habit_id,
        "habit_name": habit_name,
        "habit_type": habit_type,
        "time_period": time_period,
        "trends": {
            "overall_completion_rate": round(completion_rate, 3),
            "average_score": round(average_score, 3),
            "streak_info": {
                "current": current_streak,
                "best": best_streak
            },
            "trend_direction": trend_direction,
            "consistency_score": round(consistency_score, 3)
        },
        "insights": insights,
        "recommendations": recommendations,
        "total_records_analyzed": len(completion_records)
    }

async def _calculate_basic_epic_progress(epic_habit_id: str, time_period: str) -> Dict[str, Any]:
    """Calculate epic habit progress with formation/breaking habit support."""
    # Check if this epic habit exists
    epic_habit = await _get_epic_habit_by_id(epic_habit_id)
    if not epic_habit:
        return {"success": False, "error": f"Epic habit {epic_habit_id} not found"}
    
    user_id = epic_habit.get("user_id")
    user_limits = _get_user_habit_limits(user_id)
    
    if not user_limits["epic_progress_calculation"]:
        return {
            "success": False,
            "error": "Epic progress calculation requires premium plan",
            "upgrade_message": "Upgrade to premium to track epic habit progress with micro-habit analytics",
            "feature_blocked": "epic_progress_calculation"
        }
    
    # Get micro habits associated with this epic
    high_priority_habits = epic_habit.get("high_priority_micro_habits", [])
    low_priority_habits = epic_habit.get("low_priority_micro_habits", [])
    all_micro_habits = high_priority_habits + low_priority_habits
    
    if not all_micro_habits:
        return {
            "success": True,
            "epic_id": epic_habit_id,
            "epic_name": epic_habit.get("name", "Unknown"),
            "overall_progress": 0,
            "micro_habit_progress": {},
            "insights": ["No micro habits assigned to this epic yet"],
            "recommendations": ["Assign micro habits to this epic to track progress"]
        }
    
    # Calculate progress for each micro habit
    micro_habit_progress = {}
    total_weighted_progress = 0
    total_weight = 0
    
    for habit_id in all_micro_habits:
        # Get habit details
        habit_details = await _get_habit_by_id(habit_id)
        if not habit_details:
            continue
            
        habit_type = habit_details.get("habit_type", "formation")
        habit_name = habit_details.get("name", "Unknown")
        intrinsic_score = habit_details.get("intrinsic_score", 4)
        
        # Determine weight based on priority
        is_high_priority = habit_id in high_priority_habits
        weight = 2.0 if is_high_priority else 1.0
        
        # Get completion records for this habit
        completion_records = await _get_completion_records(habit_id, None, None)
        
        if completion_records:
            if habit_type == "breaking":
                # For bad habits: success rate = clean days / total days
                successful_days = len([r for r in completion_records if r["completion_score"] == intrinsic_score])
                success_rate = successful_days / len(completion_records)
                average_score = success_rate  # Binary score for breaking habits
                
                # Calculate consistency (consecutive clean days vs relapses)
                scores = [r["completion_score"] for r in completion_records]
                # For breaking habits, consistency = low variance (less flip-flopping between clean/relapse)
                if len(scores) > 1:
                    variance = sum((score - success_rate) ** 2 for score in scores) / len(scores)
                    consistency_rate = max(0, 1 - variance)  # Lower variance = higher consistency
                else:
                    consistency_rate = 1.0 if scores and scores[0] == 1 else 0.0
                
            else:
                # For good habits: standard calculation
                successful_days = len([r for r in completion_records if r["completion_score"] > 0])
                completion_rate = successful_days / len(completion_records)
                
                # Calculate weighted average score
                total_score = sum(r["completion_score"] for r in completion_records)
                max_possible = len(completion_records) * intrinsic_score
                average_score = total_score / max_possible if max_possible > 0 else 0
                
                # Calculate consistency rate
                consistency_rate = completion_rate
                
            # Overall progress for this habit (average of score and consistency)
            habit_progress = (average_score + consistency_rate) / 2
            
        else:
            # No data available
            habit_progress = 0
            average_score = 0
            consistency_rate = 0
        
        # Store micro habit progress details
        micro_habit_progress[habit_id] = {
            "habit_name": habit_name,
            "habit_type": habit_type,
            "weight": weight,
            "average_score": round(average_score, 3),
            "consistency_rate": round(consistency_rate, 3),
            "overall_progress": round(habit_progress, 3),
            "is_high_priority": is_high_priority
        }
        
        # Add to weighted total
        total_weighted_progress += habit_progress * weight
        total_weight += weight
    
    # Calculate overall epic progress
    overall_progress = (total_weighted_progress / total_weight * 100) if total_weight > 0 else 0
    
    # Generate insights
    insights = []
    recommendations = []
    
    # Analyze high vs low priority performance
    high_priority_avg = 0
    low_priority_avg = 0
    high_count = 0
    low_count = 0
    
    for habit_id, progress in micro_habit_progress.items():
        if progress["is_high_priority"]:
            high_priority_avg += progress["overall_progress"]
            high_count += 1
        else:
            low_priority_avg += progress["overall_progress"]
            low_count += 1
    
    if high_count > 0:
        high_priority_avg /= high_count
        insights.append(f"High priority habits average: {high_priority_avg*100:.1f}%")
        
        if high_priority_avg < 0.6:
            recommendations.append("Focus on improving high priority habits first for maximum epic progress")
    
    if low_count > 0:
        low_priority_avg /= low_count
        insights.append(f"Low priority habits average: {low_priority_avg*100:.1f}%")
    
    # Overall progress insights
    if overall_progress >= 80:
        insights.append("Epic habit is performing excellently")
        recommendations.append("Consider increasing difficulty or adding new micro habits")
    elif overall_progress >= 60:
        insights.append("Good progress on epic habit")
        recommendations.append("Identify specific micro habits that need attention")
    elif overall_progress >= 40:
        insights.append("Moderate progress - room for improvement")
        recommendations.append("Focus on consistency in underperforming micro habits")
    else:
        insights.append("Epic habit needs significant attention")
        recommendations.append("Consider simplifying micro habits or reducing the number of active habits")
    
    return {
        "success": True,
        "epic_id": epic_habit_id,
        "epic_name": epic_habit.get("name", "Unknown"),
        "overall_progress": round(overall_progress, 2),
        "micro_habit_progress": micro_habit_progress,
        "priority_breakdown": {
            "high_priority_average": round(high_priority_avg * 100, 1) if high_count > 0 else 0,
            "low_priority_average": round(low_priority_avg * 100, 1) if low_count > 0 else 0,
            "high_priority_count": high_count,
            "low_priority_count": low_count
        },
        "insights": insights,
        "recommendations": recommendations,
        "time_period": time_period
    }

# =============================================================================
# INTERNAL HELPER FUNCTIONS (support main operations above)
# =============================================================================

async def _calculate_trend_impact(recent_scores: List[int], new_score: int) -> str:
    """Calculate how new score impacts trend."""
    if not recent_scores:
        return "baseline"
    
    avg_recent = sum(recent_scores) / len(recent_scores)
    if new_score > avg_recent:
        return "positive"
    elif new_score < avg_recent:
        return "negative"
    else:
        return "neutral"

async def _filter_habits_by_date(habits: List[Dict[str, Any]], date: str) -> List[Dict[str, Any]]:
    """Filter habits scheduled for specific date based on their period and frequency."""
    filtered_habits = []
    
    try:
        for habit in habits:
            period = habit.get("period")
            
            if period == "daily":
                # Daily habits are always scheduled
                filtered_habits.append(habit)
                
            elif period == "weekly":
                weekly_days = habit.get("weekly_days", [])
                if weekly_days:
                    # Check if date falls on one of the weekly days
                    from datetime import datetime
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    day_name = date_obj.strftime("%A").lower()
                    
                    if day_name in [day.lower() for day in weekly_days]:
                        filtered_habits.append(habit)
                        
            elif period == "specific_dates":
                specific_dates = habit.get("specific_dates", [])
                if date in specific_dates:
                    filtered_habits.append(habit)
        
        return filtered_habits
        
    except Exception as e:
        print(f"Error filtering habits by date {date}: {e}")
        return habits  # Return all habits if error occurs

async def _generate_habit_schedule_for_habit(habit_record: Dict[str, Any]) -> bool:
    """Generate schedule dates for a habit based on its period and frequency."""
    try:
        habit_id = habit_record.get("habit_id")
        user_id = habit_record.get("user_id")
        period = habit_record.get("period")
        
        if not all([habit_id, user_id, period]):
            print(f"Missing required fields for schedule generation: {habit_record}")
            return False
        
        # Calculate schedule dates based on period type
        schedule_dates = []
        start_date = datetime.now().date()
        
        if period == "daily":
            # Generate next 90 days
            for i in range(90):
                date = start_date + timedelta(days=i)
                schedule_dates.append(date.strftime("%Y-%m-%d"))
                
        elif period == "weekly":
            weekly_days = habit_record.get("weekly_days", [])
            frequency = habit_record.get("frequency", "1x_week")
            
            if not weekly_days:
                print(f"Weekly habit {habit_id} missing weekly_days")
                return False
            
            # Generate dates for next 12 weeks
            current_date = start_date
            for week in range(12):
                week_start = current_date + timedelta(weeks=week)
                # Find the start of the week (Monday)
                week_start = week_start - timedelta(days=week_start.weekday())
                
                for day_name in weekly_days:
                    day_offset = {
                        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                        "friday": 4, "saturday": 5, "sunday": 6
                    }.get(day_name.lower(), 0)
                    
                    scheduled_date = week_start + timedelta(days=day_offset)
                    if scheduled_date >= start_date:  # Only future dates
                        schedule_dates.append(scheduled_date.strftime("%Y-%m-%d"))
                        
        elif period == "specific_dates":
            specific_dates = habit_record.get("specific_dates", [])
            if specific_dates:
                schedule_dates = [date for date in specific_dates if date >= start_date.strftime("%Y-%m-%d")]
        
        # Store schedule in dates collection
        if schedule_dates:
            for date in schedule_dates:
                # Create or update date record with this habit scheduled
                existing_date = mongo_habit_manager.get_date_record(user_id, date)
                
                if existing_date:
                    # Add habit to existing scheduled habits
                    habits_scheduled = existing_date.get("habits_scheduled", [])
                    if habit_id not in habits_scheduled:
                        habits_scheduled.append(habit_id)
                        mongo_habit_manager.dates.update_one(
                            {"user_id": user_id, "date": date},
                            {"$set": {"habits_scheduled": habits_scheduled}}
                        )
                else:
                    # Create new date record
                    mongo_habit_manager.create_date_record(user_id, date, {
                        "habits_scheduled": [habit_id],
                        "habits_completed": []
                    })
            
            print(f"✅ Generated {len(schedule_dates)} schedule dates for habit {habit_id}")
            return True
        else:
            print(f"⚠️ No schedule dates generated for habit {habit_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating schedule for habit {habit_record.get('habit_id', 'unknown')}: {e}")
        return False

async def _get_current_habit_trends(
    habit_id: str, time_period: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate basic habit completion trends over time period."""
    # Determine date range
    if time_period == "weekly":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
    elif time_period == "monthly":
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
    # For custom, use provided dates
    
    # Get completion records for period
    completion_records = await _get_completion_records(habit_id, str(start_date), str(end_date))
    
    # Calculate metrics
    if not completion_records:
        return {
            "habit_id": habit_id,
            "average_score": 0.0,
            "trend_direction": "insufficient_data",
            "consistency_rate": 0.0,
            "current_streak": 0
        }
    
    scores = [r["completion_score"] for r in completion_records]
    max_scores = [r["max_possible_score"] for r in completion_records]
    
    # Calculate average score (normalized)
    normalized_scores = [s/m if m > 0 else 0 for s, m in zip(scores, max_scores)]
    average_score = sum(normalized_scores) / len(normalized_scores)
    
    # Calculate trend direction
    if len(scores) >= 3:
        recent_avg = sum(normalized_scores[-3:]) / 3
        earlier_avg = sum(normalized_scores[:-3]) / max(len(normalized_scores) - 3, 1)
        
        if recent_avg > earlier_avg + 0.1:
            trend_direction = "improving"
        elif recent_avg < earlier_avg - 0.1:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "insufficient_data"
    
    # Calculate consistency rate (percentage of days habit was attempted)
    attempted_days = len([s for s in scores if s > 0])
    total_days = len(scores)
    consistency_rate = attempted_days / total_days if total_days > 0 else 0
    
    return {
        "habit_id": habit_id,
        "average_score": round(average_score, 3),
        "trend_direction": trend_direction,
        "consistency_rate": round(consistency_rate, 3)
    }

async def _get_flexible_habits_for_date(user_id: str, date: str) -> List[Dict[str, Any]]:
    """Get habits without fixed timing for a specific date."""
    try:
        # Get date record to see what habits are scheduled
        date_record = mongo_habit_manager.get_date_record(user_id, date)
        if not date_record:
            return []
        
        scheduled_habit_ids = date_record.get("habits_scheduled", [])
        if not scheduled_habit_ids:
            return []
        
        # Get habit details for scheduled habits that have flexible timing
        flexible_habits = []
        for habit_id in scheduled_habit_ids:
            habit = mongo_habit_manager.get_micro_habit(habit_id)
            if habit and not habit.get("daily_timing"):  # No fixed timing = flexible
                flexible_habits.append(habit)
        
        return flexible_habits
        
    except Exception as e:
        print(f"Error getting flexible habits for {date}: {e}")
        return []

async def _get_user_active_habits(user_id: str) -> List[Dict[str, Any]]:
    """Get all active habits for a user."""
    return mongo_habit_manager.get_user_micro_habits(user_id, "active")

async def _get_habit_by_id(habit_id: str) -> Optional[Dict[str, Any]]:
    """Get habit details by ID."""
    return mongo_habit_manager.get_micro_habit(habit_id)

async def _get_epic_habit_by_id(epic_id: str) -> Optional[Dict[str, Any]]:
    """Get epic habit details by ID."""
    return mongo_habit_manager.get_epic_habit(epic_id)

async def _get_recent_completion_scores(habit_id: str, days: int) -> List[int]:
    """Get completion scores for recent days."""
    # Mock implementation
    return [2, 3, 1, 4, 2]

async def _get_completion_records(habit_id: str, start_date: Optional[str], end_date: Optional[str]) -> List[Dict[str, Any]]:
    """Get completion records for habit in date range."""
    return mongo_habit_manager.get_habit_completions(habit_id, start_date, end_date)

async def _get_current_habit_streak(habit_id: str) -> int:
    """Get current consecutive completion streak."""
    habit = mongo_habit_manager.get_micro_habit(habit_id)
    return habit.get("current_streak", 0) if habit else 0

async def _get_best_habit_streak(habit_id: str) -> int:
    """Get best (longest) consecutive completion streak achieved."""
    habit = mongo_habit_manager.get_micro_habit(habit_id)
    return habit.get("best_streak", 0) if habit else 0

async def _get_all_user_completions(user_id: str, time_period: str) -> List[Dict[str, Any]]:
    """Get all habit completions for user in time period."""
    # Calculate date range based on time period
    end_date = datetime.now().date()
    if time_period == "weekly":
        start_date = end_date - timedelta(days=7)
    elif time_period == "monthly":
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=30)  # Default to monthly
    
    return mongo_habit_manager.get_user_completions(user_id, str(start_date), str(end_date))

async def _get_mood_records(user_id: str, time_period: str) -> List[Dict[str, Any]]:
    """Get mood records for user in time period."""
    # Calculate date range based on time period
    end_date = datetime.now().date()
    if time_period == "weekly":
        start_date = end_date - timedelta(days=7)
    elif time_period == "monthly":
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=30)  # Default to monthly
    
    return mongo_habit_manager.get_mood_records(user_id, str(start_date), str(end_date))

async def _get_mood_based_recommendations(mood_score: int, is_crisis: bool, is_depressed: bool) -> List[str]:
    """Get habit recommendations based on mood state."""
    recommendations = []
    
    if is_crisis:
        recommendations = [
            "Focus on breathing exercises",
            "Take a short walk outside", 
            "Call someone you trust",
            "Practice grounding techniques"
        ]
    elif is_depressed:
        recommendations = [
            "Start with one small habit",
            "Focus on self-care routines",
            "Gentle movement or stretching",
            "Maintain basic hygiene habits"
        ]
    elif mood_score <= 3:
        recommendations = [
            "Keep habits simple today",
            "Focus on foundational habits",
            "Practice self-compassion",
            "Consider rest and recovery"
        ]
    elif mood_score >= 8:
        recommendations = [
            "Great day for challenging habits",
            "Consider starting new routines",
            "Push comfort zones safely",
            "Build momentum for tomorrow"
        ]
    else:
        recommendations = [
            "Stick to your regular routine",
            "Balance effort with rest",
            "Focus on consistency",
            "Listen to your energy levels"
        ]
    
    return recommendations 

# =============================================================================
# NEW BASIC OPERATIONS UTILS
# =============================================================================

async def _modify_habit_parameters(
    habit_id: str, timing_type: Optional[str] = None, daily_timing: Optional[str] = None,
    start_time: Optional[str] = None, end_time: Optional[str] = None,
    difficulty_level: Optional[str] = None, intrinsic_score: Optional[int] = None
) -> Dict[str, Any]:
    """Modify habit timing, difficulty, and importance parameters."""
    try:
        # Get current habit
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        # Validate timing parameters
        if timing_type == "time_range" and (not start_time or not end_time):
            return {"success": False, "error": "start_time and end_time required for time_range timing"}
        
        if timing_type == "specific_time" and not daily_timing:
            return {"success": False, "error": "daily_timing required for specific_time timing"}
        
        # Build update document
        update_data = {}
        if timing_type is not None:
            update_data["timing_type"] = timing_type
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
        
        update_data["last_modified"] = datetime.now().isoformat()
        
        # Update in database
        result = mongo_habit_manager.update_habit_parameters(habit_id, update_data)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Habit parameters updated successfully",
                "modified_fields": list(update_data.keys()),
                "habit_id": habit_id
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to update habit")}
            
    except Exception as e:
        return {"success": False, "error": f"Error modifying habit parameters: {str(e)}"}

async def _pause_resume_habit(
    habit_id: str, action: str, reason: Optional[str] = None, pause_until: Optional[str] = None
) -> Dict[str, Any]:
    """Pause or resume a habit with optional temporary pause until date."""
    try:
        # Get current habit
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        current_status = habit.get("status", "active")
        
        if action == "pause":
            if current_status == "paused":
                return {"success": False, "error": "Habit is already paused"}
            
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

async def _get_habit_insights_from_notes(habit_id: str, days: int = 30) -> Dict[str, Any]:
    """Analyze habit notes to provide insights about patterns and triggers."""
    try:
        # Get recent notes
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        notes_result = await _get_habit_notes(habit_id, start_date, end_date)
        if not notes_result["success"]:
            return notes_result
        
        notes = notes_result["notes"]
        
        if not notes:
            return {
                "success": True,
                "insights": {
                    "total_notes": 0,
                    "message": "No notes found for analysis period"
                }
            }
        
        # Basic Statistical Analysis
        note_type_counts = {}
        tag_counts = {}
        mood_scores = []
        
        for note in notes:
            # Count note types
            note_type = note.get("note_type", "general")
            note_type_counts[note_type] = note_type_counts.get(note_type, 0) + 1
            
            # Count tags
            for tag in note.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Collect mood scores
            if note.get("mood_context"):
                mood_scores.append(note["mood_context"])
        
        # Prepare content for LLM analysis
        notes_content = []
        for note in notes:
            note_text = f"Date: {note.get('date', 'Unknown')}\n"
            note_text += f"Type: {note.get('note_type', 'general')}\n"
            note_text += f"Content: {note.get('content', '')}\n"
            if note.get('mood_context'):
                note_text += f"Mood: {note.get('mood_context')}/10\n"
            if note.get('tags'):
                note_text += f"Tags: {', '.join(note.get('tags', []))}\n"
            note_text += "---"
            notes_content.append(note_text)
        
        # Enhanced LLM Analysis
        llm_insights = await _analyze_notes_with_llm(notes_content, habit_id, days)
        
        # Calculate basic insights
        basic_insights = {
            "total_notes": len(notes),
            "analysis_period_days": days,
            "note_type_breakdown": note_type_counts,
            "common_tags": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            "mood_analysis": {
                "average_mood": round(sum(mood_scores) / len(mood_scores), 1) if mood_scores else None,
                "mood_range": {"min": min(mood_scores), "max": max(mood_scores)} if mood_scores else None,
                "total_mood_entries": len(mood_scores)
            }
        }
        
        # Combine basic stats with LLM insights
        combined_insights = {
            **basic_insights,
            "llm_analysis": llm_insights
        }
        
        return {
            "success": True,
            "insights": combined_insights,
            "habit_id": habit_id
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error analyzing habit notes: {str(e)}"}


async def _analyze_notes_with_llm(notes_content: List[str], habit_id: str, days: int) -> Dict[str, Any]:
    """Use LLM to analyze habit notes for deeper insights."""
    try:
        # Get habit info for context
        habit = await _get_habit_by_id(habit_id)
        habit_name = habit.get("name", "Unknown") if habit else "Unknown"
        habit_type = habit.get("habit_type", "formation") if habit else "formation"
        
        # Prepare the prompt for LLM analysis
        notes_text = "\n".join(notes_content)
        
        analysis_prompt = f"""Analyze habit notes for "{habit_name}" ({habit_type} habit) over {days} days. Respond with valid JSON only.

NOTES:
{notes_text}

Analyze for patterns, triggers, mood correlations, and progress. Return JSON with:
{{
  "patterns": ["pattern1", "pattern2"],
  "triggers": {{"positive": ["trigger1"], "negative": ["trigger2"]}},
  "mood_insights": "mood correlation description",
  "key_learnings": ["learning1", "learning2"],
  "recommendations": ["action1", "action2"],
  "progress_assessment": "improvement/decline/stable description",
  "confidence_score": 7
}}

Focus on actionable insights from the note content."""
        
        # Import Hugging Face client if available
        try:
            from huggingface_hub import AsyncInferenceClient
            import json
            
            # Use Hugging Face Inference API
            hf_token = os.getenv("HUGGINGFACE_API_TOKEN", os.getenv("HF_TOKEN"))
            model_name = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
            
            if not hf_token:
                return {
                    "error": "Hugging Face API token not found",
                    "suggestion": "Set HUGGINGFACE_API_TOKEN or HF_TOKEN environment variable"
                }
            
            client = AsyncInferenceClient(token=hf_token)
            
            # Format prompt for chat completion
            messages = [
                {"role": "system", "content": "You are an expert habit coach and behavioral analyst. Always respond with valid JSON only, no additional text."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # Call Hugging Face model
            response = await client.chat_completion(
                messages=messages,
                model=model_name,
                max_tokens=1200,
                temperature=0.3,
                top_p=0.9
            )
            
            # Extract response content
            llm_response = response.choices[0].message.content.strip()
            
            # Clean response - remove any markdown formatting
            if llm_response.startswith("```json"):
                llm_response = llm_response[7:]
            if llm_response.endswith("```"):
                llm_response = llm_response[:-3]
            llm_response = llm_response.strip()
            
            # Try to parse as JSON
            try:
                llm_insights = json.loads(llm_response)
            except json.JSONDecodeError:
                # Try to extract JSON from response if it contains other text
                import re
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    try:
                        llm_insights = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        llm_insights = {
                            "error": "Could not parse JSON from LLM response",
                            "raw_response": llm_response[:500] + "..." if len(llm_response) > 500 else llm_response
                        }
                else:
                    llm_insights = {
                        "error": "LLM response was not valid JSON",
                        "raw_response": llm_response[:500] + "..." if len(llm_response) > 500 else llm_response
                    }
            
            return llm_insights
            
        except ImportError:
            return {
                "error": "LLM analysis not available - Hugging Face client not installed",
                "suggestion": "Install huggingface-hub package for enhanced insights"
            }
        except Exception as llm_error:
            error_msg = str(llm_error)
            
            # Provide specific error messages for common issues
            if "rate limit" in error_msg.lower():
                return {
                    "error": "Hugging Face API rate limit exceeded",
                    "suggestion": "Try again in a few minutes or upgrade your HF plan",
                    "fallback": "Using basic statistical analysis only"
                }
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                return {
                    "error": "Invalid Hugging Face API token",
                    "suggestion": "Check your HUGGINGFACE_API_TOKEN environment variable",
                    "fallback": "Using basic statistical analysis only"
                }
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                return {
                    "error": f"Model {model_name} not found or not accessible",
                    "suggestion": "Try a different model in HF_MODEL environment variable",
                    "fallback": "Using basic statistical analysis only"
                }
            else:
                return {
                    "error": f"LLM analysis failed: {error_msg}",
                    "fallback": "Using basic statistical analysis only"
                }
            
    except Exception as e:
        return {
            "error": f"Analysis preparation failed: {str(e)}",
            "fallback": "Using basic statistical analysis only"
        }