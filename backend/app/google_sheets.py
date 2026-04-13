"""
Google Sheets integration for Omura.

Two use cases:
  1. Import leads from a Google Sheet (populated from LinkedIn/Apollo exports)
  2. Export pipeline to a Google Sheet for easy human review

Uses the same OAuth token as Gmail — no extra auth needed once Sheets
scope is added. Re-authorize at /auth/google to pick up the new scope.
"""
from __future__ import annotations

import httpx
from datetime import datetime
from typing import Any, Optional

from backend.app.utils.logging import OmuraLogger

_logger = OmuraLogger("google_sheets")

_SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
_DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"

# Column layout for the pipeline export sheet
PIPELINE_HEADERS = [
    "Name", "Email", "Company", "Title", "Status", "Score",
    "Source", "Last Contact", "Created At", "Industry / Notes",
]

# Column layout expected for lead import sheets
# (flexible — we detect columns by header name, case-insensitive)
IMPORT_COLUMN_ALIASES = {
    "name":        ["name", "full name", "contact name", "first name"],
    "email":       ["email", "email address", "e-mail", "work email"],
    "company":     ["company", "organization", "company name", "business"],
    "title":       ["title", "job title", "position", "role"],
    "industry":    ["industry", "vertical", "sector", "niche"],
    "website":     ["website", "url", "company url", "web"],
    "linkedin_url":["linkedin", "linkedin url", "linkedin profile"],
    "notes":       ["notes", "note", "comment", "additional info"],
}


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


# ──────────────────────────────────────────────
# Sheet management
# ──────────────────────────────────────────────

def get_or_create_pipeline_sheet(access_token: str) -> str:
    """Return the spreadsheet ID of the Omura pipeline sheet.

    Searches Drive for an existing 'Omura Lead Pipeline' file.
    Creates a new one if not found.
    """
    # Search for existing sheet
    resp = httpx.get(
        _DRIVE_BASE,
        headers=_headers(access_token),
        params={
            "q": "name='Omura Lead Pipeline' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            "fields": "files(id,name)",
        },
        timeout=15,
    )
    if resp.status_code == 200:
        files = resp.json().get("files", [])
        if files:
            sheet_id = files[0]["id"]
            _logger.info(f"Found existing pipeline sheet: {sheet_id}")
            return sheet_id

    # Create new sheet
    create_resp = httpx.post(
        _SHEETS_BASE,
        headers=_headers(access_token),
        json={
            "properties": {"title": "Omura Lead Pipeline"},
            "sheets": [{"properties": {"title": "Pipeline"}}],
        },
        timeout=15,
    )
    if create_resp.status_code not in (200, 201):
        raise Exception(f"Failed to create sheet: {create_resp.status_code} {create_resp.text[:200]}")

    sheet_id = create_resp.json()["spreadsheetId"]
    _logger.info(f"Created new pipeline sheet: {sheet_id}")

    # Write headers
    _write_range(access_token, sheet_id, "Pipeline!A1", [PIPELINE_HEADERS])
    return sheet_id


def _write_range(access_token: str, sheet_id: str, range_name: str, values: list[list]) -> None:
    """Write values to a sheet range (overwrites)."""
    resp = httpx.put(
        f"{_SHEETS_BASE}/{sheet_id}/values/{range_name}",
        headers=_headers(access_token),
        params={"valueInputOption": "RAW"},
        json={"range": range_name, "majorDimension": "ROWS", "values": values},
        timeout=20,
    )
    if resp.status_code not in (200, 201):
        raise Exception(f"Sheets write error {resp.status_code}: {resp.text[:200]}")


def _append_range(access_token: str, sheet_id: str, range_name: str, values: list[list]) -> None:
    """Append rows to a sheet."""
    resp = httpx.post(
        f"{_SHEETS_BASE}/{sheet_id}/values/{range_name}:append",
        headers=_headers(access_token),
        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
        json={"range": range_name, "majorDimension": "ROWS", "values": values},
        timeout=20,
    )
    if resp.status_code not in (200, 201):
        raise Exception(f"Sheets append error {resp.status_code}: {resp.text[:200]}")


def _read_range(access_token: str, sheet_id: str, range_name: str) -> list[list]:
    """Read values from a sheet range."""
    resp = httpx.get(
        f"{_SHEETS_BASE}/{sheet_id}/values/{range_name}",
        headers=_headers(access_token),
        timeout=15,
    )
    if resp.status_code != 200:
        raise Exception(f"Sheets read error {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("values", [])


# ──────────────────────────────────────────────
# Pipeline export
# ──────────────────────────────────────────────

def export_pipeline_to_sheets(db, access_token: str) -> dict:
    """Export all active leads to the Omura pipeline Google Sheet.

    Clears existing data and rewrites from the DB.
    Returns sheet URL.
    """
    from backend.app.database.models import Lead

    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(1000).all()

    sheet_id = get_or_create_pipeline_sheet(access_token)

    rows = [PIPELINE_HEADERS]
    for lead in leads:
        # Pull industry from notes if available
        notes_snippet = ""
        if lead.notes:
            for line in lead.notes.split("\n"):
                if line.startswith("Vertical:"):
                    notes_snippet = line.replace("Vertical:", "").strip()
                    break
            if not notes_snippet and "[RESEARCH]" in lead.notes:
                idx = lead.notes.find("[RESEARCH]")
                notes_snippet = lead.notes[idx:idx+100].replace("[RESEARCH]", "").strip()[:80]

        rows.append([
            lead.name or "",
            lead.email or "",
            lead.company or "",
            lead.title or "",
            lead.status.value if lead.status else "new",
            str(round(lead.score or 0, 1)),
            lead.source or "",
            lead.last_contact.strftime("%Y-%m-%d") if lead.last_contact else "",
            lead.created_at.strftime("%Y-%m-%d") if lead.created_at else "",
            notes_snippet,
        ])

    # Overwrite from row 1
    _write_range(access_token, sheet_id, "Pipeline!A1", rows)

    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    _logger.info(f"Exported {len(leads)} leads to Sheets: {sheet_url}")
    return {
        "success": True,
        "sheet_id": sheet_id,
        "sheet_url": sheet_url,
        "leads_exported": len(leads),
    }


# ──────────────────────────────────────────────
# Lead import
# ──────────────────────────────────────────────

def import_leads_from_sheet(db, access_token: str, sheet_id: str, sheet_tab: str = "Sheet1") -> dict:
    """Read leads from a Google Sheet and add them to the pipeline.

    The sheet must have a header row. Column names are matched
    case-insensitively against IMPORT_COLUMN_ALIASES.

    Returns counts of imported, skipped (duplicates), and invalid rows.
    """
    from backend.app.database.models import Lead, LeadStatus
    from backend.app.database import crud
    from backend.app.scheduler import schedule_lead_followup_sequence

    raw = _read_range(access_token, sheet_id, f"{sheet_tab}!A1:Z1000")
    if not raw or len(raw) < 2:
        return {"success": True, "imported": 0, "skipped": 0, "invalid": 0,
                "message": "Sheet is empty or has no data rows."}

    # Map column names → indices
    header_row = [h.strip().lower() for h in raw[0]]
    col_map: dict[str, int] = {}
    for field, aliases in IMPORT_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in header_row:
                col_map[field] = header_row.index(alias)
                break

    if "email" not in col_map:
        return {"success": False, "error": "Sheet must have an 'Email' column."}

    imported = 0
    skipped_dup = 0
    invalid = 0

    for row in raw[1:]:
        def _cell(field: str) -> str:
            idx = col_map.get(field)
            if idx is None or idx >= len(row):
                return ""
            return str(row[idx]).strip()

        email = _cell("email").lower()
        if not email or "@" not in email:
            invalid += 1
            continue

        # Skip duplicates
        if db.query(Lead).filter(Lead.email == email).first():
            skipped_dup += 1
            continue

        name = _cell("name") or email.split("@")[0]
        company = _cell("company") or ""
        title = _cell("title") or ""
        industry = _cell("industry") or ""
        website = _cell("website") or ""
        notes = _cell("notes") or ""

        lead = Lead(
            name=name[:255],
            email=email[:255],
            company=company[:255],
            title=title[:255],
            source="sheets_import",
            status=LeadStatus.NEW,
            notes=(
                f"[RESEARCH]\nIndustry: {industry}\nWebsite: {website}\n"
                + (f"Notes: {notes}" if notes else "")
            ).strip(),
        )
        db.add(lead)
        db.flush()

        # Queue outreach sequence
        schedule_lead_followup_sequence(lead.id)
        imported += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}

    _logger.info(f"Sheet import: {imported} imported, {skipped_dup} dupes, {invalid} invalid")
    return {
        "success": True,
        "imported": imported,
        "skipped_duplicates": skipped_dup,
        "invalid_rows": invalid,
        "message": f"Imported {imported} new leads. {skipped_dup} duplicates skipped.",
    }


def get_sheet_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def extract_sheet_id_from_url(url: str) -> Optional[str]:
    """Extract spreadsheet ID from a Google Sheets URL."""
    import re
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    return m.group(1) if m else None
