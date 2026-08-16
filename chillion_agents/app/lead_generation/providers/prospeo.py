"""
Prospeo people provider.

Search:  POST /search-person
Enrich:  POST /bulk-enrich-person  (up to 50 people per request)

Search Person does not reveal emails. Bulk Enrich Person is required for
verified professional email. LinkedIn URLs are taken only when Prospeo
supplies them.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging

import requests

from app.config import settings
from app.lead_generation.config import get_config
from app.lead_generation.models import ContactSource, FinanceContact
from app.lead_generation.contacts.domain import domains_match, normalize_domain
from app.lead_generation.contacts.titles import matches_target_title
from .base import PeopleSearchProvider
from .errors import (
    ProspeoAPIError,
    ProspeoAuthenticationError,
    ProspeoDomainRequiredError,
    ProspeoInsufficientCreditsError,
    ProspeoNotConfiguredError,
    ProspeoPlanRequiredError,
    ProspeoRateLimitError,
)

logger = logging.getLogger(__name__)

PROSPEO_BASE_URL = "https://api.prospeo.io"
SEARCH_PATH = "/search-person"
BULK_ENRICH_PATH = "/bulk-enrich-person"
SEARCH_RESULTS_PER_PAGE = 25
BULK_ENRICH_BATCH_SIZE = 50
NO_RESULTS = "NO_RESULTS"


class ProspeoPeopleProvider(PeopleSearchProvider):
    """Synchronous Prospeo Search Person + Bulk Enrich Person."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ):
        key = (api_key if api_key is not None else settings.prospeo_api_key) or ""
        self.api_key = key.strip()
        if not self.api_key:
            raise ProspeoNotConfiguredError("PROSPEO_API_KEY is not configured")

        rate_config = get_config().rate_limit
        self.timeout = timeout_seconds if timeout_seconds is not None else float(rate_config.request_timeout_seconds)
        self.session = session or requests.Session()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def search_people(
        self,
        company_name: str,
        company_domain: Optional[str],
        target_titles: List[str],
        max_results: int,
        find_emails: bool = True,
    ) -> List[FinanceContact]:
        domain = self._normalize_domain(company_domain)
        if not domain:
            raise ProspeoDomainRequiredError(
                "Prospeo Search Person requires a company domain; refusing to guess one"
            )

        titles = [t.strip() for t in target_titles if t and t.strip()]
        if not titles:
            return []

        limit = max(1, min(int(max_results or 1), 50))
        self.logger.info(
            "prospeo search company_domain=%s titles=%s max_results=%s find_emails=%s",
            domain,
            titles,
            limit,
            find_emails,
        )

        rows = self._dedupe_search_rows(self._search(domain, titles, limit))
        rows = self._prefilter_search_rows(rows, domain, titles)
        self.logger.info("prospeo search result_count=%s", len(rows))
        if not rows:
            return []

        enrichment_by_id: Dict[str, Dict[str, Any]] = {}
        if find_emails:
            enrichment_by_id = self._enrich(rows)
            self.logger.info("prospeo enriched_count=%s", len(enrichment_by_id))

        contacts = [
            self._to_contact(
                row=row,
                enrichment=enrichment_by_id.get(_person_id(row)),
                company_name=company_name,
                company_domain=domain,
                find_emails=find_emails,
            )
            for row in rows
            if _person_id(row)
        ]
        contacts = [c for c in contacts if c is not None]
        contacts = self._deduplicate(contacts)
        return contacts[:limit]

    # -------------------------------------------------------------------------
    # HTTP
    # -------------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-KEY": self.api_key,
        }

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{PROSPEO_BASE_URL}{path}"
        try:
            response = self.session.request(
                method,
                url,
                headers=self._headers(),
                timeout=self.timeout,
                json=json_body,
            )
        except requests.Timeout as exc:
            raise ProspeoAPIError("Prospeo request timed out") from exc
        except requests.RequestException as exc:
            raise ProspeoAPIError("Prospeo request failed") from exc

        payload = _safe_json(response)
        classified = _classify_prospeo_response(response.status_code, payload)
        if classified == NO_RESULTS:
            return {"error": True, "error_code": NO_RESULTS, "results": []}
        return payload or {}

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def _search(self, domain: str, titles: List[str], max_results: int) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        page = 1
        max_pages = max(1, (max_results + SEARCH_RESULTS_PER_PAGE - 1) // SEARCH_RESULTS_PER_PAGE)

        while len(collected) < max_results and page <= max_pages:
            payload = self._request(
                "POST",
                SEARCH_PATH,
                json_body=_search_body(domain=domain, titles=titles, page=page),
            )
            if payload.get("error_code") == NO_RESULTS:
                break
            results = payload.get("results") or []
            if not isinstance(results, list) or not results:
                break
            collected.extend([row for row in results if isinstance(row, dict)])

            pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
            total_page = pagination.get("total_page") or page
            if page >= int(total_page):
                break
            if len(results) < SEARCH_RESULTS_PER_PAGE:
                break
            page += 1

        return collected[:max_results]

    def _dedupe_search_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: List[Dict[str, Any]] = []
        seen = set()
        for row in rows:
            person_id = _person_id(row)
            if not person_id or person_id in seen:
                continue
            seen.add(person_id)
            unique.append(row)
        return unique

    def _prefilter_search_rows(
        self,
        rows: List[Dict[str, Any]],
        domain: str,
        titles: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Skip enrichment for people who already cannot match.

        Unknown org/title is kept. Known mismatches are dropped.
        """
        kept: List[Dict[str, Any]] = []
        for row in rows:
            org_domain = _row_org_domain(row)
            if org_domain and not domains_match(org_domain, domain):
                continue
            title = _row_title(row)
            if title and titles and not matches_target_title(title, titles):
                continue
            kept.append(row)
        return kept

    # -------------------------------------------------------------------------
    # Enrichment
    # -------------------------------------------------------------------------

    def _enrich(self, rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        by_person_id: Dict[str, Dict[str, Any]] = {}
        records: List[Tuple[str, str]] = []
        for index, row in enumerate(rows):
            person_id = _person_id(row)
            if not person_id:
                continue
            records.append((f"contact-{index}", person_id))

        for chunk in _chunks(records, BULK_ENRICH_BATCH_SIZE):
            body = {
                "only_verified_email": True,
                "enrich_mobile": False,
                "data": [
                    {"identifier": identifier, "person_id": person_id}
                    for identifier, person_id in chunk
                ],
            }
            payload = self._request("POST", BULK_ENRICH_PATH, json_body=body)
            if payload.get("error_code") == NO_RESULTS:
                continue
            identifier_to_person_id = {identifier: person_id for identifier, person_id in chunk}
            matched = payload.get("matched") or []
            if not isinstance(matched, list):
                continue
            for match in matched:
                if not isinstance(match, dict):
                    continue
                identifier = str(match.get("identifier") or "")
                person_id = identifier_to_person_id.get(identifier)
                if person_id:
                    by_person_id[person_id] = match
        return by_person_id

    # -------------------------------------------------------------------------
    # Mapping
    # -------------------------------------------------------------------------

    def _to_contact(
        self,
        row: Dict[str, Any],
        enrichment: Optional[Dict[str, Any]],
        company_name: str,
        company_domain: str,
        find_emails: bool,
    ) -> Optional[FinanceContact]:
        search_person = _person_obj(row)
        search_company = _company_obj(row)
        enrich_person = _person_obj(enrichment) if enrichment else {}
        enrich_company = _company_obj(enrichment) if enrichment else {}
        person = {**search_person, **enrich_person} if enrich_person else search_person
        company = {**search_company, **enrich_company} if enrich_company else search_company

        first_name = person.get("first_name")
        last_name = person.get("last_name")
        full_name = (
            person.get("full_name")
            or " ".join([p for p in [first_name, last_name] if p]).strip()
        )
        if not full_name:
            return None

        title = person.get("current_job_title") or "Unknown"
        linkedin_url = person.get("linkedin_url") or None
        if linkedin_url is not None:
            linkedin_url = str(linkedin_url).strip() or None

        email = None
        email_status = "not_found"
        email_confidence = None
        email_source = "none"
        if find_emails:
            email = _revealed_verified_email(person)
            if email:
                email_status = "verified"
                email_source = "prospeo"
            else:
                email = None
                email_status = "not_found"
                email_source = "none"

        person_id = person.get("person_id") or _person_id(row)
        org_domain = normalize_domain(company.get("domain") or company.get("website"))
        return FinanceContact(
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            title=title,
            company_name=company_name,
            company_domain=company_domain,
            email=email,
            email_status=email_status,
            email_confidence=email_confidence,
            email_source=email_source,
            linkedin_url=linkedin_url,
            source=ContactSource.PROSPEO,
            source_url=None,
            provider="prospeo",
            provider_id=str(person_id) if person_id else None,
            seniority_level=_seniority_from_title(str(title)),
            enrichment_data=_safe_metadata(person, company, org_domain),
        )

    def _deduplicate(self, contacts: List[FinanceContact]) -> List[FinanceContact]:
        unique: List[FinanceContact] = []
        seen_ids = set()
        seen_linkedin = set()
        seen_email = set()
        seen_name = set()

        for contact in contacts:
            keys = []
            if contact.provider_id:
                keys.append(("id", contact.provider_id))
            if contact.linkedin_url:
                keys.append(("li", contact.linkedin_url.lower().rstrip("/")))
            if contact.email and (contact.email_status or "") != "pattern_guess":
                keys.append(("em", contact.email.lower()))
            name_key = (
                "nm",
                f"{(contact.full_name or '').strip().lower()}|{(contact.company_name or '').strip().lower()}",
            )
            keys.append(name_key)

            if any(
                (kind == "id" and value in seen_ids)
                or (kind == "li" and value in seen_linkedin)
                or (kind == "em" and value in seen_email)
                or (kind == "nm" and value in seen_name)
                for kind, value in keys
            ):
                continue

            for kind, value in keys:
                if kind == "id":
                    seen_ids.add(value)
                elif kind == "li":
                    seen_linkedin.add(value)
                elif kind == "em":
                    seen_email.add(value)
                elif kind == "nm":
                    seen_name.add(value)
            unique.append(contact)
        return unique

    def _normalize_domain(self, company_domain: Optional[str]) -> Optional[str]:
        if not company_domain:
            return None
        return normalize_domain(company_domain)


def _search_body(domain: str, titles: List[str], page: int) -> Dict[str, Any]:
    return {
        "page": page,
        "filters": {
            "person_job_title": {
                "include": titles,
                "match_mode": "CONTAINS",
            },
            "company": {
                "websites": {
                    "include": [domain],
                }
            },
        },
    }


def _classify_prospeo_response(status: int, payload: Optional[Dict[str, Any]]) -> Optional[str]:
    error_code = ""
    if isinstance(payload, dict):
        if payload.get("error") is True or payload.get("error_code"):
            error_code = str(payload.get("error_code") or "")
        elif payload.get("error") is False or payload is not None:
            if status < 400:
                return None

    if error_code == NO_RESULTS or (status == 400 and error_code == NO_RESULTS):
        return NO_RESULTS
    if error_code == "INVALID_API_KEY" or status in (401, 403):
        raise ProspeoAuthenticationError(f"Prospeo authentication failed ({status or 400})", status_code=status or 400)
    if error_code == "INSUFFICIENT_CREDITS":
        raise ProspeoInsufficientCreditsError("Prospeo credits are exhausted")
    if error_code == "PLAN_REQUIRED":
        raise ProspeoPlanRequiredError("Prospeo plan does not allow this search")
    if status == 429 or error_code in ("Rate limit exceeded", "RATE_LIMIT_EXCEEDED"):
        raise ProspeoRateLimitError("Prospeo rate limit exceeded")
    if error_code in ("INVALID_FILTERS", "INVALID_REQUEST"):
        raise ProspeoAPIError(f"Prospeo rejected the request ({error_code})", status_code=status or 400)
    if error_code in ("SERVICE_TEMPORARILY_UNAVAILABLE", "INTERNAL_ERROR"):
        raise ProspeoAPIError(f"Prospeo is unavailable ({error_code})", status_code=status or 400)
    if status >= 500:
        raise ProspeoAPIError(f"Prospeo is unavailable ({status})", status_code=status)
    if status >= 400:
        raise ProspeoAPIError(f"Prospeo request failed ({status})", status_code=status)
    if error_code:
        raise ProspeoAPIError(f"Prospeo request failed ({error_code})", status_code=status or 400)
    return None


def _safe_json(response: requests.Response) -> Optional[Dict[str, Any]]:
    try:
        payload = response.json()
    except ValueError:
        if response.status_code >= 400:
            return None
        raise ProspeoAPIError("Prospeo returned a non-JSON response")
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ProspeoAPIError("Prospeo returned an unexpected payload")
    return payload


def _person_obj(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    person = row.get("person")
    if isinstance(person, dict):
        return person
    return {}


def _company_obj(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    company = row.get("company")
    if isinstance(company, dict):
        return company
    return {}


def _person_id(row: Dict[str, Any]) -> Optional[str]:
    person = _person_obj(row)
    value = person.get("person_id") or row.get("person_id")
    return str(value) if value else None


def _row_title(row: Dict[str, Any]) -> Optional[str]:
    person = _person_obj(row)
    title = person.get("current_job_title")
    return str(title) if title else None


def _row_org_domain(row: Dict[str, Any]) -> Optional[str]:
    company = _company_obj(row)
    return normalize_domain(company.get("domain") or company.get("website"))


def _revealed_verified_email(person: Dict[str, Any]) -> Optional[str]:
    email_obj = person.get("email")
    if not isinstance(email_obj, dict):
        return None
    if not email_obj.get("revealed"):
        return None
    status = str(email_obj.get("status") or "").strip().upper()
    if status != "VERIFIED":
        return None
    value = email_obj.get("email")
    if not value:
        return None
    email = str(value).strip()
    if not email or "*" in email:
        return None
    return email


def _seniority_from_title(title: str) -> Optional[str]:
    title_lower = (title or "").lower()
    if any(x in title_lower for x in ["chief", "cfo", "ceo", "coo", "cto", "cmo", "cio"]):
        return "C-Level"
    if any(x in title_lower for x in ["vp", "vice president"]):
        return "VP"
    if "director" in title_lower:
        return "Director"
    if any(x in title_lower for x in ["manager", "head", "lead", "recruiter"]):
        return "Manager"
    return "Other"


def _safe_metadata(person: Dict[str, Any], company: Dict[str, Any], org_domain: Optional[str]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if company.get("company_id"):
        data["organization_id"] = company.get("company_id")
    if company.get("name"):
        data["organization_name"] = company.get("name")
    if org_domain:
        data["organization_primary_domain"] = org_domain
    headline = person.get("headline")
    if headline:
        data["headline"] = headline
    return data


def _chunks(items: Iterable[Tuple[str, str]], size: int) -> Iterable[List[Tuple[str, str]]]:
    batch: List[Tuple[str, str]] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
