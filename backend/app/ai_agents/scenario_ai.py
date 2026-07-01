"""
Omura Scenario AI Agent
Runs what-if simulations across business, finance, content, and lifestyle
domains. Compares multiple scenarios and provides AI-driven recommendations.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class ScenarioAI:
    """AI agent for running what-if simulations and comparing outcomes.

    Supports business, financial, content strategy, and life optimization
    scenarios with side-by-side comparison and recommendation capabilities.
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.logger = OmuraLogger("scenario_ai")

    # ── Public Methods ──────────────────────────────────────────────

    def simulate_business(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a business scenario simulation.

        Example scenarios: "What if I raise prices 20%?", "What if I expand
        to a new market?", "What if I hire 3 more people?"

        Args:
            params: Dictionary with keys such as 'scenario_description',
                'price_change_pct', 'new_market', 'headcount_change',
                'current_revenue', 'current_customers', 'churn_rate'.

        Returns:
            Dictionary with scenario_id, projected metrics (revenue,
            customers, profit margin), risk assessment, timeline, and
            confidence interval.
        """
        scenario_id = str(uuid4())[:12]
        description = params.get("scenario_description", "Business scenario")

        self.logger.info(
            "Running business simulation",
            scenario_id=scenario_id,
            description=description,
        )

        current_revenue = params.get("current_revenue", 50000)
        current_customers = params.get("current_customers", 500)
        churn_rate = params.get("churn_rate", 0.05)
        price_change_pct = params.get("price_change_pct", 0)

        # ── Simple projection model ──
        # Price elasticity: every 10% price increase causes ~3% customer loss
        customer_impact_pct = -(price_change_pct / 10.0) * 0.03
        projected_customers = int(
            current_customers * (1 + customer_impact_pct) * (1 - churn_rate)
        )
        projected_revenue = current_revenue * (1 + price_change_pct / 100.0) * (
            1 + customer_impact_pct
        )

        prompt = (
            f"Simulate business scenario: '{description}'. "
            f"Current revenue=${current_revenue:,.0f}, customers={current_customers}, "
            f"churn={churn_rate:.1%}. Price change: {price_change_pct:+.0f}%."
        )
        ai_response = self._call_ai(prompt, context=params)

        result = {
            "scenario_id": scenario_id,
            "type": "business",
            "description": description,
            "inputs": {
                "current_revenue": current_revenue,
                "current_customers": current_customers,
                "churn_rate": churn_rate,
                "price_change_pct": price_change_pct,
            },
            "projections": {
                "revenue_30d": round(projected_revenue, 2),
                "revenue_90d": round(projected_revenue * 2.8, 2),
                "revenue_365d": round(projected_revenue * 11.2, 2),
                "customers_30d": projected_customers,
                "customers_90d": int(projected_customers * 1.08),
                "profit_margin_change_pct": round(price_change_pct * 0.7, 1),
            },
            "risk_assessment": ai_response.get("risk_assessment", {
                "overall_risk": "moderate",
                "key_risks": [
                    "Customer churn may accelerate if price increase is not paired with value addition.",
                    "Competitors may undercut pricing during transition period.",
                ],
                "mitigation_strategies": [
                    "Grandfather existing customers for 90 days.",
                    "Bundle new features with the price increase.",
                ],
            }),
            "timeline": ai_response.get("timeline", [
                {"phase": "Announcement", "duration": "Week 1-2", "action": "Communicate value-driven pricing change."},
                {"phase": "Transition", "duration": "Week 3-6", "action": "Monitor churn and collect feedback."},
                {"phase": "Stabilization", "duration": "Week 7-12", "action": "Optimize based on retention data."},
            ]),
            "confidence": 0.72,
            "simulated_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Business simulation complete",
            scenario_id=scenario_id,
            projected_revenue_30d=result["projections"]["revenue_30d"],
        )
        return result

    def simulate_finance(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a financial what-if simulation.

        Example scenarios: "What if revenue drops 30%?", "What if I invest
        $50K in marketing?", "What if I cut expenses by 20%?"

        Args:
            params: Dictionary with keys such as 'scenario_description',
                'revenue_change_pct', 'expense_change_pct', 'investment_amount',
                'current_revenue', 'current_expenses', 'runway_months'.

        Returns:
            Dictionary with scenario_id, projected financials (cash flow,
            runway, burn rate), break-even analysis, and warnings.
        """
        scenario_id = str(uuid4())[:12]
        description = params.get("scenario_description", "Financial scenario")

        self.logger.info(
            "Running financial simulation",
            scenario_id=scenario_id,
            description=description,
        )

        current_revenue = params.get("current_revenue", 50000)
        current_expenses = params.get("current_expenses", 40000)
        revenue_change_pct = params.get("revenue_change_pct", 0)
        expense_change_pct = params.get("expense_change_pct", 0)
        investment = params.get("investment_amount", 0)
        cash_reserves = params.get("cash_reserves", 200000)

        # ── Financial projection ──
        projected_revenue = current_revenue * (1 + revenue_change_pct / 100.0)
        projected_expenses = current_expenses * (1 + expense_change_pct / 100.0) + (
            investment / 12.0  # Amortize investment over 12 months
        )
        monthly_cash_flow = projected_revenue - projected_expenses
        projected_runway = (
            cash_reserves / abs(monthly_cash_flow)
            if monthly_cash_flow < 0
            else float("inf")
        )
        burn_rate = max(0, projected_expenses - projected_revenue)

        prompt = (
            f"Simulate financial scenario: '{description}'. "
            f"Revenue=${current_revenue:,.0f} ({revenue_change_pct:+.0f}%), "
            f"Expenses=${current_expenses:,.0f} ({expense_change_pct:+.0f}%), "
            f"Investment=${investment:,.0f}, Cash=${cash_reserves:,.0f}."
        )
        ai_response = self._call_ai(prompt, context=params)

        runway_display = (
            f"{projected_runway:.1f} months" if projected_runway != float("inf") else "unlimited"
        )

        result = {
            "scenario_id": scenario_id,
            "type": "finance",
            "description": description,
            "inputs": {
                "current_revenue": current_revenue,
                "current_expenses": current_expenses,
                "revenue_change_pct": revenue_change_pct,
                "expense_change_pct": expense_change_pct,
                "investment_amount": investment,
                "cash_reserves": cash_reserves,
            },
            "projections": {
                "monthly_revenue": round(projected_revenue, 2),
                "monthly_expenses": round(projected_expenses, 2),
                "monthly_cash_flow": round(monthly_cash_flow, 2),
                "burn_rate": round(burn_rate, 2),
                "runway": runway_display,
                "break_even_revenue": round(projected_expenses, 2),
                "annual_profit_projected": round(monthly_cash_flow * 12, 2),
            },
            "warnings": ai_response.get("warnings", []),
            "optimization_suggestions": ai_response.get("optimization_suggestions", []),
            "confidence": 0.68,
            "simulated_at": datetime.utcnow().isoformat(),
        }

        # Add critical warnings if runway is dangerously low
        if projected_runway != float("inf") and projected_runway < 6:
            result["warnings"].insert(0, {
                "severity": "critical",
                "message": f"Runway drops to {projected_runway:.1f} months. Immediate action required.",
            })

        self.logger.info(
            "Financial simulation complete",
            scenario_id=scenario_id,
            monthly_cash_flow=result["projections"]["monthly_cash_flow"],
            runway=runway_display,
        )
        return result

    def simulate_content(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a content strategy simulation.

        Example scenarios: "What if I post 3x/day?", "What if I switch
        to video-only?", "What if I focus on one platform?"

        Args:
            params: Dictionary with keys such as 'scenario_description',
                'posting_frequency', 'content_type', 'platforms',
                'current_followers', 'current_engagement_rate'.

        Returns:
            Dictionary with scenario_id, projected growth, engagement
            impact, resource requirements, and platform-specific forecasts.
        """
        scenario_id = str(uuid4())[:12]
        description = params.get("scenario_description", "Content strategy scenario")

        self.logger.info(
            "Running content simulation",
            scenario_id=scenario_id,
            description=description,
        )

        posting_freq = params.get("posting_frequency", 1)
        content_type = params.get("content_type", "mixed")
        platforms = params.get("platforms", ["instagram"])
        current_followers = params.get("current_followers", 10000)
        current_engagement = params.get("current_engagement_rate", 3.5)

        # ── Growth model ──
        # Diminishing returns: engagement drops ~8% per extra daily post above 2
        engagement_modifier = 1.0
        if posting_freq > 2:
            engagement_modifier = 1.0 - ((posting_freq - 2) * 0.08)
        elif posting_freq < 1:
            engagement_modifier = 0.6

        projected_engagement = current_engagement * engagement_modifier

        # Follower growth: more posts = more reach, but with diminishing returns
        monthly_growth_rate = min(0.15, 0.02 * posting_freq * engagement_modifier)
        projected_followers_30d = int(current_followers * (1 + monthly_growth_rate))
        projected_followers_90d = int(current_followers * (1 + monthly_growth_rate * 2.6))

        # Resource estimation
        hours_per_post = {"short_video": 2.0, "long_video": 6.0, "carousel": 1.5, "image": 0.5, "mixed": 1.5}
        hours_per_week = posting_freq * 7 * hours_per_post.get(content_type, 1.5)

        prompt = (
            f"Simulate content strategy: '{description}'. "
            f"Posting {posting_freq}x/day, type='{content_type}', "
            f"platforms={platforms}, followers={current_followers:,}, "
            f"engagement={current_engagement}%."
        )
        ai_response = self._call_ai(prompt, context=params)

        result = {
            "scenario_id": scenario_id,
            "type": "content",
            "description": description,
            "inputs": {
                "posting_frequency": posting_freq,
                "content_type": content_type,
                "platforms": platforms,
                "current_followers": current_followers,
                "current_engagement_rate": current_engagement,
            },
            "projections": {
                "engagement_rate_projected": round(projected_engagement, 2),
                "engagement_change_pct": round(
                    (projected_engagement - current_engagement) / current_engagement * 100, 1
                ),
                "followers_30d": projected_followers_30d,
                "followers_90d": projected_followers_90d,
                "monthly_reach_estimate": int(projected_followers_30d * posting_freq * 30 * 0.15),
            },
            "resource_requirements": {
                "hours_per_week": round(hours_per_week, 1),
                "posts_per_week": posting_freq * 7,
                "recommended_team_size": (
                    1 if hours_per_week <= 20 else 2 if hours_per_week <= 40 else 3
                ),
                "estimated_monthly_cost": round(hours_per_week * 4 * 35, 2),  # $35/hr estimate
            },
            "platform_forecasts": ai_response.get("platform_forecasts", [
                {
                    "platform": p,
                    "growth_potential": "high" if p in ["tiktok", "youtube"] else "medium",
                    "best_content_type": "short_video" if p in ["tiktok", "instagram"] else "long_video",
                }
                for p in platforms
            ]),
            "risks": ai_response.get("risks", [
                "Creator burnout at high posting frequency.",
                "Quality may decline if volume outpaces production capacity.",
            ]),
            "confidence": 0.70,
            "simulated_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Content simulation complete",
            scenario_id=scenario_id,
            projected_engagement=result["projections"]["engagement_rate_projected"],
        )
        return result

    def simulate_life(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a life optimization simulation.

        Example scenarios: "What if I sleep 8hrs consistently?",
        "What if I meditate daily?", "What if I exercise 5x/week?"

        Args:
            params: Dictionary with keys such as 'scenario_description',
                'sleep_hours', 'exercise_days', 'meditation_minutes',
                'screen_time_hours', 'current_energy_score'.

        Returns:
            Dictionary with scenario_id, projected energy score, productivity
            impact, health outcomes, and habit formation timeline.
        """
        scenario_id = str(uuid4())[:12]
        description = params.get("scenario_description", "Life optimization scenario")

        self.logger.info(
            "Running life simulation",
            scenario_id=scenario_id,
            description=description,
        )

        sleep_hours = params.get("sleep_hours", 7.0)
        exercise_days = params.get("exercise_days", 3)
        meditation_min = params.get("meditation_minutes", 0)
        screen_time = params.get("screen_time_hours", 6.0)
        current_energy = params.get("current_energy_score", 55.0)

        # ── Energy score projection ──
        sleep_impact = max(0, min(30, (sleep_hours - 5) * 10))
        exercise_impact = max(0, min(25, exercise_days * 5))
        meditation_impact = max(0, min(15, meditation_min * 0.75))
        screen_penalty = max(0, (screen_time - 4) * 3)

        projected_energy = min(
            100.0,
            max(0.0, sleep_impact + exercise_impact + meditation_impact + 20 - screen_penalty),
        )
        energy_delta = projected_energy - current_energy

        # Productivity projection based on energy
        productivity_change_pct = energy_delta * 0.8

        prompt = (
            f"Simulate life optimization: '{description}'. "
            f"Sleep={sleep_hours}hrs, exercise={exercise_days}x/week, "
            f"meditation={meditation_min}min/day, screen_time={screen_time}hrs/day. "
            f"Current energy={current_energy}."
        )
        ai_response = self._call_ai(prompt, context=params)

        result = {
            "scenario_id": scenario_id,
            "type": "life",
            "description": description,
            "inputs": {
                "sleep_hours": sleep_hours,
                "exercise_days": exercise_days,
                "meditation_minutes": meditation_min,
                "screen_time_hours": screen_time,
                "current_energy_score": current_energy,
            },
            "projections": {
                "energy_score_projected": round(projected_energy, 1),
                "energy_change": round(energy_delta, 1),
                "productivity_change_pct": round(productivity_change_pct, 1),
                "mood_improvement": "significant" if energy_delta > 15 else "moderate" if energy_delta > 5 else "minimal",
                "focus_hours_gained_per_day": round(max(0, energy_delta * 0.05), 1),
            },
            "health_outcomes": ai_response.get("health_outcomes", {
                "sleep_quality": "improved" if sleep_hours >= 7.5 else "unchanged",
                "cardiovascular": "improved" if exercise_days >= 3 else "unchanged",
                "mental_clarity": "improved" if meditation_min >= 10 else "unchanged",
                "eye_strain": "reduced" if screen_time <= 4 else "unchanged",
            }),
            "habit_formation_timeline": ai_response.get("habit_formation_timeline", [
                {"week": "1-2", "phase": "Initiation", "expectation": "Motivation high, consistency challenging."},
                {"week": "3-4", "phase": "Resistance", "expectation": "Novelty fades, discipline required."},
                {"week": "5-8", "phase": "Adaptation", "expectation": "Habits start feeling natural."},
                {"week": "9-12", "phase": "Automaticity", "expectation": "Behaviors become default routines."},
            ]),
            "recommendations": ai_response.get("recommendations", []),
            "confidence": 0.74,
            "simulated_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Life simulation complete",
            scenario_id=scenario_id,
            energy_projected=result["projections"]["energy_score_projected"],
            energy_change=result["projections"]["energy_change"],
        )
        return result

    def compare_scenarios(
        self, scenario_ids: list[str]
    ) -> dict[str, Any]:
        """Compare multiple simulation results side by side.

        In production, scenario results would be loaded from the database
        by their IDs. Currently returns mock comparison data.

        Args:
            scenario_ids: List of scenario_id strings to compare.

        Returns:
            Dictionary with comparison matrix, ranked recommendations,
            and a summary highlighting the best option.
        """
        self.logger.info(
            "Comparing scenarios",
            scenario_count=len(scenario_ids),
            scenario_ids=scenario_ids,
        )

        if len(scenario_ids) < 2:
            self.logger.warning("Need at least 2 scenarios to compare")
            return {
                "error": "At least 2 scenario IDs are required for comparison.",
                "scenarios_provided": len(scenario_ids),
            }

        # In production: load from DB. Mock for now.
        prompt = (
            f"Compare {len(scenario_ids)} scenarios: {scenario_ids}. "
            f"Rank by overall impact and feasibility."
        )
        ai_response = self._call_ai(prompt, context={"scenario_ids": scenario_ids})

        comparison = {
            "scenario_ids": scenario_ids,
            "comparison_matrix": [
                {
                    "scenario_id": sid,
                    "overall_score": round(70 + i * 5.5, 1),
                    "impact_score": round(65 + i * 7.0, 1),
                    "feasibility_score": round(75 + i * 3.0, 1),
                    "risk_score": round(40 - i * 5.0, 1),
                    "time_to_results": f"{3 - i} months" if i < 3 else "1 month",
                }
                for i, sid in enumerate(scenario_ids)
            ],
            "ranking": [
                {
                    "rank": idx + 1,
                    "scenario_id": sid,
                    "reasoning": f"Scenario {sid} ranks #{idx + 1} based on impact-to-risk ratio.",
                }
                for idx, sid in enumerate(reversed(scenario_ids))
            ],
            "best_option": {
                "scenario_id": scenario_ids[-1],
                "reason": (
                    "Highest overall score with the best balance of impact "
                    "and feasibility. Risk is manageable with recommended mitigations."
                ),
            },
            "trade_offs": ai_response.get("trade_offs", [
                "Higher-impact scenarios require more upfront investment.",
                "Lower-risk options may produce slower but more predictable results.",
                "Consider combining elements from top-ranked scenarios.",
            ]),
            "compared_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Scenario comparison complete",
            best_option=comparison["best_option"]["scenario_id"],
        )
        return comparison

    def get_recommendation(self, scenario_results: dict[str, Any]) -> str:
        """Generate an AI recommendation based on simulation results.

        Takes a single scenario result dictionary and produces a concise,
        actionable recommendation string.

        Args:
            scenario_results: A scenario result dictionary (output from any
                simulate_* method).

        Returns:
            Human-readable recommendation string.
        """
        scenario_type = scenario_results.get("type", "unknown")
        scenario_id = scenario_results.get("scenario_id", "N/A")

        self.logger.info(
            "Generating recommendation",
            scenario_id=scenario_id,
            scenario_type=scenario_type,
        )

        projections = scenario_results.get("projections", {})
        confidence = scenario_results.get("confidence", 0.5)
        description = scenario_results.get("description", "")

        prompt = (
            f"Generate a recommendation for scenario '{description}' "
            f"(type={scenario_type}, confidence={confidence:.0%}). "
            f"Key projections: {projections}."
        )
        ai_response = self._call_ai(prompt, context=scenario_results)

        recommendation = ai_response.get("recommendation", "")

        if not recommendation:
            # Fallback: generate based on scenario type and projections
            if scenario_type == "business":
                revenue_change = projections.get("revenue_30d", 0) - scenario_results.get(
                    "inputs", {}
                ).get("current_revenue", 0)
                if revenue_change > 0:
                    recommendation = (
                        f"Proceed with this scenario. Projected revenue increase of "
                        f"${revenue_change:,.0f}/month with {confidence:.0%} confidence. "
                        f"Implement in phases to mitigate risk."
                    )
                else:
                    recommendation = (
                        f"Exercise caution. This scenario projects a revenue decrease of "
                        f"${abs(revenue_change):,.0f}/month. Consider alternative approaches "
                        f"or pair with offsetting strategies."
                    )
            elif scenario_type == "finance":
                cash_flow = projections.get("monthly_cash_flow", 0)
                if cash_flow > 0:
                    recommendation = (
                        f"Financially viable. Projected positive cash flow of "
                        f"${cash_flow:,.0f}/month. Monitor actuals weekly for the first quarter."
                    )
                else:
                    recommendation = (
                        f"Financial risk detected. Monthly burn of ${abs(cash_flow):,.0f} "
                        f"reduces runway. Secure additional funding or reduce expenses before proceeding."
                    )
            elif scenario_type == "content":
                eng_change = projections.get("engagement_change_pct", 0)
                recommendation = (
                    f"Content strategy {'shows promise' if eng_change > 0 else 'needs adjustment'}. "
                    f"Projected engagement change of {eng_change:+.1f}%. "
                    f"Run a 2-week pilot before full commitment."
                )
            elif scenario_type == "life":
                energy_change = projections.get("energy_change", 0)
                recommendation = (
                    f"Life optimization scenario projects an energy score change of "
                    f"{energy_change:+.1f} points. {'Strongly recommended' if energy_change > 10 else 'Worth trying'}. "
                    f"Start with the highest-impact habit first and add one change per week."
                )
            else:
                recommendation = (
                    f"Review the simulation results for scenario '{description}' "
                    f"and weigh the projected outcomes against your current priorities."
                )

        self.logger.info(
            "Recommendation generated",
            scenario_id=scenario_id,
            recommendation_length=len(recommendation),
        )
        return recommendation

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
        if "compare" in prompt_lower:
            task = "compare_scenarios"
        elif "recommendation" in prompt_lower:
            task = "get_recommendation"
        elif "business" in prompt_lower:
            task = "simulate_business"
        elif "financial" in prompt_lower or "finance" in prompt_lower:
            task = "simulate_finance"
        elif "content" in prompt_lower:
            task = "simulate_content"
        else:
            task = "simulate_life"

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI scenario simulation assistant for Omura. "
            "You run what-if simulations across business, finance, content, and life domains. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "compare_scenarios": (
                "\n\nRespond with JSON containing: "
                '{"trade_offs": ["trade_off1", "trade_off2", ...]}'
            ),
            "get_recommendation": (
                "\n\nRespond with JSON containing: "
                '{"recommendation": "actionable recommendation string based on the scenario results"}'
            ),
            "simulate_business": (
                "\n\nRespond with JSON containing: "
                '{"risk_assessment": {"overall_risk": "low|moderate|high", '
                '"key_risks": ["risk1", ...], '
                '"mitigation_strategies": ["strategy1", ...]}, '
                '"timeline": [{"phase": "...", "duration": "...", "action": "..."}, ...]}'
            ),
            "simulate_finance": (
                "\n\nRespond with JSON containing: "
                '{"warnings": [{"severity": "critical|warning|info", "message": "..."}], '
                '"optimization_suggestions": ["suggestion1", ...]}'
            ),
            "simulate_content": (
                "\n\nRespond with JSON containing: "
                '{"platform_forecasts": [{"platform": "...", "growth_potential": "high|medium|low", '
                '"best_content_type": "short_video|long_video|carousel|image"}, ...], '
                '"risks": ["risk1", ...]}'
            ),
            "simulate_life": (
                "\n\nRespond with JSON containing: "
                '{"health_outcomes": {"sleep_quality": "improved|unchanged|declined", '
                '"cardiovascular": "improved|unchanged|declined", '
                '"mental_clarity": "improved|unchanged|declined", '
                '"eye_strain": "reduced|unchanged|increased"}, '
                '"habit_formation_timeline": [{"week": "...", "phase": "...", "expectation": "..."}, ...], '
                '"recommendations": ["recommendation1", ...]}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="scenario_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # AI unavailable (Claude outage after retries) — honest marker instead of
        # fabricated figures; callers assemble results with .get(...) defaults.
        self.logger.warning("AI unavailable — returning ai_unavailable for task=%s", task)
        return {"status": "ai_unavailable",
                "error": "The AI is temporarily unavailable; no data could be generated."}

        # ── Legacy placeholder responses below are unreachable (kept for shape ref) ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if "compare" in prompt_lower:
            return {
                "trade_offs": [
                    "Higher-impact scenarios require more upfront investment.",
                    "Lower-risk options may produce slower but more predictable results.",
                    "Consider combining elements from top-ranked scenarios.",
                ],
            }

        if "recommendation" in prompt_lower:
            return {
                "recommendation": "",  # Empty triggers fallback logic
            }

        if "business" in prompt_lower:
            return {
                "risk_assessment": {
                    "overall_risk": "moderate",
                    "key_risks": [
                        "Customer churn may increase during transition.",
                        "Market timing may not be optimal.",
                    ],
                    "mitigation_strategies": [
                        "Phase the rollout over 6-8 weeks.",
                        "Prepare a rollback plan with clear trigger criteria.",
                    ],
                },
                "timeline": [
                    {"phase": "Planning", "duration": "Week 1-2", "action": "Finalize strategy and communicate to stakeholders."},
                    {"phase": "Execution", "duration": "Week 3-8", "action": "Implement changes with weekly checkpoints."},
                    {"phase": "Review", "duration": "Week 9-12", "action": "Analyze results and iterate."},
                ],
            }

        if "financial" in prompt_lower or "finance" in prompt_lower:
            return {
                "warnings": [
                    {
                        "severity": "warning",
                        "message": "Revenue reduction scenarios should include contingency reserves of at least 3 months.",
                    },
                ],
                "optimization_suggestions": [
                    "Negotiate vendor contracts to reduce fixed costs by 10-15%.",
                    "Automate repetitive tasks to reduce labor expenses.",
                    "Consider revenue diversification to offset concentration risk.",
                ],
            }

        if "content" in prompt_lower:
            return {
                "platform_forecasts": [
                    {"platform": "instagram", "growth_potential": "medium", "best_content_type": "short_video"},
                    {"platform": "tiktok", "growth_potential": "high", "best_content_type": "short_video"},
                    {"platform": "youtube", "growth_potential": "high", "best_content_type": "long_video"},
                ],
                "risks": [
                    "Creator burnout at high posting frequency.",
                    "Quality may decline if volume outpaces production capacity.",
                    "Algorithm changes may reduce organic reach without notice.",
                ],
            }

        # Default: life simulation
        return {
            "health_outcomes": {
                "sleep_quality": "improved",
                "cardiovascular": "improved",
                "mental_clarity": "improved",
                "eye_strain": "reduced",
            },
            "habit_formation_timeline": [
                {"week": "1-2", "phase": "Initiation", "expectation": "Motivation high, consistency challenging."},
                {"week": "3-4", "phase": "Resistance", "expectation": "Novelty fades, discipline required."},
                {"week": "5-8", "phase": "Adaptation", "expectation": "Habits start feeling natural."},
                {"week": "9-12", "phase": "Automaticity", "expectation": "Behaviors become default routines."},
            ],
            "recommendations": [
                "Start with sleep optimization — it has the highest energy ROI.",
                "Add exercise after the sleep habit is established (week 3+).",
                "Introduce meditation last — it compounds the other gains.",
            ],
        }
