from fastapi import APIRouter, HTTPException
from langchain_core.tools import tool
# Import core operations and schemas
from utils.habit_core import (
    _create_micro_habit_record,
    _create_epic_habit_record,
    _assign_micro_to_epic_record,
    _modify_habit_parameters,
    _pause_resume_habit,
    _add_habit_note,
    _get_habit_notes,
    _get_user_habit_limits,
    check_habit_creation_limits,
    CreateMicroHabitInput,
    CreateEpicHabitInput,
    AssignMicroToEpicInput,
    ModifyHabitParametersInput,
    PauseResumeHabitInput,
    AddHabitNoteInput,
    GetHabitNotesInput,
)

# Import execution operations and schemas
from utils.habit_execution import (
    _plan_flexible_habits_timing,
    _get_daily_habit_list_organized,
    _track_habit_completion_record,
    PlanFlexibleHabitsInput,
    GetDailyHabitListInput,
    TrackHabitCompletionInput,
)

# Import analytics operations and schemas
from utils.habit_analytics import (
    _calculate_basic_habit_trends,
    _calculate_basic_epic_progress,
    _get_habit_insights_from_notes,
    CalculateHabitTrendsInput,
    GenerateEpicProgressInput,
)
from typing import List, Dict, Any, Optional

router = APIRouter(tags=["habits"])

# =============================================================================
# DUAL-PURPOSE FUNCTIONS (FastAPI + MCP Tools)
# =============================================================================

@router.post("/create_micro_habit",
        operation_id="create_micro_habit",
        description='''
        Create a new micro habit with scheduling, scoring, and validation.
        Args:
            name: str (habit name)
            description: str (detailed habit description)
            category: str (habit category)
            period: str (daily, weekly, or specific_dates)
            intrinsic_score: int (importance score 1-4, used as weight)
            habit_type: str (formation or breaking)
            frequency: Optional[str] (for weekly habits)
            weekly_days: Optional[List[str]] (specific days for weekly habits)
            specific_dates: Optional[List[str]] (dates for specific_dates period)
            daily_timing: Optional[str] (fixed timing or None for flexible)
            is_meditation: bool (whether habit requires meditation audio asset)
            meditation_audio_id: Optional[str] (required if is_meditation=True)
        Returns:
            dict with success, habit_id, schedule_generated, validation_errors
        ''',
        response_description="Creation result with habit_id and validation status")
@tool("create_micro_habit", args_schema=CreateMicroHabitInput)
async def create_micro_habit(
    user_id: str, name: str, description: str, category: str, period: str, intrinsic_score: int, 
    habit_type: str, frequency: Optional[str] = None, weekly_days: Optional[List[str]] = None,
    specific_dates: Optional[List[str]] = None, daily_timing: Optional[str] = None,
    is_meditation: bool = False, meditation_audio_id: Optional[str] = None
):
    """
    Tool Purpose: Create a new micro habit with scheduling, scoring, and validation.
    
    Args:
    - user_id (str): User identifier
    - name (str): Habit name
    - description (str): Detailed habit description
    - category (str): Habit category (health, productivity, social, financial, etc.)
    - period (str): daily, weekly, or specific_dates
    - intrinsic_score (int): Importance score 1-4, used as weight
    - habit_type (str): formation or breaking
    - frequency (Optional[str]): For weekly habits (3x_week, every_2_days, etc.)
    - weekly_days (Optional[List[str]]): Specific days for weekly habits
    - specific_dates (Optional[List[str]]): Dates for specific_dates period
    - daily_timing (Optional[str]): Fixed timing or None for flexible
    - is_meditation (bool): Whether habit requires meditation audio asset
    - meditation_audio_id (Optional[str]): Required if is_meditation=True
    
    Returns:
    - Dict with success, habit_id, schedule_generated, validation_errors
    """
    return await _create_micro_habit_record(
        user_id, name, description, category, period, intrinsic_score, habit_type,
        frequency, weekly_days, specific_dates, daily_timing, is_meditation, meditation_audio_id
    )

@router.post("/create_epic_habit",
        operation_id="create_epic_habit",
        description='''
        Create an epic habit (overarching goal) that can contain multiple micro habits.
        Args:
            name: str (epic habit name)
            description: str (detailed description)
            category: str (category)
            priority: int (overall priority 1-10)
            target_completion_date: str (target date YYYY-MM-DD)
            success_criteria: List[str] (measurable outcomes)
        Returns:
            dict with success, habit_id, schedule_generated
        ''',
        response_description="Creation result with epic_habit_id")
@tool("create_epic_habit", args_schema=CreateEpicHabitInput)
async def create_epic_habit(
    user_id: str, name: str, description: str, category: str, priority: int,
    target_completion_date: str, success_criteria: List[str]
):
    """
    Tool Purpose: Create an epic habit (overarching goal) that can contain multiple micro habits.
    
    Args:
    - user_id (str): User identifier
    - name (str): Epic habit name like 'Achieve 15% body fat'
    - description (str): Detailed description of the epic goal
    - category (str): Category (health, productivity, mental_health, etc.)
    - priority (int): Overall priority 1-10 across all epic habits
    - target_completion_date (str): Target date in YYYY-MM-DD format
    - success_criteria (List[str]): Measurable outcomes for success
    
    Returns:
    - Dict with success, habit_id, schedule_generated
    """
    return await _create_epic_habit_record(user_id, name, description, category, priority, target_completion_date, success_criteria)

@router.post("/assign_micro_to_epic",
        operation_id="assign_micro_to_epic",
        description='''
        Assign an existing micro habit to an epic habit with specified priority.
        Args:
            micro_habit_id: str (ID of micro habit to assign)
            epic_habit_id: str (ID of epic habit to assign to)
            priority_within_epic: str ("high" or "low" priority within epic)
        Returns:
            dict with success, assignment_id, epic_progress_updated
        ''',
        response_description="Assignment result with assignment details")
@tool("assign_micro_to_epic", args_schema=AssignMicroToEpicInput)
async def assign_micro_to_epic(micro_habit_id: str, epic_habit_id: str, priority_within_epic: str):
    """
    Tool Purpose: Assign an existing micro habit to an epic habit with specified priority.
    
    Args:
    - micro_habit_id (str): ID of micro habit to assign
    - epic_habit_id (str): ID of epic habit to assign to
    - priority_within_epic (str): "high" or "low" priority within this epic
    
    Returns:
    - Dict with success, assignment_id, epic_progress_updated, assignment_details
    """
    return await _assign_micro_to_epic_record(micro_habit_id, epic_habit_id, priority_within_epic)

@router.post("/plan_flexible_habits",
        operation_id="plan_flexible_habits",
        description='''
        Plan timing for flexible habits based on available slots and energy.
        Args:
            user_id: str (user identifier)
            date: str (date to plan for YYYY-MM-DD)
            available_time_slots: List[str] (available timing options)
            energy_level: int (current energy level 1-10, default 5)
        Returns:
            dict with planned_habits, timing_assignments, optimization_notes
        ''',
        response_description="Timing plan with assignments and optimization notes")
@tool("plan_flexible_habits", args_schema=PlanFlexibleHabitsInput)
async def plan_flexible_habits(
    user_id: str, date: str, available_time_slots: List[str], energy_level: int = 5
):
    """
    Tool Purpose: Plan timing for flexible habits based on available slots and energy.
    
    Args:
    - user_id (str): User identifier
    - date (str): Date to plan for in YYYY-MM-DD format
    - available_time_slots (List[str]): Available timing options
    - energy_level (int): Current energy level 1-10 (default 5)
    
    Returns:
    - Dict with planned_habits, timing_assignments, optimization_notes
    """
    return await _plan_flexible_habits_timing(user_id, date, available_time_slots, energy_level)

@router.get("/daily_habit_list/{user_id}/{date}",
        operation_id="get_daily_habit_list",
        description='''
        Retrieve all habits scheduled for a specific date, separated by timing type.
        Args:
            user_id: str (user identifier)
            date: str (date in YYYY-MM-DD format)
        Returns:
            dict with date, fixed_timing_habits, flexible_habits, total_habits
        ''',
        response_description="Habits organized by fixed vs flexible timing")
@tool("get_daily_habit_list", args_schema=GetDailyHabitListInput)
async def get_daily_habit_list(user_id: str, date: str):
    """
    Tool Purpose: Retrieve all habits scheduled for a specific date, separated by timing type.
    
    Args:
    - user_id (str): User identifier
    - date (str): Date in YYYY-MM-DD format
    
    Returns:
    - Dict with date, fixed_timing_habits, flexible_habits, total_habits
    """
    return await _get_daily_habit_list_organized(user_id, date)

@router.post("/track_habit_completion",
        operation_id="track_habit_completion",
        description='''
        Record habit completion score for one habit on one day.
        Args:
            user_id: str (user identifier)
            habit_id: str (habit identifier)
            date: str (date in YYYY-MM-DD format)
            completion_score: int (0 or 1-4, up to habit's intrinsic_score)
            actual_timing: Optional[str] (when habit actually happened)
            notes: Optional[str] (optional completion notes)
        Returns:
            dict with success, completion_id, streak_updated, trend_impact
        ''',
        response_description="Completion record with streak and trend updates")
@tool("track_habit_completion", args_schema=TrackHabitCompletionInput)
async def track_habit_completion(
    user_id: str, habit_id: str, date: str, completion_score: int,
    actual_timing: Optional[str] = None, notes: Optional[str] = None
):
    """
    Tool Purpose: Record habit completion score for one habit on one day.
    
    Args:
    - user_id (str): User identifier
    - habit_id (str): Habit identifier
    - date (str): Date in YYYY-MM-DD format
    - completion_score (int): 0 or 1-4 (up to habit's intrinsic_score)
    - actual_timing (Optional[str]): When habit actually happened
    - notes (Optional[str]): Optional completion notes
    
    Returns:
    - Dict with success, completion_id, streak_updated, trend_impact, score_percentage
    """
    return await _track_habit_completion_record(user_id, habit_id, date, completion_score, actual_timing, notes)

@router.get("/habit_trends/{habit_id}",
        operation_id="calculate_habit_trends",
        description='''
        Analyze habit completion score trends over specified time period.
        Args:
            habit_id: str (habit identifier)
            time_period: str (weekly, monthly, or custom)
            start_date: Optional[str] (start date for custom period)
            end_date: Optional[str] (end date for custom period)
        Returns:
            dict with average_score, trend_direction, consistency_rate, current_streak
        ''',
        response_description="Trend analysis with scores, direction, and consistency")
@tool("calculate_habit_trends", args_schema=CalculateHabitTrendsInput)
async def calculate_habit_trends(
    habit_id: str, time_period: str, start_date: Optional[str] = None, end_date: Optional[str] = None
):
    """
    Tool Purpose: Analyze habit completion score trends over specified time period.
    
    Args:
    - habit_id (str): Habit identifier
    - time_period (str): weekly, monthly, or custom
    - start_date (Optional[str]): Start date for custom period (YYYY-MM-DD)
    - end_date (Optional[str]): End date for custom period (YYYY-MM-DD)
    
    Returns:
    - Dict with average_score, trend_direction, consistency_rate, current_streak
    """
    return await _calculate_basic_habit_trends(habit_id, time_period, start_date, end_date)

@router.get("/epic_progress/{epic_habit_id}",
        operation_id="generate_epic_progress",
        description='''
        Calculate epic habit progress using intrinsic scores as weights for micro habits.
        Args:
            epic_habit_id: str (epic habit identifier)
            time_period: str (weekly, monthly, or all_time)
        Returns:
            dict with overall_progress, micro_habit_progress, weighted_calculation
        ''',
        response_description="Epic progress with weighted calculation details")
@tool("calculate_epic_progress", args_schema=GenerateEpicProgressInput)
async def generate_epic_progress(epic_habit_id: str, time_period: str):
    """
    Tool Purpose: Calculate epic habit progress using intrinsic scores as weights for micro habits.
    
    Args:
    - epic_habit_id (str): Epic habit identifier
    - time_period (str): weekly, monthly, or all_time
    
    Returns:
    - Dict with overall_progress, micro_habit_progress, weighted_calculation
    """
    return await _calculate_basic_epic_progress(epic_habit_id, time_period)

# =============================================================================
# PREMIUM TIER INFORMATION ENDPOINTS
# =============================================================================

@router.get("/user_limits/{user_id}",
        operation_id="_get_user_habit_limits",
        description='''
        Get habit limits and capabilities based on user's subscription tier.
        Returns limits for habit creation, analytics periods, and feature access.
        ''',
        response_description="User's habit limits and feature access")
async def get_user_limits(user_id: str):
    """
    Get comprehensive habit limits and capabilities for the user's subscription tier.
    
    Args:
    - user_id (str): User identifier
    
    Returns:
    - Dict with max_active_habits, analytics capabilities, feature access, etc.
    """
    return _get_user_habit_limits(user_id)

@router.get("/creation_check/{user_id}",
        operation_id="check_habit_creation_availability", 
        description='''
        Check if user can create more habits of specified type based on their tier limits.
        Useful for frontend to show/hide creation buttons and display upgrade messages.
        ''',
        response_description="Creation availability with upgrade messages if needed")
async def check_creation_limits(user_id: str, habit_type: str = "micro"):
    """Check if user can create more habits based on tier limits"""
    return check_habit_creation_limits(user_id, habit_type)

# =============================================================================
# NEW BASIC OPERATIONS ENDPOINTS
# =============================================================================

@router.patch("/modify_habit_parameters",
        operation_id="modify_habit_parameters",
        description='''
        Modify habit timing, difficulty, and importance parameters.
        Args:
            habit_id: str (habit identifier)
            timing_type: Optional[str] (specific_time, entire_day, or time_range)
            daily_timing: Optional[str] (fixed time like 07:00 or after_coffee)
            start_time: Optional[str] (start time for time_range habits HH:MM)
            end_time: Optional[str] (end time for time_range habits HH:MM)
            difficulty_level: Optional[str] (easy, medium, hard)
            intrinsic_score: Optional[int] (importance score 1-4)
        Returns:
            dict with success, modified_fields, habit_id
        ''',
        response_description="Parameter modification result with updated fields")
@tool("modify_habit_parameters", args_schema=ModifyHabitParametersInput)
async def modify_habit_parameters(
    habit_id: str, timing_type: Optional[str] = None, daily_timing: Optional[str] = None,
    start_time: Optional[str] = None, end_time: Optional[str] = None,
    difficulty_level: Optional[str] = None, intrinsic_score: Optional[int] = None
):
    """
    Tool Purpose: Modify habit timing, difficulty, and importance parameters.
    
    Args:
    - habit_id (str): Habit identifier
    - timing_type (Optional[str]): specific_time, entire_day, or time_range
    - daily_timing (Optional[str]): Fixed time like 07:00 or after_coffee
    - start_time (Optional[str]): Start time for time_range habits (HH:MM format)
    - end_time (Optional[str]): End time for time_range habits (HH:MM format)
    - difficulty_level (Optional[str]): Difficulty level (easy, medium, hard)
    - intrinsic_score (Optional[int]): Importance score 1-4
    
    Returns:
    - Dict with success, modified_fields, habit_id
    """
    return await _modify_habit_parameters(
        habit_id, timing_type, daily_timing, start_time, end_time, difficulty_level, intrinsic_score
    )

@router.patch("/pause_resume_habit",
        operation_id="pause_resume_habit",
        description='''
        Pause or resume a habit with optional temporary pause until date.
        Args:
            habit_id: str (habit identifier)
            action: str (pause or resume)
            reason: Optional[str] (reason for pausing/resuming)
            pause_until: Optional[str] (resume date for temporary pause YYYY-MM-DD)
        Returns:
            dict with success, action, habit_id, new_status
        ''',
        response_description="Pause/resume result with new habit status")
@tool("pause_resume_habit", args_schema=PauseResumeHabitInput)
async def pause_resume_habit(
    habit_id: str, action: str, reason: Optional[str] = None, pause_until: Optional[str] = None
):
    """
    Tool Purpose: Pause or resume a habit with optional temporary pause until date.
    
    Args:
    - habit_id (str): Habit identifier
    - action (str): "pause" or "resume"
    - reason (Optional[str]): Reason for pausing/resuming
    - pause_until (Optional[str]): Resume date for temporary pause (YYYY-MM-DD)
    
    Returns:
    - Dict with success, action, habit_id, new_status
    """
    return await _pause_resume_habit(habit_id, action, reason, pause_until)

@router.post("/add_habit_note",
        operation_id="add_habit_note",
        description='''
        Add a note/diary entry for a habit on a specific date.
        Args:
            habit_id: str (habit identifier)
            date: str (date for the note YYYY-MM-DD)
            note_type: str (trigger, difficulty, learning, reflection, or general)
            content: str (note content - thoughts, learnings, triggers faced, etc.)
            mood_context: Optional[int] (mood score at time of note 1-10)
            tags: Optional[List[str]] (tags for categorizing notes)
        Returns:
            dict with success, note_id, habit_id, date, note_type
        ''',
        response_description="Note creation result with note details")
@tool("add_habit_note", args_schema=AddHabitNoteInput)
async def add_habit_note(
    habit_id: str, date: str, note_type: str, content: str,
    mood_context: Optional[int] = None, tags: Optional[List[str]] = None
):
    """
    Tool Purpose: Add a note/diary entry for a habit on a specific date.
    
    Args:
    - habit_id (str): Habit identifier
    - date (str): Date for the note in YYYY-MM-DD format
    - note_type (str): Type of note (trigger, difficulty, learning, reflection, or general)
    - content (str): Note content - thoughts, learnings, triggers faced, difficulties, etc.
    - mood_context (Optional[int]): Mood score at time of note (1-10)
    - tags (Optional[List[str]]): Tags for categorizing notes
    
    Returns:
    - Dict with success, note_id, habit_id, date, note_type
    """
    return await _add_habit_note(habit_id, date, note_type, content, mood_context, tags)

@router.get("/habit_notes/{habit_id}",
        operation_id="get_habit_notes",
        description='''
        Get habit notes with optional filtering by date range and note type.
        Args:
            habit_id: str (habit identifier)
            start_date: Optional[str] (start date for notes query YYYY-MM-DD)
            end_date: Optional[str] (end date for notes query YYYY-MM-DD)
            note_type: Optional[str] (filter by note type)
            limit: Optional[int] (maximum number of notes to return, default 50)
        Returns:
            dict with success, notes, total_count, habit_id, filters_applied
        ''',
        response_description="Habit notes with filtering details")
@tool("get_habit_notes", args_schema=GetHabitNotesInput)
async def get_habit_notes(
    habit_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
    note_type: Optional[str] = None, limit: Optional[int] = 50
):
    """
    Tool Purpose: Get habit notes with optional filtering by date range and note type.
    
    Args:
    - habit_id (str): Habit identifier
    - start_date (Optional[str]): Start date for notes query (YYYY-MM-DD)
    - end_date (Optional[str]): End date for notes query (YYYY-MM-DD)
    - note_type (Optional[str]): Filter by note type (trigger, difficulty, learning, etc.)
    - limit (Optional[int]): Maximum number of notes to return (default 50)
    
    Returns:
    - Dict with success, notes, total_count, habit_id, filters_applied
    """
    return await _get_habit_notes(habit_id, start_date, end_date, note_type, limit)

@router.get("/habit_insights/{habit_id}",
        operation_id="get_habit_insights_from_notes",
        description='''
        Analyze habit notes to provide insights about patterns and triggers.
        Args:
            habit_id: str (habit identifier)
            days: int (number of days to analyze, default 30)
        Returns:
            dict with insights including note type breakdown, common tags, mood analysis
        ''',
        response_description="Habit insights and patterns from notes analysis")
@tool("get_habit_insights_from_notes")
async def get_habit_insights_from_notes(habit_id: str, days: int = 30):
    """
    Tool Purpose: Analyze habit notes to provide insights about patterns and triggers.
    
    Args:
    - habit_id (str): Habit identifier
    - days (int): Number of days to analyze (default 30)
    
    Returns:
    - Dict with insights including note type breakdown, common tags, mood analysis
    """
    return await _get_habit_insights_from_notes(habit_id, days) 