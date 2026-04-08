"""
Omura Automation AI Agent
Executes automated tasks (email, posting, follow-up, data sync) and
orchestrates multi-step workflows across the Omura platform.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class AutomationAI:
    """AI agent for task automation and workflow orchestration.

    Manages scheduled emails, content posting, CRM follow-ups, data
    synchronization, and composite workflows that chain multiple agents.
    """

    SUPPORTED_WORKFLOWS = {
        "lead_management",
        "content_publishing",
        "health_optimization",
        "business_metrics",
    }

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.logger = OmuraLogger("automation_ai")

    # ── Task Execution Methods ──────────────────────────────────────

    def execute_email_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Send a scheduled email response.

        Args:
            task: Dictionary with keys 'to', 'subject', 'body', 'reply_to_id'
                (optional), 'scheduled_at', and 'priority'.

        Returns:
            Dictionary with task_id, status, delivery details, and timestamp.
        """
        task_id = task.get("task_id", str(uuid4())[:12])
        recipient = task.get("to", "unknown@example.com")

        self.logger.info(
            "Executing email task",
            task_id=task_id,
            recipient=recipient,
            subject=task.get("subject", ""),
        )

        # Validate required fields
        missing_fields = [
            f for f in ["to", "subject", "body"] if f not in task
        ]
        if missing_fields:
            self.logger.error(
                "Email task missing required fields",
                task_id=task_id,
                missing=missing_fields,
            )
            return {
                "task_id": task_id,
                "task_type": "email",
                "status": "failed",
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "executed_at": datetime.utcnow().isoformat(),
            }

        # Generate AI-enhanced email body if draft mode
        if task.get("ai_enhance", False):
            prompt = (
                f"Enhance this email to '{recipient}' with subject "
                f"'{task['subject']}': {task['body'][:500]}"
            )
            ai_response = self._call_ai(prompt, context=task)
            enhanced_body = ai_response.get("enhanced_body", task["body"])
        else:
            enhanced_body = task["body"]

        # In production: integrate with email service (SendGrid, SES, etc.)
        result = {
            "task_id": task_id,
            "task_type": "email",
            "status": "sent",
            "delivery": {
                "to": recipient,
                "subject": task["subject"],
                "body_preview": enhanced_body[:200] + ("..." if len(enhanced_body) > 200 else ""),
                "reply_to_id": task.get("reply_to_id"),
                "ai_enhanced": task.get("ai_enhance", False),
            },
            "executed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Email task executed successfully",
            task_id=task_id,
            status="sent",
        )
        return result

    def execute_posting_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Post scheduled content to social media platforms.

        Args:
            task: Dictionary with keys 'platform', 'content_type',
                'content_body', 'media_urls' (optional), 'hashtags' (optional),
                'scheduled_at', and 'cross_post' (list of additional platforms).

        Returns:
            Dictionary with task_id, status, platform-specific post IDs,
            and scheduling confirmation.
        """
        task_id = task.get("task_id", str(uuid4())[:12])
        platform = task.get("platform", "unknown")

        self.logger.info(
            "Executing posting task",
            task_id=task_id,
            platform=platform,
            content_type=task.get("content_type", "unknown"),
        )

        if "content_body" not in task and "media_urls" not in task:
            self.logger.error(
                "Posting task missing content",
                task_id=task_id,
            )
            return {
                "task_id": task_id,
                "task_type": "posting",
                "status": "failed",
                "error": "Either 'content_body' or 'media_urls' is required.",
                "executed_at": datetime.utcnow().isoformat(),
            }

        # Determine all target platforms
        platforms = [platform] + task.get("cross_post", [])
        platform_results: list[dict[str, Any]] = []

        for p in platforms:
            # In production: call platform-specific API (Instagram Graph, TikTok, etc.)
            platform_results.append({
                "platform": p,
                "status": "published",
                "post_id": f"{p}_{uuid4().hex[:8]}",
                "url": f"https://{p}.com/post/{uuid4().hex[:8]}",
            })

        # Generate engagement prediction
        prompt = (
            f"Predict engagement for {task.get('content_type', 'post')} "
            f"on {platform}: '{task.get('content_body', '')[:200]}'"
        )
        ai_response = self._call_ai(prompt, context=task)

        result = {
            "task_id": task_id,
            "task_type": "posting",
            "status": "completed",
            "platforms_posted": platform_results,
            "content_preview": task.get("content_body", "")[:200],
            "hashtags_used": task.get("hashtags", []),
            "engagement_prediction": ai_response.get("engagement_prediction", {
                "estimated_reach": 2500,
                "estimated_likes": 180,
                "estimated_comments": 24,
                "estimated_shares": 12,
                "confidence": 0.65,
            }),
            "executed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Posting task executed successfully",
            task_id=task_id,
            platforms=len(platform_results),
        )
        return result

    def execute_followup_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Send a CRM follow-up message to a lead or contact.

        Args:
            task: Dictionary with keys 'contact_id', 'contact_name',
                'contact_email', 'channel' (email/sms/dm), 'context'
                (previous interaction summary), 'follow_up_type'
                (initial/reminder/closing), and 'template_id' (optional).

        Returns:
            Dictionary with task_id, status, generated message preview,
            and next follow-up suggestion.
        """
        task_id = task.get("task_id", str(uuid4())[:12])
        contact_name = task.get("contact_name", "Unknown Contact")
        channel = task.get("channel", "email")

        self.logger.info(
            "Executing follow-up task",
            task_id=task_id,
            contact=contact_name,
            channel=channel,
            follow_up_type=task.get("follow_up_type", "general"),
        )

        # Generate personalized follow-up message
        prompt = (
            f"Write a {task.get('follow_up_type', 'general')} follow-up "
            f"message to {contact_name} via {channel}. "
            f"Context: {task.get('context', 'No prior context.')}."
        )
        ai_response = self._call_ai(prompt, context=task)

        message_body = ai_response.get("message", (
            f"Hi {contact_name},\n\n"
            f"I wanted to follow up on our recent conversation. "
            f"I'd love to continue the discussion and see how we can work together.\n\n"
            f"Would you be available for a quick call this week?\n\n"
            f"Best regards"
        ))

        result = {
            "task_id": task_id,
            "task_type": "followup",
            "status": "sent",
            "delivery": {
                "contact_id": task.get("contact_id"),
                "contact_name": contact_name,
                "contact_email": task.get("contact_email"),
                "channel": channel,
                "follow_up_type": task.get("follow_up_type", "general"),
                "message_preview": message_body[:300],
            },
            "crm_updates": {
                "last_contact_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "interaction_count_incremented": True,
                "stage_updated": False,
            },
            "next_follow_up": ai_response.get("next_follow_up", {
                "suggested_date": "3 days from now",
                "suggested_channel": channel,
                "suggested_type": "reminder",
                "reason": "Allow time for response before escalating.",
            }),
            "executed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Follow-up task executed successfully",
            task_id=task_id,
            contact=contact_name,
            channel=channel,
        )
        return result

    def execute_update_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Sync and update data across connected platforms.

        Args:
            task: Dictionary with keys 'source' (platform or data source),
                'target' (destination platform/module), 'data_type'
                (e.g., 'contacts', 'transactions', 'analytics'),
                and 'filters' (optional query filters).

        Returns:
            Dictionary with task_id, status, records processed, sync
            summary, and any conflicts detected.
        """
        task_id = task.get("task_id", str(uuid4())[:12])
        source = task.get("source", "unknown")
        target = task.get("target", "unknown")
        data_type = task.get("data_type", "general")

        self.logger.info(
            "Executing update/sync task",
            task_id=task_id,
            source=source,
            target=target,
            data_type=data_type,
        )

        # In production: call platform APIs and perform actual data sync
        records_fetched = 47  # Mock
        records_updated = 42
        records_created = 3
        conflicts = 2

        result = {
            "task_id": task_id,
            "task_type": "update",
            "status": "completed",
            "sync_summary": {
                "source": source,
                "target": target,
                "data_type": data_type,
                "records_fetched": records_fetched,
                "records_updated": records_updated,
                "records_created": records_created,
                "records_skipped": records_fetched - records_updated - records_created,
                "conflicts_detected": conflicts,
            },
            "conflicts": [
                {
                    "record_id": "rec_a1b2c3",
                    "field": "email",
                    "source_value": "john@newdomain.com",
                    "target_value": "john@olddomain.com",
                    "resolution": "pending_review",
                },
                {
                    "record_id": "rec_d4e5f6",
                    "field": "phone",
                    "source_value": "+1-555-0199",
                    "target_value": "+1-555-0100",
                    "resolution": "pending_review",
                },
            ][:conflicts],
            "executed_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(
            "Update task executed successfully",
            task_id=task_id,
            records_updated=records_updated,
            conflicts=conflicts,
        )
        return result

    # ── Task Management Methods ─────────────────────────────────────

    def get_pending_tasks(self) -> list[dict[str, Any]]:
        """List all automation tasks awaiting execution.

        In production, queries the task queue table filtered by status='pending'.

        Returns:
            List of pending task dictionaries with task_id, type,
            scheduled_at, priority, and brief description.
        """
        self.logger.info("Fetching pending automation tasks")

        # In production: self.db.query(AutomationTask).filter_by(status="pending").all()
        pending_tasks = [
            {
                "task_id": "task_a1b2c3",
                "task_type": "email",
                "description": "Follow-up email to lead: Sarah M.",
                "priority": "high",
                "scheduled_at": "2026-03-24T09:00:00Z",
                "created_at": "2026-03-23T18:30:00Z",
            },
            {
                "task_id": "task_d4e5f6",
                "task_type": "posting",
                "description": "Instagram Reel: Weekly tips #12",
                "priority": "medium",
                "scheduled_at": "2026-03-24T12:00:00Z",
                "created_at": "2026-03-23T20:00:00Z",
            },
            {
                "task_id": "task_g7h8i9",
                "task_type": "update",
                "description": "Sync QuickBooks transactions to dashboard",
                "priority": "medium",
                "scheduled_at": "2026-03-24T06:00:00Z",
                "created_at": "2026-03-23T22:00:00Z",
            },
            {
                "task_id": "task_j0k1l2",
                "task_type": "followup",
                "description": "Second follow-up: Partnership inquiry from Alex",
                "priority": "high",
                "scheduled_at": "2026-03-24T10:30:00Z",
                "created_at": "2026-03-22T14:00:00Z",
            },
        ]

        self.logger.info(
            "Pending tasks retrieved",
            count=len(pending_tasks),
        )
        return pending_tasks

    def get_task_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent automation execution log.

        Args:
            limit: Maximum number of history entries to return. Defaults to 50.

        Returns:
            List of completed task records with task_id, type, status,
            execution duration, and timestamp.
        """
        self.logger.info("Fetching task history", limit=limit)

        # In production: self.db.query(AutomationTask).filter(
        #     AutomationTask.status.in_(["completed", "failed"])
        # ).order_by(AutomationTask.executed_at.desc()).limit(limit).all()
        history = [
            {
                "task_id": "task_x1y2z3",
                "task_type": "email",
                "description": "Onboarding email to new lead: James K.",
                "status": "completed",
                "duration_ms": 1240,
                "executed_at": "2026-03-23T14:32:00Z",
            },
            {
                "task_id": "task_m4n5o6",
                "task_type": "posting",
                "description": "TikTok video: Product showcase",
                "status": "completed",
                "duration_ms": 3450,
                "executed_at": "2026-03-23T12:00:00Z",
            },
            {
                "task_id": "task_p7q8r9",
                "task_type": "update",
                "description": "Sync Stripe payments to dashboard",
                "status": "completed",
                "duration_ms": 8920,
                "executed_at": "2026-03-23T06:00:00Z",
            },
            {
                "task_id": "task_s0t1u2",
                "task_type": "followup",
                "description": "Initial outreach to lead: Maria L.",
                "status": "completed",
                "duration_ms": 980,
                "executed_at": "2026-03-22T16:15:00Z",
            },
            {
                "task_id": "task_v3w4x5",
                "task_type": "email",
                "description": "Invoice reminder to client: TechCo",
                "status": "failed",
                "duration_ms": 520,
                "error": "SMTP connection timeout",
                "executed_at": "2026-03-22T09:00:00Z",
            },
        ]

        # Respect the limit
        history = history[:limit]

        self.logger.info(
            "Task history retrieved",
            entries=len(history),
        )
        return history

    # ── Workflow Orchestration ──────────────────────────────────────

    def run_workflow(
        self, workflow_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a named multi-step workflow.

        Orchestrates multiple automation steps and cross-agent calls into
        a single cohesive pipeline.

        Supported workflows:
            - lead_management: email summarize -> CRM score -> schedule follow-up -> update dashboard
            - content_publishing: draft content -> schedule posting -> predict engagement -> update metrics
            - health_optimization: collect data -> adjust schedule -> calculate energy -> suggest adjustments
            - business_metrics: collect revenue/expense -> calculate KPIs -> check alerts -> suggest optimizations

        Args:
            workflow_name: One of the supported workflow identifiers.
            params: Workflow-specific parameters dictionary.

        Returns:
            Dictionary with workflow_id, workflow_name, steps executed,
            results per step, overall status, and duration.
        """
        workflow_id = str(uuid4())[:12]

        self.logger.info(
            "Starting workflow",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
        )

        if workflow_name not in self.SUPPORTED_WORKFLOWS:
            self.logger.error(
                "Unsupported workflow requested",
                workflow_name=workflow_name,
                supported=list(self.SUPPORTED_WORKFLOWS),
            )
            return {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "status": "failed",
                "error": (
                    f"Unsupported workflow '{workflow_name}'. "
                    f"Supported: {', '.join(sorted(self.SUPPORTED_WORKFLOWS))}"
                ),
            }

        start_time = datetime.utcnow()

        # Dispatch to workflow-specific handler
        handler = {
            "lead_management": self._workflow_lead_management,
            "content_publishing": self._workflow_content_publishing,
            "health_optimization": self._workflow_health_optimization,
            "business_metrics": self._workflow_business_metrics,
        }[workflow_name]

        steps = handler(params)

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine overall status
        failed_steps = [s for s in steps if s.get("status") == "failed"]
        overall_status = "completed" if not failed_steps else "partial_failure"

        result = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": overall_status,
            "steps_total": len(steps),
            "steps_succeeded": len(steps) - len(failed_steps),
            "steps_failed": len(failed_steps),
            "steps": steps,
            "duration_ms": duration_ms,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

        self.logger.info(
            "Workflow completed",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=overall_status,
            duration_ms=duration_ms,
        )
        return result

    # ── Workflow Implementations ────────────────────────────────────

    def _workflow_lead_management(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Lead Management workflow:
        Incoming email -> Inbox AI summarizes -> CRM AI scores lead ->
        Schedule follow-up -> Update dashboard.
        """
        self.logger.info("Executing lead_management workflow")
        steps: list[dict[str, Any]] = []

        # Step 1: Summarize incoming email
        email_body = params.get("email_body", "")
        sender = params.get("sender_email", "unknown@example.com")
        sender_name = params.get("sender_name", "Unknown")

        prompt = f"Summarize this incoming email from {sender_name}: {email_body[:1000]}"
        ai_summary = self._call_ai(prompt, context={"step": "email_summary"})

        steps.append({
            "step": 1,
            "name": "email_summarization",
            "agent": "inbox_ai",
            "status": "completed",
            "result": {
                "sender": sender,
                "sender_name": sender_name,
                "summary": ai_summary.get("summary", (
                    f"Email from {sender_name} expressing interest in services. "
                    f"Requesting a call to discuss partnership opportunities."
                )),
                "intent": ai_summary.get("intent", "partnership_inquiry"),
                "urgency": ai_summary.get("urgency", "medium"),
                "key_points": ai_summary.get("key_points", [
                    "Interested in collaboration",
                    "Has budget allocated for Q2",
                    "Wants to schedule a call this week",
                ]),
            },
        })

        # Step 2: Score the lead via CRM AI
        prompt = (
            f"Score this lead: {sender_name} ({sender}). "
            f"Intent: {steps[0]['result']['intent']}. "
            f"Urgency: {steps[0]['result']['urgency']}."
        )
        ai_score = self._call_ai(prompt, context={"step": "lead_scoring"})

        lead_score = ai_score.get("score", 78)
        lead_tier = (
            "hot" if lead_score >= 80
            else "warm" if lead_score >= 50
            else "cold"
        )

        steps.append({
            "step": 2,
            "name": "lead_scoring",
            "agent": "crm_ai",
            "status": "completed",
            "result": {
                "lead_score": lead_score,
                "lead_tier": lead_tier,
                "scoring_factors": {
                    "intent_strength": 0.85,
                    "budget_signals": 0.70,
                    "urgency": 0.75,
                    "company_fit": 0.80,
                },
                "recommended_priority": "high" if lead_tier == "hot" else "medium",
            },
        })

        # Step 3: Schedule follow-up
        follow_up_task = {
            "contact_name": sender_name,
            "contact_email": sender,
            "channel": "email",
            "follow_up_type": "initial",
            "context": steps[0]["result"]["summary"],
        }
        follow_up_result = self.execute_followup_task(follow_up_task)

        steps.append({
            "step": 3,
            "name": "schedule_followup",
            "agent": "automation_ai",
            "status": follow_up_result.get("status", "completed"),
            "result": {
                "follow_up_scheduled": True,
                "channel": "email",
                "message_preview": follow_up_result.get("delivery", {}).get(
                    "message_preview", ""
                )[:200],
                "next_follow_up": follow_up_result.get("next_follow_up", {}),
            },
        })

        # Step 4: Update dashboard
        steps.append({
            "step": 4,
            "name": "update_dashboard",
            "agent": "automation_ai",
            "status": "completed",
            "result": {
                "crm_updated": True,
                "lead_added": True,
                "lead_id": f"lead_{uuid4().hex[:8]}",
                "dashboard_widgets_refreshed": [
                    "lead_pipeline",
                    "recent_activity",
                    "conversion_funnel",
                ],
            },
        })

        return steps

    def _workflow_content_publishing(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Content Publishing workflow:
        New idea -> Content AI drafts -> Schedule posting ->
        Predict engagement -> Update metrics.
        """
        self.logger.info("Executing content_publishing workflow")
        steps: list[dict[str, Any]] = []

        # Step 1: Draft content from idea
        idea = params.get("idea", "Share a productivity tip")
        platform = params.get("platform", "instagram")
        content_type = params.get("content_type", "carousel")

        prompt = (
            f"Draft a {content_type} for {platform} based on this idea: '{idea}'"
        )
        ai_draft = self._call_ai(prompt, context={"step": "content_draft"})

        steps.append({
            "step": 1,
            "name": "content_drafting",
            "agent": "content_ai",
            "status": "completed",
            "result": {
                "idea": idea,
                "platform": platform,
                "content_type": content_type,
                "draft": ai_draft.get("draft", {
                    "headline": "5 Productivity Hacks That Actually Work",
                    "body": (
                        "Slide 1: Stop multitasking — single-task for 90 minutes.\n"
                        "Slide 2: Time-block your calendar the night before.\n"
                        "Slide 3: Use the 2-minute rule for small tasks.\n"
                        "Slide 4: Take a 20-minute walk after lunch.\n"
                        "Slide 5: Review your day in 5 minutes before bed."
                    ),
                    "hashtags": ["#productivity", "#lifehacks", "#focus", "#success"],
                    "cta": "Save this for later and share with a friend who needs it!",
                }),
                "word_count": 85,
                "estimated_read_time": "45 seconds",
            },
        })

        # Step 2: Schedule posting
        posting_task = {
            "platform": platform,
            "content_type": content_type,
            "content_body": steps[0]["result"]["draft"].get("body", ""),
            "hashtags": steps[0]["result"]["draft"].get("hashtags", []),
            "scheduled_at": params.get("scheduled_at", "2026-03-25T12:00:00Z"),
            "cross_post": params.get("cross_post", []),
        }
        posting_result = self.execute_posting_task(posting_task)

        steps.append({
            "step": 2,
            "name": "schedule_posting",
            "agent": "automation_ai",
            "status": posting_result.get("status", "completed"),
            "result": {
                "platforms_posted": posting_result.get("platforms_posted", []),
                "scheduled_at": posting_task["scheduled_at"],
            },
        })

        # Step 3: Predict engagement
        prompt = (
            f"Predict engagement for this {content_type} on {platform}: "
            f"'{steps[0]['result']['draft'].get('headline', '')}'"
        )
        ai_prediction = self._call_ai(prompt, context={"step": "engagement_prediction"})

        steps.append({
            "step": 3,
            "name": "engagement_prediction",
            "agent": "content_ai",
            "status": "completed",
            "result": {
                "predicted_reach": ai_prediction.get("reach", 3200),
                "predicted_engagement_rate": ai_prediction.get("engagement_rate", 4.8),
                "predicted_saves": ai_prediction.get("saves", 145),
                "predicted_shares": ai_prediction.get("shares", 38),
                "best_time_confirmed": True,
                "confidence": 0.71,
            },
        })

        # Step 4: Update metrics dashboard
        steps.append({
            "step": 4,
            "name": "update_metrics",
            "agent": "automation_ai",
            "status": "completed",
            "result": {
                "content_calendar_updated": True,
                "metrics_dashboard_refreshed": True,
                "widgets_updated": [
                    "content_calendar",
                    "engagement_forecast",
                    "posting_schedule",
                ],
                "content_id": f"content_{uuid4().hex[:8]}",
            },
        })

        return steps

    def _workflow_health_optimization(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Health Optimization workflow:
        Collect health data -> Adjust schedule -> Calculate energy score ->
        Suggest adjustments.
        """
        self.logger.info("Executing health_optimization workflow")
        steps: list[dict[str, Any]] = []

        # Step 1: Collect health data
        health_data = {
            "last_sleep_hours": params.get("sleep_hours", 6.5),
            "sleep_quality": params.get("sleep_quality", 6),
            "exercise_days_this_week": params.get("exercise_days", 3),
            "nutrition_score": params.get("nutrition_score", 6),
            "hydration_liters": params.get("hydration_liters", 2.0),
            "stress_level": params.get("stress_level", 5),
        }

        steps.append({
            "step": 1,
            "name": "collect_health_data",
            "agent": "health_ai",
            "status": "completed",
            "result": {
                "data_sources": ["manual_entry", "sleep_tracker", "fitness_app"],
                "data_points_collected": len(health_data),
                "health_data": health_data,
                "collection_complete": True,
            },
        })

        # Step 2: Adjust daily schedule based on data
        prompt = (
            f"Adjust today's schedule based on health data: "
            f"sleep={health_data['last_sleep_hours']}hrs, "
            f"stress={health_data['stress_level']}/10."
        )
        ai_schedule = self._call_ai(prompt, context={"step": "schedule_adjustment"})

        low_sleep = health_data["last_sleep_hours"] < 7
        high_stress = health_data["stress_level"] > 6

        adjustments = []
        if low_sleep:
            adjustments.append({
                "type": "schedule",
                "change": "Delay intense work by 1 hour — start with light tasks.",
                "reason": f"Only {health_data['last_sleep_hours']} hours of sleep last night.",
            })
            adjustments.append({
                "type": "nutrition",
                "change": "Extra protein at breakfast; avoid sugar spikes.",
                "reason": "Compensate for reduced sleep recovery.",
            })
        if high_stress:
            adjustments.append({
                "type": "activity",
                "change": "Replace high-intensity workout with yoga or walking.",
                "reason": f"Stress level elevated at {health_data['stress_level']}/10.",
            })
            adjustments.append({
                "type": "schedule",
                "change": "Add a 15-minute breathing session at 14:00.",
                "reason": "Cortisol management.",
            })
        if not adjustments:
            adjustments.append({
                "type": "general",
                "change": "No major adjustments needed. Maintain current routine.",
                "reason": "Health metrics are within optimal ranges.",
            })

        steps.append({
            "step": 2,
            "name": "adjust_schedule",
            "agent": "health_ai",
            "status": "completed",
            "result": {
                "adjustments_made": len(adjustments),
                "adjustments": adjustments,
            },
        })

        # Step 3: Calculate energy score
        # Inline calculation (mirrors HealthAI.calculate_energy_score logic)
        sleep_hours_score = max(0.0, 100.0 - abs(health_data["last_sleep_hours"] - 8.0) * 15)
        sleep_quality_score = health_data["sleep_quality"] * 10.0
        sleep_component = sleep_hours_score * 0.6 + sleep_quality_score * 0.4
        exercise_component = min(100.0, (health_data["exercise_days_this_week"] / 5.0) * 100.0)
        nutrition_component = health_data["nutrition_score"] * 10.0
        hydration_component = min(100.0, (health_data["hydration_liters"] / 3.0) * 100.0)
        stress_penalty = max(0.0, (health_data["stress_level"] - 3) * 5.0)

        energy_score = max(0.0, min(100.0, (
            sleep_component * 0.35
            + exercise_component * 0.20
            + nutrition_component * 0.20
            + hydration_component * 0.10
        ) - stress_penalty))

        steps.append({
            "step": 3,
            "name": "calculate_energy_score",
            "agent": "health_ai",
            "status": "completed",
            "result": {
                "energy_score": round(energy_score, 1),
                "energy_level": (
                    "high" if energy_score >= 80
                    else "moderate" if energy_score >= 50
                    else "low"
                ),
                "components": {
                    "sleep": round(sleep_component, 1),
                    "exercise": round(exercise_component, 1),
                    "nutrition": round(nutrition_component, 1),
                    "hydration": round(hydration_component, 1),
                    "stress_penalty": round(stress_penalty, 1),
                },
            },
        })

        # Step 4: Suggest further adjustments
        prompt = (
            f"Suggest health adjustments. Energy score: {energy_score:.0f}/100. "
            f"Weakest area: {'sleep' if sleep_component < 50 else 'exercise' if exercise_component < 50 else 'nutrition'}."
        )
        ai_suggestions = self._call_ai(prompt, context={"step": "health_suggestions"})

        weakest = min(
            [("sleep", sleep_component), ("exercise", exercise_component),
             ("nutrition", nutrition_component), ("hydration", hydration_component)],
            key=lambda x: x[1],
        )

        steps.append({
            "step": 4,
            "name": "suggest_adjustments",
            "agent": "health_ai",
            "status": "completed",
            "result": {
                "primary_focus": weakest[0],
                "primary_focus_score": round(weakest[1], 1),
                "suggestions": ai_suggestions.get("suggestions", [
                    f"Focus on improving {weakest[0]} — it is your lowest scoring area.",
                    "Track your metrics daily for the next 7 days to establish a baseline.",
                    "Set one micro-habit related to your weakest area this week.",
                ]),
                "weekly_targets": {
                    "sleep": "7.5+ hours per night",
                    "exercise": "4+ sessions per week",
                    "nutrition": "Score 7+/10 daily",
                    "hydration": "2.5+ liters daily",
                    "stress": "Below 5/10 average",
                },
            },
        })

        return steps

    def _workflow_business_metrics(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Business Metrics workflow:
        Collect revenue/expense data -> Calculate KPIs ->
        Check alerts -> Suggest optimizations.
        """
        self.logger.info("Executing business_metrics workflow")
        steps: list[dict[str, Any]] = []

        # Step 1: Collect revenue and expense data
        revenue = params.get("revenue", 52000)
        expenses = params.get("expenses", 38000)
        previous_revenue = params.get("previous_revenue", 48000)
        previous_expenses = params.get("previous_expenses", 36000)
        customers = params.get("customers", 520)
        new_customers = params.get("new_customers", 45)
        churned_customers = params.get("churned_customers", 12)

        steps.append({
            "step": 1,
            "name": "collect_financial_data",
            "agent": "automation_ai",
            "status": "completed",
            "result": {
                "data_sources": ["quickbooks", "stripe", "manual_entry"],
                "period": params.get("period", "2026-03"),
                "revenue": revenue,
                "expenses": expenses,
                "previous_revenue": previous_revenue,
                "previous_expenses": previous_expenses,
                "customers": customers,
                "new_customers": new_customers,
                "churned_customers": churned_customers,
            },
        })

        # Step 2: Calculate KPIs
        profit = revenue - expenses
        profit_margin = (profit / revenue * 100) if revenue > 0 else 0
        revenue_growth = (
            (revenue - previous_revenue) / previous_revenue * 100
            if previous_revenue > 0 else 0
        )
        expense_growth = (
            (expenses - previous_expenses) / previous_expenses * 100
            if previous_expenses > 0 else 0
        )
        arpu = revenue / customers if customers > 0 else 0
        churn_rate = (
            churned_customers / (customers + churned_customers) * 100
            if (customers + churned_customers) > 0 else 0
        )
        ltv = arpu * (1 / (churn_rate / 100)) if churn_rate > 0 else arpu * 24
        cac = expenses * 0.3 / new_customers if new_customers > 0 else 0  # Assume 30% of expenses = acquisition
        ltv_cac_ratio = ltv / cac if cac > 0 else 0

        kpis = {
            "profit": round(profit, 2),
            "profit_margin_pct": round(profit_margin, 1),
            "revenue_growth_pct": round(revenue_growth, 1),
            "expense_growth_pct": round(expense_growth, 1),
            "arpu": round(arpu, 2),
            "churn_rate_pct": round(churn_rate, 2),
            "customer_ltv": round(ltv, 2),
            "cac": round(cac, 2),
            "ltv_cac_ratio": round(ltv_cac_ratio, 1),
            "net_customer_growth": new_customers - churned_customers,
            "mrr": revenue,
        }

        steps.append({
            "step": 2,
            "name": "calculate_kpis",
            "agent": "automation_ai",
            "status": "completed",
            "result": {
                "kpis": kpis,
                "period": params.get("period", "2026-03"),
            },
        })

        # Step 3: Check alerts
        alerts: list[dict[str, Any]] = []

        if churn_rate > 5:
            alerts.append({
                "severity": "critical",
                "metric": "churn_rate",
                "value": f"{churn_rate:.1f}%",
                "threshold": "5%",
                "message": "Churn rate exceeds acceptable threshold. Immediate retention analysis recommended.",
            })

        if expense_growth > revenue_growth and expense_growth > 10:
            alerts.append({
                "severity": "warning",
                "metric": "expense_growth",
                "value": f"{expense_growth:.1f}%",
                "threshold": f"revenue_growth ({revenue_growth:.1f}%)",
                "message": "Expenses growing faster than revenue. Review cost structure.",
            })

        if profit_margin < 15:
            alerts.append({
                "severity": "warning",
                "metric": "profit_margin",
                "value": f"{profit_margin:.1f}%",
                "threshold": "15%",
                "message": "Profit margin below healthy threshold for sustainable growth.",
            })

        if ltv_cac_ratio < 3:
            alerts.append({
                "severity": "info",
                "metric": "ltv_cac_ratio",
                "value": f"{ltv_cac_ratio:.1f}x",
                "threshold": "3x",
                "message": "LTV:CAC ratio below 3x. Acquisition efficiency needs improvement.",
            })

        if not alerts:
            alerts.append({
                "severity": "info",
                "metric": "overall",
                "value": "healthy",
                "threshold": "N/A",
                "message": "All business metrics are within healthy ranges.",
            })

        steps.append({
            "step": 3,
            "name": "check_alerts",
            "agent": "automation_ai",
            "status": "completed",
            "result": {
                "alerts_triggered": len(alerts),
                "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
                "warning_count": sum(1 for a in alerts if a["severity"] == "warning"),
                "alerts": alerts,
            },
        })

        # Step 4: Suggest optimizations
        prompt = (
            f"Suggest business optimizations. Revenue=${revenue:,.0f}, "
            f"Expenses=${expenses:,.0f}, margin={profit_margin:.1f}%, "
            f"churn={churn_rate:.1f}%, LTV:CAC={ltv_cac_ratio:.1f}x."
        )
        ai_optimizations = self._call_ai(prompt, context={"step": "business_optimization", "kpis": kpis})

        steps.append({
            "step": 4,
            "name": "suggest_optimizations",
            "agent": "automation_ai",
            "status": "completed",
            "result": {
                "optimization_suggestions": ai_optimizations.get("suggestions", [
                    {
                        "area": "revenue",
                        "suggestion": "Introduce an annual billing option with 15% discount to improve cash flow predictability.",
                        "estimated_impact": "+8% revenue retention",
                    },
                    {
                        "area": "expenses",
                        "suggestion": "Audit software subscriptions — eliminate tools with <2 active users.",
                        "estimated_impact": "-5% monthly expenses",
                    },
                    {
                        "area": "churn",
                        "suggestion": "Implement a win-back campaign for customers inactive >30 days.",
                        "estimated_impact": "-1.5% churn rate",
                    },
                    {
                        "area": "acquisition",
                        "suggestion": "Double down on the top-performing acquisition channel to improve CAC.",
                        "estimated_impact": "-20% CAC",
                    },
                ]),
                "priority_action": (
                    "Focus on churn reduction — it has the highest leverage on LTV and overall profitability."
                    if churn_rate > 3
                    else "Maintain current trajectory and optimize acquisition efficiency."
                ),
            },
        })

        return steps

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

        step = (context or {}).get("step", "")

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI automation assistant for Omura. "
            "You execute workflows, manage repetitive tasks, and orchestrate "
            "multi-step automated processes. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "email_summary": (
                "\n\nRespond with JSON containing: "
                '{"summary": "concise email summary", '
                '"intent": "partnership_inquiry|sales|support|general", '
                '"urgency": "high|medium|low", '
                '"key_points": ["point1", "point2", ...]}'
            ),
            "lead_scoring": (
                "\n\nRespond with JSON containing: "
                '{"score": <int 0-100 representing lead quality>}'
            ),
            "content_draft": (
                "\n\nRespond with JSON containing: "
                '{"draft": {"headline": "...", "body": "content body text", '
                '"hashtags": ["#tag1", ...], "cta": "call to action text"}}'
            ),
            "engagement_prediction": (
                "\n\nRespond with JSON containing: "
                '{"reach": <int estimated reach>, '
                '"engagement_rate": <float percentage>, '
                '"saves": <int>, "shares": <int>}'
            ),
            "schedule_adjustment": (
                "\n\nRespond with JSON containing: "
                '{"adjustments": [{"type": "schedule|nutrition|activity", '
                '"change": "...", "reason": "..."}, ...]}'
            ),
            "health_suggestions": (
                "\n\nRespond with JSON containing: "
                '{"suggestions": ["suggestion1", "suggestion2", ...]}'
            ),
            "business_optimization": (
                "\n\nRespond with JSON containing: "
                '{"suggestions": [{"area": "revenue|expenses|churn|acquisition", '
                '"suggestion": "...", "estimated_impact": "..."}, ...]}'
            ),
        }

        # For steps not in the map, determine from prompt content
        task_key = step if step in task_instructions else ""
        if not task_key:
            prompt_lower = prompt.lower()
            if "enhance" in prompt_lower and "email" in prompt_lower:
                task_key = "email_summary"
            elif "predict" in prompt_lower and "engagement" in prompt_lower:
                task_key = "engagement_prediction"
            elif "follow" in prompt_lower:
                task_key = "email_summary"

        full_prompt = prompt + task_instructions.get(task_key, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="automation_ai")

        if result is not None:
            self.logger.debug("Claude API returned valid response for step=%s", step)
            return result

        # ── Fallback: mock responses keyed by step ──
        self.logger.info("Falling back to mock response for step=%s", step)

        if step == "email_summary":
            return {
                "summary": (
                    "Prospective partner expressing interest in collaboration. "
                    "Has budget allocated and wants to schedule a call this week."
                ),
                "intent": "partnership_inquiry",
                "urgency": "medium",
                "key_points": [
                    "Interested in collaboration",
                    "Has budget allocated for Q2",
                    "Wants to schedule a call this week",
                ],
            }

        if step == "lead_scoring":
            return {"score": 78}

        if step == "content_draft":
            return {
                "draft": {
                    "headline": "5 Productivity Hacks That Actually Work",
                    "body": (
                        "Slide 1: Stop multitasking — single-task for 90 minutes.\n"
                        "Slide 2: Time-block your calendar the night before.\n"
                        "Slide 3: Use the 2-minute rule for small tasks.\n"
                        "Slide 4: Take a 20-minute walk after lunch.\n"
                        "Slide 5: Review your day in 5 minutes before bed."
                    ),
                    "hashtags": ["#productivity", "#lifehacks", "#focus", "#success"],
                    "cta": "Save this for later and share with a friend who needs it!",
                },
            }

        if step == "engagement_prediction":
            return {
                "reach": 3200,
                "engagement_rate": 4.8,
                "saves": 145,
                "shares": 38,
            }

        if step == "schedule_adjustment":
            return {"adjustments": []}

        if step == "health_suggestions":
            return {
                "suggestions": [
                    "Focus on improving your weakest health metric this week.",
                    "Track your metrics daily for 7 days to establish a baseline.",
                    "Set one micro-habit related to your weakest area.",
                ],
            }

        if step == "business_optimization":
            return {
                "suggestions": [
                    {
                        "area": "revenue",
                        "suggestion": "Introduce annual billing with 15% discount for improved cash flow.",
                        "estimated_impact": "+8% revenue retention",
                    },
                    {
                        "area": "expenses",
                        "suggestion": "Audit software subscriptions — cut tools with <2 active users.",
                        "estimated_impact": "-5% monthly expenses",
                    },
                    {
                        "area": "churn",
                        "suggestion": "Launch win-back campaign for customers inactive >30 days.",
                        "estimated_impact": "-1.5% churn rate",
                    },
                    {
                        "area": "acquisition",
                        "suggestion": "Double down on top acquisition channel to reduce CAC.",
                        "estimated_impact": "-20% CAC",
                    },
                ],
            }

        # Default fallback
        return {
            "enhanced_body": "Enhanced email content placeholder.",
            "engagement_prediction": {
                "estimated_reach": 2500,
                "estimated_likes": 180,
                "estimated_comments": 24,
                "estimated_shares": 12,
                "confidence": 0.65,
            },
            "message": (
                "Hi there,\n\n"
                "Thank you for reaching out. I'd love to continue our conversation "
                "and explore how we can work together.\n\n"
                "Would you be available for a quick call this week?\n\n"
                "Best regards"
            ),
            "next_follow_up": {
                "suggested_date": "3 days from now",
                "suggested_channel": "email",
                "suggested_type": "reminder",
                "reason": "Allow time for response before escalating.",
            },
        }
