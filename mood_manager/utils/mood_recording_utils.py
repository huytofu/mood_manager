"""
Mood Recording Utilities

This module handles mood recording functionality that was moved from the habit manager.
Mood recording should be owned by the mood manager, not the habit manager.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import sys
import os

# Add the mood_manager database path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

# Import mood manager database (our own database for mood operations)
try:
    from database.mongo_mood_manager import mongo_mood_manager
except ImportError:
    mongo_mood_manager = None

# Import habit manager database for reading mood records (for correlation analysis)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'habit_manager', 'database'))

# Import shared schemas
try:
    from database.schemas import MoodRecordDocument, validate_mood_data
except ImportError:
    # Fallback for when schemas aren't available
    def validate_mood_data(data: Dict) -> Dict:
        return data
    MoodRecordDocument = None


def _get_user_mood_limits(user_id: str) -> Dict[str, Any]:
    """Get mood recording limits for user tier."""
    # TODO: Replace with actual user tier checking
    # For now, assume all users have mood recording capability
    return {
        "mood_recording": True,
        "crisis_support": True,
        "mood_correlation": True,
        "historical_mood_analysis": True
    }


async def _record_daily_mood(
    user_id: str, date: str, mood_score: int, is_crisis: bool = False, 
    is_depressed: bool = False, notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record daily mood rating with crisis/depression flags.
    
    This function was moved from habit_manager to mood_manager as mood recording
    should be owned by the mood manager.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
        mood_score: Mood score 1-10
        is_crisis: Whether user is in crisis state
        is_depressed: Whether user is depressed
        notes: Optional mood notes
        
    Returns:
        Dict with success status and mood record details
    """
    user_limits = _get_user_mood_limits(user_id)
    
    # Check if user can record moods
    if not user_limits["mood_recording"]:
        return {
            "success": False,
            "error": "Mood recording requires premium plan",
            "upgrade_message": "Upgrade to premium for mood tracking and crisis support features",
            "feature_blocked": "mood_recording"
        }
    
    # Create mood record
    mood_record_id = f"mood_{user_id}_{date.replace('-', '')}"
    
    mood_record = {
        "record_id": mood_record_id,
        "user_id": user_id,
        "date": date,
        "mood_score": mood_score,
        "is_crisis": is_crisis,
        "is_depressed": is_depressed,
        "notes": notes or "",
        "recorded_at": datetime.now().isoformat()
    }
    
    # Validate mood data using Pydantic if available
    try:
        if validate_mood_data:
            mood_record = validate_mood_data(mood_record, MoodRecordDocument)
    except Exception as e:
        print(f"Mood data validation failed, proceeding without validation: {e}")
    
    # Save mood record to mood manager database (proper architecture separation)
    if mongo_mood_manager:
        mood_success = mongo_mood_manager.record_mood(mood_record)
        if not mood_success:
            return {"success": False, "error": "Failed to record mood in database"}
    else:
        return {"success": False, "error": "Mood database connection not available"}
    
    # Determine if this should trigger crisis intervention
    crisis_trigger = is_crisis or is_depressed or mood_score <= 3
    
    # Determine if this should trigger habit correlation analysis
    correlation_trigger = is_crisis or is_depressed or mood_score <= 3 or mood_score >= 8
    
    return {
        "success": True,
        "mood_record_id": mood_record_id,
        "mood_data": mood_record,
        "crisis_trigger": crisis_trigger,
        "correlation_trigger": correlation_trigger,
        "recommendations": await _get_mood_based_recommendations(mood_score, is_crisis, is_depressed)
    }


async def _get_mood_records(user_id: str, time_period: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get mood records for user within time period.
    
    Args:
        user_id: User identifier
        time_period: weekly, monthly, or custom
        start_date: Start date for custom period
        end_date: End date for custom period
        
    Returns:
        List of mood records
    """
    if not mongo_mood_manager:
        return []
    
    try:
        # Use mood manager database to read mood records
        mood_records = mongo_mood_manager.get_mood_records(user_id, time_period, start_date, end_date)
        return mood_records if mood_records else []
    except Exception as e:
        print(f"Failed to get mood records: {e}")
        return []


async def _get_mood_based_recommendations(mood_score: int, is_crisis: bool, is_depressed: bool) -> List[str]:
    """
    Generate mood-based recommendations for immediate support.
    
    Args:
        mood_score: Current mood score 1-10
        is_crisis: Whether user is in crisis
        is_depressed: Whether user is depressed
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    if is_crisis:
        recommendations.extend([
            "Consider reaching out to a crisis helpline or mental health professional immediately",
            "Practice deep breathing exercises or grounding techniques",
            "Ensure you're in a safe environment and consider contacting a trusted friend or family member"
        ])
    
    if is_depressed:
        recommendations.extend([
            "Consider speaking with a mental health professional about persistent low mood",
            "Engage in gentle physical activity like a short walk",
            "Try connecting with supportive friends or family members"
        ])
    
    if mood_score <= 3:
        recommendations.extend([
            "Focus on basic self-care: hydration, nutrition, and rest",
            "Consider meditation or relaxation exercises",
            "Limit demanding tasks and prioritize essential habits only"
        ])
    elif mood_score <= 5:
        recommendations.extend([
            "Maintain your core habits but be flexible with timing",
            "Consider mood-boosting activities like exercise or creative pursuits",
            "Practice gratitude or mindfulness exercises"
        ])
    elif mood_score >= 8:
        recommendations.extend([
            "Great mood for tackling challenging habits or goals",
            "Consider building momentum with consistent habit completion",
            "Use this energy to plan ahead for lower mood days"
        ])
    
    return recommendations


async def _analyze_mood_patterns(user_id: str, time_period: str = "monthly") -> Dict[str, Any]:
    """
    Analyze mood patterns for insights and trends.
    
    Args:
        user_id: User identifier
        time_period: Analysis period
        
    Returns:
        Dict with mood pattern analysis
    """
    mood_records = await _get_mood_records(user_id, time_period)
    
    if not mood_records:
        return {
            "success": False,
            "error": "No mood records found for analysis",
            "recommendation": "Start recording daily moods to enable pattern analysis"
        }
    
    # Calculate basic statistics
    mood_scores = [record.get("mood_score", 5) for record in mood_records]
    avg_mood = sum(mood_scores) / len(mood_scores)
    
    crisis_days = len([r for r in mood_records if r.get("is_crisis", False)])
    depressed_days = len([r for r in mood_records if r.get("is_depressed", False)])
    
    low_mood_days = len([score for score in mood_scores if score <= 3])
    high_mood_days = len([score for score in mood_scores if score >= 8])
    
    # Trend analysis
    if len(mood_scores) >= 7:
        recent_avg = sum(mood_scores[-7:]) / 7
        earlier_avg = sum(mood_scores[:-7]) / len(mood_scores[:-7]) if len(mood_scores) > 7 else avg_mood
        trend = "improving" if recent_avg > earlier_avg else "declining" if recent_avg < earlier_avg else "stable"
    else:
        trend = "insufficient_data"
    
    return {
        "success": True,
        "analysis_period": time_period,
        "total_records": len(mood_records),
        "average_mood": round(avg_mood, 2),
        "mood_trend": trend,
        "crisis_days": crisis_days,
        "depressed_days": depressed_days,
        "low_mood_days": low_mood_days,
        "high_mood_days": high_mood_days,
        "mood_stability": "stable" if max(mood_scores) - min(mood_scores) <= 4 else "variable",
        "recommendations": await _get_pattern_based_recommendations(avg_mood, trend, crisis_days, depressed_days)
    }


async def _get_pattern_based_recommendations(avg_mood: float, trend: str, crisis_days: int, depressed_days: int) -> List[str]:
    """Generate recommendations based on mood patterns."""
    recommendations = []
    
    if avg_mood < 4:
        recommendations.append("Your average mood has been low. Consider consulting a mental health professional.")
    
    if trend == "declining":
        recommendations.append("Your mood trend is declining. Focus on self-care and consider additional support.")
    elif trend == "improving":
        recommendations.append("Your mood is improving! Keep up the positive habits and self-care practices.")
    
    if crisis_days > 0:
        recommendations.append("You've had crisis days recently. Ensure you have crisis support resources available.")
    
    if depressed_days > 3:
        recommendations.append("Frequent depressed days detected. Consider professional mental health support.")
    
    return recommendations if recommendations else ["Your mood patterns look stable. Continue your current self-care routine."] 