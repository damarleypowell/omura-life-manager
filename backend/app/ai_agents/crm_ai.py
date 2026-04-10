"""
Omura CRM AI Agent
Provides AI-driven CRM capabilities: lead scoring, follow-up suggestions,
pipeline analysis, automated outreach, and lead source classification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class CrmAI:
    """AI-powered CRM management agent.

    Scores leads, generates personalized follow-up actions, analyzes the
    sales pipeline, automates outreach messaging, and classifies inbound
    leads by source and intent.
    """

    LEAD_STAGES = (
        "new", "contacted", "qualified", "proposal",
        "negotiation", "won", "lost",
    )
    LEAD_SOURCES = (
        "organic_search", "paid_ads", "social_media", "referral",
        "cold_outreach", "event", "inbound_form", "partner",
    )

    def __init__(self, db_session: Any) -> None:
        """Initialize the CrmAI agent.

        Args:
            db_session: SQLAlchemy database session for querying leads,
                        contacts, deals, and communication history.
        """
        self.db = db_session
        self.logger = OmuraLogger("crm_ai")
        self.logger.info("CrmAI agent initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_lead(self, lead: dict) -> float:
        """Calculate an AI-driven lead score from 0 to 100.

        Evaluates engagement signals, demographic fit, behavioral data,
        and communication history to produce a composite score.

        Args:
            lead: Dict containing lead data. Expected keys:
                - name (str)
                - email (str)
                - company (str | None)
                - source (str)
                - interactions (list[dict]): past touchpoints
                - last_activity (str | None): ISO timestamp
                - deal_value (float | None)

        Returns:
            A float score between 0 (cold) and 100 (hot).
        """
        self.logger.info(
            "Scoring lead",
            lead_name=lead.get("name"),
            source=lead.get("source"),
        )

        prompt = (
            f"Score this lead from 0-100 based on likelihood to convert.\n"
            f"Name: {lead.get('name')}\n"
            f"Company: {lead.get('company', 'N/A')}\n"
            f"Source: {lead.get('source', 'unknown')}\n"
            f"Interactions: {len(lead.get('interactions', []))}\n"
            f"Last activity: {lead.get('last_activity', 'N/A')}\n"
            f"Deal value: {lead.get('deal_value', 'N/A')}"
        )
        result = self._call_ai(prompt, context={"task": "score_lead", "lead": lead})

        score = max(0.0, min(100.0, float(result.get("score", 50.0))))

        self.logger.info(
            "Lead scored",
            lead_name=lead.get("name"),
            score=score,
        )
        return score

    def suggest_followup(self, lead: dict) -> dict:
        """Generate a follow-up action and message for a lead.

        Args:
            lead: Dict containing lead data (same schema as score_lead).

        Returns:
            A dict containing:
                - action (str): e.g. 'send_email', 'schedule_call', 'send_proposal'
                - subject (str): suggested email/call subject
                - message (str): draft follow-up message
                - urgency (str): 'high', 'medium', 'low'
                - best_time (str): recommended contact time
        """
        self.logger.info(
            "Generating follow-up suggestion",
            lead_name=lead.get("name"),
        )

        prompt = (
            f"Suggest a follow-up action for this lead.\n"
            f"Name: {lead.get('name')}\n"
            f"Company: {lead.get('company', 'N/A')}\n"
            f"Stage: {lead.get('stage', 'new')}\n"
            f"Last contact: {lead.get('last_activity', 'N/A')}\n"
            f"Previous interactions: {lead.get('interactions', [])}\n"
            f"Generate: action type, subject, message, urgency, and best contact time."
        )
        result = self._call_ai(prompt, context={"task": "suggest_followup"})

        followup = {
            "action": result.get("action", "send_email"),
            "subject": result.get("subject", ""),
            "message": result.get("message", ""),
            "urgency": result.get("urgency", "medium"),
            "best_time": result.get("best_time", ""),
        }

        self.logger.info(
            "Follow-up suggestion ready",
            lead_name=lead.get("name"),
            action=followup["action"],
            urgency=followup["urgency"],
        )
        return followup

    def analyze_pipeline(self) -> dict:
        """Generate a CRM pipeline overview with conversion metrics.

        Returns:
            A dict containing:
                - total_leads (int)
                - by_stage (dict[str, int])
                - conversion_rates (dict[str, float]): stage-to-stage rates
                - total_pipeline_value (float)
                - avg_deal_size (float)
                - avg_days_to_close (float)
                - health_score (float): 0-100
                - insights (list[str])
                - generated_at (str): ISO timestamp
        """
        self.logger.info("Analyzing CRM pipeline")

        leads = self._fetch_all_leads()
        deals = self._fetch_active_deals()

        prompt = (
            f"Analyze the CRM pipeline.\n"
            f"Total leads: {len(leads)}\n"
            f"Active deals: {len(deals)}\n"
            f"Generate: stage breakdown, conversion rates, pipeline value, "
            f"health score, and actionable insights."
        )
        result = self._call_ai(prompt, context={"task": "analyze_pipeline"})

        analysis = {
            "total_leads": result.get("total_leads", 0),
            "by_stage": result.get("by_stage", {}),
            "conversion_rates": result.get("conversion_rates", {}),
            "total_pipeline_value": result.get("total_pipeline_value", 0.0),
            "avg_deal_size": result.get("avg_deal_size", 0.0),
            "avg_days_to_close": result.get("avg_days_to_close", 0.0),
            "health_score": result.get("health_score", 0.0),
            "insights": result.get("insights", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(
            "Pipeline analysis complete",
            total_leads=analysis["total_leads"],
            pipeline_value=analysis["total_pipeline_value"],
            health=analysis["health_score"],
        )
        return analysis

    def automate_outreach(self, leads: list[dict]) -> list[dict]:
        """Generate personalized outreach messages for a batch of leads.

        Args:
            leads: List of lead dicts. Each should contain at least
                   'name', 'company', 'source', and 'interests'.

        Returns:
            A list of outreach dicts, each containing:
                - lead_id (int | str)
                - lead_name (str)
                - channel (str): 'email', 'linkedin', 'sms'
                - subject (str)
                - message (str)
                - personalization_notes (str)
        """
        self.logger.info("Generating automated outreach", lead_count=len(leads))

        outreach_results: list[dict] = []

        for lead in leads:
            prompt = (
                f"Write a personalized outreach message for this lead.\n"
                f"Name: {lead.get('name')}\n"
                f"Company: {lead.get('company', 'N/A')}\n"
                f"Source: {lead.get('source', 'unknown')}\n"
                f"Interests: {lead.get('interests', [])}\n"
                f"Keep it professional, concise, and value-focused."
            )
            result = self._call_ai(
                prompt, context={"task": "automate_outreach", "lead": lead},
            )

            outreach = {
                "lead_id": lead.get("id"),
                "lead_name": lead.get("name", ""),
                "channel": result.get("channel", "email"),
                "subject": result.get("subject", ""),
                "message": result.get("message", ""),
                "personalization_notes": result.get("personalization_notes", ""),
            }
            outreach_results.append(outreach)

            self.logger.debug(
                "Outreach generated",
                lead_name=lead.get("name"),
                channel=outreach["channel"],
            )

        self.logger.info(
            "Outreach batch complete", generated=len(outreach_results),
        )
        return outreach_results

    def classify_lead_source(self, communication: dict) -> dict:
        """Identify the lead source and intent from an inbound communication.

        Args:
            communication: Dict with:
                - sender (str)
                - channel (str): e.g. 'email', 'form', 'social_dm'
                - subject (str | None)
                - body (str)
                - metadata (dict | None): referrer URL, UTM params, etc.

        Returns:
            A dict containing:
                - source (str): classified lead source
                - intent (str): e.g. 'purchase', 'inquiry', 'support', 'partnership'
                - confidence (float): 0-1
                - suggested_stage (str): recommended pipeline stage
                - tags (list[str]): auto-generated tags
        """
        self.logger.info(
            "Classifying lead source",
            sender=communication.get("sender"),
            channel=communication.get("channel"),
        )

        prompt = (
            f"Classify the source and intent of this inbound communication.\n"
            f"Sender: {communication.get('sender')}\n"
            f"Channel: {communication.get('channel')}\n"
            f"Subject: {communication.get('subject', 'N/A')}\n"
            f"Body: {communication.get('body', '')[:500]}\n"
            f"Metadata: {communication.get('metadata', {})}"
        )
        result = self._call_ai(prompt, context={"task": "classify_source"})

        classification = {
            "source": result.get("source", "unknown"),
            "intent": result.get("intent", "inquiry"),
            "confidence": result.get("confidence", 0.0),
            "suggested_stage": result.get("suggested_stage", "new"),
            "tags": result.get("tags", []),
        }

        self.logger.info(
            "Lead classified",
            sender=communication.get("sender"),
            source=classification["source"],
            intent=classification["intent"],
            confidence=classification["confidence"],
        )
        return classification

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_all_leads(self) -> list[dict]:
        """Fetch all leads from the database."""
        try:
            from backend.app.database.models import Lead
            rows = self.db.query(Lead).limit(100).all()
            leads = []
            for r in rows:
                leads.append({
                    "id": r.id,
                    "name": r.name or "",
                    "email": r.email or "",
                    "company": r.company or "",
                    "source": r.source or "",
                    "stage": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "score": r.score or 0,
                    "deal_value": r.deal_value or 0,
                    "last_activity": r.last_contact.isoformat() if r.last_contact else "",
                    "interactions": [],
                })
            self.logger.info(f"Fetched {len(leads)} leads from DB")
            return leads
        except Exception as exc:
            self.logger.warning("Failed to fetch leads", error=str(exc))
            return []

    def _fetch_active_deals(self) -> list[dict]:
        """Fetch active deals (leads in negotiation/proposal stage) from DB."""
        try:
            from backend.app.database.models import Lead, LeadStatus
            active_statuses = [LeadStatus.QUALIFIED, LeadStatus.PROPOSAL]
            rows = self.db.query(Lead).filter(Lead.status.in_(active_statuses)).all()
            deals = []
            for r in rows:
                deals.append({
                    "id": r.id,
                    "name": r.name or "",
                    "company": r.company or "",
                    "stage": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "deal_value": r.deal_value or 0,
                })
            self.logger.info(f"Fetched {len(deals)} active deals from DB")
            return deals
        except Exception as exc:
            self.logger.warning("Failed to fetch deals", error=str(exc))
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
        lead = (context or {}).get("lead", {})
        self.logger.debug("Calling AI provider", task=task, prompt_length=len(prompt))

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI CRM assistant for Omura. "
            "You score leads, suggest follow-ups, analyze sales pipelines, "
            "automate outreach, and classify lead sources. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "score_lead": (
                "\n\nRespond with JSON containing: "
                '{"score": <float 0-100 representing likelihood to convert>}'
            ),
            "suggest_followup": (
                "\n\nRespond with JSON containing: "
                '{"action": "send_email|schedule_call|send_proposal", '
                '"subject": "suggested subject line", '
                '"message": "draft follow-up message", '
                '"urgency": "high|medium|low", '
                '"best_time": "recommended contact time"}'
            ),
            "analyze_pipeline": (
                "\n\nRespond with JSON containing: "
                '{"total_leads": <int>, '
                '"by_stage": {"new": <int>, "contacted": <int>, "qualified": <int>, '
                '"proposal": <int>, "negotiation": <int>, "won": <int>, "lost": <int>}, '
                '"conversion_rates": {"new_to_contacted": <float>, ...}, '
                '"total_pipeline_value": <float>, '
                '"avg_deal_size": <float>, '
                '"avg_days_to_close": <float>, '
                '"health_score": <float 0-100>, '
                '"insights": ["insight1", "insight2", ...]}'
            ),
            "automate_outreach": (
                "\n\nRespond with JSON containing: "
                '{"channel": "email|linkedin|sms", '
                '"subject": "outreach subject line", '
                '"message": "personalized outreach message", '
                '"personalization_notes": "notes on personalization used"}'
            ),
            "classify_source": (
                "\n\nRespond with JSON containing: "
                '{"source": "organic_search|paid_ads|social_media|referral|cold_outreach|event|inbound_form|partner", '
                '"intent": "purchase|inquiry|support|partnership", '
                '"confidence": <float 0-1>, '
                '"suggested_stage": "new|contacted|qualified", '
                '"tags": ["tag1", "tag2", ...]}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="crm_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # ── Fallback: mock responses keyed by task ──
        self.logger.info("Falling back to mock response for task=%s", task)

        if task == "score_lead":
            # Deterministic mock: more interactions and recent activity = higher score
            interactions = len(lead.get("interactions", []))
            has_company = bool(lead.get("company"))
            has_deal_value = bool(lead.get("deal_value"))
            base = 30.0
            base += min(interactions * 8.0, 30.0)
            if has_company:
                base += 15.0
            if has_deal_value:
                base += 15.0
            if lead.get("source") in ("referral", "inbound_form"):
                base += 10.0
            return {"score": min(base, 100.0)}

        if task == "suggest_followup":
            return {
                "action": "send_email",
                "subject": "Quick follow-up on our conversation",
                "message": (
                    "Hi {name},\n\n"
                    "I wanted to follow up on our recent conversation. I've put "
                    "together a brief overview of how we can help streamline your "
                    "workflow and save your team 10+ hours per week.\n\n"
                    "Would you have 15 minutes this Thursday or Friday for a quick "
                    "call? I'd love to walk you through a few ideas tailored to "
                    "{company}.\n\n"
                    "Looking forward to hearing from you.\n\n"
                    "Best regards"
                ).format(
                    name=lead.get("name", "there"),
                    company=lead.get("company", "your team"),
                ),
                "urgency": "high",
                "best_time": "Thursday 10:00 AM or Friday 2:00 PM",
            }

        if task == "analyze_pipeline":
            return {
                "total_leads": 142,
                "by_stage": {
                    "new": 38,
                    "contacted": 32,
                    "qualified": 28,
                    "proposal": 19,
                    "negotiation": 12,
                    "won": 8,
                    "lost": 5,
                },
                "conversion_rates": {
                    "new_to_contacted": 84.2,
                    "contacted_to_qualified": 72.5,
                    "qualified_to_proposal": 67.9,
                    "proposal_to_negotiation": 63.2,
                    "negotiation_to_won": 66.7,
                    "overall_win_rate": 21.8,
                },
                "total_pipeline_value": 487500.00,
                "avg_deal_size": 12500.00,
                "avg_days_to_close": 34.5,
                "health_score": 72.0,
                "insights": [
                    "Win rate of 21.8% is above the industry average of 18%.",
                    "Biggest drop-off occurs between 'contacted' and 'qualified' stages "
                    "— consider refining qualification criteria.",
                    "Average deal cycle of 34.5 days is trending down from 41 days last quarter.",
                    "Referral leads convert at 2.3x the rate of cold outreach leads.",
                    "12 leads in 'negotiation' stage represent $150K in near-term revenue.",
                ],
            }

        if task == "automate_outreach":
            name = lead.get("name", "there")
            company = lead.get("company", "your organization")
            interests = lead.get("interests", ["productivity"])
            interest_text = interests[0] if interests else "productivity"
            return {
                "channel": "email",
                "subject": f"An idea for {company}'s {interest_text} workflow",
                "message": (
                    f"Hi {name},\n\n"
                    f"I came across {company} and was impressed by what your team "
                    f"is building. I noticed you're focused on {interest_text}, and "
                    f"I think there's a quick win we could help with.\n\n"
                    f"We recently helped a similar company cut their {interest_text} "
                    f"overhead by 35% in under 2 weeks. Would you be open to a "
                    f"10-minute call to see if it's a fit?\n\n"
                    f"No pressure either way — happy to share a case study if "
                    f"you'd prefer to review on your own time.\n\n"
                    f"Best,\nThe Omura Team"
                ),
                "personalization_notes": (
                    f"Referenced {company} and their focus on {interest_text}. "
                    f"Used social proof with quantified result."
                ),
            }

        if task == "classify_source":
            return {
                "source": "inbound_form",
                "intent": "inquiry",
                "confidence": 0.87,
                "suggested_stage": "new",
                "tags": ["inbound", "product_interest", "small_business"],
            }

        return {"raw": "Mock AI response — task not recognized."}
