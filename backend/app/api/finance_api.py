"""
Omura Finance and Health API Integrations
Async-ready clients for QuickBooks Online and aggregated health data.
QuickBooksClient normalizes accounting data into the Metric schema.
HealthDataClient normalizes fitness/sleep/nutrition into the HealthEntry schema.

All methods return mock data during development.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


# ═══════════════════════════════════════════════════════════════════════
#  QuickBooks Online
# ═══════════════════════════════════════════════════════════════════════

class QuickBooksClient:
    """Async-ready client for the QuickBooks Online Accounting API.

    Provides revenue, expense, invoice, and profit-and-loss reporting,
    normalizing everything into the Omura Metric schema for the
    unified finance dashboard.
    """

    BASE_URL = "https://quickbooks.api.intuit.com/v3/company"

    def __init__(self) -> None:
        self.client_id: Optional[str] = settings.QUICKBOOKS_CLIENT_ID
        self.client_secret: Optional[str] = settings.QUICKBOOKS_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.realm_id: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept": "application/json"},
        )
        self._logger = OmuraLogger("quickbooks_client")
        self._logger.info("QuickBooksClient initialized")

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth 2.0 code for QuickBooks access tokens.

        Args:
            auth_code: Authorization code from Intuit's OAuth flow.

        Returns:
            Token payload with ``access_token``, ``refresh_token``, and
            ``realm_id``.
        """
        self._logger.info("Authenticating with QuickBooks API", auth_code_provided=bool(auth_code))
        self.access_token = "mock_qb_access_token"
        self.refresh_token = "mock_qb_refresh_token"
        self.realm_id = "mock_realm_12345"
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "realm_id": self.realm_id,
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def get_revenue(self, period: str = "this_month") -> List[Dict[str, Any]]:
        """Retrieve revenue metrics for the specified period.

        Args:
            period: Time period identifier. Supported values:
                ``"this_month"``, ``"last_month"``, ``"this_quarter"``,
                ``"this_year"``, or an ISO date range ``"2026-01-01:2026-03-31"``.

        Returns:
            List of Metric-schema dicts with revenue breakdowns.
        """
        self._logger.info("Fetching revenue data", period=period)
        period_start, period_end = self._resolve_period(period)
        metrics = [
            {
                "category": "revenue",
                "name": "total_revenue",
                "value": 28750.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "currency": "USD"},
            },
            {
                "category": "revenue",
                "name": "service_revenue",
                "value": 18500.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "revenue_type": "service"},
            },
            {
                "category": "revenue",
                "name": "product_revenue",
                "value": 7250.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "revenue_type": "product"},
            },
            {
                "category": "revenue",
                "name": "recurring_revenue",
                "value": 3000.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "revenue_type": "recurring"},
            },
        ]
        self._logger.info("Revenue data fetched", period=period, metrics_count=len(metrics))
        return metrics

    async def get_expenses(self, period: str = "this_month") -> List[Dict[str, Any]]:
        """Retrieve expense metrics for the specified period.

        Args:
            period: Time period identifier (same format as ``get_revenue``).

        Returns:
            List of Metric-schema dicts with expense breakdowns by category.
        """
        self._logger.info("Fetching expense data", period=period)
        period_start, period_end = self._resolve_period(period)
        metrics = [
            {
                "category": "expense",
                "name": "total_expenses",
                "value": 15200.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period},
            },
            {
                "category": "expense",
                "name": "payroll",
                "value": 8000.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "expense_type": "payroll"},
            },
            {
                "category": "expense",
                "name": "software_subscriptions",
                "value": 1200.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "expense_type": "software"},
            },
            {
                "category": "expense",
                "name": "ad_spend",
                "value": 3500.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "expense_type": "marketing"},
            },
            {
                "category": "expense",
                "name": "office_and_utilities",
                "value": 1500.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "expense_type": "overhead"},
            },
            {
                "category": "expense",
                "name": "miscellaneous",
                "value": 1000.00,
                "unit": "USD",
                "source": "quickbooks",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "metadata": {"period": period, "expense_type": "other"},
            },
        ]
        self._logger.info("Expense data fetched", period=period, metrics_count=len(metrics))
        return metrics

    async def get_invoices(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve invoices from QuickBooks.

        Args:
            status: Optional filter — ``"paid"``, ``"unpaid"``, ``"overdue"``.
                ``None`` returns all invoices.

        Returns:
            List of invoice dicts with Metric-compatible value fields.
        """
        self._logger.info("Fetching invoices", status=status)
        now = datetime.utcnow()
        invoices = [
            {
                "id": "qb_inv_001",
                "customer_name": "Acme Corp",
                "amount": 5000.00,
                "currency": "USD",
                "status": "paid",
                "issued_date": (now - timedelta(days=30)).isoformat(),
                "due_date": (now - timedelta(days=15)).isoformat(),
                "paid_date": (now - timedelta(days=10)).isoformat(),
                "metadata": {"source": "quickbooks", "invoice_number": "INV-2026-001"},
            },
            {
                "id": "qb_inv_002",
                "customer_name": "Beta LLC",
                "amount": 3200.00,
                "currency": "USD",
                "status": "unpaid",
                "issued_date": (now - timedelta(days=10)).isoformat(),
                "due_date": (now + timedelta(days=20)).isoformat(),
                "paid_date": None,
                "metadata": {"source": "quickbooks", "invoice_number": "INV-2026-002"},
            },
            {
                "id": "qb_inv_003",
                "customer_name": "Gamma Inc",
                "amount": 1800.00,
                "currency": "USD",
                "status": "overdue",
                "issued_date": (now - timedelta(days=45)).isoformat(),
                "due_date": (now - timedelta(days=5)).isoformat(),
                "paid_date": None,
                "metadata": {"source": "quickbooks", "invoice_number": "INV-2026-003"},
            },
            {
                "id": "qb_inv_004",
                "customer_name": "Delta Co",
                "amount": 7500.00,
                "currency": "USD",
                "status": "paid",
                "issued_date": (now - timedelta(days=60)).isoformat(),
                "due_date": (now - timedelta(days=30)).isoformat(),
                "paid_date": (now - timedelta(days=28)).isoformat(),
                "metadata": {"source": "quickbooks", "invoice_number": "INV-2026-004"},
            },
        ]
        if status:
            invoices = [inv for inv in invoices if inv["status"] == status]
        self._logger.info("Invoices fetched", count=len(invoices))
        return invoices

    async def get_profit_loss(self, period: str = "this_month") -> Dict[str, Any]:
        """Generate a profit-and-loss summary for the specified period.

        Args:
            period: Time period identifier (same format as ``get_revenue``).

        Returns:
            Dict with revenue, expenses, net income, and margin percentage,
            each as Metric-compatible entries.
        """
        self._logger.info("Generating P&L report", period=period)
        period_start, period_end = self._resolve_period(period)
        report = {
            "period": period,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_revenue": 28750.00,
            "total_expenses": 15200.00,
            "net_income": 13550.00,
            "profit_margin_pct": 47.13,
            "metrics": [
                {
                    "category": "kpi",
                    "name": "net_income",
                    "value": 13550.00,
                    "unit": "USD",
                    "source": "quickbooks",
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "metadata": {"period": period, "report": "profit_loss"},
                },
                {
                    "category": "kpi",
                    "name": "profit_margin",
                    "value": 47.13,
                    "unit": "%",
                    "source": "quickbooks",
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "metadata": {"period": period, "report": "profit_loss"},
                },
            ],
            "metadata": {"source": "quickbooks", "generated_at": datetime.utcnow().isoformat()},
        }
        self._logger.info(
            "P&L report generated",
            period=period,
            net_income=report["net_income"],
        )
        return report

    @staticmethod
    def _resolve_period(period: str) -> tuple[datetime, datetime]:
        """Convert a human-readable period string into start/end datetimes.

        Args:
            period: One of ``"this_month"``, ``"last_month"``,
                ``"this_quarter"``, ``"this_year"``, or a colon-separated
                ISO date range.

        Returns:
            Tuple of (period_start, period_end) datetimes.
        """
        now = datetime.utcnow()
        if period == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "last_month":
            first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = first_of_this_month - timedelta(seconds=1)
            start = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "this_quarter":
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "this_year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif ":" in period:
            parts = period.split(":")
            start = datetime.fromisoformat(parts[0])
            end = datetime.fromisoformat(parts[1])
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        return start, end

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("QuickBooksClient HTTP connection closed")


# ═══════════════════════════════════════════════════════════════════════
#  Health Data
# ═══════════════════════════════════════════════════════════════════════

class HealthDataClient:
    """Async-ready client for aggregated health and fitness data.

    Abstracts over multiple potential sources (Google Fit, Apple Health,
    wearables) and normalizes everything into the Omura HealthEntry schema.
    In production, this would connect to Google Fit REST API, Apple
    HealthKit via a bridge service, or direct wearable APIs.
    """

    GOOGLE_FIT_URL = "https://www.googleapis.com/fitness/v1/users/me"

    def __init__(self) -> None:
        self.client_id: Optional[str] = settings.GOOGLE_CLIENT_ID
        self.client_secret: Optional[str] = settings.GOOGLE_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("health_data_client")
        self._logger.info("HealthDataClient initialized")

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate with the health data provider (Google Fit by default).

        Args:
            auth_code: Authorization code from Google's OAuth consent screen
                with Fitness API scopes.

        Returns:
            Token payload confirming access.
        """
        self._logger.info("Authenticating with Health Data API", auth_code_provided=bool(auth_code))
        self.access_token = "mock_health_access_token"
        return {
            "access_token": self.access_token,
            "provider": "google_fit",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def get_workouts(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve workout/exercise entries for the past N days.

        Args:
            days: Number of past days to retrieve.

        Returns:
            List of HealthEntry-schema dicts for workout activities.
        """
        self._logger.info("Fetching workout data", days=days)
        now = datetime.utcnow()
        workouts = [
            {
                "category": "workout",
                "name": "Morning Run",
                "value": 5.2,
                "unit": "km",
                "notes": "Easy pace, zone 2 heart rate. Felt good.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=0, hours=8)).isoformat(),
                "metadata": {
                    "activity_type": "running",
                    "duration_minutes": 32,
                    "calories_burned": 380,
                    "avg_heart_rate": 142,
                },
            },
            {
                "category": "workout",
                "name": "Weight Training - Upper Body",
                "value": 55.0,
                "unit": "minutes",
                "notes": "Bench press, overhead press, rows. Progressive overload week 3.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=1, hours=7)).isoformat(),
                "metadata": {
                    "activity_type": "strength_training",
                    "duration_minutes": 55,
                    "calories_burned": 290,
                    "exercises": ["bench_press", "overhead_press", "barbell_row", "curls"],
                },
            },
            {
                "category": "workout",
                "name": "Yoga Session",
                "value": 40.0,
                "unit": "minutes",
                "notes": "Vinyasa flow. Recovery day.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=2, hours=6)).isoformat(),
                "metadata": {
                    "activity_type": "yoga",
                    "duration_minutes": 40,
                    "calories_burned": 150,
                },
            },
            {
                "category": "workout",
                "name": "HIIT Circuit",
                "value": 25.0,
                "unit": "minutes",
                "notes": "4 rounds of burpees, kettlebell swings, box jumps.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=3, hours=7)).isoformat(),
                "metadata": {
                    "activity_type": "hiit",
                    "duration_minutes": 25,
                    "calories_burned": 320,
                    "avg_heart_rate": 165,
                },
            },
            {
                "category": "workout",
                "name": "Evening Walk",
                "value": 3.8,
                "unit": "km",
                "notes": "Neighborhood loop with podcast.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=4, hours=18)).isoformat(),
                "metadata": {
                    "activity_type": "walking",
                    "duration_minutes": 45,
                    "calories_burned": 180,
                    "steps": 5200,
                },
            },
        ]
        # Filter to requested window
        cutoff = now - timedelta(days=days)
        workouts = [
            w for w in workouts
            if datetime.fromisoformat(w["recorded_at"]) >= cutoff
        ]
        self._logger.info("Workout data fetched", count=len(workouts))
        return workouts

    async def get_sleep_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve sleep tracking entries for the past N days.

        Args:
            days: Number of past days to retrieve.

        Returns:
            List of HealthEntry-schema dicts for sleep sessions.
        """
        self._logger.info("Fetching sleep data", days=days)
        now = datetime.utcnow()
        sleep_entries = [
            {
                "category": "sleep",
                "name": "Night Sleep",
                "value": 7.5,
                "unit": "hours",
                "notes": "Good quality. Woke up once.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=0)).replace(hour=7, minute=0).isoformat(),
                "metadata": {
                    "sleep_start": (now - timedelta(days=0)).replace(hour=23, minute=30).isoformat(),
                    "sleep_end": (now).replace(hour=7, minute=0).isoformat(),
                    "deep_sleep_hours": 2.1,
                    "light_sleep_hours": 3.8,
                    "rem_sleep_hours": 1.6,
                    "awake_minutes": 15,
                    "sleep_score": 82,
                },
            },
            {
                "category": "sleep",
                "name": "Night Sleep",
                "value": 6.8,
                "unit": "hours",
                "notes": "Went to bed late. Slightly restless.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=1)).replace(hour=7, minute=30).isoformat(),
                "metadata": {
                    "deep_sleep_hours": 1.8,
                    "light_sleep_hours": 3.5,
                    "rem_sleep_hours": 1.5,
                    "awake_minutes": 22,
                    "sleep_score": 71,
                },
            },
            {
                "category": "sleep",
                "name": "Night Sleep",
                "value": 8.1,
                "unit": "hours",
                "notes": "Excellent. No disruptions.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=2)).replace(hour=6, minute=45).isoformat(),
                "metadata": {
                    "deep_sleep_hours": 2.5,
                    "light_sleep_hours": 3.9,
                    "rem_sleep_hours": 1.7,
                    "awake_minutes": 8,
                    "sleep_score": 91,
                },
            },
            {
                "category": "sleep",
                "name": "Night Sleep",
                "value": 7.0,
                "unit": "hours",
                "notes": "Average night.",
                "source": "google_fit",
                "recorded_at": (now - timedelta(days=3)).replace(hour=7, minute=15).isoformat(),
                "metadata": {
                    "deep_sleep_hours": 2.0,
                    "light_sleep_hours": 3.4,
                    "rem_sleep_hours": 1.6,
                    "awake_minutes": 18,
                    "sleep_score": 76,
                },
            },
        ]
        cutoff = now - timedelta(days=days)
        sleep_entries = [
            s for s in sleep_entries
            if datetime.fromisoformat(s["recorded_at"]) >= cutoff
        ]
        self._logger.info("Sleep data fetched", count=len(sleep_entries))
        return sleep_entries

    async def get_nutrition(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve nutrition/meal logging entries for the past N days.

        Args:
            days: Number of past days to retrieve.

        Returns:
            List of HealthEntry-schema dicts for nutrition records.
        """
        self._logger.info("Fetching nutrition data", days=days)
        now = datetime.utcnow()
        nutrition_entries = [
            {
                "category": "nutrition",
                "name": "Daily Intake Summary",
                "value": 2150.0,
                "unit": "calories",
                "notes": "Balanced day. Hit protein target.",
                "source": "manual",
                "recorded_at": (now - timedelta(days=0)).replace(hour=21, minute=0).isoformat(),
                "metadata": {
                    "protein_g": 145,
                    "carbs_g": 220,
                    "fat_g": 72,
                    "fiber_g": 28,
                    "water_liters": 2.8,
                    "meals": 4,
                },
            },
            {
                "category": "nutrition",
                "name": "Daily Intake Summary",
                "value": 2400.0,
                "unit": "calories",
                "notes": "Slightly over target. Had a late snack.",
                "source": "manual",
                "recorded_at": (now - timedelta(days=1)).replace(hour=21, minute=0).isoformat(),
                "metadata": {
                    "protein_g": 130,
                    "carbs_g": 260,
                    "fat_g": 85,
                    "fiber_g": 22,
                    "water_liters": 2.5,
                    "meals": 5,
                },
            },
            {
                "category": "nutrition",
                "name": "Daily Intake Summary",
                "value": 1950.0,
                "unit": "calories",
                "notes": "Light eating day. Intermittent fasting.",
                "source": "manual",
                "recorded_at": (now - timedelta(days=2)).replace(hour=21, minute=0).isoformat(),
                "metadata": {
                    "protein_g": 120,
                    "carbs_g": 190,
                    "fat_g": 65,
                    "fiber_g": 25,
                    "water_liters": 3.0,
                    "meals": 2,
                },
            },
            {
                "category": "nutrition",
                "name": "Daily Intake Summary",
                "value": 2200.0,
                "unit": "calories",
                "notes": "On target. Meal prep day.",
                "source": "manual",
                "recorded_at": (now - timedelta(days=3)).replace(hour=21, minute=0).isoformat(),
                "metadata": {
                    "protein_g": 150,
                    "carbs_g": 230,
                    "fat_g": 68,
                    "fiber_g": 30,
                    "water_liters": 2.7,
                    "meals": 4,
                },
            },
        ]
        cutoff = now - timedelta(days=days)
        nutrition_entries = [
            n for n in nutrition_entries
            if datetime.fromisoformat(n["recorded_at"]) >= cutoff
        ]
        self._logger.info("Nutrition data fetched", count=len(nutrition_entries))
        return nutrition_entries

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("HealthDataClient HTTP connection closed")
