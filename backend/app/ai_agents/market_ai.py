"""
Omura Market AI Agent
Monitors competitors, identifies trends, discovers business opportunities,
and generates market intelligence reports for the Omura dashboard.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class MarketAI:
    """AI agent for market intelligence, competitor tracking, and trend analysis.

    Aggregates data from social platforms, web scraping pipelines, and manual
    inputs to provide actionable business intelligence.
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.logger = OmuraLogger("market_ai")

    # ── Public Methods ──────────────────────────────────────────────

    def monitor_competitors(
        self, competitors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Track competitor activity and surface notable changes.

        Each competitor dict should contain 'name', 'website', and optionally
        'social_handles', 'products', and 'pricing'.

        Args:
            competitors: List of competitor profile dictionaries.

        Returns:
            List of change-detection results, each with competitor name,
            detected changes, threat level, and recommended actions.
        """
        self.logger.info(
            "Monitoring competitors",
            competitor_count=len(competitors),
        )

        if not competitors:
            self.logger.warning("No competitors provided for monitoring")
            return []

        results: list[dict[str, Any]] = []
        for competitor in competitors:
            name = competitor.get("name", "Unknown")
            self.logger.info("Analyzing competitor", competitor=name)

            prompt = (
                f"Analyze competitor '{name}': "
                f"website={competitor.get('website', 'N/A')}, "
                f"products={competitor.get('products', [])}, "
                f"pricing={competitor.get('pricing', 'N/A')}. "
                f"Identify recent changes, threats, and opportunities."
            )
            ai_response = self._call_ai(prompt, context=competitor)

            results.append({
                "competitor": name,
                "website": competitor.get("website"),
                "changes_detected": ai_response.get("changes", []),
                "threat_level": ai_response.get("threat_level", "medium"),
                "market_position": ai_response.get("market_position", "stable"),
                "recommended_actions": ai_response.get("recommended_actions", []),
                "monitored_at": datetime.utcnow().isoformat(),
            })

        self.logger.info(
            "Competitor monitoring complete",
            competitors_analyzed=len(results),
        )
        return results

    def identify_trends(self, industry: str) -> list[dict[str, Any]]:
        """Spot emerging trends in a given industry.

        Args:
            industry: Industry name or vertical (e.g., "ecommerce", "saas",
                "health_and_fitness", "content_creation").

        Returns:
            List of trend dictionaries, each with name, category,
            momentum score (0-100), time horizon, and description.
        """
        self.logger.info("Identifying trends", industry=industry)

        prompt = (
            f"Identify top emerging trends in the '{industry}' industry. "
            f"Include momentum, time horizon, and actionable insights."
        )
        ai_response = self._call_ai(prompt, context={"industry": industry})

        trends = ai_response.get("trends", [])

        self.logger.info(
            "Trend identification complete",
            industry=industry,
            trends_found=len(trends),
        )
        return trends

    def find_opportunities(
        self, market_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify actionable business opportunities from market data.

        Args:
            market_data: Dictionary with keys such as 'industry', 'revenue',
                'customer_segments', 'competitors', 'current_products',
                and 'growth_goals'.

        Returns:
            List of opportunity dictionaries with title, category,
            potential_revenue, effort_estimate, confidence, and rationale.
        """
        self.logger.info(
            "Finding market opportunities",
            industry=market_data.get("industry", "unknown"),
        )

        prompt = (
            f"Analyze market data for '{market_data.get('industry', 'unknown')}' "
            f"with revenue={market_data.get('revenue', 'N/A')}, "
            f"segments={market_data.get('customer_segments', [])}, "
            f"goals={market_data.get('growth_goals', 'N/A')}. "
            f"Find untapped opportunities."
        )
        ai_response = self._call_ai(prompt, context=market_data)

        opportunities = ai_response.get("opportunities", [])

        self.logger.info(
            "Opportunity analysis complete",
            opportunities_found=len(opportunities),
        )
        return opportunities

    def analyze_audience(self, platform: str) -> dict[str, Any]:
        """Analyze audience demographics and behavior on a specific platform.

        Args:
            platform: Platform identifier (e.g., "instagram", "youtube",
                "tiktok", "twitter", "linkedin").

        Returns:
            Dictionary with demographics breakdown, peak activity times,
            content preferences, engagement patterns, and growth insights.
        """
        self.logger.info("Analyzing audience", platform=platform)

        prompt = (
            f"Analyze audience demographics and behavior on '{platform}'. "
            f"Include age distribution, peak times, content preferences, "
            f"and engagement patterns."
        )
        ai_response = self._call_ai(prompt, context={"platform": platform})

        result = {
            "platform": platform,
            "demographics": ai_response.get("demographics", {}),
            "peak_activity_hours": ai_response.get("peak_activity_hours", []),
            "content_preferences": ai_response.get("content_preferences", []),
            "engagement_patterns": ai_response.get("engagement_patterns", {}),
            "growth_insights": ai_response.get("growth_insights", []),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Audience analysis complete",
            platform=platform,
            demographic_segments=len(result["demographics"]),
        )
        return result

    def generate_market_report(self) -> dict[str, Any]:
        """Generate a comprehensive market intelligence summary.

        Combines competitor monitoring, trend analysis, audience insights,
        and opportunity scanning into a single executive-level report.

        Returns:
            Dictionary with report_date, executive_summary, sections for
            competitors, trends, opportunities, audience, and action_items.
        """
        self.logger.info("Generating comprehensive market report")

        prompt = (
            "Generate a comprehensive market intelligence report combining "
            "competitor activity, emerging trends, business opportunities, "
            "and audience insights."
        )
        ai_response = self._call_ai(prompt, context={"report_type": "comprehensive"})

        report = {
            "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "executive_summary": ai_response.get("executive_summary", ""),
            "sections": {
                "competitor_landscape": ai_response.get("competitor_landscape", {}),
                "emerging_trends": ai_response.get("emerging_trends", []),
                "opportunities": ai_response.get("opportunities", []),
                "audience_insights": ai_response.get("audience_insights", {}),
            },
            "risk_factors": ai_response.get("risk_factors", []),
            "action_items": ai_response.get("action_items", []),
            "confidence_score": ai_response.get("confidence_score", 72.0),
            "generated_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Market report generated",
            sections=len(report["sections"]),
            action_items=len(report["action_items"]),
        )
        return report

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
        if "competitor" in prompt_lower and "report" not in prompt_lower:
            task = "monitor_competitors"
        elif "trend" in prompt_lower:
            task = "identify_trends"
        elif "opportunit" in prompt_lower:
            task = "find_opportunities"
        elif "audience" in prompt_lower:
            task = "analyze_audience"
        else:
            task = "generate_market_report"

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI market intelligence assistant for Omura. "
            "You monitor competitors, identify trends, analyze market opportunities, "
            "and provide strategic recommendations. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "monitor_competitors": (
                "\n\nRespond with JSON containing: "
                '{"changes": [{"type": "pricing|product|marketing", "detail": "...", "detected_date": "ISO date"}], '
                '"threat_level": "low|medium|high", '
                '"market_position": "growing|stable|declining", '
                '"recommended_actions": ["action1", "action2", ...]}'
            ),
            "identify_trends": (
                "\n\nRespond with JSON containing: "
                '{"trends": [{"name": "...", "category": "technology|market_dynamics|audience|lifestyle", '
                '"momentum_score": <int 0-100>, "time_horizon": "3-6 months|6-12 months|12-18 months", '
                '"description": "...", "actionable_insight": "..."}, ...]}'
            ),
            "find_opportunities": (
                "\n\nRespond with JSON containing: "
                '{"opportunities": [{"title": "...", "category": "product|distribution|feature", '
                '"potential_revenue": "estimated MRR range", '
                '"effort_estimate": "low|medium|high", '
                '"confidence": <float 0-1>, '
                '"rationale": "..."}, ...]}'
            ),
            "analyze_audience": (
                "\n\nRespond with JSON containing: "
                '{"demographics": {"age_groups": {"18-24": <float>, ...}, '
                '"gender": {"female": <float>, "male": <float>, "other": <float>}, '
                '"top_locations": ["country1", ...]}, '
                '"peak_activity_hours": [{"hour": "HH:MM", "engagement_index": <float>}, ...], '
                '"content_preferences": [{"type": "...", "preference_score": <float>}, ...], '
                '"engagement_patterns": {"avg_engagement_rate": <float>, '
                '"best_performing_format": "...", "avg_saves_per_post": <int>, "avg_shares_per_post": <int>}, '
                '"growth_insights": ["insight1", ...]}'
            ),
            "generate_market_report": (
                "\n\nRespond with JSON containing: "
                '{"executive_summary": "...", '
                '"competitor_landscape": {"total_tracked": <int>, "notable_moves": ["..."], "overall_threat": "..."}, '
                '"emerging_trends": ["trend1", ...], '
                '"opportunities": ["opp1", ...], '
                '"audience_insights": {"fastest_growing_segment": "...", "top_platform": "...", "content_trend": "..."}, '
                '"risk_factors": [{"risk": "...", "likelihood": "...", "impact": "...", "mitigation": "..."}], '
                '"action_items": [{"priority": "high|medium|low", "action": "...", "deadline": "ISO date"}], '
                '"confidence_score": <float 0-100>}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="market_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # ── Fallback: mock responses keyed on prompt content ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if "competitor" in prompt_lower and "report" not in prompt_lower:
            return {
                "changes": [
                    {
                        "type": "pricing",
                        "detail": "Reduced starter plan price by 15%",
                        "detected_date": "2026-03-22",
                    },
                    {
                        "type": "product",
                        "detail": "Launched new AI-powered analytics feature",
                        "detected_date": "2026-03-20",
                    },
                ],
                "threat_level": "medium",
                "market_position": "growing",
                "recommended_actions": [
                    "Review our pricing against their new tier structure.",
                    "Accelerate our analytics feature roadmap.",
                    "Emphasize differentiators in upcoming marketing campaigns.",
                ],
            }

        if "trend" in prompt_lower:
            return {
                "trends": [
                    {
                        "name": "AI-Powered Personalization",
                        "category": "technology",
                        "momentum_score": 92,
                        "time_horizon": "6-12 months",
                        "description": (
                            "Hyper-personalized user experiences driven by "
                            "generative AI are becoming table stakes."
                        ),
                        "actionable_insight": (
                            "Integrate AI personalization into onboarding "
                            "and content delivery."
                        ),
                    },
                    {
                        "name": "Creator Economy Consolidation",
                        "category": "market_dynamics",
                        "momentum_score": 78,
                        "time_horizon": "12-18 months",
                        "description": (
                            "Platforms are consolidating creator tools into "
                            "all-in-one suites, raising user expectations."
                        ),
                        "actionable_insight": (
                            "Position Omura as the unified life-and-business "
                            "management hub for creators."
                        ),
                    },
                    {
                        "name": "Micro-Community Engagement",
                        "category": "audience",
                        "momentum_score": 85,
                        "time_horizon": "3-6 months",
                        "description": (
                            "Smaller, niche communities are driving higher "
                            "engagement than broad audiences."
                        ),
                        "actionable_insight": (
                            "Build community features and targeted content "
                            "strategies for niche segments."
                        ),
                    },
                    {
                        "name": "Wellness-Productivity Integration",
                        "category": "lifestyle",
                        "momentum_score": 71,
                        "time_horizon": "6-12 months",
                        "description": (
                            "Users increasingly demand tools that blend "
                            "health tracking with productivity systems."
                        ),
                        "actionable_insight": (
                            "Leverage Omura's health module as a "
                            "competitive differentiator."
                        ),
                    },
                ],
            }

        if "opportunit" in prompt_lower:
            return {
                "opportunities": [
                    {
                        "title": "Premium Health-Business Bundle",
                        "category": "product",
                        "potential_revenue": "$15K-25K MRR",
                        "effort_estimate": "medium",
                        "confidence": 0.78,
                        "rationale": (
                            "No competitor offers integrated health and business "
                            "management. High willingness-to-pay among creators "
                            "who value holistic optimization."
                        ),
                    },
                    {
                        "title": "Agency White-Label Plan",
                        "category": "distribution",
                        "potential_revenue": "$30K-50K MRR",
                        "effort_estimate": "high",
                        "confidence": 0.65,
                        "rationale": (
                            "Agencies managing multiple creators need a "
                            "centralized dashboard. White-label offering "
                            "unlocks B2B revenue stream."
                        ),
                    },
                    {
                        "title": "Automated Competitor Reports as a Feature",
                        "category": "feature",
                        "potential_revenue": "$5K-10K MRR",
                        "effort_estimate": "low",
                        "confidence": 0.82,
                        "rationale": (
                            "Market intelligence is currently manual for most "
                            "small businesses. Automating it drives retention."
                        ),
                    },
                ],
            }

        if "audience" in prompt_lower:
            platform = (context or {}).get("platform", "instagram")
            return {
                "demographics": {
                    "age_groups": {
                        "18-24": 0.28,
                        "25-34": 0.42,
                        "35-44": 0.18,
                        "45+": 0.12,
                    },
                    "gender": {"female": 0.56, "male": 0.41, "other": 0.03},
                    "top_locations": ["United States", "United Kingdom", "Canada"],
                },
                "peak_activity_hours": [
                    {"hour": "09:00", "engagement_index": 0.72},
                    {"hour": "12:00", "engagement_index": 0.88},
                    {"hour": "18:00", "engagement_index": 0.95},
                    {"hour": "21:00", "engagement_index": 0.81},
                ],
                "content_preferences": [
                    {"type": "short_video", "preference_score": 0.91},
                    {"type": "carousel", "preference_score": 0.78},
                    {"type": "story", "preference_score": 0.74},
                    {"type": "static_image", "preference_score": 0.52},
                ],
                "engagement_patterns": {
                    "avg_engagement_rate": 4.2,
                    "best_performing_format": "short_video",
                    "avg_saves_per_post": 34,
                    "avg_shares_per_post": 18,
                },
                "growth_insights": [
                    "Posting Reels at 18:00 UTC yields 40% more reach than other times.",
                    "Carousel posts drive 2x more saves than single images.",
                    "Engagement spikes when posting frequency is 4-5x per week.",
                    f"Your {platform} audience responds best to educational content.",
                ],
            }

        # Default: comprehensive market report
        return {
            "executive_summary": (
                "The market shows strong momentum in AI-powered tools and "
                "creator economy platforms. Key competitors are investing in "
                "pricing optimization while new entrants focus on niche verticals. "
                "Omura is well-positioned to capture the wellness-productivity "
                "intersection."
            ),
            "competitor_landscape": {
                "total_tracked": 8,
                "notable_moves": [
                    "Competitor A reduced pricing by 15%.",
                    "Competitor B launched AI analytics.",
                    "New entrant C targeting health-creator niche.",
                ],
                "overall_threat": "moderate",
            },
            "emerging_trends": [
                "AI-Powered Personalization",
                "Creator Economy Consolidation",
                "Micro-Community Engagement",
            ],
            "opportunities": [
                "Premium Health-Business Bundle",
                "Agency White-Label Plan",
                "Automated Competitor Reports",
            ],
            "audience_insights": {
                "fastest_growing_segment": "25-34 health-conscious creators",
                "top_platform": "Instagram",
                "content_trend": "Short-form educational video",
            },
            "risk_factors": [
                {
                    "risk": "Competitor price war",
                    "likelihood": "medium",
                    "impact": "high",
                    "mitigation": "Differentiate on value, not price.",
                },
                {
                    "risk": "Platform algorithm changes",
                    "likelihood": "high",
                    "impact": "medium",
                    "mitigation": "Diversify across platforms and owned channels.",
                },
            ],
            "action_items": [
                {
                    "priority": "high",
                    "action": "Launch competitive pricing analysis dashboard.",
                    "deadline": "2026-04-15",
                },
                {
                    "priority": "high",
                    "action": "Accelerate AI personalization features.",
                    "deadline": "2026-05-01",
                },
                {
                    "priority": "medium",
                    "action": "Develop agency white-label proposal.",
                    "deadline": "2026-06-01",
                },
            ],
            "confidence_score": 74.5,
        }
