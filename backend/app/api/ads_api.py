"""
Omura Advertising Platform API Integrations
Async-ready clients for Facebook Ads, Google Ads, and TikTok Ads.
Each client normalizes campaign and performance data into the Metric schema
so the finance dashboard can aggregate ad spend across all platforms.

All methods return mock data during development.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


# ═══════════════════════════════════════════════════════════════════════
#  Facebook Ads
# ═══════════════════════════════════════════════════════════════════════

class FacebookAdsClient:
    """Async-ready client for the Facebook Marketing API.

    Manages ad campaigns, retrieves performance metrics, and maps
    everything to the Omura Metric schema for unified reporting.
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self) -> None:
        self.app_id: Optional[str] = settings.FACEBOOK_APP_ID
        self.app_secret: Optional[str] = settings.FACEBOOK_APP_SECRET
        self.access_token: Optional[str] = None
        self.ad_account_id: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("facebook_ads_client")
        self._logger.info("FacebookAdsClient initialized")

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth code for Facebook Marketing API access tokens.

        Args:
            auth_code: Authorization code from Facebook Business Login.

        Returns:
            Token payload with ``access_token`` and ``ad_account_id``.
        """
        self._logger.info("Authenticating with Facebook Ads API", auth_code_provided=bool(auth_code))
        self.access_token = "mock_fb_ads_access_token"
        self.ad_account_id = "act_mock_12345"
        return {
            "access_token": self.access_token,
            "ad_account_id": self.ad_account_id,
            "expires_in": 5184000,
        }

    async def get_campaigns(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all ad campaigns for the connected account.

        Args:
            status_filter: Optional filter — ``"ACTIVE"``, ``"PAUSED"``,
                or ``"ARCHIVED"``. ``None`` returns all.

        Returns:
            List of campaign summary dicts.
        """
        self._logger.info("Fetching Facebook Ads campaigns", status_filter=status_filter)
        campaigns = [
            {
                "id": "fb_campaign_001",
                "name": "Spring Sale 2026",
                "status": "ACTIVE",
                "objective": "CONVERSIONS",
                "daily_budget": 50.00,
                "lifetime_budget": 1500.00,
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "metadata": {"source": "facebook_ads"},
            },
            {
                "id": "fb_campaign_002",
                "name": "Brand Awareness Q1",
                "status": "ACTIVE",
                "objective": "REACH",
                "daily_budget": 30.00,
                "lifetime_budget": 900.00,
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
                "metadata": {"source": "facebook_ads"},
            },
            {
                "id": "fb_campaign_003",
                "name": "Retargeting - Website Visitors",
                "status": "PAUSED",
                "objective": "CONVERSIONS",
                "daily_budget": 25.00,
                "lifetime_budget": 750.00,
                "start_date": "2026-02-01",
                "end_date": "2026-04-30",
                "metadata": {"source": "facebook_ads"},
            },
        ]
        if status_filter:
            campaigns = [c for c in campaigns if c["status"] == status_filter]
        self._logger.info("Fetched Facebook Ads campaigns", count=len(campaigns))
        return campaigns

    async def get_campaign_metrics(self, campaign_id: str, period_days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve performance metrics for a specific campaign.

        Args:
            campaign_id: The Facebook campaign ID.
            period_days: Number of past days to aggregate.

        Returns:
            List of Metric-schema dicts covering spend, impressions,
            clicks, conversions, CPA, and ROAS.
        """
        self._logger.info(
            "Fetching Facebook Ads campaign metrics",
            campaign_id=campaign_id,
            period_days=period_days,
        )
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        metrics = [
            {
                "category": "ad_spend",
                "name": f"fb_ads_spend_{campaign_id}",
                "value": 342.50,
                "unit": "USD",
                "source": "facebook_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "facebook"},
            },
            {
                "category": "kpi",
                "name": f"fb_ads_impressions_{campaign_id}",
                "value": 45000,
                "unit": "count",
                "source": "facebook_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "facebook"},
            },
            {
                "category": "kpi",
                "name": f"fb_ads_clicks_{campaign_id}",
                "value": 1230,
                "unit": "count",
                "source": "facebook_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "facebook"},
            },
            {
                "category": "kpi",
                "name": f"fb_ads_conversions_{campaign_id}",
                "value": 48,
                "unit": "count",
                "source": "facebook_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "facebook"},
            },
            {
                "category": "kpi",
                "name": f"fb_ads_cpa_{campaign_id}",
                "value": 7.14,
                "unit": "USD",
                "source": "facebook_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "facebook"},
            },
            {
                "category": "kpi",
                "name": f"fb_ads_roas_{campaign_id}",
                "value": 3.8,
                "unit": "ratio",
                "source": "facebook_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "facebook"},
            },
        ]
        self._logger.info(
            "Fetched Facebook Ads campaign metrics",
            campaign_id=campaign_id,
            metrics_count=len(metrics),
        )
        return metrics

    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Facebook ad campaign.

        Args:
            data: Campaign configuration containing:
                - ``name``: Campaign name.
                - ``objective``: Campaign objective (e.g. ``"CONVERSIONS"``).
                - ``daily_budget``: Daily spend limit in account currency.
                - ``targeting``: Audience targeting parameters.
                - ``start_date``: Campaign start date.
                - ``end_date``: Optional campaign end date.

        Returns:
            Created campaign confirmation with ``id`` and ``status``.
        """
        self._logger.info("Creating Facebook Ads campaign", name=data.get("name"))
        result = {
            "id": "fb_campaign_new_001",
            "name": data.get("name", "Untitled Campaign"),
            "status": "PAUSED",
            "objective": data.get("objective", "CONVERSIONS"),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Facebook Ads campaign created", campaign_id=result["id"])
        return result

    async def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause an active Facebook ad campaign.

        Args:
            campaign_id: The campaign ID to pause.

        Returns:
            Updated campaign status confirmation.
        """
        self._logger.info("Pausing Facebook Ads campaign", campaign_id=campaign_id)
        result = {
            "id": campaign_id,
            "status": "PAUSED",
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Facebook Ads campaign paused", campaign_id=campaign_id)
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("FacebookAdsClient HTTP connection closed")


# ═══════════════════════════════════════════════════════════════════════
#  Google Ads
# ═══════════════════════════════════════════════════════════════════════

class GoogleAdsClient:
    """Async-ready client for the Google Ads API (v15).

    Manages Search, Display, and YouTube ad campaigns and normalizes
    performance data into the Omura Metric schema.
    """

    BASE_URL = "https://googleads.googleapis.com/v15"

    def __init__(self) -> None:
        self.client_id: Optional[str] = settings.GOOGLE_CLIENT_ID
        self.client_secret: Optional[str] = settings.GOOGLE_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.customer_id: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("google_ads_client")
        self._logger.info("GoogleAdsClient initialized")

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth code for Google Ads API access tokens.

        Args:
            auth_code: Authorization code from Google's OAuth consent screen
                with Ads API scopes.

        Returns:
            Token payload with ``access_token`` and ``customer_id``.
        """
        self._logger.info("Authenticating with Google Ads API", auth_code_provided=bool(auth_code))
        self.access_token = "mock_gads_access_token"
        self.customer_id = "mock_gads_customer_12345"
        return {
            "access_token": self.access_token,
            "customer_id": self.customer_id,
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def get_campaigns(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all Google Ads campaigns for the connected account.

        Args:
            status_filter: Optional filter — ``"ENABLED"``, ``"PAUSED"``,
                or ``"REMOVED"``. ``None`` returns all.

        Returns:
            List of campaign summary dicts.
        """
        self._logger.info("Fetching Google Ads campaigns", status_filter=status_filter)
        campaigns = [
            {
                "id": "gads_campaign_001",
                "name": "Search - Brand Terms",
                "status": "ENABLED",
                "type": "SEARCH",
                "daily_budget": 40.00,
                "start_date": "2026-01-15",
                "end_date": None,
                "metadata": {"source": "google_ads"},
            },
            {
                "id": "gads_campaign_002",
                "name": "Display - Retargeting",
                "status": "ENABLED",
                "type": "DISPLAY",
                "daily_budget": 25.00,
                "start_date": "2026-02-01",
                "end_date": "2026-06-30",
                "metadata": {"source": "google_ads"},
            },
            {
                "id": "gads_campaign_003",
                "name": "YouTube - Product Demo",
                "status": "PAUSED",
                "type": "VIDEO",
                "daily_budget": 60.00,
                "start_date": "2026-03-01",
                "end_date": "2026-04-30",
                "metadata": {"source": "google_ads"},
            },
        ]
        if status_filter:
            campaigns = [c for c in campaigns if c["status"] == status_filter]
        self._logger.info("Fetched Google Ads campaigns", count=len(campaigns))
        return campaigns

    async def get_campaign_metrics(self, campaign_id: str, period_days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve performance metrics for a specific Google Ads campaign.

        Args:
            campaign_id: The Google Ads campaign ID.
            period_days: Number of past days to aggregate.

        Returns:
            List of Metric-schema dicts with spend, impressions, clicks,
            conversions, CPC, and conversion rate.
        """
        self._logger.info(
            "Fetching Google Ads campaign metrics",
            campaign_id=campaign_id,
            period_days=period_days,
        )
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        metrics = [
            {
                "category": "ad_spend",
                "name": f"gads_spend_{campaign_id}",
                "value": 278.90,
                "unit": "USD",
                "source": "google_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "google"},
            },
            {
                "category": "kpi",
                "name": f"gads_impressions_{campaign_id}",
                "value": 32000,
                "unit": "count",
                "source": "google_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "google"},
            },
            {
                "category": "kpi",
                "name": f"gads_clicks_{campaign_id}",
                "value": 890,
                "unit": "count",
                "source": "google_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "google"},
            },
            {
                "category": "kpi",
                "name": f"gads_conversions_{campaign_id}",
                "value": 35,
                "unit": "count",
                "source": "google_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "google"},
            },
            {
                "category": "kpi",
                "name": f"gads_cpc_{campaign_id}",
                "value": 0.31,
                "unit": "USD",
                "source": "google_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "google"},
            },
            {
                "category": "kpi",
                "name": f"gads_conversion_rate_{campaign_id}",
                "value": 3.93,
                "unit": "%",
                "source": "google_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "google"},
            },
        ]
        self._logger.info(
            "Fetched Google Ads campaign metrics",
            campaign_id=campaign_id,
            metrics_count=len(metrics),
        )
        return metrics

    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Google Ads campaign.

        Args:
            data: Campaign configuration containing:
                - ``name``: Campaign name.
                - ``type``: Campaign type (``"SEARCH"``, ``"DISPLAY"``, ``"VIDEO"``).
                - ``daily_budget``: Daily spend limit in USD.
                - ``bidding_strategy``: Bidding strategy type.
                - ``targeting``: Targeting parameters (keywords, audiences, etc.).

        Returns:
            Created campaign confirmation with ``id`` and ``status``.
        """
        self._logger.info("Creating Google Ads campaign", name=data.get("name"))
        result = {
            "id": "gads_campaign_new_001",
            "name": data.get("name", "Untitled Campaign"),
            "status": "PAUSED",
            "type": data.get("type", "SEARCH"),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Google Ads campaign created", campaign_id=result["id"])
        return result

    async def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause an active Google Ads campaign.

        Args:
            campaign_id: The campaign ID to pause.

        Returns:
            Updated campaign status confirmation.
        """
        self._logger.info("Pausing Google Ads campaign", campaign_id=campaign_id)
        result = {
            "id": campaign_id,
            "status": "PAUSED",
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("Google Ads campaign paused", campaign_id=campaign_id)
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("GoogleAdsClient HTTP connection closed")


# ═══════════════════════════════════════════════════════════════════════
#  TikTok Ads
# ═══════════════════════════════════════════════════════════════════════

class TikTokAdsClient:
    """Async-ready client for the TikTok Marketing API.

    Manages Spark Ads, In-Feed Ads, and TopView campaigns while
    normalizing performance data to the Omura Metric schema.
    """

    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

    def __init__(self) -> None:
        self.client_key: Optional[str] = settings.TIKTOK_CLIENT_KEY
        self.client_secret: Optional[str] = settings.TIKTOK_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.advertiser_id: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("tiktok_ads_client")
        self._logger.info("TikTokAdsClient initialized")

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth code for TikTok Marketing API access tokens.

        Args:
            auth_code: Authorization code from TikTok Business Center.

        Returns:
            Token payload with ``access_token`` and ``advertiser_id``.
        """
        self._logger.info("Authenticating with TikTok Ads API", auth_code_provided=bool(auth_code))
        self.access_token = "mock_tt_ads_access_token"
        self.advertiser_id = "mock_tt_advertiser_12345"
        return {
            "access_token": self.access_token,
            "advertiser_id": self.advertiser_id,
            "expires_in": 86400,
        }

    async def get_campaigns(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all TikTok ad campaigns for the connected advertiser.

        Args:
            status_filter: Optional filter — ``"ACTIVE"``, ``"PAUSED"``,
                or ``"DELETED"``. ``None`` returns all.

        Returns:
            List of campaign summary dicts.
        """
        self._logger.info("Fetching TikTok Ads campaigns", status_filter=status_filter)
        campaigns = [
            {
                "id": "tt_campaign_001",
                "name": "Spark Ads - UGC Push",
                "status": "ACTIVE",
                "objective": "TRAFFIC",
                "daily_budget": 75.00,
                "lifetime_budget": 2250.00,
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "metadata": {"source": "tiktok_ads"},
            },
            {
                "id": "tt_campaign_002",
                "name": "In-Feed - Product Launch",
                "status": "ACTIVE",
                "objective": "CONVERSIONS",
                "daily_budget": 100.00,
                "lifetime_budget": 3000.00,
                "start_date": "2026-03-10",
                "end_date": "2026-04-10",
                "metadata": {"source": "tiktok_ads"},
            },
            {
                "id": "tt_campaign_003",
                "name": "TopView - Brand Moment",
                "status": "PAUSED",
                "objective": "REACH",
                "daily_budget": 200.00,
                "lifetime_budget": 2000.00,
                "start_date": "2026-02-14",
                "end_date": "2026-02-15",
                "metadata": {"source": "tiktok_ads"},
            },
        ]
        if status_filter:
            campaigns = [c for c in campaigns if c["status"] == status_filter]
        self._logger.info("Fetched TikTok Ads campaigns", count=len(campaigns))
        return campaigns

    async def get_campaign_metrics(self, campaign_id: str, period_days: int = 7) -> List[Dict[str, Any]]:
        """Retrieve performance metrics for a specific TikTok Ads campaign.

        Args:
            campaign_id: The TikTok campaign ID.
            period_days: Number of past days to aggregate.

        Returns:
            List of Metric-schema dicts covering spend, impressions, clicks,
            video views, conversions, and CPM.
        """
        self._logger.info(
            "Fetching TikTok Ads campaign metrics",
            campaign_id=campaign_id,
            period_days=period_days,
        )
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        metrics = [
            {
                "category": "ad_spend",
                "name": f"tt_ads_spend_{campaign_id}",
                "value": 520.00,
                "unit": "USD",
                "source": "tiktok_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "tiktok"},
            },
            {
                "category": "kpi",
                "name": f"tt_ads_impressions_{campaign_id}",
                "value": 180000,
                "unit": "count",
                "source": "tiktok_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "tiktok"},
            },
            {
                "category": "kpi",
                "name": f"tt_ads_clicks_{campaign_id}",
                "value": 4200,
                "unit": "count",
                "source": "tiktok_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "tiktok"},
            },
            {
                "category": "kpi",
                "name": f"tt_ads_video_views_{campaign_id}",
                "value": 95000,
                "unit": "count",
                "source": "tiktok_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "tiktok"},
            },
            {
                "category": "kpi",
                "name": f"tt_ads_conversions_{campaign_id}",
                "value": 67,
                "unit": "count",
                "source": "tiktok_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "tiktok"},
            },
            {
                "category": "kpi",
                "name": f"tt_ads_cpm_{campaign_id}",
                "value": 2.89,
                "unit": "USD",
                "source": "tiktok_ads",
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "metadata": {"campaign_id": campaign_id, "platform": "tiktok"},
            },
        ]
        self._logger.info(
            "Fetched TikTok Ads campaign metrics",
            campaign_id=campaign_id,
            metrics_count=len(metrics),
        )
        return metrics

    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new TikTok ad campaign.

        Args:
            data: Campaign configuration containing:
                - ``name``: Campaign name.
                - ``objective``: e.g. ``"TRAFFIC"``, ``"CONVERSIONS"``, ``"REACH"``.
                - ``daily_budget``: Daily spend limit in USD.
                - ``targeting``: Audience targeting (age, interests, regions).
                - ``creative``: Ad creative specifications.

        Returns:
            Created campaign confirmation with ``id`` and ``status``.
        """
        self._logger.info("Creating TikTok Ads campaign", name=data.get("name"))
        result = {
            "id": "tt_campaign_new_001",
            "name": data.get("name", "Untitled Campaign"),
            "status": "PAUSED",
            "objective": data.get("objective", "TRAFFIC"),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("TikTok Ads campaign created", campaign_id=result["id"])
        return result

    async def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pause an active TikTok ad campaign.

        Args:
            campaign_id: The campaign ID to pause.

        Returns:
            Updated campaign status confirmation.
        """
        self._logger.info("Pausing TikTok Ads campaign", campaign_id=campaign_id)
        result = {
            "id": campaign_id,
            "status": "PAUSED",
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._logger.info("TikTok Ads campaign paused", campaign_id=campaign_id)
        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
        self._logger.info("TikTokAdsClient HTTP connection closed")
