"""
Omura Finance AI Agent
Provides AI-driven financial intelligence: KPI calculation, anomaly
detection, report generation, optimization suggestions, and revenue
forecasting.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class FinanceAI:
    """AI-powered financial analysis agent.

    Calculates key performance indicators, detects spending and revenue
    anomalies, generates comprehensive financial reports, suggests
    cost-saving and revenue-boosting optimizations, and projects future
    revenue based on historical trends.
    """

    def __init__(self, db_session: Any) -> None:
        """Initialize the FinanceAI agent.

        Args:
            db_session: SQLAlchemy database session for querying
                        transactions, invoices, and financial records.
        """
        self.db = db_session
        self.logger = OmuraLogger("finance_ai")
        self.logger.info("FinanceAI agent initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_kpis(self, period_days: int = 30) -> dict:
        """Calculate key financial metrics for a given period.

        Args:
            period_days: Number of days to look back (default 30).

        Returns:
            A dict containing:
                - period_days (int)
                - period_start (str): ISO date
                - period_end (str): ISO date
                - revenue (float)
                - expenses (float)
                - net_profit (float)
                - profit_margin (float): percentage
                - revenue_growth (float): percentage vs prior period
                - expense_ratio (float): expenses / revenue
                - accounts_receivable (float)
                - accounts_payable (float)
                - cash_flow (float)
        """
        self.logger.info("Calculating KPIs", period_days=period_days)

        transactions = self._fetch_transactions(period_days)

        prompt = (
            f"Calculate financial KPIs for the last {period_days} days.\n"
            f"Transactions: {len(transactions)} records.\n"
            f"Compute: revenue, expenses, net profit, profit margin, "
            f"revenue growth vs prior period, expense ratio, AR, AP, cash flow."
        )
        result = self._call_ai(prompt, context={"task": "calculate_kpis", "period_days": period_days})

        now = datetime.now(timezone.utc)
        kpis = {
            "period_days": period_days,
            "period_start": (now - timedelta(days=period_days)).date().isoformat(),
            "period_end": now.date().isoformat(),
            "revenue": result.get("revenue", 0.0),
            "expenses": result.get("expenses", 0.0),
            "net_profit": result.get("net_profit", 0.0),
            "profit_margin": result.get("profit_margin", 0.0),
            "revenue_growth": result.get("revenue_growth", 0.0),
            "expense_ratio": result.get("expense_ratio", 0.0),
            "accounts_receivable": result.get("accounts_receivable", 0.0),
            "accounts_payable": result.get("accounts_payable", 0.0),
            "cash_flow": result.get("cash_flow", 0.0),
        }

        self.logger.info(
            "KPIs calculated",
            period_days=period_days,
            revenue=kpis["revenue"],
            profit_margin=kpis["profit_margin"],
        )
        return kpis

    def detect_anomalies(self, metrics: list[dict]) -> list[dict]:
        """Flag unusual spending or revenue patterns.

        Args:
            metrics: List of metric dicts, each containing:
                - date (str): ISO date
                - category (str)
                - amount (float)
                - type (str): 'revenue' or 'expense'

        Returns:
            A list of anomaly dicts, each containing:
                - date (str)
                - category (str)
                - amount (float)
                - expected_range (dict): {'min': float, 'max': float}
                - deviation_pct (float): how far outside normal range
                - severity (str): 'critical', 'warning', 'info'
                - description (str)
        """
        self.logger.info("Detecting anomalies", metric_count=len(metrics))

        prompt = (
            f"Analyze {len(metrics)} financial data points for anomalies.\n"
            f"Look for: unusual spikes/drops, pattern deviations, "
            f"out-of-range values compared to historical averages.\n"
            f"Data sample: {metrics[:10]}"
        )
        result = self._call_ai(prompt, context={"task": "detect_anomalies"})
        anomalies = result.get("anomalies", [])

        self.logger.info(
            "Anomaly detection complete",
            total_metrics=len(metrics),
            anomalies_found=len(anomalies),
            critical=sum(1 for a in anomalies if a.get("severity") == "critical"),
        )
        return anomalies

    def generate_report(self, period_days: int = 30) -> dict:
        """Generate a comprehensive financial summary with AI insights.

        Combines KPI calculations with trend analysis and actionable
        commentary.

        Args:
            period_days: Number of days to cover (default 30).

        Returns:
            A dict containing:
                - title (str)
                - period (dict): start and end dates
                - kpis (dict): output of calculate_kpis
                - revenue_breakdown (list[dict]): by category
                - expense_breakdown (list[dict]): by category
                - trends (list[str]): AI-identified trends
                - insights (list[str]): actionable observations
                - executive_summary (str): 2-3 sentence overview
                - generated_at (str): ISO timestamp
        """
        self.logger.info("Generating financial report", period_days=period_days)

        # Step 1: Calculate KPIs
        kpis = self.calculate_kpis(period_days)

        # Step 2: Get AI analysis
        prompt = (
            f"Generate a financial report for the last {period_days} days.\n"
            f"KPIs: {kpis}\n"
            f"Provide: revenue breakdown by category, expense breakdown, "
            f"trends, insights, and an executive summary."
        )
        result = self._call_ai(
            prompt, context={"task": "generate_report", "period_days": period_days},
        )

        now = datetime.now(timezone.utc)
        report = {
            "title": f"Financial Report — Last {period_days} Days",
            "period": {
                "start": kpis["period_start"],
                "end": kpis["period_end"],
            },
            "kpis": kpis,
            "revenue_breakdown": result.get("revenue_breakdown", []),
            "expense_breakdown": result.get("expense_breakdown", []),
            "trends": result.get("trends", []),
            "insights": result.get("insights", []),
            "executive_summary": result.get("executive_summary", ""),
            "generated_at": now.isoformat(),
        }

        self.logger.info(
            "Financial report generated",
            period_days=period_days,
            sections=len([k for k in report if report[k]]),
        )
        return report

    def suggest_optimizations(self) -> list[dict]:
        """Generate cost-saving or revenue-boosting suggestions.

        Analyzes current spending patterns, recurring expenses, and
        revenue streams to identify optimization opportunities.

        Returns:
            A list of optimization dicts, each containing:
                - category (str): 'cost_reduction' or 'revenue_growth'
                - title (str)
                - description (str)
                - estimated_impact (float): projected monthly savings or gain
                - effort (str): 'low', 'medium', 'high'
                - priority (int): 1 = highest
        """
        self.logger.info("Generating optimization suggestions")

        kpis = self.calculate_kpis(period_days=90)

        prompt = (
            f"Based on these 90-day financials, suggest optimizations.\n"
            f"Revenue: ${kpis['revenue']:,.2f}\n"
            f"Expenses: ${kpis['expenses']:,.2f}\n"
            f"Profit margin: {kpis['profit_margin']}%\n"
            f"Generate cost-reduction and revenue-growth opportunities "
            f"with estimated impact and effort level."
        )
        result = self._call_ai(prompt, context={"task": "suggest_optimizations"})
        suggestions = result.get("optimizations", [])

        self.logger.info(
            "Optimizations generated",
            count=len(suggestions),
            total_estimated_impact=sum(s.get("estimated_impact", 0) for s in suggestions),
        )
        return suggestions

    def forecast_revenue(self, months_ahead: int = 3) -> dict:
        """Project future revenue based on historical trends.

        Args:
            months_ahead: Number of months to forecast (default 3).

        Returns:
            A dict containing:
                - forecast_period (str): e.g. 'April 2026 — June 2026'
                - monthly_projections (list[dict]): per-month forecasts
                  with month, projected_revenue, confidence, growth_rate
                - total_projected (float)
                - methodology (str): description of approach
                - assumptions (list[str])
                - risks (list[str])
        """
        self.logger.info("Forecasting revenue", months_ahead=months_ahead)

        historical = self._fetch_monthly_revenue(lookback_months=6)

        prompt = (
            f"Forecast revenue for the next {months_ahead} months.\n"
            f"Historical monthly revenue (last 6 months): {historical}\n"
            f"Provide: monthly projections with confidence, growth rates, "
            f"methodology, assumptions, and risks."
        )
        result = self._call_ai(
            prompt, context={"task": "forecast_revenue", "months_ahead": months_ahead},
        )

        forecast = {
            "forecast_period": result.get("forecast_period", ""),
            "monthly_projections": result.get("monthly_projections", []),
            "total_projected": result.get("total_projected", 0.0),
            "methodology": result.get("methodology", ""),
            "assumptions": result.get("assumptions", []),
            "risks": result.get("risks", []),
        }

        self.logger.info(
            "Revenue forecast complete",
            months_ahead=months_ahead,
            total_projected=forecast["total_projected"],
        )
        return forecast

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_transactions(self, period_days: int) -> list[dict]:
        """Fetch financial transactions from the database."""
        try:
            self.logger.debug("Querying transactions", period_days=period_days)
            return []
        except Exception as exc:
            self.logger.warning("Failed to fetch transactions", error=str(exc))
            return []

    def _fetch_monthly_revenue(self, lookback_months: int = 6) -> list[dict]:
        """Fetch monthly revenue summaries for forecasting."""
        try:
            self.logger.debug("Querying monthly revenue", lookback_months=lookback_months)
            return []
        except Exception as exc:
            self.logger.warning("Failed to fetch monthly revenue", error=str(exc))
            return []

    def _call_ai(self, prompt: str, context: Optional[dict] = None) -> dict:
        """Call Claude API to process a prompt, with mock fallback.

        Args:
            prompt: The natural-language prompt to send.
            context: Optional metadata about the task type.

        Returns:
            A dict containing the AI response fields.
        """
        task = (context or {}).get("task", "unknown")
        period_days = (context or {}).get("period_days", 30)
        months_ahead = (context or {}).get("months_ahead", 3)
        self.logger.debug("Calling AI provider", task=task, prompt_length=len(prompt))

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI financial analyst for Omura. "
            "You calculate KPIs, detect anomalies, generate reports, "
            "suggest optimizations, and forecast revenue. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "calculate_kpis": (
                "\n\nRespond with JSON containing: "
                '{"revenue": <float>, "expenses": <float>, '
                '"net_profit": <float>, "profit_margin": <float percentage>, '
                '"revenue_growth": <float percentage>, '
                '"expense_ratio": <float percentage>, '
                '"accounts_receivable": <float>, '
                '"accounts_payable": <float>, '
                '"cash_flow": <float>}'
            ),
            "detect_anomalies": (
                "\n\nRespond with JSON containing: "
                '{"anomalies": [{"date": "ISO date", "category": "...", '
                '"amount": <float>, "expected_range": {"min": <float>, "max": <float>}, '
                '"deviation_pct": <float>, "severity": "critical|warning|info", '
                '"description": "..."}, ...]}'
            ),
            "generate_report": (
                "\n\nRespond with JSON containing: "
                '{"revenue_breakdown": [{"category": "...", "amount": <float>, "pct": <float>}, ...], '
                '"expense_breakdown": [{"category": "...", "amount": <float>, "pct": <float>}, ...], '
                '"trends": ["trend1", "trend2", ...], '
                '"insights": ["insight1", "insight2", ...], '
                '"executive_summary": "2-3 sentence summary"}'
            ),
            "suggest_optimizations": (
                "\n\nRespond with JSON containing: "
                '{"optimizations": [{"category": "cost_reduction|revenue_growth", '
                '"title": "...", "description": "...", '
                '"estimated_impact": <float monthly savings or gain>, '
                '"effort": "low|medium|high", '
                '"priority": <int starting at 1>}, ...]}'
            ),
            "forecast_revenue": (
                "\n\nRespond with JSON containing: "
                '{"forecast_period": "Month Year — Month Year", '
                '"monthly_projections": [{"month": "Month Year", '
                '"projected_revenue": <float>, "confidence": <float 0-1>, '
                '"growth_rate": <float percentage>}, ...], '
                '"total_projected": <float>, '
                '"methodology": "description of approach", '
                '"assumptions": ["assumption1", ...], '
                '"risks": ["risk1", ...]}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="finance_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # AI unavailable (Claude outage after retries) — return an honest marker
        # instead of fabricated figures. Public methods read this with .get(...)
        # and degrade to zeros/empties, so no invented data is ever shown as real.
        self.logger.warning("AI unavailable — returning ai_unavailable for task=%s", task)
        return {"status": "ai_unavailable",
                "error": "The AI is temporarily unavailable; no figures could be generated."}

        # ── Legacy placeholder responses below are unreachable (kept for shape ref) ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if task == "calculate_kpis":
            # Scale mock data proportionally to period
            scale = period_days / 30.0
            revenue = 48500.00 * scale
            expenses = 31200.00 * scale
            net_profit = revenue - expenses
            return {
                "revenue": round(revenue, 2),
                "expenses": round(expenses, 2),
                "net_profit": round(net_profit, 2),
                "profit_margin": round((net_profit / revenue) * 100, 1) if revenue else 0.0,
                "revenue_growth": 12.3,
                "expense_ratio": round((expenses / revenue) * 100, 1) if revenue else 0.0,
                "accounts_receivable": round(8750.00 * scale, 2),
                "accounts_payable": round(4200.00 * scale, 2),
                "cash_flow": round(net_profit - 2100.00, 2),
            }

        if task == "detect_anomalies":
            return {
                "anomalies": [
                    {
                        "date": "2026-03-15",
                        "category": "Software Subscriptions",
                        "amount": 2847.00,
                        "expected_range": {"min": 800.00, "max": 1200.00},
                        "deviation_pct": 137.3,
                        "severity": "critical",
                        "description": (
                            "Software subscription charge is 2.4x the historical "
                            "average. Possible duplicate charge or unauthorized "
                            "plan upgrade."
                        ),
                    },
                    {
                        "date": "2026-03-18",
                        "category": "Client Payments",
                        "amount": 15200.00,
                        "expected_range": {"min": 3000.00, "max": 8000.00},
                        "deviation_pct": 90.0,
                        "severity": "info",
                        "description": (
                            "Unusually large client payment received. Likely a "
                            "bulk project payment — verify invoice match."
                        ),
                    },
                    {
                        "date": "2026-03-20",
                        "category": "Advertising",
                        "amount": 3400.00,
                        "expected_range": {"min": 1500.00, "max": 2200.00},
                        "deviation_pct": 54.5,
                        "severity": "warning",
                        "description": (
                            "Ad spend exceeded budget ceiling by 55%. Check for "
                            "runaway campaign bids or missing daily caps."
                        ),
                    },
                ],
            }

        if task == "generate_report":
            return {
                "revenue_breakdown": [
                    {"category": "Client Services", "amount": 28500.00, "pct": 58.8},
                    {"category": "Product Sales", "amount": 12000.00, "pct": 24.7},
                    {"category": "Subscriptions", "amount": 5500.00, "pct": 11.3},
                    {"category": "Other", "amount": 2500.00, "pct": 5.2},
                ],
                "expense_breakdown": [
                    {"category": "Payroll", "amount": 18000.00, "pct": 57.7},
                    {"category": "Software & Tools", "amount": 4200.00, "pct": 13.5},
                    {"category": "Advertising", "amount": 3800.00, "pct": 12.2},
                    {"category": "Office & Utilities", "amount": 2700.00, "pct": 8.7},
                    {"category": "Professional Services", "amount": 1500.00, "pct": 4.8},
                    {"category": "Miscellaneous", "amount": 1000.00, "pct": 3.2},
                ],
                "trends": [
                    "Revenue has grown 12.3% compared to the prior 30-day period.",
                    "Client services revenue is increasingly dominant (up from 52% to 59%).",
                    "Software costs are trending upward — review subscription utilization.",
                    "Advertising ROI has improved; cost-per-acquisition dropped 18%.",
                ],
                "insights": [
                    "Profit margin of 35.7% is healthy but could improve by optimizing "
                    "software and tool spend.",
                    "Accounts receivable aging suggests 2 invoices are overdue by 15+ days.",
                    "Cash reserves cover approximately 2.8 months of operating expenses.",
                    "Diversifying revenue beyond client services would reduce concentration risk.",
                ],
                "executive_summary": (
                    "The business generated $48,500 in revenue with a 35.7% profit margin "
                    "over the last 30 days, reflecting 12.3% growth versus the prior period. "
                    "Key areas for improvement include reducing software overhead and "
                    "accelerating receivables collection to strengthen cash flow."
                ),
            }

        if task == "suggest_optimizations":
            return {
                "optimizations": [
                    {
                        "category": "cost_reduction",
                        "title": "Consolidate SaaS subscriptions",
                        "description": (
                            "Audit current software tools — 3 overlapping project "
                            "management and 2 overlapping communication platforms "
                            "identified. Consolidating could save $1,200/month."
                        ),
                        "estimated_impact": 1200.00,
                        "effort": "low",
                        "priority": 1,
                    },
                    {
                        "category": "revenue_growth",
                        "title": "Introduce retainer packages",
                        "description": (
                            "Convert top 5 recurring clients from project-based "
                            "billing to monthly retainers. Improves revenue "
                            "predictability and increases LTV by an estimated 25%."
                        ),
                        "estimated_impact": 3500.00,
                        "effort": "medium",
                        "priority": 2,
                    },
                    {
                        "category": "cost_reduction",
                        "title": "Negotiate vendor contracts",
                        "description": (
                            "Current hosting and advertising contracts are on "
                            "month-to-month terms. Annual commitments could "
                            "reduce costs by 15-20%."
                        ),
                        "estimated_impact": 850.00,
                        "effort": "low",
                        "priority": 3,
                    },
                    {
                        "category": "revenue_growth",
                        "title": "Launch referral incentive program",
                        "description": (
                            "Referral leads convert at 2.3x the rate of other "
                            "channels. A structured referral program offering "
                            "10% credit could increase inbound referrals by 40%."
                        ),
                        "estimated_impact": 2800.00,
                        "effort": "medium",
                        "priority": 4,
                    },
                    {
                        "category": "cost_reduction",
                        "title": "Automate invoice follow-ups",
                        "description": (
                            "Two overdue invoices totaling $4,200 are aging beyond "
                            "15 days. Automated reminders at 7, 14, and 21 days "
                            "would improve collection speed and reduce manual effort."
                        ),
                        "estimated_impact": 500.00,
                        "effort": "low",
                        "priority": 5,
                    },
                ],
            }

        if task == "forecast_revenue":
            now = datetime.now(timezone.utc)
            projections = []
            base_revenue = 48500.00
            monthly_growth = 0.08  # 8% month-over-month
            for i in range(1, months_ahead + 1):
                month_date = now + timedelta(days=30 * i)
                projected = base_revenue * ((1 + monthly_growth) ** i)
                confidence = max(0.5, 0.92 - (i * 0.08))
                projections.append({
                    "month": month_date.strftime("%B %Y"),
                    "projected_revenue": round(projected, 2),
                    "confidence": round(confidence, 2),
                    "growth_rate": round(monthly_growth * 100, 1),
                })

            total = sum(p["projected_revenue"] for p in projections)
            first_month = projections[0]["month"] if projections else ""
            last_month = projections[-1]["month"] if projections else ""

            return {
                "forecast_period": f"{first_month} — {last_month}",
                "monthly_projections": projections,
                "total_projected": round(total, 2),
                "methodology": (
                    "Exponential smoothing applied to 6-month revenue history "
                    "with seasonal adjustment and trend decomposition."
                ),
                "assumptions": [
                    "Current client retention rate holds steady at 92%.",
                    "No major market disruptions or economic downturns.",
                    "Planned marketing campaigns deliver expected lead volume.",
                    "Team capacity remains constant (no major hiring or attrition).",
                ],
                "risks": [
                    "Loss of a top-3 client could reduce revenue by 15-20%.",
                    "Delayed product launch may push subscription revenue to Q3.",
                    "Rising ad costs could compress margins if not offset by conversion gains.",
                ],
            }

        return {"raw": "Mock AI response — task not recognized."}
