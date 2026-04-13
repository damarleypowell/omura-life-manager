"""
Scheduled job functions — kept separate to avoid circular imports.
"""
from __future__ import annotations
from datetime import datetime


def send_followup_email(lead_id: int, day: int):
    """Send a scheduled follow-up email for a lead on day 2, 4, or 7."""
    from backend.app.database.session import SessionLocal
    from backend.app.database import models, crud
    from backend.app.email_utils import send_via_sendgrid

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            return
        if lead.status not in (models.LeadStatus.NEW, models.LeadStatus.CONTACTED):
            return
        if not lead.email:
            return

        # Use the exact proven templates stored in the lead notes
        notes = lead.notes or ""
        touch_map = {3: "TOUCH 2", 7: "TOUCH 3", 14: "TOUCH 4"}
        touch_header = touch_map.get(day, "TOUCH 2")

        def _extract_section(text: str, header: str) -> str:
            start = text.find(f"[{header}]")
            if start == -1:
                return ""
            after = text.find("\n", start) + 1
            next_bracket = text.find("\n[", after)
            return (text[after:next_bracket] if next_bracket != -1 else text[after:]).strip()

        body = _extract_section(notes, touch_header)
        if not body:
            # Fallback if template not found
            body = f"Hi {lead.name.split()[0]},\n\nJust following up on my last message.\n\nWorth a quick chat?\n\n— Damarley"

        subject_line = _extract_section(notes, "OUTREACH COPY")
        # Extract subject from the copy block
        subject = ""
        for line in subject_line.split("\n"):
            if line.startswith("Subject:"):
                subject = line.replace("Subject:", "").strip()
                break
        if not subject:
            subject = f"Re: {lead.company or lead.name}"

        result = send_via_sendgrid(to=lead.email, subject=subject, body=body)
        lead.status = models.LeadStatus.CONTACTED
        lead.last_contact = datetime.utcnow()
        db.commit()

        crud.log_agent_action(db, "automation", f"followup_day{day}",
            input_data={"lead_id": lead_id, "email": lead.email},
            output_data=result, status="success")

    except Exception as exc:
        from backend.app.database import crud
        crud.log_agent_action(db, "automation", f"followup_day{day}",
            input_data={"lead_id": lead_id}, status="error", error_message=str(exc))
    finally:
        db.close()


def scheduled_inbox_triage():
    """Run every 30 min: sync new emails, triage, auto-classify leads."""
    from backend.app.database.session import SessionLocal
    from backend.app.database import models, crud
    from backend.app.ai_agents.inbox_ai import InboxAI
    import httpx as _httpx
    from backend.app.config import settings

    db = SessionLocal()
    try:
        # Sync new emails
        from backend.app.google_utils import get_google_access_token, extract_email_body
        access_token = get_google_access_token()
        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
            list_resp = _httpx.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"maxResults": 10, "labelIds": "INBOX", "q": "is:unread"},
            )
            if list_resp.status_code == 200:
                import base64 as _base64
                from datetime import datetime as _dt
                message_ids = [m["id"] for m in list_resp.json().get("messages", [])]
                new_saved = 0
                for msg_id in message_ids[:10]:
                    existing = db.query(models.Communication).filter(
                        models.Communication.external_id == msg_id
                    ).first()
                    if existing:
                        continue
                    msg_resp = _httpx.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                        headers=headers, params={"format": "full"},
                    )
                    if msg_resp.status_code != 200:
                        continue
                    msg = msg_resp.json()
                    headers_list = msg.get("payload", {}).get("headers", [])
                    header_map = {h["name"].lower(): h["value"] for h in headers_list}
                    subject = header_map.get("subject", "(no subject)")
                    sender = header_map.get("from", "unknown")
                    recipient = header_map.get("to", "")
                    date_str = header_map.get("date", "")
                    payload = msg.get("payload", {})
                    body = extract_email_body(payload)
                    labels = msg.get("labelIds", [])
                    try:
                        received_at = _dt.strptime(date_str[:25].strip(), "%a, %d %b %Y %H:%M:%S") if date_str else _dt.utcnow()
                    except Exception:
                        received_at = _dt.utcnow()
                    comm = models.Communication(
                        platform="gmail", external_id=msg_id,
                        sender=sender[:255], recipient=recipient[:255],
                        subject=subject[:500], body=body[:10000],
                        is_read=False, labels=labels, received_at=received_at,
                    )
                    db.add(comm)
                    new_saved += 1
                if new_saved:
                    db.commit()

        inbox = InboxAI(db)
        result = inbox.process_inbox()

        triaged = result.get("triaged", [])
        _auto_classify_leads(db, triaged)
        _detect_lead_replies(db, triaged)

        crud.log_agent_action(db, "scheduler", "inbox_triage", {}, {
            "processed": result.get("total_processed", 0),
            "urgent": len(result.get("urgent", [])),
        }, "success")
    except Exception as exc:
        crud.log_agent_action(db, "scheduler", "inbox_triage", {}, None, "error", str(exc))
    finally:
        db.close()


def _auto_classify_leads(db, triaged_messages: list):
    """Auto-create Lead records from emails that look like business opportunities."""
    from backend.app.database import models, crud
    from backend.app.ai_agents.crm_ai import CrmAI
    from backend.app.scheduler import schedule_lead_followup_sequence
    import re as _re

    crm = CrmAI(db)
    BUSINESS_KEYWORDS = (
        "partnership", "collaborate", "proposal", "invest", "funding",
        "client", "hire", "contract", "opportunity", "inquiry", "interested",
        "work together", "business", "project", "quote", "pricing",
    )
    SKIP_DOMAINS = ("noreply", "no-reply", "notifications", "newsletter", "mailer", "donotreply")

    for msg in triaged_messages:
        sender = msg.get("sender", "")
        subject = msg.get("subject", "").lower()
        body = msg.get("body", "").lower()
        urgency = msg.get("urgency", "low")

        if any(skip in sender.lower() for skip in SKIP_DOMAINS):
            continue
        has_keyword = any(kw in subject or kw in body[:500] for kw in BUSINESS_KEYWORDS)
        if urgency not in ("critical", "high", "medium") and not has_keyword:
            continue

        email_match = _re.search(r'<([^>]+)>', sender)
        email_addr = email_match.group(1) if email_match else sender.split()[0] if sender else ""
        if not email_addr or "@" not in email_addr:
            continue

        existing_lead = db.query(models.Lead).filter(models.Lead.email == email_addr).first()
        if existing_lead:
            continue

        classification = crm.classify_lead_source({
            "sender": sender, "channel": "email",
            "subject": msg.get("subject", ""), "body": msg.get("body", "")[:500],
            "metadata": {},
        })

        if classification.get("intent") not in ("purchase", "inquiry", "partnership"):
            continue

        name_part = sender.split("<")[0].strip().strip('"') or email_addr.split("@")[0]
        lead = models.Lead(
            name=name_part[:255], email=email_addr[:255],
            source=classification.get("source", "inbound_email"),
            status=models.LeadStatus.NEW,
            notes=f"Auto-classified from email. Subject: {msg.get('subject', '')}. Intent: {classification.get('intent')}.",
        )
        db.add(lead)
        db.flush()
        schedule_lead_followup_sequence(lead.id)

    try:
        db.commit()
    except Exception:
        db.rollback()


def _detect_lead_replies(db, triaged_messages: list):
    """If a triaged email is from a known lead, mark QUALIFIED, cancel follow-ups, send Loom."""
    import re as _re
    from backend.app.database import models, crud
    from backend.app.scheduler import scheduler

    for msg in triaged_messages:
        sender = msg.get("sender", "")
        email_match = _re.search(r'<([^>]+)>', sender)
        email_addr = email_match.group(1) if email_match else sender.split()[0] if sender else ""
        if not email_addr or "@" not in email_addr:
            continue

        lead = db.query(models.Lead).filter(models.Lead.email == email_addr).first()
        if not lead:
            continue
        # Only trigger once — skip leads already past CONTACTED
        if lead.status in (models.LeadStatus.QUALIFIED, models.LeadStatus.PROPOSAL,
                           models.LeadStatus.WON, models.LeadStatus.LOST):
            continue

        # Mark as qualified (replied/interested)
        lead.status = models.LeadStatus.QUALIFIED
        lead.last_contact = datetime.utcnow()

        # Cancel pending generic follow-ups — they replied, no more cold sequence
        for day in (3, 7, 14):
            job_id = f"followup_lead{lead.id}_day{day}"
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass

        # Send personalized Loom email immediately
        try:
            _send_loom_email(lead)
            crud.log_agent_action(db, "automation", "loom_triggered",
                input_data={"lead_id": lead.id, "email": lead.email},
                status="success")
        except Exception as exc:
            crud.log_agent_action(db, "automation", "loom_triggered",
                input_data={"lead_id": lead.id},
                status="error", error_message=str(exc))

    try:
        db.commit()
    except Exception:
        db.rollback()


def _send_loom_email(lead) -> dict:
    """Send the personalized Loom video email to a lead who has shown interest (replied)."""
    from backend.app.email_utils import send_via_sendgrid

    notes = lead.notes or ""

    def _extract_section(text: str, header: str) -> str:
        start = text.find(f"[{header}]")
        if start == -1:
            return ""
        after = text.find("\n", start) + 1
        next_bracket = text.find("\n[", after)
        return (text[after:next_bracket] if next_bracket != -1 else text[after:]).strip()

    loom_block = _extract_section(notes, "LOOM EMAIL")

    # Parse subject and body from the loom block
    subject = ""
    body_lines = []
    in_body = False
    for line in loom_block.split("\n"):
        if line.startswith("Subject:") and not subject:
            subject = line.replace("Subject:", "").strip()
        elif line.startswith("Body:"):
            in_body = True
            rest = line.replace("Body:", "").strip()
            if rest:
                body_lines.append(rest)
        elif in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    if not subject:
        subject = f"Quick Loom I recorded for {lead.company or lead.name}"
    if not body:
        # Fallback generic loom email
        first = (lead.name or "there").split()[0]
        company = lead.company or "your business"
        body = (
            f"Hey {first},\n\n"
            f"Thanks for getting back — I put together a short Loom specifically "
            f"for {company} showing exactly where leads are slipping through.\n\n"
            f"[LOOM LINK]\n\n"
            f"Happy to walk through it on a quick 15-min call if it's relevant.\n\n"
            f"— Damarley"
        )

    return send_via_sendgrid(to=lead.email, subject=subject, body=body)


def scheduled_daily_inbox_categorize():
    """Run once daily at 6am: categorize ALL uncategorized inbox messages.

    Assigns each communication an ai_category in extra_data:
      spam        — newsletters, no-reply, marketing blasts
      important   — direct message that needs a response
      outreach_reply — someone replied to IronLogic cold outreach
      newsletter  — subscription updates / digests
      follow_up   — needs a reply or follow-up action
      general     — everything else
    """
    from backend.app.database.session import SessionLocal
    from backend.app.database import models, crud
    from backend.app.ai_agents._claude_caller import call_claude_json
    import re as _re

    SPAM_SIGNALS = (
        "unsubscribe", "newsletter", "no-reply", "noreply",
        "notifications@", "mailer-daemon", "donotreply",
        "marketing", "promotions", "offer", "deal", "sale",
    )
    OUTREACH_SIGNALS = (
        "ironlogic", "ai automation", "damarley",
        "quick question", "quick idea", "loom",
    )

    db = SessionLocal()
    try:
        # Only process emails not yet categorized
        messages = (
            db.query(models.Communication)
            .filter(models.Communication.platform == "gmail")
            .order_by(models.Communication.received_at.desc())
            .limit(200)
            .all()
        )

        categorized = 0
        for msg in messages:
            extra = msg.extra_data or {}
            if extra.get("ai_category"):
                continue  # already done

            sender = (msg.sender or "").lower()
            subject = (msg.subject or "").lower()
            body_snippet = (msg.body or "")[:300].lower()

            # Rule-based fast path — no Claude needed
            if any(s in sender or s in subject or s in body_snippet for s in SPAM_SIGNALS):
                category = "spam"
            elif any(s in sender or s in subject or s in body_snippet for s in OUTREACH_SIGNALS):
                category = "outreach_reply"
            else:
                # Ask Claude to classify
                result = call_claude_json(
                    f"Classify this email into ONE category.\n"
                    f"From: {msg.sender}\nSubject: {msg.subject}\nSnippet: {(msg.body or '')[:300]}\n\n"
                    f'Categories: spam, important, newsletter, outreach_reply, follow_up, general\n'
                    f'Respond with {{"category": "..."}}',
                    "You are an email classifier. Return only valid JSON.",
                    agent_name="inbox_ai",
                )
                category = (result or {}).get("category", "general")
                if category not in ("spam", "important", "newsletter", "outreach_reply", "follow_up", "general"):
                    category = "general"

            msg.extra_data = {**extra, "ai_category": category}
            categorized += 1

        db.commit()
        crud.log_agent_action(db, "scheduler", "inbox_categorize", {}, {"categorized": categorized}, "success")

    except Exception as exc:
        crud.log_agent_action(db, "scheduler", "inbox_categorize", {}, None, "error", str(exc))
    finally:
        db.close()


def scheduled_daily_briefing():
    from backend.app.database.session import SessionLocal
    from backend.app.database import models, crud
    from backend.app.ai_agents.project_ai import ProjectAI
    from backend.app.ai_agents.crm_ai import CrmAI

    db = SessionLocal()
    try:
        project = ProjectAI(db)
        agenda = project.generate_daily_agenda()
        crud.log_agent_action(db, "scheduler", "daily_briefing", {}, {"tasks": len(agenda.get("priority_tasks", []))}, "success")
        crm = CrmAI(db)
        leads = crm._fetch_all_leads()
        scored = 0
        for lead_dict in leads[:20]:
            score = crm.score_lead(lead_dict)
            db.query(models.Lead).filter(models.Lead.id == lead_dict["id"]).update({"score": score})
            scored += 1
        db.commit()
        crud.log_agent_action(db, "scheduler", "lead_scoring", {}, {"scored": scored}, "success")
    except Exception as exc:
        crud.log_agent_action(db, "scheduler", "daily_briefing", {}, None, "error", str(exc))
    finally:
        db.close()


def scheduled_weekly_pipeline():
    from backend.app.database.session import SessionLocal
    from backend.app.database import crud
    from backend.app.ai_agents.crm_ai import CrmAI

    db = SessionLocal()
    try:
        crm = CrmAI(db)
        analysis = crm.analyze_pipeline()
        crud.log_agent_action(db, "scheduler", "pipeline_analysis", {}, {
            "total_leads": analysis.get("total_leads", 0),
            "health_score": analysis.get("health_score", 0),
        }, "success")
    except Exception as exc:
        crud.log_agent_action(db, "scheduler", "pipeline_analysis", {}, None, "error", str(exc))
    finally:
        db.close()


def scheduled_daily_outreach():
    """Run every day at 9am UTC: scrape new leads, draft copy, send Touch 1, queue sequences."""
    from backend.app.database.session import SessionLocal
    from backend.app.database import crud
    from backend.app.ai_agents.outreach_ai import OutreachAI

    VERTICALS = [
        {"titles": ["Practice Owner", "Dentist", "Dental Director"], "industries": ["dental"], "locations": ["New York", "Los Angeles", "Miami", "Dallas", "Houston", "Chicago"], "daily_limit": 15},
        {"titles": ["Owner", "Principal", "Broker"], "industries": ["real estate"], "locations": ["New York", "Los Angeles", "Miami", "Dallas", "Houston"], "daily_limit": 10},
        {"titles": ["Owner", "Managing Partner", "Attorney"], "industries": ["law"], "locations": ["New York", "Los Angeles", "Miami", "Dallas"], "daily_limit": 10},
        {"titles": ["Owner", "CEO", "Founder"], "industries": ["solar"], "locations": ["Los Angeles", "Miami", "Dallas", "Phoenix"], "daily_limit": 10},
        {"titles": ["Owner", "Operations Manager"], "industries": ["hvac", "roofing", "plumbing"], "locations": ["Dallas", "Houston", "Chicago", "Atlanta"], "daily_limit": 10},
    ]

    db = SessionLocal()
    total_queued = 0
    total_sent = 0
    try:
        agent = OutreachAI(db)
        for v in VERTICALS:
            result = agent.run_pipeline(
                titles=v["titles"],
                locations=v["locations"],
                industries=v["industries"],
                daily_limit=v["daily_limit"],
            )
            queued = result.get("queued", 0)
            total_queued += queued

            # Send Touch 1 to all newly queued leads
            from backend.app.database.models import Lead, LeadStatus
            new_leads = (
                db.query(Lead)
                .filter(Lead.status == LeadStatus.NEW, Lead.email.isnot(None))
                .order_by(Lead.created_at.desc())
                .limit(queued or 5)
                .all()
            )
            for lead in new_leads:
                try:
                    agent.send_initial_outreach(lead.id)
                    total_sent += 1
                except Exception:
                    pass

        crud.log_agent_action(db, "scheduler", "daily_outreach", {}, {
            "total_queued": total_queued, "total_sent": total_sent,
        }, "success")
    except Exception as exc:
        crud.log_agent_action(db, "scheduler", "daily_outreach", {}, None, "error", str(exc))
    finally:
        db.close()


def scheduled_sheets_sync():
    """Run every day at 7:30am UTC: export full lead pipeline to Google Sheets."""
    from backend.app.database.session import SessionLocal
    from backend.app.database import crud
    from backend.app.google_utils import get_google_access_token
    from backend.app.google_sheets import export_pipeline_to_sheets

    access_token = get_google_access_token()
    if not access_token:
        return  # Google not connected yet — skip silently

    db = SessionLocal()
    try:
        result = export_pipeline_to_sheets(db, access_token)
        crud.log_agent_action(db, "scheduler", "sheets_sync", {},
            {"leads_exported": result.get("leads_exported", 0),
             "sheet_url": result.get("sheet_url", "")}, "success")
    except Exception as exc:
        try:
            crud.log_agent_action(db, "scheduler", "sheets_sync", {}, None, "error", str(exc))
        except Exception:
            pass
    finally:
        db.close()
