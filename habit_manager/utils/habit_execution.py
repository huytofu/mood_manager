"""
Habit Execution Operations
==========================
Functions for daily habit execution, scheduling, tracking, and completion.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel, Field, field_validator
from database.mongo_habit_manager import mongo_habit_manager
from .habit_core import _get_habit_by_id, _get_user_active_habits

# =============================================================================
# EXECUTION SCHEMAS
# =============================================================================

class PlanFlexibleHabitsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date to plan for in YYYY-MM-DD format")
    available_time_slots: List[str] = Field(..., description="Available timing options")
    energy_level: Optional[int] = Field(default=5, description="Current energy level 1-10")

class GetDailyHabitListInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")

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
            # Bad habits: only 0 (relapsed) or full score (stayed clean) are valid
            if not (v == 0 or v >= 1):
                raise ValueError("For breaking habits, completion_score must be 0 (relapsed) or positive (stayed clean)")
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

# =============================================================================
# DAILY PLANNING AND SCHEDULING
# =============================================================================

async def _plan_flexible_habits_timing(
    user_id: str, date: str, available_time_slots: List[str], energy_level: int = 5
) -> Dict[str, Any]:
    """Plan timing for flexible habits based on available time slots and energy."""
    try:
        # Validate date format
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Get flexible habits for the user that need scheduling
        flexible_habits = await _get_flexible_habits_for_date(user_id, date)
        
        if not flexible_habits:
            return {
                "success": True,
                "message": "No flexible habits found for planning",
                "planned_habits": []
            }
        
        planned_habits = []
        
        # Sort habits by intrinsic score (priority) and energy requirements
        habits_sorted = sorted(flexible_habits, key=lambda h: (
            h.get("intrinsic_score", 1),
            _get_energy_requirement_numeric(h)
        ), reverse=True)
        
        # Plan timing for each habit
        for habit in habits_sorted:
            habit_id = habit["habit_id"]
            timing_type = habit.get("timing_type", "specific_time")
            
            if timing_type == "entire_day":
                # Entire day habits don't need specific timing
                planned_habits.append({
                    "habit_id": habit_id,
                    "name": habit["name"],
                    "planned_timing": "entire_day",
                    "timing_type": "entire_day",
                    "energy_requirement": _get_energy_requirement(habit)
                })
            elif timing_type == "time_range":
                # Find best slot within the range
                start_time = habit.get("start_time")
                end_time = habit.get("end_time")
                if start_time and end_time:
                    best_slot = _find_best_slot_in_range(available_time_slots, start_time, end_time, energy_level)
                    if best_slot:
                        planned_habits.append({
                            "habit_id": habit_id,
                            "name": habit["name"],
                            "planned_timing": best_slot,
                            "timing_type": "time_range",
                            "time_range": f"{start_time}-{end_time}",
                            "energy_requirement": _get_energy_requirement(habit)
                        })
                        # Remove used slot
                        if best_slot in available_time_slots:
                            available_time_slots.remove(best_slot)
            elif timing_type == "specific_time":
                # Use fixed timing if set, otherwise assign from available slots
                daily_timing = habit.get("daily_timing")
                if daily_timing and daily_timing != "flexible":
                    planned_habits.append({
                        "habit_id": habit_id,
                        "name": habit["name"],
                        "planned_timing": daily_timing,
                        "timing_type": "specific_time",
                        "energy_requirement": _get_energy_requirement(habit)
                    })
                else:
                    # Assign from available slots based on energy matching
                    energy_req = _get_energy_requirement_numeric(habit)
                    suitable_slots = [slot for slot in available_time_slots 
                                    if _is_slot_suitable_for_energy(slot, energy_req, energy_level)]
                    
                    if suitable_slots:
                        best_slot = suitable_slots[0]  # Take first suitable slot
                        planned_habits.append({
                            "habit_id": habit_id,
                            "name": habit["name"],
                            "planned_timing": best_slot,
                            "timing_type": "specific_time",
                            "energy_requirement": _get_energy_requirement(habit)
                        })
                        available_time_slots.remove(best_slot)
        
        return {
            "success": True,
            "date": date,
            "user_id": user_id,
            "planned_habits": planned_habits,
            "total_planned": len(planned_habits),
            "remaining_slots": available_time_slots
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error planning flexible habits: {str(e)}"}

async def _get_daily_habit_list_organized(user_id: str, date: str) -> Dict[str, Any]:
    """Get organized list of habits for a specific date."""
    try:
        # Validate date format
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Get all active habits for user
        all_habits = await _get_user_active_habits(user_id)
        
        # Filter habits that should be scheduled for this date
        scheduled_habits = []
        for habit in all_habits:
            if await _generate_habit_schedule_for_habit(habit, date):
                scheduled_habits.append(habit)
        
        # Organize by timing type and priority
        organized_habits = {
            "specific_time": [],
            "time_range": [],
            "entire_day": [],
            "flexible": []
        }
        
        for habit in scheduled_habits:
            timing_type = habit.get("timing_type", "specific_time")
            daily_timing = habit.get("daily_timing")
            
            habit_info = {
                "habit_id": habit["habit_id"],
                "name": habit["name"],
                "description": habit.get("description", ""),
                "category": habit.get("category", "other"),
                "intrinsic_score": habit.get("intrinsic_score", 1),
                "difficulty_level": habit.get("difficulty_level", "easy"),
                "habit_type": habit.get("habit_type", "formation"),
                "timing_type": timing_type,
                "energy_requirement": _get_energy_requirement(habit),
                "is_meditation": habit.get("is_meditation", False)
            }
            
            if timing_type == "specific_time":
                if daily_timing and daily_timing != "flexible":
                    habit_info["scheduled_time"] = daily_timing
                    organized_habits["specific_time"].append(habit_info)
                else:
                    organized_habits["flexible"].append(habit_info)
            elif timing_type == "time_range":
                habit_info["time_range"] = f"{habit.get('start_time', 'Unknown')}-{habit.get('end_time', 'Unknown')}"
                organized_habits["time_range"].append(habit_info)
            elif timing_type == "entire_day":
                organized_habits["entire_day"].append(habit_info)
        
        # Sort each category by intrinsic score (priority)
        for category in organized_habits:
            organized_habits[category].sort(key=lambda h: h["intrinsic_score"], reverse=True)
        
        return {
            "success": True,
            "date": date,
            "user_id": user_id,
            "organized_habits": organized_habits,
            "total_habits": len(scheduled_habits),
            "summary": {
                "specific_time": len(organized_habits["specific_time"]),
                "time_range": len(organized_habits["time_range"]),
                "entire_day": len(organized_habits["entire_day"]),
                "flexible": len(organized_habits["flexible"])
            }
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error getting daily habit list: {str(e)}"}

# =============================================================================
# HABIT COMPLETION TRACKING
# =============================================================================

async def _track_habit_completion_record(
    user_id: str, habit_id: str, date: str, completion_score: int,
    actual_timing: Optional[str] = None, notes: Optional[str] = None
) -> Dict[str, Any]:
    """Track completion of a habit for a specific date."""
    try:
        # Validate habit exists
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        # Validate user owns the habit
        if habit.get("user_id") != user_id:
            return {"success": False, "error": "Habit does not belong to this user"}
        
        # Validate date format
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            if date_obj > datetime.now():
                return {"success": False, "error": "Cannot track completion for future dates"}
        except ValueError:
            return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        
        # Get habit details for validation
        habit_type = habit.get("habit_type", "formation")
        intrinsic_score = habit.get("intrinsic_score", 1)
        
        # Validate completion score
        if habit_type == "formation":
            if not (0 <= completion_score <= 4):
                return {"success": False, "error": "Formation habit completion score must be 0-4"}
        elif habit_type == "breaking":
            if completion_score not in [0, intrinsic_score]:
                return {"success": False, "error": f"Breaking habit completion score must be 0 (relapsed) or {intrinsic_score} (stayed clean)"}
        
        # Check if completion already exists for this date
        existing_completions = mongo_habit_manager.get_habit_completions(habit_id, date, date)
        if existing_completions:
            return {"success": False, "error": "Completion already recorded for this date. Use update instead."}
        
        # Prepare completion record
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
        
        # Record completion in database
        success = mongo_habit_manager.record_habit_completion(completion_record)
        
        if success:
            # Calculate trend impact
            trend_impact = await _calculate_trend_impact(habit_id, completion_score)
            
            # Update habit streak information
            is_completed = completion_score > 0
            mongo_habit_manager._update_habit_streak(habit_id, is_completed)
            
            return {
                "success": True,
                "message": f"Completion recorded successfully for {habit['name']}",
                "completion_data": {
                    "habit_id": habit_id,
                    "habit_name": habit["name"],
                    "date": date,
                    "completion_score": completion_score,
                    "max_score": 4 if habit_type == "formation" else intrinsic_score,
                    "percentage": (completion_score / (4 if habit_type == "formation" else intrinsic_score)) * 100,
                    "trend_impact": trend_impact,
                    "actual_timing": actual_timing
                }
            }
        else:
            return {"success": False, "error": "Failed to record completion in database"}
            
    except Exception as e:
        return {"success": False, "error": f"Error tracking completion: {str(e)}"}

# =============================================================================
# UTILITY FUNCTIONS FOR EXECUTION
# =============================================================================

def _get_energy_requirement(habit: Dict[str, Any]) -> str:
    """Get human-readable energy requirement for a habit."""
    difficulty = habit.get("difficulty_level", "easy")
    category = habit.get("category", "other")
    
    if difficulty == "hard":
        return "high"
    elif difficulty == "medium":
        return "medium"
    elif category in ["health", "productivity"]:
        return "medium"
    else:
        return "low"

def _get_energy_requirement_numeric(habit: Dict[str, Any]) -> int:
    """Get numeric energy requirement (1-10) for a habit."""
    energy_req = _get_energy_requirement(habit)
    energy_map = {"low": 3, "medium": 6, "high": 9}
    return energy_map.get(energy_req, 5)

def _find_best_slot_in_range(available_slots: List[str], start_time: str, end_time: str, energy_level: int) -> Optional[str]:
    """Find the best available time slot within a time range."""
    suitable_slots = []
    for slot in available_slots:
        if _is_time_in_range(slot, start_time, end_time):
            suitable_slots.append(slot)
    
    return suitable_slots[0] if suitable_slots else None

def _is_time_in_range(time_slot: str, start_time: str, end_time: str) -> bool:
    """Check if a time slot falls within a range."""
    try:
        slot_time = datetime.strptime(time_slot, "%H:%M").time()
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
        return start <= slot_time <= end
    except ValueError:
        return False

def _is_slot_suitable_for_energy(slot: str, habit_energy_req: int, user_energy_level: int) -> bool:
    """Check if a time slot is suitable for a habit based on energy requirements."""
    # Morning slots (6-11) are good for high energy habits
    # Afternoon slots (11-17) are good for medium energy habits  
    # Evening slots (17-22) are good for low energy habits
    try:
        slot_hour = int(slot.split(":")[0])
        if habit_energy_req >= 7 and 6 <= slot_hour <= 11:  # High energy, morning
            return True
        elif 4 <= habit_energy_req <= 7 and 11 <= slot_hour <= 17:  # Medium energy, afternoon
            return True
        elif habit_energy_req <= 4 and 17 <= slot_hour <= 22:  # Low energy, evening
            return True
        return user_energy_level >= habit_energy_req  # Fallback to user energy level
    except:
        return True  # Default to suitable if parsing fails

async def _generate_habit_schedule_for_habit(habit_record: Dict[str, Any], date: str) -> bool:
    """Check if a habit should be scheduled for a specific date."""
    try:
        period = habit_record.get("period", "daily")
        
        if period == "daily":
            return True
        elif period == "weekly":
            # Check if today is one of the scheduled days
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            day_name = date_obj.strftime("%A").lower()
            weekly_days = habit_record.get("weekly_days", [])
            return day_name in [day.lower() for day in weekly_days]
        elif period == "specific_dates":
            # Check if date is in specific dates list
            specific_dates = habit_record.get("specific_dates", [])
            return date in specific_dates
        
        return False
        
    except Exception:
        return False

async def _get_flexible_habits_for_date(user_id: str, date: str) -> List[Dict[str, Any]]:
    """Get habits that need flexible timing assignment for a date."""
    try:
        all_habits = await _get_user_active_habits(user_id)
        flexible_habits = []
        
        for habit in all_habits:
            if await _generate_habit_schedule_for_habit(habit, date):
                timing_type = habit.get("timing_type", "specific_time")
                daily_timing = habit.get("daily_timing")
                
                # Include habits that need timing assignment
                if (timing_type == "entire_day" or 
                    timing_type == "time_range" or 
                    (timing_type == "specific_time" and (not daily_timing or daily_timing == "flexible"))):
                    flexible_habits.append(habit)
        
        return flexible_habits
        
    except Exception:
        return []

async def _calculate_trend_impact(habit_id: str, new_score: int) -> str:
    """Calculate the impact of a new completion score on habit trends."""
    try:
        # Get recent completion scores (last 7 days)
        recent_scores = await _get_recent_completion_scores(habit_id, 7)
        
        if len(recent_scores) < 2:
            return "insufficient_data"
        
        # Calculate trend
        if len(recent_scores) >= 3:
            recent_avg = sum(recent_scores[-3:]) / 3
            previous_avg = sum(recent_scores[-6:-3]) / 3 if len(recent_scores) >= 6 else recent_avg
            
            if recent_avg > previous_avg:
                return "improving"
            elif recent_avg < previous_avg:
                return "declining"
            else:
                return "stable"
        
        return "stable"
        
    except Exception:
        return "unknown"

async def _get_recent_completion_scores(habit_id: str, days: int) -> List[int]:
    """Get recent completion scores for a habit."""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        completions = mongo_habit_manager.get_habit_completions(habit_id, start_date, end_date)
        return [c.get("completion_score", 0) for c in completions]
        
    except Exception:
        return [] 