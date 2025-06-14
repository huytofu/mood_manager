"""
Mood Recording Utilities

This module handles mood recording functionality that was moved from the habit manager.
Mood recording should be owned by the mood manager, not the habit manager.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
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
    from database.schemas import (
        DateRecordDocument, 
        EmotionRecordDocument,
        validate_date_record_data,
        validate_emotion_record_data
    )
except ImportError:
    # Fallback for when schemas aren't available
    def validate_date_record_data(data: Dict) -> Dict:
        return data
    def validate_emotion_record_data(data: Dict) -> Dict:
        return data
    DateRecordDocument = None
    EmotionRecordDocument = None


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


async def _get_mood_stats(user_id: str, time_period: str = None, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """
    Get mood records for user within time period or date range.
    
    Args:
        user_id: User identifier
        time_period: weekly, monthly, or custom (optional)
        start_date: Start date for custom period (YYYY-MM-DD)
        end_date: End date for custom period (YYYY-MM-DD)
        limit: Maximum number of records to return
        
    Returns:
        Dict with success status and mood records data
    """
    if not mongo_mood_manager:
        return {"success": False, "error": "Mood database connection not available"}
    
    try:
        # Calculate dates based on time_period if dates not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            if time_period == "weekly":
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            elif time_period == "monthly":
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            else:
                # Default to 30 days if no time_period specified
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Use the updated get_mood_stats method
        result = mongo_mood_manager.get_mood_stats(user_id, start_date, end_date)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        # Limit records if requested
        mood_records = result.get("mood_records", [])
        if limit and len(mood_records) > limit:
            mood_records = mood_records[:limit]
        
        return {
            "success": True,
            "mood_records": mood_records,
            "total_records": result.get("total_records", 0),
            "date_range": f"{result.get('start_date', start_date)} to {result.get('end_date', end_date)}",
            "statistics": {
                "average_mood": result.get("average_mood"),
                "min_mood": result.get("min_mood"),
                "max_mood": result.get("max_mood"),
                "crisis_days": result.get("crisis_days", 0),
                "depressed_days": result.get("depressed_days", 0)
            }
        }
        
    except Exception as e:
        print(f"Failed to get mood records: {e}")
        return {"success": False, "error": f"Failed to retrieve mood records: {str(e)}"}


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


# =============================================================================
# ENHANCED MOOD AND EMOTION RECORDING UTILITIES (Phase 1 & 2)
# =============================================================================

async def _record_daily_mood(
    user_id: str, date: str, mood_score: int = None, mood_notes: str = None,
    is_crisis: bool = False, is_depressed: bool = False, notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record daily mood rating with optional notes, crisis/depression flags.
    Consolidated function that replaces both old _record_daily_mood and _record_daily_mood_enhanced.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
        mood_score: Optional mood score 1-10 (if None, only notes will be recorded)
        mood_notes: Optional emotional diary notes (preferred parameter name)
        is_crisis: Whether user is in crisis state
        is_depressed: Whether user is depressed
        notes: Optional mood notes (legacy parameter name, maps to mood_notes)
        
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
    
    # Handle legacy 'notes' parameter by mapping to mood_notes
    if notes and not mood_notes:
        mood_notes = notes
    
    # Save to enhanced date record structure using consolidated approach
    if mongo_mood_manager:
        success = mongo_mood_manager.record_daily_mood_with_notes(
            user_id=user_id,
            date=date,
            mood_score=mood_score,
            mood_notes=mood_notes,
            is_crisis=is_crisis,
            is_depressed=is_depressed
        )
        
        if not success:
            return {"success": False, "error": "Failed to record mood in database"}
    else:
        return {"success": False, "error": "Mood database connection not available"}
    
    # Determine triggers for interventions and analytics
    crisis_trigger = is_crisis or is_depressed or (mood_score is not None and mood_score <= 3)
    correlation_trigger = crisis_trigger or (mood_score is not None and mood_score >= 8)
    
    # Generate mood record ID for tracking
    mood_record_id = f"mood_{user_id}_{date.replace('-', '')}"
    
    return {
        "success": True,
        "mood_record_id": mood_record_id,
        "date": date,
        "mood_score": mood_score,
        "mood_notes": mood_notes,
        "crisis_trigger": crisis_trigger,
        "correlation_trigger": correlation_trigger,
        "recommendations": await _get_mood_based_recommendations(mood_score or 5, is_crisis, is_depressed)
    }


async def _record_daily_mood_notes(
    user_id: str, date: str, mood_notes: str
) -> Dict[str, Any]:
    """
    Record daily emotional diary notes (emotional diary functionality).
    Updates existing date record or creates new one.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
        mood_notes: Emotional diary entry
        
    Returns:
        Dict with success status
    """
    if not mongo_mood_manager:
        return {"success": False, "error": "Mood database connection not available"}
    
    success = mongo_mood_manager.record_daily_mood_with_notes(
        user_id=user_id,
        date=date,
        mood_notes=mood_notes
    )
    
    if success:
        return {
            "success": True,
            "message": "Emotional diary entry recorded successfully",
            "date": date,
            "note_length": len(mood_notes) if mood_notes else 0
        }
    else:
        return {"success": False, "error": "Failed to record mood notes"}


async def _record_daily_emotion(
    user_id: str, date: str, emotion_type: str, emotion_score: int,
    triggers: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record specific emotion with intensity score.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
        emotion_type: Type of emotion (e.g., "anxiety", "joy")
        emotion_score: Intensity score 1-10
        triggers: Optional list of triggers
        context: Optional context dictionary
        
    Returns:
        Dict with success status and emotion record details
    """
    if not mongo_mood_manager:
        return {"success": False, "error": "Mood database connection not available"}
    
    # Record emotion with consolidated method
    success = mongo_mood_manager.record_daily_emotion_with_notes(
        user_id=user_id,
        date=date,
        emotion_type=emotion_type,
        emotion_score=emotion_score,
        triggers=triggers,
        context=context
    )
    
    if success:
        # Generate emotion record ID for tracking
        emotion_record_id = f"emotion_{user_id}_{date.replace('-', '')}_{emotion_type.lower()}"
        
        return {
            "success": True,
            "emotion_record_id": emotion_record_id,
            "emotion_type": emotion_type,
            "emotion_score": emotion_score,
            "date": date,
            "triggers": triggers or [],
            "context": context or {},
            "recommendations": await _get_emotion_based_recommendations(emotion_type, emotion_score)
        }
    else:
        return {"success": False, "error": "Failed to record emotion"}


async def _record_daily_emotion_notes(
    user_id: str, date: str, emotion_type: str, emotion_notes: str,
    triggers: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Record notes for a specific emotion on a specific date.
    Uses the consolidated emotion recording method with a default score.
    
    Args:
        user_id: User identifier
        date: Date in YYYY-MM-DD format
        emotion_type: Type of emotion
        emotion_notes: Notes about this emotion
        triggers: Optional list of triggers
        context: Optional context dictionary
        
    Returns:
        Dict with success status
    """
    if not mongo_mood_manager:
        return {"success": False, "error": "Mood database connection not available"}
    
    # Use consolidated method with default score of 5 (mid-range) for notes-only entries
    success = mongo_mood_manager.record_daily_emotion_with_notes(
        user_id=user_id,
        date=date,
        emotion_type=emotion_type,
        emotion_score=5,  # Default mid-range score for notes-only entries
        emotion_notes=emotion_notes,
        triggers=triggers,
        context=context
    )
    
    if success:
        return {
            "success": True,
            "message": "Emotion notes recorded successfully",
            "emotion_type": emotion_type,
            "date": date,
            "note_length": len(emotion_notes) if emotion_notes else 0
        }
    else:
        return {"success": False, "error": "Failed to record emotion notes"}


async def _analyze_mood_trend(
    user_id: str, time_period: str = "monthly", include_note_analysis: bool = True
) -> Dict[str, Any]:
    """
    Enhanced mood trend analysis including NLP insights from mood notes.
    
    Args:
        user_id: User identifier
        time_period: Analysis period
        include_note_analysis: Whether to analyze mood notes
        
    Returns:
        Dict with comprehensive mood trend analysis
    """
    if not mongo_mood_manager:
        return {"success": False, "error": "Mood database connection not available"}
    
    # Get date records with mood data
    if time_period == "weekly":
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    elif time_period == "monthly":
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        # Default to monthly
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    date_records = mongo_mood_manager.get_date_records_range(user_id, start_date, end_date)
    
    if not date_records:
        return {
            "success": False,
            "error": "No mood data found for analysis",
            "recommendation": "Start recording daily moods to enable pattern analysis"
        }
    
    # Filter records with mood data
    mood_records = [r for r in date_records if r.get("mood_score") is not None]
    
    if not mood_records:
        return {
            "success": False,
            "error": "No mood scores found for analysis",
            "recommendation": "Record mood scores with your entries to enable trend analysis"
        }
    
    # Statistical analysis
    mood_scores = [r["mood_score"] for r in mood_records]
    avg_mood = sum(mood_scores) / len(mood_scores)
    
    crisis_days = len([r for r in mood_records if r.get("is_crisis", False)])
    depressed_days = len([r for r in mood_records if r.get("is_depressed", False)])
    
    low_mood_days = len([score for score in mood_scores if score <= 3])
    high_mood_days = len([score for score in mood_scores if score >= 8])
    
    # Trend calculation
    if len(mood_scores) >= 7:
        recent_avg = sum(mood_scores[-7:]) / 7
        earlier_avg = sum(mood_scores[:-7]) / len(mood_scores[:-7]) if len(mood_scores) > 7 else avg_mood
        if recent_avg > earlier_avg + 0.5:
            trend = "improving"
        elif recent_avg < earlier_avg - 0.5:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    # Note analysis
    note_insights = []
    if include_note_analysis:
        notes = [r.get("mood_notes", "") for r in mood_records if r.get("mood_notes")]
        if notes:
            note_insights = await _analyze_notes_sentiment(notes, "mood_trend")
    
    return {
        "success": True,
        "analysis_period": time_period,
        "date_range": f"{start_date} to {end_date}",
        "total_records": len(mood_records),
        "average_mood": round(avg_mood, 2),
        "mood_trend": trend,
        "crisis_days": crisis_days,
        "depressed_days": depressed_days,
        "low_mood_days": low_mood_days,
        "high_mood_days": high_mood_days,
        "mood_stability": "stable" if max(mood_scores) - min(mood_scores) <= 4 else "variable",
        "note_insights": note_insights,
        "recommendations": await _get_pattern_based_recommendations(avg_mood, trend, crisis_days, depressed_days)
    }


async def _analyze_emotion_trend(
    user_id: str, emotions: Union[str, List[str]], time_period: str = "monthly",
    include_note_analysis: bool = True
) -> Dict[str, Any]:
    """
    Analyze specific emotion trends with optional multi-emotion correlation.
    
    Args:
        user_id: User identifier
        emotions: Single emotion string, list of emotions, or "all"
        time_period: Analysis period
        include_note_analysis: Whether to analyze emotion notes
        
    Returns:
        Dict with emotion trend analysis
    """
    if not mongo_mood_manager:
        return {"success": False, "error": "Mood database connection not available"}
    
    # Determine date range
    if time_period == "weekly":
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    elif time_period == "monthly":
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Handle emotion parameter
    if emotions == "all":
        emotion_types = None  # Get all emotions
    elif isinstance(emotions, str):
        emotion_types = [emotions.lower().strip()]
    else:
        emotion_types = [e.lower().strip() for e in emotions]
    
    # Get emotion records
    emotion_records = mongo_mood_manager.get_emotion_records(
        user_id=user_id,
        emotion_types=emotion_types,
        start_date=start_date,
        end_date=end_date
    )
    
    if not emotion_records:
        return {
            "success": False,
            "error": "No emotion data found for analysis",
            "recommendation": "Start recording specific emotions to enable trend analysis"
        }
    
    if len(emotion_types) == 1:
        # Single emotion analysis
        return await _analyze_single_emotion(emotion_records, emotion_types[0], include_note_analysis, start_date, end_date)
    else:
        # Multi-emotion analysis
        return await _analyze_multiple_emotions(emotion_records, include_note_analysis, start_date, end_date)


async def _analyze_single_emotion(
    emotion_records: List[Dict], emotion_type: str, include_note_analysis: bool,
    start_date: str, end_date: str
) -> Dict[str, Any]:
    """Analyze trends for a single emotion type."""
    scores = [r.get("emotion_score", 5) for r in emotion_records]
    avg_intensity = sum(scores) / len(scores)
    
    # Trend calculation
    if len(scores) >= 5:
        recent_avg = sum(scores[-5:]) / 5
        earlier_avg = sum(scores[:-5]) / len(scores[:-5]) if len(scores) > 5 else avg_intensity
        if recent_avg > earlier_avg + 0.5:
            trend = "intensifying"
        elif recent_avg < earlier_avg - 0.5:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    # Trigger analysis
    all_triggers = []
    for record in emotion_records:
        all_triggers.extend(record.get("triggers", []))
    
    trigger_counts = {}
    for trigger in all_triggers:
        if trigger:
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
    
    common_triggers = sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Note analysis
    note_insights = []
    if include_note_analysis:
        notes = [r.get("emotion_notes", "") for r in emotion_records if r.get("emotion_notes")]
        if notes:
            note_insights = await _analyze_notes_sentiment(notes, "single_emotion")
    
    return {
        "success": True,
        "analysis_type": "single_emotion",
        "emotion_type": emotion_type,
        "date_range": f"{start_date} to {end_date}",
        "total_records": len(emotion_records),
        "average_intensity": round(avg_intensity, 2),
        "min_intensity": min(scores),
        "max_intensity": max(scores),
        "intensity_trend": trend,
        "common_triggers": [{"trigger": t, "count": c} for t, c in common_triggers],
        "note_insights": note_insights,
        "recommendations": await _get_emotion_trend_recommendations(emotion_type, avg_intensity, trend, common_triggers)
    }


async def _analyze_multiple_emotions(
    emotion_records: List[Dict], include_note_analysis: bool,
    start_date: str, end_date: str
) -> Dict[str, Any]:
    """Analyze trends and correlations for multiple emotions."""
    # Group by emotion type
    emotion_groups = {}
    for record in emotion_records:
        etype = record.get("emotion_type", "unknown")
        if etype not in emotion_groups:
            emotion_groups[etype] = []
        emotion_groups[etype].append(record)
    
    # Analyze each emotion
    emotion_analysis = {}
    for etype, records in emotion_groups.items():
        scores = [r.get("emotion_score", 5) for r in records]
        emotion_analysis[etype] = {
            "count": len(records),
            "average_intensity": round(sum(scores) / len(scores), 2),
            "intensity_range": [min(scores), max(scores)]
        }
    
    # Calculate basic correlations (simplified)
    correlations = {}
    emotion_types = list(emotion_groups.keys())
    for i, etype1 in enumerate(emotion_types):
        for etype2 in emotion_types[i+1:]:
            # Simple correlation based on same-day occurrences
            correlation_strength = await _calculate_emotion_correlation(emotion_groups[etype1], emotion_groups[etype2])
            if correlation_strength > 0.3:  # Only include meaningful correlations
                correlations[f"{etype1}_vs_{etype2}"] = correlation_strength
    
    return {
        "success": True,
        "analysis_type": "multiple_emotions",
        "date_range": f"{start_date} to {end_date}",
        "total_records": len(emotion_records),
        "emotion_breakdown": emotion_analysis,
        "emotion_correlations": correlations,
        "recommendations": await _get_multi_emotion_recommendations(emotion_analysis, correlations)
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _get_emotion_based_recommendations(emotion_type: str, emotion_score: int) -> List[str]:
    """Generate recommendations based on specific emotion and intensity."""
    recommendations = []
    
    if emotion_score >= 8:  # High intensity
        if emotion_type in ["anxiety", "stress", "overwhelm"]:
            recommendations.extend([
                "Practice immediate calming techniques (deep breathing, grounding)",
                "Consider reducing stimulation and finding a quiet space",
                "Try progressive muscle relaxation or meditation"
            ])
        elif emotion_type in ["anger", "frustration", "irritation"]:
            recommendations.extend([
                "Take a break before responding to triggers",
                "Try physical release like walking or stretching",
                "Practice the STOP technique (Stop, Take a breath, Observe, Proceed)"
            ])
        elif emotion_type in ["sadness", "grief", "despair"]:
            recommendations.extend([
                "Allow yourself to feel the emotion without judgment",
                "Consider reaching out to a supportive friend or professional",
                "Engage in gentle, nurturing self-care activities"
            ])
    
    if emotion_score <= 3:  # Low intensity but still present
        recommendations.extend([
            f"Notice the presence of {emotion_type} without amplifying it",
            "Use this as an opportunity to practice emotional awareness",
            f"Consider what might be triggering the {emotion_type}"
        ])
    
    return recommendations


async def _get_emotion_trend_recommendations(emotion_type: str, avg_intensity: float, 
                                           trend: str, common_triggers: List) -> List[str]:
    """Generate recommendations based on emotion trend analysis."""
    recommendations = []
    
    if trend == "intensifying":
        recommendations.append(f"Your {emotion_type} is becoming more intense. Consider preventive strategies.")
        
        if common_triggers:
            top_trigger = common_triggers[0][0]
            recommendations.append(f"Focus on managing '{top_trigger}' as it's your most common trigger.")
    
    elif trend == "decreasing":
        recommendations.append(f"Your {emotion_type} intensity is decreasing - keep up the positive practices!")
    
    if avg_intensity >= 7:
        recommendations.append(f"High average {emotion_type} detected. Consider professional support if persistent.")
    
    return recommendations


async def _get_multi_emotion_recommendations(emotion_analysis: Dict, correlations: Dict) -> List[str]:
    """Generate recommendations for multi-emotion patterns."""
    recommendations = []
    
    # Check for concerning emotion combinations
    high_intensity_emotions = [etype for etype, data in emotion_analysis.items() 
                             if data["average_intensity"] >= 7]
    
    if len(high_intensity_emotions) >= 2:
        recommendations.append("Multiple high-intensity emotions detected. Consider comprehensive stress management.")
    
    # Check correlations
    if correlations:
        strongest_correlation = max(correlations.items(), key=lambda x: x[1])
        emotions_pair = strongest_correlation[0].replace("_vs_", " and ")
        recommendations.append(f"Strong correlation found between {emotions_pair}. Consider addressing them together.")
    
    return recommendations


async def _calculate_emotion_correlation(emotion1_records: List[Dict], emotion2_records: List[Dict]) -> float:
    """Calculate simple correlation between two emotions based on same-day occurrences."""
    # Get dates for each emotion
    dates1 = set(r.get("date") for r in emotion1_records)
    dates2 = set(r.get("date") for r in emotion2_records)
    
    # Calculate overlap
    overlap = len(dates1.intersection(dates2))
    total_unique_dates = len(dates1.union(dates2))
    
    # Simple correlation metric
    return overlap / total_unique_dates if total_unique_dates > 0 else 0


async def _analyze_notes_sentiment(notes: List[str], analysis_context: str = "mood_trend") -> List[str]:
    """Advanced LLM-based analysis of mood/emotion notes for deep insights."""
    if not notes:
        return ["No notes available for analysis"]
    
    # Enhanced LLM Analysis similar to habit manager approach
    llm_insights = await _analyze_mood_notes_with_llm(notes, analysis_context)
    
    # Fallback to basic analysis if LLM fails
    if "error" in llm_insights:
        return await _basic_sentiment_analysis(notes)
    
    # Extract insights from LLM analysis
    insights = []
    
    if isinstance(llm_insights, dict):
        # Add pattern insights
        if "patterns" in llm_insights and isinstance(llm_insights["patterns"], list):
            insights.extend(llm_insights["patterns"])
        
        # Add mood insights
        if "mood_insights" in llm_insights:
            insights.append(llm_insights["mood_insights"])
        
        # Add key learnings
        if "key_learnings" in llm_insights and isinstance(llm_insights["key_learnings"], list):
            insights.extend(llm_insights["key_learnings"])
        
        # Add progress assessment
        if "progress_assessment" in llm_insights:
            insights.append(f"Progress: {llm_insights['progress_assessment']}")
    
    return insights if insights else await _basic_sentiment_analysis(notes)


async def _analyze_mood_notes_with_llm(notes: List[str], analysis_context: str = "mood_trend") -> Dict[str, Any]:
    """Use LLM to analyze mood/emotion notes for deeper insights."""
    try:
        # Prepare notes content
        notes_text = "\n".join([f"Entry {i+1}: {note}" for i, note in enumerate(notes)])
        
        # Load appropriate prompt template based on context
        try:
            import os
            if analysis_context == "single_emotion":
                prompt_file = "emotion_analysis.txt"
            else:  # Default to mood_trend
                prompt_file = "mood_trend_analysis.txt"
            
            prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", prompt_file)
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            analysis_prompt = prompt_template.format(notes_text=notes_text)
        except Exception as e:
            # Fallback to original prompt if file loading fails
            analysis_prompt = f"""Analyze mood and emotion diary entries for patterns and insights. Respond with valid JSON only.

DIARY ENTRIES:
{notes_text}

Analyze for emotional patterns, triggers, coping strategies, and progress indicators. Return JSON with:
{{
  "patterns": ["emotional pattern1", "behavioral pattern2"],
  "triggers": {{"positive": ["trigger1"], "negative": ["trigger2"]}},
  "mood_insights": "overall mood progression and correlation description",
  "key_learnings": ["insight1", "insight2"],
  "recommendations": ["action1", "action2"],
  "progress_assessment": "improvement/decline/stable with description",
  "emotional_themes": ["theme1", "theme2"],
  "coping_strategies_observed": ["strategy1", "strategy2"],
  "confidence_score": 8
}}

Focus on actionable therapeutic insights from emotional content."""

        # Import Hugging Face client if available
        try:
            from huggingface_hub import AsyncInferenceClient
            import json
            import os
            
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
                {"role": "system", "content": "You are an expert therapist and emotional intelligence coach. Always respond with valid JSON only, no additional text."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # Call Hugging Face model
            response = await client.chat_completion(
                messages=messages,
                model=model_name,
                max_tokens=1500,
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
                    "fallback": "Using basic sentiment analysis only"
                }
            elif "unauthorized" in error_msg.lower() or "401" in error_msg:
                return {
                    "error": "Invalid Hugging Face API token",
                    "suggestion": "Check your HUGGINGFACE_API_TOKEN environment variable",
                    "fallback": "Using basic sentiment analysis only"
                }
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                return {
                    "error": f"Model {model_name} not found or not accessible",
                    "suggestion": "Try a different model in HF_MODEL environment variable",
                    "fallback": "Using basic sentiment analysis only"
                }
            else:
                return {
                    "error": f"LLM analysis failed: {error_msg}",
                    "fallback": "Using basic sentiment analysis only"
                }
            
    except Exception as e:
        return {
            "error": f"Analysis preparation failed: {str(e)}",
            "fallback": "Using basic sentiment analysis only"
        }


async def _basic_sentiment_analysis(notes: List[str]) -> List[str]:
    """Basic sentiment analysis fallback when LLM is not available."""
    # Original simple sentiment analysis - kept as fallback
    positive_words = ["good", "happy", "great", "better", "calm", "peaceful", "grateful", "content", "joyful", "excited", "proud", "confident"]
    negative_words = ["bad", "sad", "awful", "worse", "anxious", "stressed", "overwhelmed", "depressed", "angry", "frustrated", "hopeless", "worried"]
    coping_words = ["meditation", "exercise", "therapy", "breathe", "relax", "walk", "music", "friend", "family", "journal"]
    
    insights = []
    all_text = " ".join(notes).lower()
    
    positive_count = sum(1 for word in positive_words if word in all_text)
    negative_count = sum(1 for word in negative_words if word in all_text)
    coping_count = sum(1 for word in coping_words if word in all_text)
    
    if positive_count > negative_count * 1.5:
        insights.append("Overall positive sentiment detected in your notes")
    elif negative_count > positive_count * 1.5:
        insights.append("Negative sentiment patterns found - consider focusing on self-care")
    else:
        insights.append("Mixed sentiment in notes - normal emotional complexity")
    
    if coping_count > 0:
        insights.append("Positive coping strategies mentioned in your entries")
    
    if len(notes) >= 5:
        insights.append("Consistent journaling practice developing - great for emotional awareness")
    
    return insights 