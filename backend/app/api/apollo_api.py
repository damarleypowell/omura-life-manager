"""
Omura Apollo.io API Integration
Provides lead enrichment, people search, company lookup, and contact
management through the Apollo.io REST API v1.

All methods return mock data when APOLLO_API_KEY is not configured,
allowing the rest of the app to function in dev mode.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class ApolloClient:
    """Client for the Apollo.io API.

    Capabilities:
    - People search (find contacts by title, company, location)
    - People enrichment (get full profile from email)
    - Company enrichment (get firmographic data from domain)
    - Contact list management (push/pull contacts to Apollo sequences)
    - Lead stage sync (keep Omura Lead model in sync with Apollo)
    """

    BASE_URL = "https://api.apollo.io/api/v1"

    def __init__(self) -> None:
        self.api_key: Optional[str] = settings.APOLLO_API_KEY
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers=self._build_headers(),
        )
        self._logger = OmuraLogger("apollo_client")
        self._logger.info("ApolloClient initialized", configured=bool(self.api_key))

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    # ──────────────────────────────────────────────
    # People Search
    # ──────────────────────────────────────────────

    async def search_people(
        self,
        q_keywords: Optional[str] = None,
        person_titles: Optional[List[str]] = None,
        person_locations: Optional[List[str]] = None,
        organization_domains: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """Search Apollo's database for people matching criteria.

        Args:
            q_keywords: Free-text keyword query.
            person_titles: Job titles to filter by (e.g. ["CEO", "CTO"]).
            person_locations: Locations (e.g. ["New York", "London"]).
            organization_domains: Company domains (e.g. ["acme.com"]).
            page: Pagination page number.
            per_page: Results per page (max 100).

        Returns:
            Dict with 'people' list and 'pagination' metadata.
        """
        self._logger.info(
            "Searching people on Apollo",
            keywords=q_keywords,
            titles=person_titles,
            page=page,
        )

        if not self.is_configured:
            return self._mock_people_search(q_keywords, per_page)

        # api_search does NOT return emails — use has_email flag then enrich
        payload = {
            "page": page,
            "per_page": min(per_page, 100),
        }
        if q_keywords:
            payload["q_keywords"] = q_keywords
        if person_titles:
            payload["person_titles"] = person_titles
        if person_locations:
            payload["person_locations"] = person_locations
        if organization_domains:
            payload["q_organization_domains_list"] = organization_domains

        try:
            resp = await self._http.post(
                f"{self.BASE_URL}/mixed_people/api_search",
                json=payload,
                headers={**self._build_headers(), "X-Api-Key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            self._logger.info("Apollo people search complete", total=data.get("total_entries", 0))
            return {
                "people": data.get("people", []),
                "total_entries": data.get("total_entries", 0),
            }
        except httpx.HTTPError as exc:
            self._logger.error("Apollo people search failed", error=str(exc))
            return self._mock_people_search(q_keywords, per_page)

    # ──────────────────────────────────────────────
    # People Enrichment
    # ──────────────────────────────────────────────

    async def enrich_person(self, email: str) -> Dict[str, Any]:
        """Enrich a person's profile from their email address.

        Args:
            email: The person's email address.

        Returns:
            Dict with full profile data (name, title, company, LinkedIn, phone, etc.).
        """
        self._logger.info("Enriching person on Apollo", email=email)

        if not self.is_configured:
            return self._mock_person_enrichment(email)

        payload = {"api_key": self.api_key, "email": email}
        try:
            resp = await self._http.post(
                f"{self.BASE_URL}/people/match",
                json=payload,
                headers={**self._build_headers(), "X-Api-Key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            person = data.get("person", {})
            self._logger.info("Person enriched", name=person.get("name"), company=person.get("organization", {}).get("name"))
            return person
        except httpx.HTTPError as exc:
            self._logger.error("Apollo person enrichment failed", error=str(exc))
            return self._mock_person_enrichment(email)

    async def enrich_person_by_id(self, apollo_id: str) -> Dict[str, Any]:
        """Enrich a person using their Apollo ID (from search results).

        This is the two-step flow: search → get IDs → enrich by ID to get email.
        Uses the bulk_match endpoint which is credit-efficient.
        """
        self._logger.info("Enriching person by Apollo ID", apollo_id=apollo_id)
        if not self.is_configured:
            return self._mock_person_enrichment(f"id_{apollo_id}@example.com")

        payload = {
            "api_key": self.api_key,
            "details": [{"id": apollo_id}],
            "reveal_personal_emails": False,
        }
        try:
            resp = await self._http.post(
                f"{self.BASE_URL}/people/bulk_match",
                json=payload,
                headers={**self._build_headers(), "X-Api-Key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            matches = data.get("matches", [])
            if matches:
                return matches[0]
            return {}
        except httpx.HTTPError as exc:
            self._logger.error("Apollo bulk_match failed", error=str(exc))
            return {}

    # ──────────────────────────────────────────────
    # Company Enrichment
    # ──────────────────────────────────────────────

    async def enrich_company(self, domain: str) -> Dict[str, Any]:
        """Get firmographic data for a company from its domain.

        Args:
            domain: Company website domain (e.g. "acme.com").

        Returns:
            Dict with company data (name, industry, size, location, funding, etc.).
        """
        self._logger.info("Enriching company on Apollo", domain=domain)

        if not self.is_configured:
            return self._mock_company_enrichment(domain)

        payload = {"api_key": self.api_key, "domain": domain}
        try:
            resp = await self._http.post(
                f"{self.BASE_URL}/organizations/enrich",
                json=payload,
                headers={**self._build_headers(), "X-Api-Key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            org = data.get("organization", {})
            self._logger.info("Company enriched", name=org.get("name"), industry=org.get("industry"))
            return org
        except httpx.HTTPError as exc:
            self._logger.error("Apollo company enrichment failed", error=str(exc))
            return self._mock_company_enrichment(domain)

    # ──────────────────────────────────────────────
    # Contact Management
    # ──────────────────────────────────────────────

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact in Apollo.

        Args:
            contact_data: Dict with 'first_name', 'last_name', 'email',
                          'organization_name', 'title', etc.

        Returns:
            The created contact record from Apollo.
        """
        self._logger.info("Creating contact in Apollo", email=contact_data.get("email"))

        if not self.is_configured:
            return {
                "id": "mock_apollo_contact_001",
                **contact_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            resp = await self._http.post(f"{self.BASE_URL}/contacts", json=contact_data)
            resp.raise_for_status()
            data = resp.json()
            self._logger.info("Contact created in Apollo", id=data.get("contact", {}).get("id"))
            return data.get("contact", {})
        except httpx.HTTPError as exc:
            self._logger.error("Apollo contact creation failed", error=str(exc))
            return {"id": None, "error": str(exc), **contact_data}

    async def update_contact(self, apollo_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing Apollo contact.

        Args:
            apollo_id: The Apollo contact ID.
            update_data: Fields to update.

        Returns:
            The updated contact record.
        """
        self._logger.info("Updating Apollo contact", apollo_id=apollo_id)

        if not self.is_configured:
            return {"id": apollo_id, **update_data, "updated_at": datetime.now(timezone.utc).isoformat()}

        try:
            resp = await self._http.put(f"{self.BASE_URL}/contacts/{apollo_id}", json=update_data)
            resp.raise_for_status()
            data = resp.json()
            self._logger.info("Apollo contact updated", apollo_id=apollo_id)
            return data.get("contact", {})
        except httpx.HTTPError as exc:
            self._logger.error("Apollo contact update failed", error=str(exc))
            return {"id": apollo_id, "error": str(exc)}

    async def search_contacts(self, query: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
        """Search contacts saved in your Apollo account.

        Args:
            query: Search string (name, email, company).
            page: Page number.
            per_page: Results per page.

        Returns:
            Dict with 'contacts' list and 'pagination' metadata.
        """
        self._logger.info("Searching Apollo contacts", query=query, page=page)

        if not self.is_configured:
            return self._mock_contact_search(query)

        payload = {"q_keywords": query, "page": page, "per_page": per_page}
        try:
            resp = await self._http.post(f"{self.BASE_URL}/contacts/search", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "contacts": data.get("contacts", []),
                "pagination": data.get("pagination", {}),
            }
        except httpx.HTTPError as exc:
            self._logger.error("Apollo contact search failed", error=str(exc))
            return self._mock_contact_search(query)

    # ──────────────────────────────────────────────
    # Sync — Push Omura leads to Apollo
    # ──────────────────────────────────────────────

    async def sync_lead_to_apollo(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Push an Omura Lead to Apollo as a contact, or update if exists.

        Args:
            lead: Dict from Omura's Lead model (name, email, company, etc.)

        Returns:
            Apollo contact record (created or updated).
        """
        name_parts = (lead.get("name") or "").split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        contact_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": lead.get("email"),
            "organization_name": lead.get("company"),
            "title": lead.get("extra_data", {}).get("title", ""),
            "phone_numbers": [{"raw_number": lead.get("phone")}] if lead.get("phone") else [],
        }

        self._logger.info("Syncing lead to Apollo", name=lead.get("name"), email=lead.get("email"))
        return await self.create_contact(contact_data)

    async def pull_enrichment_for_lead(self, email: str) -> Dict[str, Any]:
        """Enrich an Omura lead with Apollo data and return fields to update.

        Args:
            email: The lead's email address.

        Returns:
            Dict with fields suitable for updating the Omura Lead model:
            - company, phone, extra_data (title, linkedin_url, etc.)
        """
        person = await self.enrich_person(email)
        org = person.get("organization", {})

        enriched = {
            "company": org.get("name") or person.get("organization_name"),
            "phone": person.get("phone_number"),
            "extra_data": {
                "title": person.get("title"),
                "linkedin_url": person.get("linkedin_url"),
                "city": person.get("city"),
                "state": person.get("state"),
                "country": person.get("country"),
                "company_domain": org.get("primary_domain"),
                "company_industry": org.get("industry"),
                "company_size": org.get("estimated_num_employees"),
                "company_linkedin": org.get("linkedin_url"),
                "apollo_id": person.get("id"),
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        self._logger.info(
            "Lead enrichment from Apollo complete",
            email=email,
            company=enriched["company"],
            title=enriched["extra_data"]["title"],
        )
        return enriched

    # ──────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────

    async def close(self) -> None:
        await self._http.aclose()
        self._logger.info("ApolloClient HTTP connection closed")

    # ──────────────────────────────────────────────
    # Mock helpers (used when API key is not set)
    # ──────────────────────────────────────────────

    def _mock_people_search(self, query: Optional[str], per_page: int) -> Dict[str, Any]:
        self._logger.info("Returning mock Apollo people search")
        return {
            "people": [
                {
                    "id": f"mock_apollo_person_{i}",
                    "first_name": ["Sarah", "James", "Maria", "David", "Emily"][i - 1],
                    "last_name": ["Chen", "Wilson", "Garcia", "Kim", "Patel"][i - 1],
                    "name": f'{["Sarah", "James", "Maria", "David", "Emily"][i - 1]} {["Chen", "Wilson", "Garcia", "Kim", "Patel"][i - 1]}',
                    "title": ["CEO", "VP Engineering", "Head of Marketing", "CTO", "Director of Sales"][i - 1],
                    "email": f"person{i}@example.com",
                    "organization": {
                        "name": ["TechFlow Inc", "DataBridge", "GrowthLab", "CloudNine", "ScaleUp Co"][i - 1],
                        "primary_domain": f"company{i}.com",
                        "estimated_num_employees": [50, 200, 30, 500, 80][i - 1],
                    },
                    "city": "New York",
                    "state": "NY",
                    "country": "United States",
                    "linkedin_url": f"https://linkedin.com/in/person{i}",
                    "phone_number": f"+1-555-010{i}",
                }
                for i in range(1, min(per_page, 5) + 1)
            ],
            "pagination": {
                "page": 1,
                "per_page": per_page,
                "total_entries": 5,
                "total_pages": 1,
            },
        }

    def _mock_person_enrichment(self, email: str) -> Dict[str, Any]:
        self._logger.info("Returning mock Apollo person enrichment")
        username = email.split("@")[0]
        return {
            "id": f"mock_apollo_{username}",
            "first_name": username.capitalize(),
            "last_name": "Doe",
            "name": f"{username.capitalize()} Doe",
            "title": "Head of Operations",
            "email": email,
            "phone_number": "+1-555-0100",
            "linkedin_url": f"https://linkedin.com/in/{username}",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
            "organization": {
                "name": "Acme Corp",
                "primary_domain": email.split("@")[1] if "@" in email else "acme.com",
                "industry": "Technology",
                "estimated_num_employees": 150,
                "linkedin_url": "https://linkedin.com/company/acme",
            },
        }

    def _mock_company_enrichment(self, domain: str) -> Dict[str, Any]:
        self._logger.info("Returning mock Apollo company enrichment")
        return {
            "id": f"mock_apollo_org_{domain.replace('.', '_')}",
            "name": domain.split(".")[0].capitalize() + " Inc",
            "primary_domain": domain,
            "industry": "Technology",
            "estimated_num_employees": 150,
            "annual_revenue": 5000000,
            "founded_year": 2018,
            "city": "San Francisco",
            "state": "California",
            "country": "United States",
            "linkedin_url": f"https://linkedin.com/company/{domain.split('.')[0]}",
            "short_description": f"A leading technology company at {domain}.",
        }

    def _mock_contact_search(self, query: str) -> Dict[str, Any]:
        self._logger.info("Returning mock Apollo contact search")
        return {
            "contacts": [
                {
                    "id": "mock_contact_1",
                    "first_name": "Alex",
                    "last_name": "Thompson",
                    "email": "alex@example.com",
                    "title": "Product Manager",
                    "organization_name": "TechFlow Inc",
                },
                {
                    "id": "mock_contact_2",
                    "first_name": "Jordan",
                    "last_name": "Lee",
                    "email": "jordan@example.com",
                    "title": "Engineering Lead",
                    "organization_name": "DataBridge",
                },
            ],
            "pagination": {"page": 1, "per_page": 25, "total_entries": 2, "total_pages": 1},
        }
