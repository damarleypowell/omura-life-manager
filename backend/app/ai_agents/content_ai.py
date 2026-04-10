"""
Omura Content AI Agent
Handles AI-driven content creation, editing, hashtag generation,
scheduling, performance analysis, and ideation for social media platforms.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class ContentAI:
    """AI-powered content creation and management agent.

    Generates drafts, refines copy, produces platform-specific hashtags,
    manages posting schedules, analyzes engagement metrics, and suggests
    new content ideas based on trends.
    """

    SUPPORTED_PLATFORMS = (
        "instagram", "tiktok", "youtube", "facebook",
        "twitter", "linkedin", "threads",
    )

    def __init__(self, db_session: Any) -> None:
        """Initialize the ContentAI agent.

        Args:
            db_session: SQLAlchemy database session for content CRUD
                        and analytics queries.
        """
        self.db = db_session
        self.logger = OmuraLogger("content_ai")
        self.logger.info("ContentAI agent initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_draft(self, topic: str, platform: str) -> dict:
        """Create a content draft tailored to a specific platform.

        Args:
            topic: The subject or theme for the content.
            platform: Target platform (e.g. 'instagram', 'tiktok').

        Returns:
            A dict containing:
                - title (str)
                - caption (str)
                - hashtags (list[str])
                - platform (str)
                - content_type (str): e.g. 'reel', 'carousel', 'post'
                - created_at (str): ISO timestamp
        """
        platform = self._normalize_platform(platform)
        self.logger.info(
            "Generating content draft", topic=topic, platform=platform,
        )

        prompt = (
            f"Create a {platform} content draft about: {topic}\n"
            f"Include a catchy title, engaging caption, relevant hashtags, "
            f"and suggest the best content format for this platform."
        )
        result = self._call_ai(prompt, context={"task": "generate_draft", "platform": platform})

        draft = {
            "title": result.get("title", ""),
            "caption": result.get("caption", ""),
            "hashtags": result.get("hashtags", []),
            "platform": platform,
            "content_type": result.get("content_type", "post"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(
            "Draft generated",
            platform=platform,
            title=draft["title"],
            hashtag_count=len(draft["hashtags"]),
        )
        return draft

    def edit_content(self, content: dict, instructions: str) -> dict:
        """Refine existing content based on editing instructions.

        Args:
            content: The current content dict (must include 'caption').
            instructions: Natural-language editing directions, e.g.
                          'make it shorter', 'add a call to action'.

        Returns:
            Updated content dict with revised fields and an
            'edit_history' entry appended.
        """
        self.logger.info(
            "Editing content",
            content_id=content.get("id"),
            instructions=instructions[:100],
        )

        prompt = (
            f"Edit the following content based on these instructions: {instructions}\n\n"
            f"Title: {content.get('title', '')}\n"
            f"Caption: {content.get('caption', '')}\n"
            f"Hashtags: {content.get('hashtags', [])}"
        )
        result = self._call_ai(prompt, context={"task": "edit_content"})

        edit_entry = {
            "instructions": instructions,
            "edited_at": datetime.now(timezone.utc).isoformat(),
        }

        edited = {
            **content,
            "title": result.get("title", content.get("title", "")),
            "caption": result.get("caption", content.get("caption", "")),
            "hashtags": result.get("hashtags", content.get("hashtags", [])),
            "edit_history": content.get("edit_history", []) + [edit_entry],
        }

        self.logger.info(
            "Content edited successfully",
            content_id=content.get("id"),
            revisions=len(edited["edit_history"]),
        )
        return edited

    def generate_hashtags(self, content: str, platform: str) -> list[str]:
        """Generate relevant hashtags for the given content and platform.

        Args:
            content: The text content (caption, description, etc.).
            platform: Target platform to tailor hashtag strategy.

        Returns:
            A list of hashtag strings (including the '#' prefix).
        """
        platform = self._normalize_platform(platform)
        self.logger.info(
            "Generating hashtags",
            platform=platform,
            content_length=len(content),
        )

        prompt = (
            f"Generate relevant hashtags for this {platform} content:\n"
            f"{content[:500]}\n"
            f"Return 10-15 hashtags ranked by relevance."
        )
        result = self._call_ai(prompt, context={"task": "generate_hashtags", "platform": platform})
        hashtags = result.get("hashtags", [])

        self.logger.info("Hashtags generated", count=len(hashtags), platform=platform)
        return hashtags

    def schedule_post(self, content_id: int, scheduled_at: datetime) -> dict:
        """Schedule content for future posting.

        Args:
            content_id: Database ID of the content to schedule.
            scheduled_at: The UTC datetime to publish.

        Returns:
            A dict with scheduling confirmation details:
                - content_id (int)
                - scheduled_at (str): ISO timestamp
                - status (str): 'scheduled'
                - optimal_time_suggestion (str | None)
        """
        self.logger.info(
            "Scheduling post",
            content_id=content_id,
            scheduled_at=scheduled_at.isoformat(),
        )

        prompt = (
            f"The user wants to schedule content ID {content_id} at "
            f"{scheduled_at.isoformat()}. Is this an optimal posting time? "
            f"If not, suggest a better time."
        )
        result = self._call_ai(prompt, context={"task": "schedule_post"})

        schedule_info = {
            "content_id": content_id,
            "scheduled_at": scheduled_at.isoformat(),
            "status": "scheduled",
            "optimal_time_suggestion": result.get("optimal_time"),
        }

        # Placeholder: persist to DB
        # self.db.query(Content).filter_by(id=content_id).update({"scheduled_at": scheduled_at})
        # self.db.commit()

        self.logger.info(
            "Post scheduled",
            content_id=content_id,
            status="scheduled",
            suggestion=schedule_info["optimal_time_suggestion"],
        )
        return schedule_info

    def analyze_performance(self, content_id: int) -> dict:
        """Analyze engagement metrics for a piece of published content.

        Args:
            content_id: Database ID of the published content.

        Returns:
            A dict with:
                - content_id (int)
                - metrics (dict): likes, comments, shares, reach, impressions
                - engagement_rate (float): percentage
                - insights (list[str]): AI-generated observations
                - recommendations (list[str]): actionable next steps
        """
        self.logger.info("Analyzing content performance", content_id=content_id)

        # Placeholder: fetch actual metrics from DB / platform APIs
        metrics = self._fetch_content_metrics(content_id)

        prompt = (
            f"Analyze the performance of content ID {content_id}.\n"
            f"Metrics: {metrics}\n"
            f"Provide insights and recommendations to improve engagement."
        )
        result = self._call_ai(prompt, context={"task": "analyze_performance"})

        analysis = {
            "content_id": content_id,
            "metrics": metrics,
            "engagement_rate": result.get("engagement_rate", 0.0),
            "insights": result.get("insights", []),
            "recommendations": result.get("recommendations", []),
        }

        self.logger.info(
            "Performance analysis complete",
            content_id=content_id,
            engagement_rate=analysis["engagement_rate"],
        )
        return analysis

    def suggest_content_ideas(self, recent_trends: list[str]) -> list[dict]:
        """Generate new content ideas based on recent trends.

        Args:
            recent_trends: A list of trending topics, keywords, or
                           hashtags to use as inspiration.

        Returns:
            A list of idea dicts, each containing:
                - title (str)
                - description (str)
                - suggested_platform (str)
                - content_type (str)
                - estimated_engagement (str): 'high', 'medium', 'low'
        """
        self.logger.info(
            "Generating content ideas", trend_count=len(recent_trends),
        )

        prompt = (
            f"Based on these trending topics, suggest 5 content ideas:\n"
            f"Trends: {recent_trends}\n"
            f"For each idea provide: title, description, best platform, "
            f"content format, and estimated engagement potential."
        )
        result = self._call_ai(prompt, context={"task": "suggest_ideas"})
        ideas = result.get("ideas", [])

        self.logger.info("Content ideas generated", count=len(ideas))
        return ideas

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name to lowercase, validate against supported list."""
        normalized = platform.strip().lower()
        if normalized not in self.SUPPORTED_PLATFORMS:
            self.logger.warning(
                "Unsupported platform, defaulting to instagram",
                requested=platform,
            )
            normalized = "instagram"
        return normalized

    def _fetch_content_metrics(self, content_id: int) -> dict:
        """Fetch engagement metrics from DB or platform APIs.

        Returns mock metrics until integrations are wired up.
        """
        try:
            # Placeholder: actual DB / API query
            self.logger.debug("Fetching metrics", content_id=content_id)
            return {
                "likes": 342,
                "comments": 28,
                "shares": 15,
                "saves": 47,
                "reach": 4820,
                "impressions": 6140,
            }
        except Exception as exc:
            self.logger.warning(
                "Failed to fetch metrics, returning defaults",
                content_id=content_id,
                error=str(exc),
            )
            return {
                "likes": 0, "comments": 0, "shares": 0,
                "saves": 0, "reach": 0, "impressions": 0,
            }

    def _call_ai(self, prompt: str, context: Optional[dict] = None) -> dict:
        """Call Claude API to process a prompt, with mock fallback.

        Args:
            prompt: The natural-language prompt to send.
            context: Optional metadata about the task type.

        Returns:
            A dict containing the AI response fields.
        """
        task = (context or {}).get("task", "unknown")
        platform = (context or {}).get("platform", "instagram")
        self.logger.debug("Calling AI provider", task=task, prompt_length=len(prompt))

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI content creation assistant for Omura, a personal life & business manager. "
            "You create social media content, generate hashtags, suggest posting schedules, and analyze engagement. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "generate_draft": (
                "\n\nRespond with JSON containing: "
                '{"title": "catchy content title", '
                '"caption": "engaging caption text", '
                '"hashtags": ["#hashtag1", "#hashtag2", ...], '
                '"content_type": "reel|carousel|video|post|article|thread"}'
            ),
            "edit_content": (
                "\n\nRespond with JSON containing: "
                '{"title": "updated title", '
                '"caption": "revised caption text", '
                '"hashtags": ["#hashtag1", "#hashtag2", ...]}'
            ),
            "generate_hashtags": (
                "\n\nRespond with JSON containing: "
                '{"hashtags": ["#hashtag1", "#hashtag2", ...]} '
                "Return 10-15 hashtags ranked by relevance."
            ),
            "schedule_post": (
                "\n\nRespond with JSON containing: "
                '{"optimal_time": "ISO datetime string for best posting time", '
                '"reason": "explanation of why this time is optimal"}'
            ),
            "analyze_performance": (
                "\n\nRespond with JSON containing: "
                '{"engagement_rate": <float percentage>, '
                '"insights": ["insight1", "insight2", ...], '
                '"recommendations": ["recommendation1", "recommendation2", ...]}'
            ),
            "suggest_ideas": (
                "\n\nRespond with JSON containing: "
                '{"ideas": [{"title": "...", "description": "...", '
                '"suggested_platform": "...", "content_type": "...", '
                '"estimated_engagement": "high|medium|low"}, ...]}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="content_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # ── Fallback: mock responses keyed by task ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if task == "generate_draft":
            content_types = {
                "instagram": "carousel",
                "tiktok": "reel",
                "youtube": "video",
                "linkedin": "article",
                "twitter": "thread",
                "facebook": "post",
                "threads": "post",
            }
            return {
                "title": "5 Productivity Hacks That Actually Work",
                "caption": (
                    "Stop wasting time on hacks that don't stick. Here are "
                    "5 battle-tested strategies I use every single day to stay "
                    "focused and get more done. Save this for later!\n\n"
                    "Which one are you trying first? Drop a comment below."
                ),
                "hashtags": [
                    "#productivity", "#timemanagement", "#entrepreneurlife",
                    "#businesstips", "#growthmindset", "#motivation",
                    "#dailyroutine", "#successhabits",
                ],
                "content_type": content_types.get(platform, "post"),
            }

        if task == "edit_content":
            return {
                "title": "5 Productivity Hacks (Updated)",
                "caption": (
                    "These 5 productivity strategies helped me reclaim 2 hours "
                    "every day. Swipe to see each one explained step by step.\n\n"
                    "Save this post and try #3 today!"
                ),
                "hashtags": [
                    "#productivity", "#timemanagement", "#lifehacks",
                    "#entrepreneurship", "#worksmarter",
                ],
            }

        if task == "generate_hashtags":
            return {
                "hashtags": [
                    "#contentcreator", "#socialmediamarketing", "#digitalmarketing",
                    "#brandgrowth", "#contentmarketing", "#creatoreconomy",
                    "#instagramgrowth", "#reelsinstagram", "#viralcontent",
                    "#onlinebusiness", "#marketingtips", "#socialmediatips",
                ],
            }

        if task == "schedule_post":
            return {
                "optimal_time": "2026-03-25T18:30:00+00:00",
                "reason": (
                    "Engagement peaks on Wednesday evenings between 6-8 PM UTC "
                    "for your audience demographic."
                ),
            }

        if task == "analyze_performance":
            return {
                "engagement_rate": 7.6,
                "insights": [
                    "Engagement rate of 7.6% is above the platform average of 3.2%.",
                    "Carousel format drove 40% more saves than single-image posts.",
                    "Peak engagement occurred within the first 2 hours of posting.",
                ],
                "recommendations": [
                    "Continue using carousel format for educational content.",
                    "Experiment with posting 30 minutes earlier to capture a wider audience.",
                    "Add a stronger CTA in the final slide to boost comment rate.",
                ],
            }

        if task == "suggest_ideas":
            return {
                "ideas": [
                    {
                        "title": "Day in the Life: Entrepreneur Edition",
                        "description": "Behind-the-scenes vlog showing real daily workflow.",
                        "suggested_platform": "tiktok",
                        "content_type": "reel",
                        "estimated_engagement": "high",
                    },
                    {
                        "title": "Tools I Can't Live Without",
                        "description": "Showcase top 5 apps and tools with quick demos.",
                        "suggested_platform": "instagram",
                        "content_type": "carousel",
                        "estimated_engagement": "high",
                    },
                    {
                        "title": "Myth vs. Reality: Passive Income",
                        "description": "Debunk common misconceptions with real numbers.",
                        "suggested_platform": "youtube",
                        "content_type": "video",
                        "estimated_engagement": "medium",
                    },
                    {
                        "title": "Client Wins This Month",
                        "description": "Celebrate client success stories with permission.",
                        "suggested_platform": "linkedin",
                        "content_type": "post",
                        "estimated_engagement": "medium",
                    },
                    {
                        "title": "Quick Tip: Automate Your Inbox",
                        "description": "60-second tutorial on inbox automation workflow.",
                        "suggested_platform": "tiktok",
                        "content_type": "reel",
                        "estimated_engagement": "high",
                    },
                ],
            }

        return {"raw": "Mock AI response — task not recognized."}
