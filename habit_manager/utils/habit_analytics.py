"""
Habit Analytics Operations
=========================
Functions for habit analytics, trends analysis, insights generation, and LLM-powered analysis.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from pydantic import BaseModel, Field, field_validator
from database.mongo_habit_manager import mongo_habit_manager
from .habit_core import _get_habit_by_id, _get_epic_habit_by_id
import os

# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class CalculateHabitTrendsInput(BaseModel):
    habit_id: str = Field(..., description="Habit identifier")
    time_period: str = Field(..., description="weekly, monthly, or custom")
    start_date: Optional[str] = Field(default=None, description="Start date for custom period")
    end_date: Optional[str] = Field(default=None, description="End date for custom period")

class GenerateEpicProgressInput(BaseModel):
    epic_habit_id: str = Field(..., description="Epic habit identifier")
    time_period: str = Field(..., description="weekly, monthly, or all_time")

# =============================================================================
# HABIT TRENDS AND ANALYTICS
# =============================================================================

async def _calculate_basic_habit_trends(
    habit_id: str, time_period: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate basic habit trends and performance metrics."""
    try:
        # Validate habit exists
        habit = await _get_habit_by_id(habit_id)
        if not habit:
            return {"success": False, "error": "Habit not found"}
        
        # Calculate date range
        if time_period == "custom":
            if not start_date or not end_date:
                return {"success": False, "error": "start_date and end_date required for custom period"}
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
        else:
            end_dt = datetime.now()
            if time_period == "weekly":
                start_dt = end_dt - timedelta(weeks=1)
            elif time_period == "monthly":
                start_dt = end_dt - timedelta(days=30)
            else:
                return {"success": False, "error": "Invalid time_period. Use weekly, monthly, or custom"}
            
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")
        
        # Get completion records for the period
        completion_records = await _get_completion_records(habit_id, start_date, end_date)
        
        if not completion_records:
            return {
                "success": True,
                "habit_id": habit_id,
                "habit_name": habit.get("name", "Unknown"),
                "time_period": time_period,
                "start_date": start_date,
                "end_date": end_date,
                "trends": {
                    "total_days": 0,
                    "completed_days": 0,
                    "completion_rate": 0.0,
                    "average_score": 0.0,
                    "trend_direction": "no_data",
                    "streak_info": {
                        "current_streak": 0,
                        "longest_streak_in_period": 0
                    }
                }
            }
        
        # Calculate basic metrics
        total_days = len(completion_records)
        completed_days = len([r for r in completion_records if r.get("completion_score", 0) > 0])
        completion_rate = (completed_days / total_days) * 100 if total_days > 0 else 0
        
        # Calculate average score
        scores = [r.get("completion_score", 0) for r in completion_records]
        average_score = sum(scores) / len(scores) if scores else 0
        
        # Analyze trend direction
        trend_direction = _analyze_trend_direction(scores)
        
        # Calculate streak information
        current_streak = await _get_current_habit_streak(habit_id)
        longest_streak_in_period = _calculate_longest_streak_in_period(completion_records)
        
        # Weekly breakdown for longer periods
        weekly_breakdown = None
        if time_period == "monthly" or (time_period == "custom" and (end_dt - start_dt).days > 14):
            weekly_breakdown = _calculate_weekly_breakdown(completion_records, start_dt, end_dt)
        
        trends = {
            "total_days": total_days,
            "completed_days": completed_days,
            "completion_rate": round(completion_rate, 2),
            "average_score": round(average_score, 2),
            "trend_direction": trend_direction,
            "streak_info": {
                "current_streak": current_streak,
                "longest_streak_in_period": longest_streak_in_period
            },
            "score_distribution": _calculate_score_distribution(scores),
            "weekly_breakdown": weekly_breakdown
        }
        
        return {
            "success": True,
            "habit_id": habit_id,
            "habit_name": habit.get("name", "Unknown"),
            "habit_type": habit.get("habit_type", "formation"),
            "time_period": time_period,
            "start_date": start_date,
            "end_date": end_date,
            "trends": trends
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error calculating trends: {str(e)}"}

async def _calculate_basic_epic_progress(epic_habit_id: str, time_period: str) -> Dict[str, Any]:
    """Calculate progress for an epic habit based on its micro habits."""
    try:
        # Validate epic habit exists
        epic_habit = await _get_epic_habit_by_id(epic_habit_id)
        if not epic_habit:
            return {"success": False, "error": "Epic habit not found"}
        
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        if time_period == "weekly":
            start_date = (datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d")
        elif time_period == "monthly":
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        elif time_period == "all_time":
            start_date = epic_habit.get("created_date", end_date)[:10]  # Extract date part
        else:
            return {"success": False, "error": "Invalid time_period. Use weekly, monthly, or all_time"}
        
        # Get micro habits assigned to this epic
        high_priority_habits = epic_habit.get("high_priority_micro_habits", [])
        low_priority_habits = epic_habit.get("low_priority_micro_habits", [])
        all_micro_habits = high_priority_habits + low_priority_habits
        
        if not all_micro_habits:
            return {
                "success": True,
                "epic_habit_id": epic_habit_id,
                "epic_name": epic_habit.get("name", "Unknown"),
                "time_period": time_period,
                "progress": {
                    "overall_progress": 0.0,
                    "micro_habits_count": 0,
                    "message": "No micro habits assigned to this epic habit"
                }
            }
        
        # Calculate progress for each micro habit
        micro_habit_progress = []
        total_weighted_score = 0
        total_weight = 0
        
        for habit_id in all_micro_habits:
            is_high_priority = habit_id in high_priority_habits
            weight = 2 if is_high_priority else 1
            
            # Get habit details
            habit = await _get_habit_by_id(habit_id)
            if not habit:
                continue
            
            # Calculate trend for this habit
            trend_result = await _calculate_basic_habit_trends(habit_id, time_period, start_date, end_date)
            
            if trend_result["success"]:
                completion_rate = trend_result["trends"]["completion_rate"]
                average_score = trend_result["trends"]["average_score"]
                
                # Calculate weighted score
                weighted_score = (completion_rate / 100) * weight
                total_weighted_score += weighted_score
                total_weight += weight
                
                micro_habit_progress.append({
                    "habit_id": habit_id,
                    "habit_name": habit.get("name", "Unknown"),
                    "priority": "high" if is_high_priority else "low",
                    "weight": weight,
                    "completion_rate": completion_rate,
                    "average_score": average_score,
                    "weighted_score": weighted_score
                })
        
        # Calculate overall progress
        overall_progress = (total_weighted_score / total_weight * 100) if total_weight > 0 else 0
        
        # Update epic habit progress in database
        mongo_habit_manager.update_epic_progress(epic_habit_id, overall_progress)
        
        # Calculate time remaining
        target_date = epic_habit.get("target_completion_date")
        time_analysis = None
        if target_date:
            try:
                target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                days_remaining = (target_dt - datetime.now()).days
                
                if overall_progress > 0:
                    days_at_current_rate = int((100 - overall_progress) / (overall_progress / (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d")).days))
                    on_track = days_at_current_rate <= days_remaining
                else:
                    days_at_current_rate = float('inf')
                    on_track = False
                
                time_analysis = {
                    "target_date": target_date,
                    "days_remaining": days_remaining,
                    "estimated_days_to_completion": days_at_current_rate if days_at_current_rate != float('inf') else None,
                    "on_track": on_track
                }
            except ValueError:
                pass
        
        return {
            "success": True,
            "epic_habit_id": epic_habit_id,
            "epic_name": epic_habit.get("name", "Unknown"),
            "time_period": time_period,
            "start_date": start_date,
            "end_date": end_date,
            "progress": {
                "overall_progress": round(overall_progress, 2),
                "micro_habits_count": len(micro_habit_progress),
                "high_priority_count": len(high_priority_habits),
                "low_priority_count": len(low_priority_habits),
                "micro_habit_details": micro_habit_progress,
                "time_analysis": time_analysis
            }
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error calculating epic progress: {str(e)}"}

# =============================================================================
# LLM-POWERED HABIT INSIGHTS
# =============================================================================

async def _get_habit_insights_from_notes(habit_id: str, days: int = 30) -> Dict[str, Any]:
    """Analyze habit notes to provide insights about patterns and triggers."""
    try:
        # Get recent notes
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        from .habit_core import _get_habit_notes
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

# =============================================================================
# ANALYTICS UTILITY FUNCTIONS
# =============================================================================

def _analyze_trend_direction(scores: List[int]) -> str:
    """Analyze the trend direction of completion scores."""
    if len(scores) < 3:
        return "insufficient_data"
    
    # Compare first half vs second half
    mid_point = len(scores) // 2
    first_half_avg = sum(scores[:mid_point]) / mid_point if mid_point > 0 else 0
    second_half_avg = sum(scores[mid_point:]) / (len(scores) - mid_point) if len(scores) > mid_point else 0
    
    if second_half_avg > first_half_avg * 1.1:  # 10% improvement threshold
        return "improving"
    elif second_half_avg < first_half_avg * 0.9:  # 10% decline threshold
        return "declining"
    else:
        return "stable"

def _calculate_longest_streak_in_period(completion_records: List[Dict[str, Any]]) -> int:
    """Calculate the longest completion streak within a period."""
    if not completion_records:
        return 0
    
    # Sort by date
    sorted_records = sorted(completion_records, key=lambda x: x.get("date", ""))
    
    current_streak = 0
    longest_streak = 0
    
    for record in sorted_records:
        if record.get("completion_score", 0) > 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0
    
    return longest_streak

def _calculate_score_distribution(scores: List[int]) -> Dict[str, int]:
    """Calculate distribution of completion scores."""
    distribution = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}
    
    for score in scores:
        score_str = str(min(max(score, 0), 4))  # Clamp to 0-4 range
        distribution[score_str] = distribution.get(score_str, 0) + 1
    
    return distribution

def _calculate_weekly_breakdown(completion_records: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> List[Dict[str, Any]]:
    """Calculate weekly breakdown of habit performance."""
    weekly_data = []
    current_week_start = start_dt
    
    while current_week_start < end_dt:
        week_end = min(current_week_start + timedelta(days=6), end_dt)
        
        # Get completions for this week
        week_completions = [
            record for record in completion_records
            if current_week_start.strftime("%Y-%m-%d") <= record.get("date", "") <= week_end.strftime("%Y-%m-%d")
        ]
        
        week_scores = [r.get("completion_score", 0) for r in week_completions]
        completion_rate = (len([s for s in week_scores if s > 0]) / len(week_scores) * 100) if week_scores else 0
        avg_score = sum(week_scores) / len(week_scores) if week_scores else 0
        
        weekly_data.append({
            "week_start": current_week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "completion_rate": round(completion_rate, 2),
            "average_score": round(avg_score, 2),
            "total_days": len(week_completions)
        })
        
        current_week_start = week_end + timedelta(days=1)
    
    return weekly_data

# =============================================================================
# DATA RETRIEVAL FUNCTIONS
# =============================================================================

async def _get_completion_records(habit_id: str, start_date: Optional[str], end_date: Optional[str]) -> List[Dict[str, Any]]:
    """Get completion records for a habit within a date range."""
    try:
        return mongo_habit_manager.get_habit_completions(habit_id, start_date, end_date)
    except Exception:
        return []

async def _get_current_habit_streak(habit_id: str) -> int:
    """Get current streak for a habit."""
    try:
        habit = await _get_habit_by_id(habit_id)
        return habit.get("current_streak", 0) if habit else 0
    except Exception:
        return 0

async def _get_best_habit_streak(habit_id: str) -> int:
    """Get best streak for a habit."""
    try:
        habit = await _get_habit_by_id(habit_id)
        return habit.get("best_streak", 0) if habit else 0
    except Exception:
        return 0

async def _get_all_user_completions(user_id: str, time_period: str) -> List[Dict[str, Any]]:
    """Get all completions for a user within a time period."""
    try:
        return mongo_habit_manager.get_user_completions(user_id, time_period)
    except Exception:
        return []

async def _get_mood_records(user_id: str, time_period: str) -> List[Dict[str, Any]]:
    """Get mood records for a user within a time period."""
    try:
        return mongo_habit_manager.get_mood_records(user_id, time_period)
    except Exception:
        return []

async def _get_mood_based_recommendations(mood_score: int, is_crisis: bool, is_depressed: bool) -> List[str]:
    """Get habit recommendations based on mood state."""
    recommendations = []
    
    if is_crisis or mood_score <= 3:
        recommendations.extend([
            "Focus on basic self-care habits (eating, sleeping, hygiene)",
            "Consider gentle movement like short walks",
            "Practice breathing exercises or meditation",
            "Reach out to trusted friends or family",
            "Avoid making major decisions about habits right now"
        ])
    elif is_depressed or mood_score <= 5:
        recommendations.extend([
            "Start with very small, achievable habits",
            "Prioritize sleep hygiene and regular sleep schedule",
            "Include light physical activity or stretching",
            "Consider journaling or mood tracking",
            "Focus on social connection habits"
        ])
    elif mood_score <= 7:
        recommendations.extend([
            "Maintain consistent daily routines",
            "Add moderate exercise or physical activity",
            "Include creative or enjoyable activities",
            "Work on productivity habits during good energy periods",
            "Practice gratitude or mindfulness habits"
        ])
    else:  # mood_score > 7
        recommendations.extend([
            "This is a good time to tackle challenging habits",
            "Consider adding new habits or increasing difficulty",
            "Use high energy for productivity and exercise habits",
            "Share positive momentum with others",
            "Plan for maintaining habits during lower mood periods"
        ])
    
    return recommendations 