"""
Omura Health AI Agent
Analyzes sleep, workouts, supplements, and overall energy to provide
personalized health recommendations. Integrates with wearable data
and manual health entries.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class HealthAI:
    """AI agent for health data analysis and personalized recommendations.

    Processes sleep logs, workout entries, supplement tracking, and nutrition
    data to produce actionable health insights and an overall energy score.
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.logger = OmuraLogger("health_ai")

    # ── Public Methods ──────────────────────────────────────────────

    def analyze_sleep(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze sleep quality from a list of sleep log entries.

        Each entry is expected to contain keys like 'date', 'hours_slept',
        'deep_sleep_pct', 'wake_ups', and optional 'notes'.

        Args:
            entries: List of sleep log dictionaries.

        Returns:
            Dictionary with overall sleep score (0-100), trend direction,
            per-night breakdown, and AI-generated recommendations.
        """
        self.logger.info(
            "Analyzing sleep data",
            entry_count=len(entries),
        )

        if not entries:
            self.logger.warning("No sleep entries provided for analysis")
            return {
                "score": 0.0,
                "trend": "insufficient_data",
                "nights_analyzed": 0,
                "recommendations": [
                    "Start logging your sleep to receive personalized insights."
                ],
            }

        total_hours = sum(e.get("hours_slept", 0) for e in entries)
        avg_hours = total_hours / len(entries)
        avg_deep = (
            sum(e.get("deep_sleep_pct", 0) for e in entries) / len(entries)
        )
        avg_wakeups = (
            sum(e.get("wake_ups", 0) for e in entries) / len(entries)
        )

        # Heuristic score before AI refinement
        base_score = min(100.0, max(0.0, (avg_hours / 8.0) * 60 + avg_deep * 0.4 - avg_wakeups * 5))

        prompt = (
            f"Analyze sleep data: avg {avg_hours:.1f} hrs/night, "
            f"{avg_deep:.0f}% deep sleep, {avg_wakeups:.1f} wake-ups/night "
            f"over {len(entries)} nights."
        )
        ai_response = self._call_ai(prompt, context={"entries_summary": {
            "avg_hours": round(avg_hours, 1),
            "avg_deep_pct": round(avg_deep, 1),
            "avg_wakeups": round(avg_wakeups, 1),
        }})

        result = {
            "score": round(base_score, 1),
            "trend": self._compute_trend([e.get("hours_slept", 0) for e in entries]),
            "nights_analyzed": len(entries),
            "averages": {
                "hours_per_night": round(avg_hours, 1),
                "deep_sleep_pct": round(avg_deep, 1),
                "wake_ups_per_night": round(avg_wakeups, 1),
            },
            "recommendations": ai_response.get("recommendations", []),
            "analysis_summary": ai_response.get("summary", ""),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Sleep analysis complete",
            score=result["score"],
            trend=result["trend"],
        )
        return result

    def analyze_workouts(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze workout data for volume, consistency, and progression.

        Each entry is expected to contain keys like 'date', 'type', 'duration_min',
        'intensity' (1-10), and optional 'exercises' list.

        Args:
            entries: List of workout log dictionaries.

        Returns:
            Dictionary with consistency score, weekly volume, muscle-group
            balance, and suggestions for improvement.
        """
        self.logger.info(
            "Analyzing workout data",
            entry_count=len(entries),
        )

        if not entries:
            self.logger.warning("No workout entries provided for analysis")
            return {
                "consistency_score": 0.0,
                "weekly_volume_min": 0,
                "sessions_analyzed": 0,
                "suggestions": [
                    "Begin logging workouts to get personalized training insights."
                ],
            }

        total_duration = sum(e.get("duration_min", 0) for e in entries)
        avg_intensity = (
            sum(e.get("intensity", 5) for e in entries) / len(entries)
        )

        # Group by workout type
        type_breakdown: dict[str, int] = {}
        for entry in entries:
            wtype = entry.get("type", "general")
            type_breakdown[wtype] = type_breakdown.get(wtype, 0) + 1

        # Estimate weekly volume assuming entries span recent weeks
        days_span = max(1, len(entries))
        weeks = max(1, days_span / 7)
        weekly_volume = total_duration / weeks
        sessions_per_week = len(entries) / weeks

        # Consistency heuristic: 4-5 sessions/week at moderate intensity is ideal
        consistency_score = min(
            100.0,
            max(0.0, (sessions_per_week / 5.0) * 60 + (avg_intensity / 10.0) * 40),
        )

        prompt = (
            f"Analyze workout routine: {len(entries)} sessions, "
            f"{total_duration} total minutes, avg intensity {avg_intensity:.1f}/10, "
            f"types: {type_breakdown}."
        )
        ai_response = self._call_ai(prompt, context={
            "total_duration": total_duration,
            "avg_intensity": round(avg_intensity, 1),
            "type_breakdown": type_breakdown,
        })

        result = {
            "consistency_score": round(consistency_score, 1),
            "sessions_analyzed": len(entries),
            "total_duration_min": total_duration,
            "weekly_volume_min": round(weekly_volume, 1),
            "sessions_per_week": round(sessions_per_week, 1),
            "avg_intensity": round(avg_intensity, 1),
            "type_breakdown": type_breakdown,
            "muscle_group_balance": ai_response.get("muscle_group_balance", {}),
            "progression_trend": ai_response.get("progression_trend", "stable"),
            "suggestions": ai_response.get("suggestions", []),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Workout analysis complete",
            consistency_score=result["consistency_score"],
            weekly_volume=result["weekly_volume_min"],
        )
        return result

    def review_supplements(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Review current supplement stack and provide timing recommendations.

        Each entry is expected to contain keys like 'name', 'dosage',
        'frequency', 'time_of_day', and optional 'brand'.

        Args:
            entries: List of supplement dictionaries.

        Returns:
            Dictionary with stack assessment, interaction warnings,
            timing schedule, and optimization suggestions.
        """
        self.logger.info(
            "Reviewing supplement stack",
            supplement_count=len(entries),
        )

        if not entries:
            self.logger.warning("No supplements provided for review")
            return {
                "stack_score": 0.0,
                "supplements_reviewed": 0,
                "timing_schedule": {},
                "recommendations": [
                    "Add your supplements to receive stack optimization advice."
                ],
            }

        supplement_names = [e.get("name", "unknown") for e in entries]

        prompt = (
            f"Review supplement stack: {', '.join(supplement_names)}. "
            f"Check for interactions, optimal timing, and gaps."
        )
        ai_response = self._call_ai(prompt, context={"supplements": entries})

        # Build a timing schedule grouped by time of day
        timing_schedule: dict[str, list[str]] = {
            "morning_empty_stomach": [],
            "morning_with_food": [],
            "afternoon": [],
            "evening": [],
            "before_bed": [],
        }
        for entry in entries:
            time_slot = entry.get("time_of_day", "morning_with_food")
            if time_slot in timing_schedule:
                timing_schedule[time_slot].append(entry.get("name", "unknown"))
            else:
                timing_schedule["morning_with_food"].append(entry.get("name", "unknown"))

        result = {
            "stack_score": ai_response.get("stack_score", 70.0),
            "supplements_reviewed": len(entries),
            "current_stack": [
                {
                    "name": e.get("name"),
                    "dosage": e.get("dosage"),
                    "frequency": e.get("frequency"),
                    "status": "adequate",
                }
                for e in entries
            ],
            "timing_schedule": timing_schedule,
            "interactions": ai_response.get("interactions", []),
            "gaps": ai_response.get("gaps", []),
            "recommendations": ai_response.get("recommendations", []),
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Supplement review complete",
            stack_score=result["stack_score"],
            interaction_count=len(result["interactions"]),
        )
        return result

    def generate_daily_recommendation(self) -> dict[str, Any]:
        """Generate personalized daily health recommendations.

        Pulls recent health data from the database session and produces
        energy score, suggested schedule adjustments, and focus areas.

        Returns:
            Dictionary with energy_score, focus_areas, schedule_adjustments,
            and priority recommendations for the day.
        """
        self.logger.info("Generating daily health recommendation")

        # In production, these would be fetched from the database
        recent_data = self._fetch_recent_health_data()

        energy_score = self.calculate_energy_score(recent_data)

        prompt = (
            f"Generate daily health recommendations. "
            f"Current energy score: {energy_score:.0f}/100. "
            f"Sleep last night: {recent_data.get('last_sleep_hours', 'unknown')} hrs. "
            f"Workout yesterday: {recent_data.get('last_workout_type', 'none')}."
        )
        ai_response = self._call_ai(prompt, context=recent_data)

        # Determine focus areas based on energy score
        if energy_score >= 80:
            energy_level = "high"
            focus_areas = ["high-intensity training", "deep work sessions", "creative tasks"]
        elif energy_score >= 50:
            energy_level = "moderate"
            focus_areas = ["moderate exercise", "structured work blocks", "social activities"]
        else:
            energy_level = "low"
            focus_areas = ["recovery", "light movement", "rest prioritization"]

        result = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "energy_score": round(energy_score, 1),
            "energy_level": energy_level,
            "focus_areas": focus_areas,
            "schedule_adjustments": ai_response.get("schedule_adjustments", [
                {
                    "time": "07:00",
                    "action": "Morning sunlight exposure — 10 minutes",
                    "reason": "Circadian rhythm optimization",
                },
                {
                    "time": "12:00",
                    "action": "Midday walk — 20 minutes",
                    "reason": "Energy maintenance and vitamin D",
                },
                {
                    "time": "22:00",
                    "action": "Begin wind-down routine",
                    "reason": "Sleep quality improvement",
                },
            ]),
            "nutrition_tips": ai_response.get("nutrition_tips", [
                "Prioritize protein at breakfast for sustained energy.",
                "Stay hydrated — aim for 3L of water today.",
            ]),
            "supplement_reminders": ai_response.get("supplement_reminders", [
                {"time": "07:00", "supplements": ["Vitamin D3", "Omega-3"]},
                {"time": "22:00", "supplements": ["Magnesium Glycinate"]},
            ]),
            "generated_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Daily recommendation generated",
            energy_score=result["energy_score"],
            energy_level=result["energy_level"],
        )
        return result

    def calculate_energy_score(self, health_data: dict[str, Any]) -> float:
        """Calculate a 0-100 energy score from composite health data.

        The score is a weighted blend of sleep quality, exercise recency,
        nutrition quality, and hydration. Higher is better.

        Args:
            health_data: Dictionary containing recent health metrics such as
                'last_sleep_hours', 'sleep_quality' (0-10), 'exercise_days_this_week',
                'nutrition_score' (0-10), 'hydration_liters', 'stress_level' (0-10).

        Returns:
            Energy score between 0.0 and 100.0.
        """
        self.logger.info("Calculating energy score")

        sleep_hours = health_data.get("last_sleep_hours", 7.0)
        sleep_quality = health_data.get("sleep_quality", 5)
        exercise_days = health_data.get("exercise_days_this_week", 0)
        nutrition_score = health_data.get("nutrition_score", 5)
        hydration = health_data.get("hydration_liters", 2.0)
        stress_level = health_data.get("stress_level", 5)

        # ── Component scores (each 0-100) ──
        # Sleep component: 8 hours optimal, diminishing above/below
        sleep_hours_score = max(0.0, 100.0 - abs(sleep_hours - 8.0) * 15)
        sleep_quality_score = sleep_quality * 10.0
        sleep_component = (sleep_hours_score * 0.6 + sleep_quality_score * 0.4)

        # Exercise component: 4-5 days/week is optimal
        exercise_component = min(100.0, (exercise_days / 5.0) * 100.0)

        # Nutrition component: direct mapping from 0-10 scale
        nutrition_component = nutrition_score * 10.0

        # Hydration component: 3L is optimal
        hydration_component = min(100.0, (hydration / 3.0) * 100.0)

        # Stress penalty: high stress drags down energy
        stress_penalty = max(0.0, (stress_level - 3) * 5.0)

        # ── Weighted blend ──
        weights = {
            "sleep": 0.35,
            "exercise": 0.20,
            "nutrition": 0.20,
            "hydration": 0.10,
        }

        raw_score = (
            sleep_component * weights["sleep"]
            + exercise_component * weights["exercise"]
            + nutrition_component * weights["nutrition"]
            + hydration_component * weights["hydration"]
        )

        # Apply stress penalty and clamp
        final_score = max(0.0, min(100.0, raw_score - stress_penalty))

        self.logger.info(
            "Energy score calculated",
            score=round(final_score, 1),
            sleep_component=round(sleep_component, 1),
            exercise_component=round(exercise_component, 1),
        )
        return round(final_score, 1)

    # ── Private Helpers ─────────────────────────────────────────────

    def _call_ai(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Call Claude API to process a prompt, with mock fallback.

        Args:
            prompt: The natural language prompt for the AI model.
            context: Supplementary data passed alongside the prompt.

        Returns:
            AI response dictionary.
        """
        self.logger.debug(
            "Calling AI provider",
            prompt_length=len(prompt),
            has_context=context is not None,
        )

        # Determine task from prompt content for instruction selection
        prompt_lower = prompt.lower()
        if "sleep" in prompt_lower:
            task = "analyze_sleep"
        elif "workout" in prompt_lower or "exercise" in prompt_lower:
            task = "analyze_workouts"
        elif "supplement" in prompt_lower:
            task = "review_supplements"
        else:
            task = "daily_recommendation"

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI health and wellness assistant for Omura. "
            "You analyze sleep patterns, track workouts, manage supplements, "
            "calculate energy scores, and provide wellness recommendations. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "analyze_sleep": (
                "\n\nRespond with JSON containing: "
                '{"summary": "analysis summary of sleep patterns", '
                '"recommendations": ["recommendation1", "recommendation2", ...]}'
            ),
            "analyze_workouts": (
                "\n\nRespond with JSON containing: "
                '{"muscle_group_balance": {"upper_body": "adequate|needs_attention", '
                '"lower_body": "adequate|needs_attention", '
                '"core": "adequate|needs_attention", '
                '"cardio": "adequate|below_target|on_target"}, '
                '"progression_trend": "gradual_improvement|stable|declining", '
                '"suggestions": ["suggestion1", "suggestion2", ...]}'
            ),
            "review_supplements": (
                "\n\nRespond with JSON containing: "
                '{"stack_score": <float 0-100>, '
                '"interactions": [{"pair": ["supp1", "supp2"], "severity": "moderate|mild|severe", "note": "..."}], '
                '"gaps": [{"nutrient": "...", "reason": "..."}], '
                '"recommendations": ["recommendation1", ...]}'
            ),
            "daily_recommendation": (
                "\n\nRespond with JSON containing: "
                '{"schedule_adjustments": [{"time": "HH:MM", "action": "...", "reason": "..."}], '
                '"nutrition_tips": ["tip1", "tip2", ...], '
                '"supplement_reminders": [{"time": "HH:MM", "supplements": ["supp1", ...]}, ...]}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="health_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # ── Fallback: mock responses keyed on prompt content ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if "sleep" in prompt_lower:
            return {
                "summary": (
                    "Sleep patterns show room for improvement. Average duration "
                    "is below the optimal 7-9 hour range for most adults."
                ),
                "recommendations": [
                    "Aim for a consistent bedtime within a 30-minute window.",
                    "Reduce screen exposure 60 minutes before sleep.",
                    "Keep the bedroom temperature between 65-68 F (18-20 C).",
                    "Consider magnesium glycinate 30 minutes before bed.",
                ],
            }

        if "workout" in prompt_lower or "exercise" in prompt_lower:
            return {
                "muscle_group_balance": {
                    "upper_body": "adequate",
                    "lower_body": "needs_attention",
                    "core": "adequate",
                    "cardio": "below_target",
                },
                "progression_trend": "gradual_improvement",
                "suggestions": [
                    "Add one dedicated leg day per week for balanced development.",
                    "Incorporate 2 sessions of zone-2 cardio (30 min each) weekly.",
                    "Track progressive overload — increase weight or reps each week.",
                    "Schedule a deload week every 4-6 weeks to prevent overtraining.",
                ],
            }

        if "supplement" in prompt_lower:
            return {
                "stack_score": 75.0,
                "interactions": [
                    {
                        "pair": ["Calcium", "Iron"],
                        "severity": "moderate",
                        "note": "Take at least 2 hours apart — calcium inhibits iron absorption.",
                    },
                ],
                "gaps": [
                    {
                        "nutrient": "Magnesium",
                        "reason": "Supports sleep quality and muscle recovery.",
                    },
                    {
                        "nutrient": "Vitamin K2",
                        "reason": "Synergistic with Vitamin D3 for calcium metabolism.",
                    },
                ],
                "recommendations": [
                    "Add magnesium glycinate (400 mg) before bed.",
                    "Pair Vitamin D3 with K2 (MK-7) for optimal absorption.",
                    "Take fat-soluble vitamins (D, K, A, E) with a meal containing fats.",
                ],
            }

        # Default: daily recommendation response
        return {
            "schedule_adjustments": [
                {
                    "time": "07:00",
                    "action": "Morning sunlight exposure — 10 minutes",
                    "reason": "Circadian rhythm optimization",
                },
                {
                    "time": "09:00",
                    "action": "First deep work block — 90 minutes",
                    "reason": "Cortisol peak alignment",
                },
                {
                    "time": "12:30",
                    "action": "Midday walk — 20 minutes",
                    "reason": "Energy maintenance and digestion",
                },
                {
                    "time": "22:00",
                    "action": "Begin wind-down routine — dim lights, no screens",
                    "reason": "Melatonin production support",
                },
            ],
            "nutrition_tips": [
                "Prioritize protein at breakfast for sustained energy.",
                "Stay hydrated — aim for 3L of water today.",
                "Limit caffeine after 14:00 to protect sleep quality.",
            ],
            "supplement_reminders": [
                {"time": "07:00", "supplements": ["Vitamin D3", "Omega-3"]},
                {"time": "14:00", "supplements": ["B-Complex"]},
                {"time": "22:00", "supplements": ["Magnesium Glycinate"]},
            ],
        }

    def _fetch_recent_health_data(self) -> dict[str, Any]:
        """Fetch recent health metrics from the database.

        In production this queries the health_logs table for the last 7 days.
        Returns mock data for now.
        """
        self.logger.debug("Fetching recent health data from database (mock)")
        return {
            "last_sleep_hours": 6.8,
            "sleep_quality": 6,
            "exercise_days_this_week": 3,
            "last_workout_type": "strength",
            "nutrition_score": 7,
            "hydration_liters": 2.5,
            "stress_level": 4,
        }

    @staticmethod
    def _compute_trend(values: list[float]) -> str:
        """Determine whether a series of values is trending up, down, or stable.

        Compares the average of the first half to the second half.
        """
        if len(values) < 4:
            return "insufficient_data"

        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / (len(values) - mid)

        delta = second_half_avg - first_half_avg
        if delta > 0.3:
            return "improving"
        elif delta < -0.3:
            return "declining"
        return "stable"
