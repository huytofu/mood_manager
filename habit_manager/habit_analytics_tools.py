"""
Habit Analytics Tools
====================
Advanced analytics tools for habit insights, patterns, correlations, and recommendations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from datetime import datetime, timedelta
import uuid

# Import analytics functions
from utils.habit_analytics import (
    _get_habit_insights_from_notes,
    _get_mood_based_recommendations,
    _get_all_user_completions,
    _get_mood_records,
    _calculate_basic_habit_trends,
    _calculate_basic_epic_progress,
)

from utils.habit_core import (
    _get_habit_by_id,
    _get_epic_habit_by_id,
    _get_user_active_habits,
)

# =============================================================================
# ANALYTICS TOOL SCHEMAS
# =============================================================================

class AnalyzeUnderperformingHabitsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(default="monthly", description="Time period for analysis")
    threshold: float = Field(default=0.3, description="Completion rate threshold below which habits are considered underperforming")

class AnalyzeLaggingEpicProgressInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    epic_habit_id: str = Field(..., description="Epic habit identifier")
    target_progress_rate: Optional[float] = Field(default=None, description="Expected progress rate, if None calculates from target_completion_date")

class AnalyzeHabitInteractionsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(default="monthly", description="Time period for analysis")
    interaction_type: str = Field(default="all", description="Type of interactions to detect: synchronous, antagonistic, or all")

class AnalyzeMoodHabitCorrelationInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    habit_id: Optional[str] = Field(default=None, description="Specific habit ID, or None for all habits")
    time_period: str = Field(default="monthly", description="Time period for analysis")

class GenerateHabitInsightsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    habit_id: Optional[str] = Field(default=None, description="Specific habit ID, or None for all habits")
    insight_type: str = Field(default="comprehensive", description="Type of insights: completion_patterns, timing_optimization, comprehensive")
    underperformance_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Results from analyze_underperforming_habits")
    epic_progress_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Results from analyze_lagging_epic_progress")
    interaction_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Results from analyze_habit_interactions")
    mood_correlation_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Results from analyze_mood_habit_correlation")

class RecommendMoodSupportingHabitsInput(BaseModel):
    mood_state: str = Field(..., description="Current mood state: 'stress' or 'depression'")
    is_crisis: bool = Field(default=False, description="Whether user is in crisis state")
    is_depressed: bool = Field(default=False, description="Whether user is depressed")
    crisis_level: int = Field(default=0, description="Crisis level 0-10 for stress gradation")

# =============================================================================
# ADVANCED ANALYTICS TOOLS
# =============================================================================

@tool("analyze_underperforming_habits", args_schema=AnalyzeUnderperformingHabitsInput)
async def analyze_underperforming_habits(
    user_id: str, time_period: str = "monthly", threshold: float = 0.3
) -> Dict[str, Any]:
    """
    Tool Purpose: Identify habits with low completion rates that need attention.
    
    Args:
    - user_id (str): User identifier
    - time_period (str): Time period for analysis (weekly, monthly)
    - threshold (float): Completion rate threshold (0.0-1.0)
    
    Returns:
    - Dict containing: success (bool), underperforming_habits (list), recommendations (list)
    """
    try:
        # Get user's active habits
        active_habits = await _get_user_active_habits(user_id)
        
        if not active_habits:
            return {
                "success": True,
                "underperforming_habits": [],
                "message": "No active habits found for user",
                "recommendations": ["Consider creating some habits to start building positive routines"]
            }
        
        underperforming = []
        
        # Analyze each habit
        for habit in active_habits:
            habit_id = habit["habit_id"]
            
            # Calculate completion trends
            trends_result = await _calculate_basic_habit_trends(habit_id, time_period)
            
            if trends_result["success"]:
                completion_rate = trends_result["trends"]["completion_rate"] / 100
                
                if completion_rate < threshold:
                    underperforming.append({
                        "habit_id": habit_id,
                        "habit_name": habit.get("name", "Unknown"),
                        "category": habit.get("category", "other"),
                        "completion_rate": completion_rate,
                        "completion_percentage": round(completion_rate * 100, 2),
                        "trend_direction": trends_result["trends"]["trend_direction"],
                        "current_streak": trends_result["trends"]["streak_info"]["current_streak"],
                        "difficulty_level": habit.get("difficulty_level", "easy"),
                        "intrinsic_score": habit.get("intrinsic_score", 1)
                    })
        
        # Generate recommendations
        recommendations = []
        if underperforming:
            recommendations.append(f"Found {len(underperforming)} habits below {threshold*100}% completion rate")
            
            # Categorize issues
            high_difficulty = [h for h in underperforming if h["difficulty_level"] == "hard"]
            low_streak = [h for h in underperforming if h["current_streak"] == 0]
            declining = [h for h in underperforming if h["trend_direction"] == "declining"]
            
            if high_difficulty:
                recommendations.append("Consider reducing difficulty for challenging habits that aren't sticking")
            if low_streak:
                recommendations.append("Focus on rebuilding momentum for habits with broken streaks")
            if declining:
                recommendations.append("Investigate recent changes that may have caused declining performance")
                
            recommendations.extend([
                "Review timing and triggers for underperforming habits",
                "Consider pausing some habits to focus on fewer, more achievable goals",
                "Add habit notes to track what's working and what isn't"
            ])
        else:
            recommendations.append("Great job! All habits are performing above the threshold")
            recommendations.append("Consider gradually increasing difficulty or adding new habits")
        
        return {
            "success": True,
            "underperforming_habits": underperforming,
            "total_habits_analyzed": len(active_habits),
            "threshold_used": threshold,
            "time_period": time_period,
            "recommendations": recommendations
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error analyzing underperforming habits: {str(e)}",
            "underperforming_habits": [],
            "recommendations": []
        }

@tool("analyze_lagging_epic_progress", args_schema=AnalyzeLaggingEpicProgressInput)
async def analyze_lagging_epic_progress(
    user_id: str, epic_habit_id: str, target_progress_rate: Optional[float] = None
) -> Dict[str, Any]:
    """
    Tool Purpose: Analyze epic habit progress and identify if it's lagging behind schedule.
    
    Args:
    - user_id (str): User identifier
    - epic_habit_id (str): Epic habit identifier
    - target_progress_rate (Optional[float]): Expected progress rate
    
    Returns:
    - Dict containing: success (bool), progress_analysis (dict), recommendations (list)
    """
    try:
        # Get epic habit details
        epic_habit = await _get_epic_habit_by_id(epic_habit_id)
        if not epic_habit:
            return {"success": False, "error": "Epic habit not found"}
        
        if epic_habit.get("user_id") != user_id:
            return {"success": False, "error": "Epic habit does not belong to this user"}
        
        # Calculate current progress
        progress_result = await _calculate_basic_epic_progress(epic_habit_id, "all_time")
        
        if not progress_result["success"]:
            return {"success": False, "error": "Failed to calculate epic progress"}
        
        current_progress = progress_result["progress"]["overall_progress"]
        target_date = epic_habit.get("target_completion_date")
        created_date = epic_habit.get("created_date", datetime.now().isoformat())[:10]
        
        # Calculate expected progress
        if target_date:
            try:
                target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                created_dt = datetime.strptime(created_date, "%Y-%m-%d")
                total_days = (target_dt - created_dt).days
                elapsed_days = (datetime.now() - created_dt).days
                
                if total_days > 0:
                    expected_progress = (elapsed_days / total_days) * 100
                    expected_progress = min(expected_progress, 100)  # Cap at 100%
                else:
                    expected_progress = 100  # Past due date
                    
                progress_gap = current_progress - expected_progress
                is_lagging = progress_gap < -10  # More than 10% behind
                days_remaining = max(0, (target_dt - datetime.now()).days)
                
            except ValueError:
                expected_progress = None
                progress_gap = None
                is_lagging = None
                days_remaining = None
        else:
            expected_progress = None
            progress_gap = None
            is_lagging = None
            days_remaining = None
        
        # Analyze micro habits performance
        micro_habits = progress_result["progress"]["micro_habit_details"]
        low_performing_micros = [h for h in micro_habits if h["completion_rate"] < 50]
        high_priority_low = [h for h in low_performing_micros if h["priority"] == "high"]
        
        # Generate recommendations
        recommendations = []
        
        if is_lagging:
            recommendations.append(f"Epic goal is {abs(progress_gap):.1f}% behind schedule")
            recommendations.append(f"With {days_remaining} days remaining, need to accelerate progress")
            
            if high_priority_low:
                recommendations.append("Focus on improving high-priority micro habits first")
                for habit in high_priority_low[:3]:  # Top 3
                    recommendations.append(f"- Improve '{habit['habit_name']}' (currently {habit['completion_rate']:.1f}%)")
            
            recommendations.extend([
                "Consider adjusting target date if goals are too ambitious",
                "Review and potentially simplify some micro habits",
                "Add more frequent check-ins and progress reviews"
            ])
        elif progress_gap is not None and progress_gap > 10:
            recommendations.append(f"Epic goal is {progress_gap:.1f}% ahead of schedule - excellent progress!")
            recommendations.append("Consider adding stretch goals or new micro habits")
        else:
            recommendations.append("Epic goal progress is on track")
            recommendations.append("Maintain current momentum and consistency")
        
        return {
            "success": True,
            "epic_habit_id": epic_habit_id,
            "epic_name": epic_habit.get("name", "Unknown"),
            "progress_analysis": {
                "current_progress": current_progress,
                "expected_progress": expected_progress,
                "progress_gap": progress_gap,
                "is_lagging": is_lagging,
                "days_remaining": days_remaining,
                "target_date": target_date,
                "micro_habits_count": len(micro_habits),
                "low_performing_micros": len(low_performing_micros),
                "high_priority_struggling": len(high_priority_low)
            },
            "micro_habit_details": micro_habits,
            "recommendations": recommendations
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error analyzing epic progress: {str(e)}",
            "recommendations": []
        }

@tool("analyze_habit_interactions", args_schema=AnalyzeHabitInteractionsInput)
async def analyze_habit_interactions(
    user_id: str, time_period: str = "monthly", interaction_type: str = "all"
) -> Dict[str, Any]:
    """
    Tool Purpose: Analyze how habits interact with each other (synergies and conflicts).
    
    Args:
    - user_id (str): User identifier
    - time_period (str): Time period for analysis
    - interaction_type (str): Type of interactions to detect
    
    Returns:
    - Dict containing: success (bool), interactions (dict), insights (list)
    """
    try:
        # Get user completions for the period
        completions = await _get_all_user_completions(user_id, time_period)
        
        if not completions:
            return {
                "success": True,
                "interactions": {"synchronous": [], "antagonistic": []},
                "insights": ["Not enough completion data to analyze habit interactions"],
                "message": "Need more completion data for interaction analysis"
            }
        
        # Group completions by date
        daily_completions = {}
        for completion in completions:
            date = completion.get("date")
            if date not in daily_completions:
                daily_completions[date] = []
            daily_completions[date].append(completion)
        
        # Get unique habits
        habit_ids = list(set(c.get("habit_id") for c in completions))
        
        if len(habit_ids) < 2:
            return {
                "success": True,
                "interactions": {"synchronous": [], "antagonistic": []},
                "insights": ["Need at least 2 habits to analyze interactions"],
                "message": "Insufficient habits for interaction analysis"
            }
        
        # Calculate habit correlations
        synchronous_pairs = []
        antagonistic_pairs = []
        
        for i, habit1_id in enumerate(habit_ids):
            for habit2_id in habit_ids[i+1:]:
                correlation = await _calculate_habit_correlation(habit1_id, habit2_id, daily_completions)
                
                habit1 = await _get_habit_by_id(habit1_id)
                habit2 = await _get_habit_by_id(habit2_id)
                
                if habit1 and habit2:
                    habit1_name = habit1.get("name", "Unknown")
                    habit2_name = habit2.get("name", "Unknown")
                    habit1_type = habit1.get("habit_type", "formation")
                    habit2_type = habit2.get("habit_type", "formation")
                    
                    interaction_data = {
                        "habit1_id": habit1_id,
                        "habit1_name": habit1_name,
                        "habit1_type": habit1_type,
                        "habit2_id": habit2_id,
                        "habit2_name": habit2_name,
                        "habit2_type": habit2_type,
                        "correlation": correlation,
                        "strength": _get_correlation_strength(correlation),
                        "interpretation": _interpret_habit_correlation(correlation, habit1_type, habit2_type)
                    }
                    
                    if correlation > 0.3:  # Strong positive correlation
                        synchronous_pairs.append(interaction_data)
                    elif correlation < -0.3:  # Strong negative correlation
                        antagonistic_pairs.append(interaction_data)
        
        # Sort by correlation strength
        synchronous_pairs.sort(key=lambda x: x["correlation"], reverse=True)
        antagonistic_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        
        # Generate insights
        insights = []
        
        if synchronous_pairs:
            insights.append(f"Found {len(synchronous_pairs)} habit synergies")
            for pair in synchronous_pairs[:3]:  # Top 3
                insights.append(f"- {pair['habit1_name']} and {pair['habit2_name']} reinforce each other")
        
        if antagonistic_pairs:
            insights.append(f"Found {len(antagonistic_pairs)} habit conflicts")
            for pair in antagonistic_pairs[:3]:  # Top 3
                insights.append(f"- {pair['habit1_name']} and {pair['habit2_name']} may interfere with each other")
        
        if not synchronous_pairs and not antagonistic_pairs:
            insights.append("No strong habit interactions detected")
            insights.append("Habits appear to be largely independent")
        
        return {
            "success": True,
            "interactions": {
                "synchronous": synchronous_pairs,
                "antagonistic": antagonistic_pairs
            },
            "insights": insights,
            "time_period": time_period,
            "total_habits_analyzed": len(habit_ids)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error analyzing habit interactions: {str(e)}",
            "interactions": {"synchronous": [], "antagonistic": []},
            "insights": []
        }

@tool("analyze_mood_habit_correlation", args_schema=AnalyzeMoodHabitCorrelationInput)
async def analyze_mood_habit_correlation(
    user_id: str, habit_id: Optional[str] = None, time_period: str = "monthly"
) -> Dict[str, Any]:
    """
    Tool Purpose: Analyze correlation between mood and habit performance.
    
    Args:
    - user_id (str): User identifier
    - habit_id (Optional[str]): Specific habit or None for all habits
    - time_period (str): Time period for analysis
    
    Returns:
    - Dict containing: success (bool), correlations (dict), insights (list)
    """
    try:
        # Get mood records and habit completions
        mood_records = await _get_mood_records(user_id, time_period)
        habit_completions = await _get_all_user_completions(user_id, time_period)
        
        if not mood_records:
            return {
                "success": True,
                "correlations": {},
                "insights": ["No mood data available for correlation analysis"],
                "message": "Mood tracking needed for correlation analysis"
            }
        
        if not habit_completions:
            return {
                "success": True,
                "correlations": {},
                "insights": ["No habit completion data available"],
                "message": "Habit completion data needed for analysis"
            }
        
        # Filter by specific habit if provided
        if habit_id:
            habit_completions = [c for c in habit_completions if c.get("habit_id") == habit_id]
            if not habit_completions:
                return {"success": False, "error": "No completion data found for specified habit"}
        
        # Calculate correlations
        correlations = {}
        
        if habit_id:
            # Single habit analysis
            habit = await _get_habit_by_id(habit_id)
            habit_name = habit.get("name", "Unknown") if habit else "Unknown"
            
            mood_correlation = await _calculate_correlation_with_mood_scores(habit_completions, mood_records)
            crisis_correlation = await _calculate_correlation_with_flags(habit_completions, mood_records, "is_crisis")
            depression_correlation = await _calculate_correlation_with_flags(habit_completions, mood_records, "is_depressed")
            
            correlations[habit_id] = {
                "habit_name": habit_name,
                "mood_score_correlation": mood_correlation,
                "crisis_correlation": crisis_correlation,
                "depression_correlation": depression_correlation
            }
        else:
            # All habits analysis
            habit_ids = list(set(c.get("habit_id") for c in habit_completions))
            
            for hid in habit_ids:
                habit = await _get_habit_by_id(hid)
                habit_name = habit.get("name", "Unknown") if habit else "Unknown"
                
                habit_data = [c for c in habit_completions if c.get("habit_id") == hid]
                
                mood_correlation = await _calculate_correlation_with_mood_scores(habit_data, mood_records)
                crisis_correlation = await _calculate_correlation_with_flags(habit_data, mood_records, "is_crisis")
                depression_correlation = await _calculate_correlation_with_flags(habit_data, mood_records, "is_depressed")
                
                correlations[hid] = {
                    "habit_name": habit_name,
                    "mood_score_correlation": mood_correlation,
                    "crisis_correlation": crisis_correlation,
                    "depression_correlation": depression_correlation
                }
        
        # Generate insights
        insights = []
        strong_mood_correlations = []
        strong_crisis_correlations = []
        
        for hid, data in correlations.items():
            if abs(data["mood_score_correlation"]) > 0.3:
                strong_mood_correlations.append((data["habit_name"], data["mood_score_correlation"]))
            if abs(data["crisis_correlation"]) > 0.3:
                strong_crisis_correlations.append((data["habit_name"], data["crisis_correlation"]))
        
        if strong_mood_correlations:
            insights.append(f"Found {len(strong_mood_correlations)} habits with strong mood correlations")
            for habit_name, correlation in strong_mood_correlations:
                if correlation > 0:
                    insights.append(f"- {habit_name} performance improves with better mood")
                else:
                    insights.append(f"- {habit_name} becomes harder when mood is low")
        
        if strong_crisis_correlations:
            insights.append("Some habits are significantly affected by crisis periods")
            for habit_name, correlation in strong_crisis_correlations:
                if correlation < 0:
                    insights.append(f"- {habit_name} drops during crisis periods")
        
        # Generate recommendations
        recommendations = await _generate_correlation_recommendations(correlations, insights)
        
        return {
            "success": True,
            "correlations": correlations,
            "insights": insights,
            "recommendations": recommendations,
            "time_period": time_period,
            "mood_records_count": len(mood_records)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error analyzing mood-habit correlation: {str(e)}",
            "correlations": {},
            "insights": []
        }

@tool("generate_habit_insights", args_schema=GenerateHabitInsightsInput)
async def generate_habit_insights(
    user_id: str, 
    habit_id: Optional[str] = None, 
    insight_type: str = "comprehensive",
    underperformance_analysis: Optional[Dict[str, Any]] = None,
    epic_progress_analysis: Optional[Dict[str, Any]] = None,
    interaction_analysis: Optional[Dict[str, Any]] = None,
    mood_correlation_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tool Purpose: Generate comprehensive behavioral insights from habit data.
    
    Args:
    - user_id (str): User identifier
    - habit_id (Optional[str]): Specific habit or None for all habits
    - insight_type (str): Type of insights to generate
    - Various analysis inputs from other analytics tools
    
    Returns:
    - Dict containing: success (bool), insights (list), patterns (dict), recommendations (list)
    """
    try:
        insights = []
        patterns = {}
        recommendations = []
        
        # Get habit details
        if habit_id:
            habit = await _get_habit_by_id(habit_id)
            if not habit:
                return {"success": False, "error": "Habit not found"}
            
            habit_name = habit.get("name", "Unknown")
            insights.append(f"Analyzing patterns for: {habit_name}")
            
            # Get habit-specific insights from notes
            notes_insights = await _get_habit_insights_from_notes(habit_id, 30)
            if notes_insights["success"] and notes_insights.get("insights"):
                patterns["notes_analysis"] = notes_insights["insights"]
                if "llm_analysis" in notes_insights["insights"]:
                    llm_data = notes_insights["insights"]["llm_analysis"]
                    if isinstance(llm_data, dict) and "patterns" in llm_data:
                        insights.extend(llm_data.get("patterns", []))
                    if isinstance(llm_data, dict) and "recommendations" in llm_data:
                        recommendations.extend(llm_data.get("recommendations", []))
        else:
            # All habits analysis
            active_habits = await _get_user_active_habits(user_id)
            insights.append(f"Analyzing patterns across {len(active_habits)} active habits")
        
        # Integrate external analysis results
        if underperformance_analysis:
            patterns["underperformance"] = underperformance_analysis
            underperforming = underperformance_analysis.get("underperforming_habits", [])
            if underperforming:
                insights.append(f"Identified {len(underperforming)} underperforming habits")
                recommendations.extend(underperformance_analysis.get("recommendations", []))
        
        if epic_progress_analysis:
            patterns["epic_progress"] = epic_progress_analysis
            progress_data = epic_progress_analysis.get("progress_analysis", {})
            if progress_data.get("is_lagging"):
                insights.append("Epic goal progress is behind schedule")
                recommendations.extend(epic_progress_analysis.get("recommendations", []))
        
        if interaction_analysis:
            patterns["interactions"] = interaction_analysis
            synergies = len(interaction_analysis.get("interactions", {}).get("synchronous", []))
            conflicts = len(interaction_analysis.get("interactions", {}).get("antagonistic", []))
            if synergies:
                insights.append(f"Found {synergies} beneficial habit synergies")
            if conflicts:
                insights.append(f"Detected {conflicts} potential habit conflicts")
        
        if mood_correlation_analysis:
            patterns["mood_correlations"] = mood_correlation_analysis
            insights.extend(mood_correlation_analysis.get("insights", []))
            recommendations.extend(mood_correlation_analysis.get("recommendations", []))
        
        # Generate summary insights based on insight_type
        if insight_type == "completion_patterns":
            completion_insights = await _generate_completion_insights(patterns)
            insights.extend(completion_insights)
        elif insight_type == "timing_optimization":
            timing_insights = await _generate_timing_insights(patterns)
            insights.extend(timing_insights)
        elif insight_type == "comprehensive":
            overall_insights = await _generate_overall_insights(patterns)
            insights.extend(overall_insights)
            
            overall_recommendations = await _generate_overall_recommendations(patterns)
            recommendations.extend(overall_recommendations)
        
        # Remove duplicates while preserving order
        insights = list(dict.fromkeys(insights))
        recommendations = list(dict.fromkeys(recommendations))
        
        return {
            "success": True,
            "user_id": user_id,
            "habit_id": habit_id,
            "insight_type": insight_type,
            "insights": insights,
            "patterns": patterns,
            "recommendations": recommendations,
            "analysis_sources": {
                "underperformance_included": underperformance_analysis is not None,
                "epic_progress_included": epic_progress_analysis is not None,
                "interactions_included": interaction_analysis is not None,
                "mood_correlations_included": mood_correlation_analysis is not None,
                "notes_analysis_included": habit_id is not None
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating insights: {str(e)}",
            "insights": [],
            "patterns": {},
            "recommendations": []
        }

@tool("recommend_mood_supporting_habits", args_schema=RecommendMoodSupportingHabitsInput)
async def recommend_mood_supporting_habits(
    mood_state: str, is_crisis: bool = False, is_depressed: bool = False, crisis_level: int = 0
) -> List[str]:
    """
    Tool Purpose: Recommend habits that support specific mood states.
    
    Args:
    - mood_state (str): Current mood state
    - is_crisis (bool): Whether user is in crisis
    - is_depressed (bool): Whether user is depressed
    - crisis_level (int): Crisis level 0-10
    
    Returns:
    - List of habit recommendations
    """
    try:
        recommendations = []
        
        # Base mood score estimation
        if is_crisis:
            mood_score = max(1, 3 - crisis_level)
        elif is_depressed:
            mood_score = 4
        elif mood_state == "stress":
            mood_score = 5
        elif mood_state == "depression":
            mood_score = 3
        else:
            mood_score = 6  # Default moderate mood
        
        # Get mood-based recommendations
        mood_recommendations = await _get_mood_based_recommendations(mood_score, is_crisis, is_depressed)
        recommendations.extend(mood_recommendations)
        
        # Add specific recommendations based on mood state
        if mood_state == "stress":
            recommendations.extend([
                "Practice deep breathing exercises for 5 minutes",
                "Take short walks during breaks",
                "Limit caffeine intake",
                "Set boundaries on work/technology time",
                "Practice progressive muscle relaxation"
            ])
        elif mood_state == "depression":
            recommendations.extend([
                "Maintain a consistent sleep schedule",
                "Engage in gentle physical activity",
                "Practice gratitude journaling",
                "Connect with supportive friends or family",
                "Spend time in natural light"
            ])
        
        # Remove duplicates while preserving order
        recommendations = list(dict.fromkeys(recommendations))
        
        return recommendations
        
    except Exception as e:
        return [f"Error generating recommendations: {str(e)}"]

# =============================================================================
# UTILITY FUNCTIONS FOR ANALYTICS
# =============================================================================

async def _calculate_habit_correlation(habit1_id: str, habit2_id: str, daily_completions: Dict) -> float:
    """Calculate correlation between two habits based on daily completion patterns."""
    try:
        paired_days = []
        
        for date, completions in daily_completions.items():
            habit1_score = 0
            habit2_score = 0
            
            for completion in completions:
                if completion.get("habit_id") == habit1_id:
                    habit1_score = completion.get("completion_score", 0)
                elif completion.get("habit_id") == habit2_id:
                    habit2_score = completion.get("completion_score", 0)
            
            paired_days.append((habit1_score, habit2_score))
        
        if len(paired_days) < 5:  # Need minimum data points
            return 0.0
        
        # Calculate Pearson correlation
        n = len(paired_days)
        sum_x = sum(x for x, y in paired_days)
        sum_y = sum(y for x, y in paired_days)
        sum_x2 = sum(x*x for x, y in paired_days)
        sum_y2 = sum(y*y for x, y in paired_days)
        sum_xy = sum(x*y for x, y in paired_days)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))**0.5
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
        
    except Exception:
        return 0.0

def _get_correlation_strength(correlation: float) -> str:
    """Get human-readable correlation strength."""
    abs_corr = abs(correlation)
    if abs_corr >= 0.7:
        return "very strong"
    elif abs_corr >= 0.5:
        return "strong"
    elif abs_corr >= 0.3:
        return "moderate"
    elif abs_corr >= 0.1:
        return "weak"
    else:
        return "negligible"

def _interpret_habit_correlation(correlation: float, habit1_type: str, habit2_type: str) -> Dict[str, str]:
    """Interpret the meaning of habit correlation."""
    interpretation = {
        "relationship": "",
        "recommendation": ""
    }
    
    if correlation > 0.3:
        if habit1_type == "formation" and habit2_type == "formation":
            interpretation["relationship"] = "These positive habits reinforce each other"
            interpretation["recommendation"] = "Schedule them together to maximize synergy"
        elif habit1_type == "breaking" and habit2_type == "breaking":
            interpretation["relationship"] = "These habits tend to fail together"
            interpretation["recommendation"] = "Focus on one at a time to avoid overwhelming yourself"
    elif correlation < -0.3:
        interpretation["relationship"] = "These habits tend to conflict with each other"
        interpretation["recommendation"] = "Consider scheduling them at different times or focusing on one"
    else:
        interpretation["relationship"] = "These habits appear to be independent"
        interpretation["recommendation"] = "Can be managed separately without concern for interference"
    
    return interpretation

# Import additional utility functions from analytics
async def _calculate_correlation_with_mood_scores(habit_records: List[Dict], mood_records: List[Dict]) -> float:
    """Calculate correlation between habit performance and mood scores."""
    from utils.habit_analytics import _calculate_correlation_with_mood_scores as analytics_func
    return await analytics_func(habit_records, mood_records)

async def _calculate_correlation_with_flags(habit_records: List[Dict], mood_records: List[Dict], flag: str) -> float:
    """Calculate correlation between habit performance and mood flags."""
    from utils.habit_analytics import _calculate_correlation_with_flags as analytics_func
    return await analytics_func(habit_records, mood_records, flag)

async def _generate_correlation_recommendations(correlations: Dict, insights: List[str]) -> List[str]:
    """Generate recommendations based on correlation analysis."""
    from utils.habit_analytics import _generate_correlation_recommendations as analytics_func
    return await analytics_func(correlations, insights)

async def _generate_completion_insights(patterns: Dict) -> List[str]:
    """Generate insights about completion patterns."""
    insights = []
    
    if "underperformance" in patterns:
        underperforming = patterns["underperformance"].get("underperforming_habits", [])
        if underperforming:
            avg_completion = sum(h["completion_rate"] for h in underperforming) / len(underperforming)
            insights.append(f"Underperforming habits average {avg_completion:.1f}% completion rate")
    
    return insights

async def _generate_timing_insights(patterns: Dict) -> List[str]:
    """Generate insights about timing patterns."""
    insights = []
    
    if "interactions" in patterns:
        synergies = patterns["interactions"].get("interactions", {}).get("synchronous", [])
        if synergies:
            insights.append("Some habits work better when done together")
    
    return insights

async def _generate_overall_insights(patterns: Dict) -> List[str]:
    """Generate overall insights from all patterns."""
    insights = []
    
    # Combine insights from different analysis types
    pattern_types = len([k for k in patterns.keys() if patterns[k]])
    insights.append(f"Analysis includes {pattern_types} different behavioral patterns")
    
    return insights

async def _generate_overall_recommendations(patterns: Dict) -> List[str]:
    """Generate overall recommendations from all patterns."""
    recommendations = []
    
    if "interactions" in patterns:
        recommendations.append("Consider habit timing and interactions when planning daily routines")
    
    if "mood_correlations" in patterns:
        recommendations.append("Monitor mood patterns to optimize habit scheduling")
    
    return recommendations 