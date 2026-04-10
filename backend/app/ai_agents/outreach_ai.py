"""
Omura Outreach AI — Autonomous Lead Generation & Personalized Outreach
=======================================================================
Full pipeline:
  1. Find leads (Apollo if key present, else web search via approved httpx)
  2. Research each lead (company website, LinkedIn, news)
  3. Verify email addresses (MX record check)
  4. Draft hyper-personalized email + DM copy using Claude
  5. Queue follow-up sequences (day 3 / 7 / 14)
  6. Log everything for auditability

All internet access goes through approved httpx calls — no silent scraping.
"""

from __future__ import annotations

import dns.resolver  # dnspython
import json
import re
import socket
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger
from backend.app.ai_agents._claude_caller import call_claude_json


_logger = OmuraLogger("outreach_ai")

# ── IronLogic AI value proposition (used in all outreach) ──
IRONLOGIC_CONTEXT = """
IronLogic AI is an AI automation agency run by Damarley.
We help businesses cut manual work, automate lead follow-up, streamline
operations, and deploy custom AI tools — typically saving 10-20 hours/week.
Services: CRM automation, email outreach sequences, AI chatbots,
workflow automation, data pipelines, custom AI integrations.
Target clients: SMBs, agencies, real estate firms, auto dealers,
financial services, e-commerce brands.
"""


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

def verify_email(email: str) -> dict:
    """Check if an email address is likely deliverable.

    Does NOT send a test email — uses MX record lookup + syntax check.
    Returns dict with 'valid' bool and 'reason'.
    """
    if not email or "@" not in email:
        return {"valid": False, "reason": "invalid_syntax"}

    local, domain = email.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        return {"valid": False, "reason": "invalid_syntax"}

    # Block obvious pattern-guessed throwaway domains
    THROWAWAY = ("mailinator", "guerrillamail", "tempmail", "sharklasers", "yopmail")
    if any(t in domain.lower() for t in THROWAWAY):
        return {"valid": False, "reason": "throwaway_domain"}

    # MX record lookup — if domain has no mail server, email will bounce
    try:
        dns.resolver.resolve(domain, "MX")
        return {"valid": True, "reason": "mx_found"}
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return {"valid": False, "reason": "no_mx_record"}
    except Exception:
        # DNS timeout or other error — assume valid to avoid false negatives
        return {"valid": True, "reason": "dns_check_skipped"}


# ---------------------------------------------------------------------------
# Hunter.io — Email Finding & Verification
# ---------------------------------------------------------------------------

def hunter_find_emails(domain: str, limit: int = 5) -> list[dict]:
    """Find email addresses for a company domain using Hunter.io.

    Returns list of dicts with email, first_name, last_name, position, confidence.
    Free tier: 25 searches/month.
    """
    api_key = settings.HUNTER_API_KEY
    if not api_key:
        return []
    try:
        resp = httpx.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": api_key, "limit": limit},
            timeout=10,
        )
        if resp.status_code != 200:
            _logger.warning(f"Hunter domain-search failed: {resp.status_code}")
            return []
        emails = resp.json().get("data", {}).get("emails", [])
        results = []
        for e in emails:
            results.append({
                "email": e.get("value", ""),
                "first_name": e.get("first_name", ""),
                "last_name": e.get("last_name", ""),
                "position": e.get("position", ""),
                "confidence": e.get("confidence", 0),
                "type": e.get("type", ""),
            })
        return results
    except Exception as exc:
        _logger.error(f"Hunter domain search error: {exc}")
        return []


def hunter_find_email(first_name: str, last_name: str, domain: str) -> dict:
    """Find a specific person's email using Hunter.io email finder.

    Returns dict with email, score, status.
    """
    api_key = settings.HUNTER_API_KEY
    if not api_key:
        return {}
    try:
        resp = httpx.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": api_key,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json().get("data", {})
        return {
            "email": data.get("email", ""),
            "score": data.get("score", 0),
            "status": data.get("status", ""),
        }
    except Exception as exc:
        _logger.error(f"Hunter email-finder error: {exc}")
        return {}


def hunter_verify_email(email: str) -> dict:
    """Verify an email address using Hunter.io (more accurate than MX check).

    Returns dict with result (deliverable/undeliverable/risky/unknown) and score.
    """
    api_key = settings.HUNTER_API_KEY
    if not api_key:
        return verify_email(email)  # fallback to MX check
    try:
        resp = httpx.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return verify_email(email)
        data = resp.json().get("data", {})
        result = data.get("result", "unknown")
        return {
            "valid": result in ("deliverable", "risky"),
            "result": result,
            "score": data.get("score", 0),
            "reason": result,
        }
    except Exception as exc:
        _logger.error(f"Hunter verify error: {exc}")
        return verify_email(email)


# ---------------------------------------------------------------------------
# Lead Research
# ---------------------------------------------------------------------------

def research_lead(name: str, company: str, email: str, website: str = "") -> dict:
    """Research a lead using their public web presence.

    Fetches company website (if provided) and asks Claude to extract
    pain points, tech stack, business model, and personalization hooks.

    Returns dict with research fields.
    """
    raw_content = ""

    # Fetch company website if we have it
    if website:
        url = website if website.startswith("http") else f"https://{website}"
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (research bot)"})
            if resp.status_code == 200:
                # Strip HTML tags for Claude context
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()
                raw_content = text[:3000]
        except Exception as exc:
            _logger.debug(f"Could not fetch {website}: {exc}")

    # Fallback: ask Claude to reason from name + company alone
    prompt = (
        f"Research this lead for a personalized outreach email.\n"
        f"Name: {name}\n"
        f"Company: {company}\n"
        f"Email domain: {email.split('@')[-1] if '@' in email else ''}\n"
        f"Website content snippet: {raw_content[:2000] if raw_content else 'Not available'}\n\n"
        f"Based on the company name, domain, and any website content, infer:\n"
        f"- What the company does\n"
        f"- Their likely pain points around automation/operations\n"
        f"- Industry sector\n"
        f"- Company size estimate\n"
        f"- One specific hook for a cold email (something unique about them)\n"
    )

    system = (
        "You are a B2B sales researcher. Extract practical intel about a prospect "
        "from limited public info. Be specific and factual — don't invent details. "
        "Always respond with valid JSON only."
    )

    task_format = (
        "\n\nRespond with JSON: "
        '{"what_they_do": "...", "pain_points": ["..."], "industry": "...", '
        '"size_estimate": "...", "personalization_hook": "...", "confidence": "high|medium|low"}'
    )

    result = call_claude_json(prompt + task_format, system, agent_name="outreach_ai")
    return result or {
        "what_they_do": company,
        "pain_points": ["manual operations", "lead follow-up"],
        "industry": "unknown",
        "size_estimate": "SMB",
        "personalization_hook": f"Your work at {company}",
        "confidence": "low",
    }


# ---------------------------------------------------------------------------
# Vertical Templates — exact proven copy per industry
# ---------------------------------------------------------------------------

VERTICAL_TEMPLATES = {
    "dental": {
        "detect": ["dental", "dentist", "implant", "orthodont", "clinic", "oral", "teeth"],
        "subjects": [
            "Quick question about {clinic}",
            "Missed implant consults at {clinic}",
            "Idea for {clinic}",
        ],
        "touch1": (
            "Hey Dr. {name},\n\n"
            "Noticed you're offering dental implants — most clinics like yours lose a significant "
            "number of consult requests due to slow or missed follow-up.\n\n"
            "I recorded a 90-sec walkthrough showing exactly where leads usually drop off and how "
            "an AI intake system can automatically book implant consults into your calendar.\n\n"
            "Want me to send it over?\n\n"
            "— Damarley"
        ),
        "touch2": (
            "Hey Dr. {name},\n\n"
            "Sent this over for you:\n\n"
            "[LOOM LINK]\n\n"
            "Shows:\n"
            "- where implant inquiries typically get lost\n"
            "- how AI handles intake instantly\n"
            "- how it books consults directly into your calendar\n\n"
            "If this is relevant, I can run a 14-day test for your clinic tied to booked consults.\n\n"
            "— Damarley"
        ),
        "touch3": (
            "Hey Dr. {name},\n\n"
            "Should I close this out or is increasing implant consult bookings something "
            "you're actively focusing on right now?\n\n"
            "— Damarley"
        ),
        "touch4": (
            "Hey Dr. {name},\n\n"
            "Not sure if improving lead follow-up is a priority right now, but I figured "
            "I'd check before closing this out.\n\n"
            "— Damarley"
        ),
        "dm": (
            "Hey Dr. {name} — most implant clinics lose consult bookings to slow follow-up. "
            "I built a system that fixes it automatically. Worth a look?"
        ),
        "linkedin": "Hi Dr. {name}, I help implant clinics recover missed consult bookings with AI follow-up. Would love to show you a quick example.",
        "loom_script": (
            "0-15s: Hey Dr. {name}, I looked at your implant page and I want to show you something quick.\n"
            "15-45s: Most clinics like yours lose consult requests because of: missed calls, delayed responses, no instant booking system.\n"
            "45-75s: I built an AI intake system that qualifies implant leads and books directly into your calendar — automatically.\n"
            "75-90s: I can run this as a 14-day pilot tied to booked consults. If it works, we continue. If not, we stop."
        ),
    },
    "solar": {
        "detect": ["solar", "photovoltaic", "renewable", "clean energy", "pv install"],
        "subjects": [
            "Quick question about {clinic}",
            "Missed solar leads at {clinic}",
            "Idea for {clinic}",
        ],
        "touch1": (
            "Hey {name},\n\n"
            "Noticed {clinic} is in the solar space — most installers I've talked to are losing "
            "qualified leads because follow-up takes too long after the initial inquiry.\n\n"
            "I recorded a 90-sec walkthrough showing exactly where leads drop off and how an AI "
            "system can automatically qualify and book consultations into your calendar.\n\n"
            "Want me to send it over?\n\n"
            "— Damarley"
        ),
        "touch2": (
            "Hey {name},\n\n"
            "Sent this over for you:\n\n"
            "[LOOM LINK]\n\n"
            "Shows:\n"
            "- where solar inquiries typically go cold\n"
            "- how AI qualifies leads instantly (are they a homeowner? roof type? bill size?)\n"
            "- how it books site visits directly into your calendar\n\n"
            "I can run a 14-day test for {clinic} tied to booked consultations.\n\n"
            "— Damarley"
        ),
        "touch3": (
            "Hey {name},\n\n"
            "Should I close this out or is converting more solar inquiries into booked "
            "consultations something you're actively working on?\n\n"
            "— Damarley"
        ),
        "touch4": (
            "Hey {name},\n\n"
            "Not sure if this is a priority right now, but wanted to check before closing out.\n\n"
            "— Damarley"
        ),
        "dm": (
            "Hey {name} — solar installers lose a ton of leads to slow follow-up. "
            "I built an AI system that qualifies and books them automatically. Worth a look?"
        ),
        "linkedin": "Hi {name}, I help solar companies stop losing qualified leads to slow follow-up. Built an AI system that books consultations automatically. Would love to connect.",
        "loom_script": (
            "0-15s: Hey {name}, I looked at {clinic} and want to show you where you're likely losing leads.\n"
            "15-45s: Most solar companies lose inquiries because: calls go unanswered, follow-up takes 24-48hrs, no automated qualification.\n"
            "45-75s: AI system qualifies leads instantly (homeowner? bill size? roof condition?) and books site visits directly into your calendar.\n"
            "75-90s: 14-day pilot tied to booked consultations. Works or we stop."
        ),
    },
    "real_estate": {
        "detect": ["real estate", "realtor", "broker", "property", "realty", "homes", "listings"],
        "subjects": [
            "Quick question about {clinic}",
            "Losing deals after hours at {clinic}?",
            "Idea for {clinic}",
        ],
        "touch1": (
            "Hey {name},\n\n"
            "You're probably losing deals after hours — buyers reach out, nobody responds fast "
            "enough, and they move on to the next agent.\n\n"
            "I recorded a 90-sec walkthrough showing how an AI follow-up system responds to "
            "every inquiry instantly and books showings directly into your calendar.\n\n"
            "Want me to send it over?\n\n"
            "— Damarley"
        ),
        "touch2": (
            "Hey {name},\n\n"
            "Sent this over for you:\n\n"
            "[LOOM LINK]\n\n"
            "Shows:\n"
            "- how leads go cold when response takes more than 5 minutes\n"
            "- how AI responds instantly, qualifies the buyer, and books the showing\n"
            "- how it works with your existing calendar\n\n"
            "I can run a 14-day test for your business tied to booked showings.\n\n"
            "— Damarley"
        ),
        "touch3": (
            "Hey {name},\n\n"
            "Should I close this out or is converting more inquiries into booked showings "
            "something you're actively focused on?\n\n"
            "— Damarley"
        ),
        "touch4": (
            "Hey {name},\n\n"
            "Not sure if this is a priority right now — figured I'd check before closing out.\n\n"
            "— Damarley"
        ),
        "dm": (
            "Hey {name} — most agents lose deals because follow-up is too slow. "
            "I built a system that responds and books showings automatically. Worth a look?"
        ),
        "linkedin": "Hi {name}, I help real estate agents stop losing after-hours leads with AI follow-up that books showings automatically. Would love to connect.",
        "loom_script": (
            "0-15s: Hey {name}, I want to show you exactly where you're losing deals after hours.\n"
            "15-45s: Buyers reach out at 9pm — no response until morning — they've already called 3 other agents.\n"
            "45-75s: AI responds in under 60 seconds, qualifies the buyer, and books the showing directly into your calendar.\n"
            "75-90s: 14-day pilot tied to booked showings. Works or we stop."
        ),
    },
    "hvac": {
        "detect": ["hvac", "heating", "cooling", "plumbing", "roofing", "air condition", "mechanical"],
        "subjects": [
            "Quick question about {clinic}",
            "Jobs going to whoever responds first",
            "Idea for {clinic}",
        ],
        "touch1": (
            "Hey {name},\n\n"
            "The job goes to whoever responds first — and most HVAC companies are still relying "
            "on voicemail and call-back queues.\n\n"
            "I recorded a 90-sec walkthrough showing how an AI system responds to every service "
            "request instantly and books the job into your calendar before your competitor even calls back.\n\n"
            "Want me to send it over?\n\n"
            "— Damarley"
        ),
        "touch2": (
            "Hey {name},\n\n"
            "Sent this over for you:\n\n"
            "[LOOM LINK]\n\n"
            "Shows:\n"
            "- how emergency requests go to the fastest responder\n"
            "- how AI captures the job before voicemail even picks up\n"
            "- how it books directly into your dispatch calendar\n\n"
            "I can run a 14-day test for {clinic} tied to booked jobs.\n\n"
            "— Damarley"
        ),
        "touch3": (
            "Hey {name},\n\n"
            "Should I close this out or is winning more jobs against faster competitors "
            "something you're working on?\n\n"
            "— Damarley"
        ),
        "touch4": (
            "Hey {name},\n\nNot sure if this is a priority right now — wanted to check before closing out.\n\n— Damarley"
        ),
        "dm": "Hey {name} — HVAC jobs go to whoever responds first. I built an AI that responds instantly and books the job before your competitors call back. Worth a look?",
        "linkedin": "Hi {name}, I help HVAC companies win more jobs by responding to service requests instantly with AI. Would love to connect.",
        "loom_script": (
            "0-15s: Hey {name}, want to show you exactly how jobs are going to your competitors.\n"
            "15-45s: Customer calls 3 companies — first one to respond gets the job. Voicemail loses every time.\n"
            "45-75s: AI answers instantly, qualifies the job, and books it into your dispatch calendar automatically.\n"
            "75-90s: 14-day pilot tied to booked jobs. Works or we stop."
        ),
    },
    "law": {
        "detect": ["law", "lawyer", "attorney", "legal", "counsel", "litigation", "firm"],
        "subjects": [
            "Quick question about {clinic}",
            "Potential clients slipping through at {clinic}?",
            "Idea for {clinic}",
        ],
        "touch1": (
            "Hey {name},\n\n"
            "How many potential clients slipped through this month because follow-up was too slow?\n\n"
            "I recorded a 90-sec walkthrough showing how an AI intake system responds to every "
            "inquiry instantly, qualifies the case, and books consultations directly into your calendar.\n\n"
            "Want me to send it over?\n\n"
            "— Damarley"
        ),
        "touch2": (
            "Hey {name},\n\n"
            "Sent this over for you:\n\n"
            "[LOOM LINK]\n\n"
            "Shows:\n"
            "- how potential clients choose the first firm that responds\n"
            "- how AI qualifies the case and books the consultation automatically\n"
            "- how it integrates with your existing calendar\n\n"
            "I can run a 14-day test for {clinic} tied to booked consultations.\n\n"
            "— Damarley"
        ),
        "touch3": (
            "Hey {name},\n\n"
            "Should I close this out or is capturing more qualified consultations "
            "something you're actively focused on?\n\n"
            "— Damarley"
        ),
        "touch4": (
            "Hey {name},\n\nNot sure if this is a priority right now — wanted to check before closing out.\n\n— Damarley"
        ),
        "dm": "Hey {name} — law firms lose clients to whoever responds first. I built AI intake that qualifies cases and books consultations automatically. Worth a look?",
        "linkedin": "Hi {name}, I help law firms stop losing qualified leads to slow intake response. AI system that books consultations automatically. Would love to connect.",
        "loom_script": (
            "0-15s: Hey {name}, want to show you how many consultations you're likely losing to slow intake.\n"
            "15-45s: Potential clients shop multiple firms — first to respond and qualify wins.\n"
            "45-75s: AI responds instantly, qualifies the case type, and books the consultation directly into your calendar.\n"
            "75-90s: 14-day pilot tied to booked consultations. Works or we stop."
        ),
    },
    "auto": {
        "detect": ["auto", "car", "vehicle", "dealer", "motors", "automotive", "sales"],
        "subjects": [
            "Quick question about {clinic}",
            "Missing car buyers at {clinic}?",
            "Idea for {clinic}",
        ],
        "touch1": (
            "Hey {name},\n\n"
            "Most dealerships and auto businesses lose buyers who inquire online but never "
            "get a fast enough response to book a test drive or appointment.\n\n"
            "I recorded a 90-sec walkthrough showing how an AI follow-up system responds "
            "instantly and books appointments directly into your calendar.\n\n"
            "Want me to send it over?\n\n"
            "— Damarley"
        ),
        "touch2": (
            "Hey {name},\n\n"
            "Sent this over for you:\n\n"
            "[LOOM LINK]\n\n"
            "Shows:\n"
            "- how online inquiries go cold within 30 minutes\n"
            "- how AI follows up instantly and qualifies the buyer\n"
            "- how it books test drives or appointments directly into your calendar\n\n"
            "I can run a 14-day test for {clinic} tied to booked appointments.\n\n"
            "— Damarley"
        ),
        "touch3": (
            "Hey {name},\n\n"
            "Should I close this out or is converting more online inquiries into "
            "booked appointments something you're working on?\n\n"
            "— Damarley"
        ),
        "touch4": (
            "Hey {name},\n\nNot sure if this is a priority — wanted to check before closing out.\n\n— Damarley"
        ),
        "dm": "Hey {name} — auto buyers go to whoever responds fastest online. I built AI that follows up instantly and books appointments automatically. Worth a look?",
        "linkedin": "Hi {name}, I help auto businesses convert more online inquiries into booked appointments with AI follow-up. Would love to connect.",
        "loom_script": (
            "0-15s: Hey {name}, want to show you exactly where you're losing online buyers.\n"
            "15-45s: Buyer submits a form — waits 2 hours — already bought from someone else.\n"
            "45-75s: AI responds within 60 seconds, qualifies the buyer, books the appointment directly into your calendar.\n"
            "75-90s: 14-day pilot tied to booked appointments. Works or we stop."
        ),
    },
}

# Default template for any vertical not specifically mapped
DEFAULT_TEMPLATE = {
    "subjects": ["Quick question about {clinic}", "Idea for {clinic}"],
    "touch1": (
        "Hey {name},\n\n"
        "Most businesses like {clinic} lose leads because follow-up is too slow.\n\n"
        "I recorded a 90-sec walkthrough showing how an AI system responds to every inquiry "
        "instantly and books appointments directly into your calendar.\n\n"
        "Want me to send it over?\n\n"
        "— Damarley"
    ),
    "touch2": (
        "Hey {name},\n\n"
        "Sent this over for you:\n\n"
        "[LOOM LINK]\n\n"
        "If this is relevant, I can run a 14-day test for {clinic} tied to booked appointments.\n\n"
        "— Damarley"
    ),
    "touch3": (
        "Hey {name},\n\n"
        "Should I close this out or is converting more inquiries into appointments "
        "something you're actively focused on?\n\n"
        "— Damarley"
    ),
    "touch4": (
        "Hey {name},\n\nNot sure if this is a priority right now — wanted to check before closing out.\n\n— Damarley"
    ),
    "dm": "Hey {name} — most businesses lose leads to slow follow-up. I built an AI system that responds instantly and books appointments automatically. Worth a look?",
    "linkedin": "Hi {name}, I help businesses stop losing leads with AI follow-up that books appointments automatically. Would love to connect.",
    "loom_script": (
        "0-15s: Hey {name}, want to show you exactly where {clinic} is losing leads.\n"
        "15-45s: Every minute you wait to follow up, the lead gets colder.\n"
        "45-75s: AI responds instantly, qualifies the lead, books the appointment into your calendar automatically.\n"
        "75-90s: 14-day pilot tied to booked appointments. Works or we stop."
    ),
}


REPLY_SCRIPTS = {
    "what_is_this": (
        "It's a simple system that helps businesses recover missed inquiries and automatically "
        "book appointments into your calendar using AI follow-up.\n\n"
        "I showed a quick example in the video I sent — want me to resend it?"
    ),
    "not_interested": (
        "No problem at all.\n\n"
        "Is it fair to say improving lead follow-up just isn't a priority right now?"
    ),
    "how_much": (
        "I usually don't price it upfront because it's a 14-day test tied to booked appointments.\n\n"
        "If it works, we continue. If not, we stop.\n\n"
        "Would you be open to testing it first?"
    ),
}

CLOSING_FRAMEWORK = (
    "CLOSING CALL FRAMEWORK (15-20 min)\n\n"
    "Step 1 — Confirm pain: 'How are inquiries handled right now?'\n"
    "Step 2 — Quantify loss: 'Roughly how many inquiries per week?'\n"
    "Step 3 — Gap expose: 'How many do you think go unbooked?'\n"
    "Step 4 — Present system: AI intake + booking automation\n"
    "Step 5 — Offer: 14-day pilot tied to booked appointments\n"
    "Step 6 — Close: 'Want to test it this week?'"
)


def detect_vertical(company: str, industry: str) -> str:
    """Detect which vertical a lead belongs to based on company name and industry."""
    text = f"{company} {industry}".lower()
    for vertical, tmpl in VERTICAL_TEMPLATES.items():
        if any(keyword in text for keyword in tmpl["detect"]):
            return vertical
    return "default"


def get_template(vertical: str) -> dict:
    return VERTICAL_TEMPLATES.get(vertical, DEFAULT_TEMPLATE)


# ---------------------------------------------------------------------------
# Personalized Copy Generation
# ---------------------------------------------------------------------------

def draft_outreach_copy(lead: dict, research: dict) -> dict:
    """Generate personalized outreach copy using vertical-specific proven templates.

    Detects the vertical from research data and fills in the exact proven templates.
    Falls back to AI generation only if no template matches.
    """
    first_name = lead.get("name", "there").split()[0]
    company = lead.get("company", "your company")
    industry = research.get("industry", "")

    vertical = detect_vertical(company, industry)
    tmpl = get_template(vertical)

    def fill(text: str) -> str:
        return text.replace("{name}", first_name).replace("{clinic}", company)

    subject = fill(tmpl["subjects"][0])
    body = fill(tmpl["touch1"])
    dm = fill(tmpl.get("dm", DEFAULT_TEMPLATE["dm"]))
    linkedin = fill(tmpl.get("linkedin", DEFAULT_TEMPLATE["linkedin"]))
    loom_script = fill(tmpl.get("loom_script", DEFAULT_TEMPLATE["loom_script"]))

    # Store all 4 touches so the scheduler can send them
    touch2 = fill(tmpl["touch2"])
    touch3 = fill(tmpl["touch3"])
    touch4 = fill(tmpl["touch4"])

    return {
        "email_subject": subject,
        "email_body": body,
        "dm_copy": dm,
        "linkedin_note": linkedin,
        "loom_script": loom_script,
        "touch2": touch2,
        "touch3": touch3,
        "touch4": touch4,
        "vertical": vertical,
    }


# ---------------------------------------------------------------------------
# Apollo Lead Search (when API key is present)
# ---------------------------------------------------------------------------

def find_leads_apollo(
    titles: list[str],
    locations: list[str],
    industries: list[str],
    per_page: int = 10,
) -> list[dict]:
    """Search Apollo.io for leads then enrich to get emails.

    Two-step: api_search (free, no credits) → bulk_match (credits, gets emails).
    Returns list of lead dicts with name, email, company, title.
    Falls back to empty list if no API key.
    """
    api_key = settings.APOLLO_API_KEY
    if not api_key:
        _logger.warning("Apollo API key not set — skipping Apollo search")
        return []

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
        "accept": "application/json",
    }

    # Step 1: Search — free, no credits, no emails returned
    payload: dict = {
        "per_page": min(per_page, 100),
        "page": 1,
    }
    if titles:
        payload["person_titles"] = titles
    if locations:
        payload["person_locations"] = locations
    if industries:
        payload["q_keywords"] = " ".join(industries)

    try:
        resp = httpx.post(
            "https://api.apollo.io/api/v1/mixed_people/api_search",
            json=payload,
            headers=headers,
            timeout=20,
        )
        if resp.status_code != 200:
            _logger.warning(f"Apollo search failed: {resp.status_code} {resp.text[:300]}")
            return []

        people = resp.json().get("people", [])
        _logger.info(f"Apollo search found {len(people)} candidates")

        # Filter to only people Apollo has emails for
        with_email = [p for p in people if p.get("has_email")]
        if not with_email:
            return []

        # Step 2: Enrich by ID to get actual emails (uses credits)
        ids = [p["id"] for p in with_email[:per_page]]
        enrich_payload = {
            "api_key": api_key,
            "details": [{"id": pid} for pid in ids],
            "reveal_personal_emails": False,
        }
        enrich_resp = httpx.post(
            "https://api.apollo.io/api/v1/people/bulk_match",
            json=enrich_payload,
            headers=headers,
            timeout=30,
        )
        if enrich_resp.status_code != 200:
            _logger.warning(f"Apollo enrichment failed: {enrich_resp.status_code}")
            return []

        matches = enrich_resp.json().get("matches", [])
        leads = []
        for m in matches:
            email = m.get("email") or ""
            if not email:
                continue
            org = m.get("organization") or {}
            leads.append({
                "name": f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(),
                "email": email,
                "company": org.get("name", ""),
                "title": m.get("title", ""),
                "linkedin_url": m.get("linkedin_url", ""),
                "website": org.get("website_url", "") or org.get("primary_domain", ""),
                "source": "apollo",
            })

        _logger.info(f"Apollo enriched {len(leads)} leads with emails")
        return leads

    except Exception as exc:
        _logger.error(f"Apollo pipeline error: {exc}")
        return []


# ---------------------------------------------------------------------------
# Full Autonomous Pipeline
# ---------------------------------------------------------------------------

class OutreachAI:
    """Full autonomous lead generation + personalized outreach pipeline."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.logger = OmuraLogger("outreach_ai")

    def find_leads_by_domains(self, domains: list[str], limit_per_domain: int = 3) -> list[dict]:
        """Find decision-maker emails from a list of company domains using Hunter.io.

        Args:
            domains: List of company domains e.g. ["rossautoja.com", "scotiabank.com"]
            limit_per_domain: Max emails to pull per domain

        Returns:
            List of lead dicts ready for the pipeline
        """
        leads = []
        for domain in domains:
            emails = hunter_find_emails(domain, limit=limit_per_domain)
            # Prefer decision makers: CEO, founder, director, owner, manager
            PRIORITY_TITLES = ("ceo", "founder", "owner", "director", "president", "head", "manager", "vp")
            emails.sort(key=lambda e: (
                0 if any(t in (e.get("position") or "").lower() for t in PRIORITY_TITLES) else 1,
                -(e.get("confidence") or 0),
            ))
            # Skip generic/info emails — target named decision makers only
            SKIP_PREFIXES = ("info", "contact", "hello", "support", "admin", "sales", "enquiries", "enquiry", "general")
            named = [e for e in emails if e.get("email") and not any(
                e["email"].split("@")[0].lower().startswith(p) for p in SKIP_PREFIXES
            )]
            targets = named if named else []  # don't fall back to info@ emails
            for e in targets[:1]:
                if not e.get("email"):
                    continue
                name = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()
                leads.append({
                    "name": name or domain.split(".")[0].title(),
                    "email": e["email"],
                    "company": domain.split(".")[0].title(),
                    "title": e.get("position", ""),
                    "website": domain,
                    "source": "hunter",
                })
        self.logger.info(f"Hunter found {len(leads)} leads from {len(domains)} domains")
        return leads

    def run_pipeline(
        self,
        titles: list[str] = None,
        locations: list[str] = None,
        industries: list[str] = None,
        manual_leads: list[dict] = None,
        domains: list[str] = None,
        daily_limit: int = 20,
    ) -> dict:
        """Full pipeline: find → verify → research → draft → queue.

        Args:
            titles: Job titles to target (e.g. ["CEO", "Founder", "Director"])
            locations: Locations (e.g. ["Jamaica", "Caribbean"])
            industries: Industries (e.g. ["automotive", "real estate"])
            manual_leads: Manually provided leads (bypass search step)
            daily_limit: Max emails to queue today

        Returns:
            Summary dict with counts and results
        """
        from backend.app.database.models import Lead, LeadStatus
        from backend.app.database import crud

        titles = titles or ["CEO", "Founder", "Owner", "Director", "Manager"]
        locations = locations or ["Jamaica"]
        industries = industries or []

        self.logger.info(f"Starting outreach pipeline — limit={daily_limit}")

        # Step 1: Get leads — priority: manual > domains (Hunter) > Apollo
        raw_leads = manual_leads or []
        if not raw_leads and domains:
            raw_leads = self.find_leads_by_domains(domains, limit_per_domain=3)
        if not raw_leads:
            raw_leads = find_leads_apollo(titles, locations, industries, per_page=daily_limit)

        if not raw_leads:
            self.logger.warning("No leads found — Apollo key may be missing. Provide manual_leads.")
            return {"status": "no_leads", "processed": 0, "queued": 0}

        results = []
        queued = 0
        skipped_invalid = 0
        skipped_duplicate = 0

        for lead_data in raw_leads[:daily_limit]:
            email = lead_data.get("email", "")
            name = lead_data.get("name", "Unknown")
            company = lead_data.get("company", "")

            # Step 2: Verify email — use Hunter if available, else MX check
            verification = hunter_verify_email(email)
            if not verification["valid"]:
                self.logger.debug(f"Skipping {email}: {verification['reason']}")
                skipped_invalid += 1
                continue

            # Step 3: Skip duplicates
            existing = self.db.query(Lead).filter(Lead.email == email).first()
            if existing:
                skipped_duplicate += 1
                continue

            # Step 4: Research the lead
            research = research_lead(
                name=name,
                company=company,
                email=email,
                website=lead_data.get("website", ""),
            )

            # Step 5: Draft personalized copy
            copy = draft_outreach_copy(
                lead={**lead_data, "name": name, "company": company},
                research=research,
            )

            # Step 6: Create Lead record
            lead = Lead(
                name=name[:255],
                email=email[:255],
                company=company[:255],
                source=lead_data.get("source", "outreach_pipeline"),
                status=LeadStatus.NEW,
                notes=(
                    f"Research: {research.get('what_they_do', '')}. "
                    f"Hook: {research.get('personalization_hook', '')}. "
                    f"Industry: {research.get('industry', '')}."
                ),
            )
            self.db.add(lead)
            self.db.flush()  # get ID

            # Step 7: Store all copy, touches, reply scripts, and closing framework in notes
            lead.notes = (
                f"[OUTREACH COPY]\n"
                f"Subject: {copy.get('email_subject', '')}\n"
                f"Body: {copy.get('email_body', '')}\n\n"
                f"DM: {copy.get('dm_copy', '')}\n"
                f"LinkedIn: {copy.get('linkedin_note', '')}\n\n"
                f"[TOUCH 2]\n{copy.get('touch2', '')}\n\n"
                f"[TOUCH 3]\n{copy.get('touch3', '')}\n\n"
                f"[TOUCH 4]\n{copy.get('touch4', '')}\n\n"
                f"[LOOM SCRIPT]\n{copy.get('loom_script', '')}\n\n"
                f"[REPLY SCRIPTS]\n"
                f"What is this: {REPLY_SCRIPTS['what_is_this']}\n\n"
                f"Not interested: {REPLY_SCRIPTS['not_interested']}\n\n"
                f"How much: {REPLY_SCRIPTS['how_much']}\n\n"
                f"[CLOSING FRAMEWORK]\n{CLOSING_FRAMEWORK}\n\n"
                f"[RESEARCH]\n"
                f"Does: {research.get('what_they_do', '')}\n"
                f"Pain: {', '.join(research.get('pain_points', []))}\n"
                f"Hook: {research.get('personalization_hook', '')}\n"
                f"Vertical: {copy.get('vertical', 'default')}"
            )

            results.append({
                "name": name,
                "email": email,
                "company": company,
                "email_subject": copy.get("email_subject"),
                "research_confidence": research.get("confidence"),
            })
            queued += 1

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            self.logger.error(f"Pipeline DB commit failed: {exc}")
            return {"status": "error", "error": str(exc)}

        # Step 8: Queue follow-up sequences
        from backend.app.scheduler import schedule_lead_followup_sequence
        for r in results:
            # Find the lead we just created
            lead_rec = self.db.query(Lead).filter(Lead.email == r["email"]).first()
            if lead_rec:
                schedule_lead_followup_sequence(lead_rec.id)

        crud.log_agent_action(self.db, "outreach_ai", "run_pipeline", {
            "titles": titles, "locations": locations, "limit": daily_limit,
        }, {
            "queued": queued,
            "skipped_invalid": skipped_invalid,
            "skipped_duplicate": skipped_duplicate,
        }, "success")

        self.logger.info(f"Pipeline complete — queued={queued}, invalid={skipped_invalid}, dupes={skipped_duplicate}")

        return {
            "status": "success",
            "queued": queued,
            "skipped_invalid_email": skipped_invalid,
            "skipped_duplicate": skipped_duplicate,
            "leads": results,
        }

    def send_initial_outreach(self, lead_id: int) -> dict:
        """Send the first outreach email to a lead immediately (day 0).

        Uses the drafted copy stored in the lead's notes.
        """
        from backend.app.database.models import Lead, LeadStatus
        from backend.app.email_utils import send_via_sendgrid as _send_via_sendgrid

        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"success": False, "error": "Lead not found"}

        # Parse drafted copy from notes
        subject = None
        body = None
        if lead.notes and "[OUTREACH COPY]" in lead.notes:
            lines = lead.notes.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("Subject: "):
                    subject = line[9:].strip()
                if line.startswith("Body: "):
                    body = "\n".join(lines[i:]).replace("Body: ", "", 1).split("\n\nDM:")[0].strip()
                    break

        if not subject or not body:
            # Fallback: generate fresh copy
            research = research_lead(lead.name or "", lead.company or "", lead.email or "")
            copy = draft_outreach_copy(
                {"name": lead.name, "company": lead.company, "email": lead.email},
                research,
            )
            subject = copy.get("email_subject", f"Quick idea for {lead.company}")
            body = copy.get("email_body", "")

        try:
            result = _send_via_sendgrid(to=lead.email, subject=subject, body=body)
            lead.status = LeadStatus.CONTACTED
            lead.last_contact = datetime.utcnow()
            self.db.commit()
            self.logger.info(f"Initial outreach sent to {lead.email}")
            return {"success": True, "to": lead.email, "subject": subject}
        except Exception as exc:
            self.logger.error(f"Send failed for {lead.email}: {exc}")
            return {"success": False, "error": str(exc)}
