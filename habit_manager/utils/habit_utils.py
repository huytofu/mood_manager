from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel, Field
from database.mongo_habit_manager import mongo_habit_manager
from database.mongo_user_manager import mongo_user_manager

# =============================================================================
# PREMIUM TIER MANAGEMENT
# =============================================================================

def get_user_habit_limits(user_id: str) -> Dict[str, Any]:
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
    limits = get_user_habit_limits(user_id)
    
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

# HABIT CREATION SCHEMAS
class CreateMicroHabitInput(BaseModel):
    name: str = Field(..., description="Habit name")
    description: str = Field(..., description="Detailed habit description")
    category: str = Field(..., description="Habit category: health, productivity, social, financial, etc.")
    period: str = Field(..., description="daily, weekly, or specific_dates")
    frequency: Optional[str] = Field(default=None, description="For weekly: 3x_week, every_2_days, etc.")
    weekly_days: Optional[List[str]] = Field(default=None, description="For weekly habits: [monday, wednesday, friday]")
    specific_dates: Optional[List[str]] = Field(default=None, description="For specific_dates period")
    daily_timing: Optional[str] = Field(default=None, description="Fixed time like 07:00 or after_coffee, None for flexible")
    intrinsic_score: int = Field(..., ge=1, le=4, description="Importance score 1-4, used as weight")
    is_meditation: bool = Field(default=False, description="Whether this is a meditation habit requiring audio asset")
    meditation_audio_id: Optional[str] = Field(default=None, description="Required if is_meditation=True")
    habit_type: str = Field(..., description="formation or breaking")

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

class RateDailyMoodInput(BaseModel):
    user_id: str = Field(..., description="User identifier") 
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    mood_score: int = Field(..., ge=1, le=10, description="Daily mood score 1-10")
    is_crisis: bool = Field(default=False, description="Whether user is in crisis/stress state")
    is_depressed: bool = Field(default=False, description="Whether user is in depressed state")
    notes: Optional[str] = Field(default=None, description="Optional mood notes")

class GetDailyHabitListInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")

# PROGRESS TRACKING SCHEMAS
class TrackHabitCompletionInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    habit_id: str = Field(..., description="Habit identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    completion_score: int = Field(..., ge=0, le=4, description="0 or 1-4 (up to intrinsic_score)")
    actual_timing: Optional[str] = Field(default=None, description="When habit actually happened")
    notes: Optional[str] = Field(default=None, description="Optional completion notes")

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
    habit_type: str, frequency: Optional[str] = None, weekly_days: Optional[List[str]] = None,
    specific_dates: Optional[List[str]] = None, daily_timing: Optional[str] = None,
    is_meditation: bool = False, meditation_audio_id: Optional[str] = None
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
    user_limits = get_user_habit_limits(user_id)
    
    # Advanced scheduling is now available to all users - no validation needed
    
    # Validate meditation habit requirements
    if is_meditation and not meditation_audio_id:
        validation_errors.append("Meditation habit requires meditation_audio_id. Create meditation audio first.")
        return {
            "success": False,
            "habit_id": "",
            "schedule_generated": False,
            "validation_errors": validation_errors
        }
    
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
        "daily_timing": daily_timing,
        "intrinsic_score": intrinsic_score,
        "habit_type": habit_type,
        "is_meditation": is_meditation,
        "assets": [meditation_audio_id] if meditation_audio_id else [],
        "status": "active"
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
    """Plan timing for flexible habits based on available slots and energy."""
    # Get flexible habits for the date
    flexible_habits = await _get_flexible_habits_for_date(user_id, date)
    
    # Optimize timing based on energy level and habit importance
    timing_assignments = {}
    optimization_notes = []
    
    # Sort habits by intrinsic score (highest first)
    sorted_habits = sorted(flexible_habits, key=lambda h: h.get("intrinsic_score", 1), reverse=True)
    
    # Assign timing based on energy level
    for i, habit in enumerate(sorted_habits):
        if i < len(available_time_slots):
            # High energy habits in high energy slots
            if energy_level >= 7 and habit.get("intrinsic_score", 1) >= 3:
                slot = available_time_slots[0] if available_time_slots else "morning"
            else:
                slot = available_time_slots[i % len(available_time_slots)]
            
            timing_assignments[habit["habit_id"]] = {
                "planned_time": slot,
                "priority_order": i + 1,
                "energy_matched": energy_level >= 7 and habit.get("intrinsic_score", 1) >= 3
            }
    
    # Generate optimization notes
    if energy_level <= 3:
        optimization_notes.append("Low energy detected - prioritize essential habits only")
    if len(sorted_habits) > len(available_time_slots):
        optimization_notes.append(f"More habits ({len(sorted_habits)}) than time slots ({len(available_time_slots)}) - prioritized by importance")
    
    return {
        "planned_habits": sorted_habits,
        "timing_assignments": timing_assignments,
        "optimization_notes": optimization_notes,
        "energy_level": energy_level,
        "total_habits_planned": len(timing_assignments)
    }

async def _record_daily_mood(
    user_id: str, date: str, mood_score: int, is_crisis: bool = False, 
    is_depressed: bool = False, notes: Optional[str] = None
) -> Dict[str, Any]:
    """Record daily mood rating with crisis/depression flags and premium tier validation."""
    user_limits = get_user_habit_limits(user_id)
    
    # For free users, block mood recording entirely or only allow basic recording without correlation
    if not user_limits["mood_correlation"]:
        return {
            "success": False,
            "error": "Mood recording and habit correlation requires premium plan",
            "upgrade_message": "Upgrade to premium for mood tracking, habit correlation analysis, and crisis support features",
            "feature_blocked": "mood_correlation",
            "available_alternative": "Focus on habit tracking without mood data"
        }
    
    # Premium users get full mood recording with correlation features
    # Create mood record
    mood_record_id = f"mood_{user_id}_{date.replace('-', '')}"
    
    mood_record = {
        "record_id": mood_record_id,
        "user_id": user_id,
        "date": date,
        "mood_score": mood_score,
        "is_crisis": is_crisis,
        "is_depressed": is_depressed,
        "notes": notes or ""
    }
    
    # Save to MongoDB
    mood_success = mongo_habit_manager.record_mood(mood_record)
    if not mood_success:
        return {"success": False, "error": "Failed to record mood in database"}
    
    # Determine if this should trigger correlation analysis
    correlation_trigger = is_crisis or is_depressed or mood_score <= 3 or mood_score >= 8
    
    return {
        "success": True,
        "mood_record_id": mood_record_id,
        "correlation_trigger": correlation_trigger,
        "mood_data": mood_record,
        "recommendations": await _get_mood_based_recommendations(mood_score, is_crisis, is_depressed)
    }

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
    """Record habit completion score for one habit on one day."""
    # Get habit details for validation
    habit = await _get_habit_by_id(habit_id)
    if not habit:
        return {"success": False, "error": f"Habit {habit_id} not found"}
    
    # Validate completion score
    max_score = habit.get("intrinsic_score", 4)
    if completion_score > max_score:
        return {"success": False, "error": f"Completion score {completion_score} exceeds habit's intrinsic score {max_score}"}
    
    # Create completion record
    completion_id = f"comp_{habit_id}_{date.replace('-', '')}"
    
    completion_record = {
        "completion_id": completion_id,
        "user_id": user_id,
        "habit_id": habit_id,
        "date": date,
        "completion_score": completion_score,
        "max_possible_score": max_score,
        "completion_rate": completion_score / max_score if max_score > 0 else 0,
        "actual_timing": actual_timing,
        "notes": notes or ""
    }
    
    # Save to MongoDB
    completion_success = mongo_habit_manager.record_habit_completion(completion_record)
    if not completion_success:
        return {"success": False, "error": "Failed to record completion in database"}
    
    # Streak is updated automatically by MongoDB manager
    streak_updated = True
    
    # Determine trend impact
    recent_scores = await _get_recent_completion_scores(habit_id, 7)  # Last 7 days
    trend_impact = await _calculate_trend_impact(recent_scores, completion_score)
    
    return {
        "success": True,
        "completion_id": completion_id,
        "completion_record": completion_record,
        "streak_updated": streak_updated,
        "trend_impact": trend_impact,
        "score_percentage": completion_record["completion_rate"] * 100
    }

async def _calculate_basic_habit_trends(
    habit_id: str, time_period: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate basic habit completion trends over time period with premium tier limits."""
    # Get habit to find user_id for tier checking
    habit = await _get_habit_by_id(habit_id)
    if not habit:
        return {"success": False, "error": f"Habit {habit_id} not found"}
    
    user_id = habit.get("user_id")
    user_limits = get_user_habit_limits(user_id)
    
    # Custom periods are now available to all users - no validation needed
    
    # Limit analysis period for free users
    if time_period == "custom" and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days_requested = (end_dt - start_dt).days
            
            if days_requested > user_limits["trend_analysis_days"]:
                return {
                    "success": False,
                    "error": f"Analysis period too long. Maximum {user_limits['trend_analysis_days']} days allowed for your plan",
                    "upgrade_message": "Upgrade to premium for unlimited analysis periods",
                    "max_days_allowed": user_limits["trend_analysis_days"]
                }
        except ValueError:
            pass  # Invalid date format, let the main function handle it
    
    # Get current streak
    current_streak = await _get_current_habit_streak(habit_id)
    # Get completion records for period
    habit_progress = await _get_current_habit_trends(habit_id, time_period, start_date, end_date)

    overall_progress = {
        "habit_id": habit_id,
        "average_score": habit_progress["average_score"],
        "trend_direction": habit_progress["trend_direction"],
        "consistency_rate": habit_progress["consistency_rate"],
        "current_streak": current_streak
    }
    return overall_progress

async def _calculate_basic_epic_progress(epic_habit_id: str, time_period: str) -> Dict[str, Any]:
    """Calculate basic epic habit progress using intrinsic scores as weights with premium tier validation."""
    # Get epic habit and its micro habits
    epic_habit = await _get_epic_habit_by_id(epic_habit_id)
    if not epic_habit:
        return {"success": False, "error": f"Epic habit {epic_habit_id} not found"}
    
    # Check if user can calculate epic progress (requires epic habit creation capability)
    user_id = epic_habit.get("user_id")
    user_limits = get_user_habit_limits(user_id)
    
    if not user_limits["epic_progress_calculation"]:
        return {
            "success": False,
            "error": "Epic progress calculation requires premium plan",
            "upgrade_message": "Upgrade to premium to track progress on epic habits",
            "feature_blocked": "epic_progress_calculation"
        }
    
    high_priority_habits = epic_habit.get("high_priority_micro_habits", [])
    low_priority_habits = epic_habit.get("low_priority_micro_habits", [])
    all_micro_habits = high_priority_habits + low_priority_habits
    
    if not all_micro_habits:
        return {
            "overall_progress": 0.0,
            "micro_habit_progress": {},
            "weighted_calculation": {"total_weight": 0, "weighted_score": 0},
            "message": "No micro habits assigned to this epic habit"
        }
    
    # Calculate progress for each micro habit
    micro_habit_progress = {}
    total_weighted_score = 0
    total_possible_weight = 0
    
    for habit_id in all_micro_habits:
        # Get habit progress
        habit_progress = await _get_current_habit_trends(habit_id, time_period)
        
        # Get habit details for weight
        habit = await _get_habit_by_id(habit_id)
        weight = habit.get("intrinsic_score", 1) if habit else 1
        
        # Store individual progress
        micro_habit_progress[habit_id] = {
            "average_score": habit_progress["average_score"],
            "trend_direction": habit_progress["trend_direction"],
            "consistency_rate": habit_progress["consistency_rate"],
            "weight": weight,
            "weighted_contribution": habit_progress["average_score"] * weight
        }
        
        # Add to totals
        total_weighted_score += habit_progress["average_score"] * weight
        total_possible_weight += weight
    
    # Calculate overall weighted progress
    overall_progress = (total_weighted_score / total_possible_weight * 100) if total_possible_weight > 0 else 0
    
    return {
        "overall_progress": round(overall_progress, 2),
        "micro_habit_progress": micro_habit_progress,
        "weighted_calculation": {
            "total_weighted_score": round(total_weighted_score, 3),
            "total_possible_weight": total_possible_weight,
            "epic_habit_id": epic_habit_id,
            "time_period": time_period
        },
        "success": True
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
    """Get recommendations based on mood rating."""
    recommendations = []
    
    if is_crisis:
        recommendations.extend(["Seek immediate support", "Use crisis meditation audio"])
    elif is_depressed:
        recommendations.extend(["Consider gentle movement", "Practice self-compassion"])
    elif mood_score <= 3:
        recommendations.extend(["Focus on basic self-care", "Use mood-boosting habits"])
    elif mood_score >= 8:
        recommendations.extend(["Great day for challenging habits", "Build on positive momentum"])
    
    return recommendations 