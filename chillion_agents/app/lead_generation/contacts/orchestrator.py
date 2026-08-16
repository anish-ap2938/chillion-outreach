"""
Contact discovery orchestrator.

Owns the discovery decision tree: trusted domain, Prospeo-first, current
employer/title verification, website fallback, email strategy, merge/dedupe,
and persistence. FastAPI stays thin.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import logging

from ..models import Company, FinanceContact
from ..config import get_config
from ..providers.base import PeopleSearchProvider
from ..providers.prospeo import ProspeoPeopleProvider
from ..providers.errors import (
    ProspeoAPIError,
    ProspeoAuthenticationError,
    ProspeoDomainRequiredError,
    ProspeoInsufficientCreditsError,
    ProspeoNotConfiguredError,
    ProspeoPlanRequiredError,
    ProspeoRateLimitError,
)
from ..storage.database import LeadDatabase
from .discovery import ContactDiscoveryService
from .email import EmailDiscoveryService
from .domain import (
    TrustedDomain,
    domains_match,
    normalize_linkedin_url,
    resolve_trusted_domain,
)
from .titles import matches_target_title

logger = logging.getLogger(__name__)

PROSPEO_PROVIDER = "prospeo"
WEBSITE_PROVIDER = "company_website"
AUDIT_ACTOR = "system"

PROVIDER_SKIPPED = "skipped"
PROVIDER_FAILED = "failed"
PROVIDER_SUCCEEDED = "succeeded"

EMAIL_RANK = {
    "verified": 5,
    "likely": 4,
    "unverified": 3,
    "pattern_guess": 2,
    "invalid": 1,
    "not_found": 0,
}


@dataclass
class ContactDiscoveryOutcome:
    contacts: List[FinanceContact] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ContactDiscoveryOrchestrator:
    """
    Production discovery pipeline.

    ContactDiscoveryOrchestrator
            ├── ProspeoPeopleProvider (when configured + trusted domain)
            ├── ContactDiscoveryService (website scrape fallback)
            └── EmailDiscoveryService (pattern guess on trusted domains only)
    """

    def __init__(
        self,
        people_provider: Optional[PeopleSearchProvider] = None,
        website_service: Optional[ContactDiscoveryService] = None,
        email_service: Optional[EmailDiscoveryService] = None,
        db: Optional[LeadDatabase] = None,
        *,
        prospeo_configured: Optional[bool] = None,
        persist: bool = True,
        audit_actor: str = AUDIT_ACTOR,
    ):
        self._injected_provider = people_provider
        self.website_service = website_service or ContactDiscoveryService()
        self.email_service = email_service or EmailDiscoveryService()
        self.db = db
        self.persist = persist
        self.audit_actor = audit_actor
        if prospeo_configured is None:
            from app.config import settings
            self.prospeo_configured = bool((settings.prospeo_api_key or "").strip())
        else:
            self.prospeo_configured = bool(prospeo_configured)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def discover(
        self,
        company_name: str,
        company_domain: Optional[str] = None,
        company_website: Optional[str] = None,
        target_titles: Optional[List[str]] = None,
        max_results: int = 10,
        find_emails: bool = True,
    ) -> ContactDiscoveryOutcome:
        titles = self._resolve_titles(target_titles)
        limit = max(1, min(int(max_results or 1), 50))
        warnings: List[str] = []
        trusted = resolve_trusted_domain(company_domain, company_website)

        self.logger.info(
            "orchestrator start company=%s trusted_domain=%s origin=%s titles=%s max_results=%s find_emails=%s",
            company_name,
            trusted.domain,
            trusted.origin,
            titles,
            limit,
            find_emails,
        )

        if not trusted.is_trusted:
            if company_domain:
                warnings.append("Company domain was invalid; skipped Prospeo.")
            else:
                warnings.append("No trusted company domain; skipped Prospeo and pattern email.")
            self.logger.info("no trusted domain; skipping Prospeo")

        people_contacts, people_warnings, outcome = self._discover_people(
            company_name=company_name,
            trusted=trusted,
            titles=titles,
            max_results=limit,
            find_emails=find_emails,
        )
        warnings.extend(people_warnings)

        usable_people = self._filter_people(people_contacts, trusted, titles)
        self.logger.info(
            "Prospeo returned %s raw results; %s passed current-employer/title validation",
            len(people_contacts),
            len(usable_people),
        )

        if outcome == PROVIDER_SUCCEEDED and not usable_people:
            warnings.append(
                "Prospeo returned no contacts matching the current company and requested titles; used company website fallback."
            )

        need_website = (not usable_people) or (len(usable_people) < limit)
        website_contacts: List[FinanceContact] = []
        if need_website:
            website_contacts = self._discover_website(
                company_name=company_name,
                trusted=trusted,
                titles=titles,
                max_results=limit,
            )
            self.logger.info(
                "Website fallback requested remaining=%s website_raw=%s",
                max(limit - len(usable_people), 0),
                len(website_contacts),
            )
            if website_contacts and outcome == PROVIDER_SUCCEEDED and usable_people:
                warnings.append("Company website fallback used to fill remaining results.")

        merged = self._merge_and_dedupe(usable_people, website_contacts)
        self.logger.info("contacts after merge/dedupe=%s", len(merged))
        merged = merged[:limit]
        self._apply_email_strategy(merged, find_emails=find_emails, trusted=trusted)

        if self.persist and self.db is not None:
            self._persist(merged)

        return ContactDiscoveryOutcome(contacts=merged, warnings=_unique_warnings(warnings))

    # -------------------------------------------------------------------------
    # People provider
    # -------------------------------------------------------------------------

    def _people_provider(self) -> Optional[PeopleSearchProvider]:
        if self._injected_provider is not None:
            return self._injected_provider
        if not self.prospeo_configured:
            return None
        try:
            return ProspeoPeopleProvider()
        except ProspeoNotConfiguredError:
            return None

    def _discover_people(
        self,
        company_name: str,
        trusted: TrustedDomain,
        titles: List[str],
        max_results: int,
        find_emails: bool,
    ) -> tuple:
        warnings: List[str] = []
        if not trusted.is_trusted:
            return [], warnings, PROVIDER_SKIPPED
        provider = self._people_provider()
        if provider is None:
            if not self.prospeo_configured and self._injected_provider is None:
                warnings.append("Prospeo is not configured; used company website fallback.")
            return [], warnings, PROVIDER_SKIPPED

        self.logger.info("Prospeo selected for %s", trusted.domain)
        try:
            contacts = provider.search_people(
                company_name=company_name,
                company_domain=trusted.domain,
                target_titles=titles,
                max_results=max_results,
                find_emails=find_emails,
            )
            return list(contacts or []), warnings, PROVIDER_SUCCEEDED
        except ProspeoDomainRequiredError:
            warnings.append("No trusted company domain; skipped Prospeo and pattern email.")
            return [], warnings, PROVIDER_SKIPPED
        except ProspeoAuthenticationError:
            self.logger.warning("Prospeo authentication failed; falling back to website")
            warnings.append("Prospeo authentication failed; used company website fallback.")
            return [], warnings, PROVIDER_FAILED
        except ProspeoInsufficientCreditsError:
            self.logger.warning("Prospeo credits exhausted; falling back to website")
            warnings.append("Prospeo credits are exhausted; used company website fallback.")
            return [], warnings, PROVIDER_FAILED
        except ProspeoPlanRequiredError:
            self.logger.warning("Prospeo plan required; falling back to website")
            warnings.append("Prospeo plan does not allow this search; used company website fallback.")
            return [], warnings, PROVIDER_FAILED
        except ProspeoRateLimitError:
            self.logger.warning("Prospeo rate limited; falling back to website")
            warnings.append("Prospeo was rate limited; used company website fallback.")
            return [], warnings, PROVIDER_FAILED
        except (ProspeoAPIError, ProspeoNotConfiguredError) as exc:
            self.logger.warning("Prospeo unavailable (%s); falling back to website", exc.__class__.__name__)
            warnings.append("Prospeo was unavailable; used company website fallback.")
            return [], warnings, PROVIDER_FAILED
        except Exception:
            self.logger.warning("Prospeo request failed; falling back to website", exc_info=False)
            warnings.append("Prospeo was unavailable; used company website fallback.")
            return [], warnings, PROVIDER_FAILED

    def _filter_people(
        self,
        contacts: List[FinanceContact],
        trusted: TrustedDomain,
        titles: List[str],
    ) -> List[FinanceContact]:
        kept: List[FinanceContact] = []
        for contact in contacts:
            current_domain = _current_employer_domain(contact)
            if not current_domain or not domains_match(current_domain, trusted.domain):
                self.logger.info(
                    "dropping contact without current-employer match name=%s org_domain=%s",
                    contact.full_name,
                    current_domain,
                )
                continue
            if not matches_target_title(contact.title, titles):
                self.logger.info(
                    "dropping contact without current-title match name=%s title=%s",
                    contact.full_name,
                    contact.title,
                )
                continue
            kept.append(contact)
        return kept

    # -------------------------------------------------------------------------
    # Website
    # -------------------------------------------------------------------------

    def _discover_website(
        self,
        company_name: str,
        trusted: TrustedDomain,
        titles: List[str],
        max_results: int,
    ) -> List[FinanceContact]:
        company = Company(
            name=company_name,
            domain=trusted.domain if trusted.is_trusted else None,
            website=trusted.website if trusted.is_trusted else None,
        )
        try:
            contacts = self.website_service.discover_contacts(
                company,
                target_titles=titles,
                max_results=max_results,
                find_emails=False,
            )
            return list(contacts or [])
        except Exception as exc:
            self.logger.warning("Website contact discovery failed: %s", exc)
            return []

    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------

    def _apply_email_strategy(
        self,
        contacts: List[FinanceContact],
        find_emails: bool,
        trusted: TrustedDomain,
    ) -> None:
        for contact in contacts:
            if not find_emails:
                contact.email = None
                contact.email_status = "not_found"
                contact.email_confidence = None
                contact.email_source = "none"
                continue

            if contact.email:
                if not getattr(contact, "email_source", None):
                    contact.email_source = "prospeo" if (contact.provider or "") == PROSPEO_PROVIDER else None
                continue

            if not trusted.is_trusted:
                contact.email = None
                contact.email_status = "not_found"
                contact.email_source = "none"
                continue

            contact.company_domain = trusted.domain
            self.email_service.discover_email(contact)
            if contact.email and (contact.email_status or "") == "pattern_guess":
                contact.email_source = "pattern_guess"
                contact.provider = contact.provider or WEBSITE_PROVIDER
            elif not contact.email:
                contact.email_status = contact.email_status or "not_found"
                contact.email_source = "none"

    # -------------------------------------------------------------------------
    # Merge / dedupe
    # -------------------------------------------------------------------------

    def _merge_and_dedupe(
        self,
        people_contacts: List[FinanceContact],
        website_contacts: List[FinanceContact],
    ) -> List[FinanceContact]:
        merged: List[FinanceContact] = []
        for contact in list(people_contacts) + list(website_contacts):
            idx = self._find_duplicate_index(merged, contact)
            if idx is None:
                merged.append(contact)
                continue
            merged[idx] = _prefer_contact(merged[idx], contact)
        return merged

    def _find_duplicate_index(
        self,
        existing: List[FinanceContact],
        candidate: FinanceContact,
    ) -> Optional[int]:
        cand_id = (candidate.provider_id or "").strip()
        cand_li = normalize_linkedin_url(candidate.linkedin_url)
        cand_email = _dedupe_email(candidate)
        cand_name = _name_company_key(candidate)
        cand_title = _name_title_company_key(candidate)

        for idx, current in enumerate(existing):
            if cand_id and current.provider_id and cand_id == current.provider_id:
                return idx
            cur_li = normalize_linkedin_url(current.linkedin_url)
            if cand_li and cur_li and cand_li == cur_li:
                return idx
            cur_email = _dedupe_email(current)
            if cand_email and cur_email and cand_email == cur_email:
                return idx
            if cand_name and cand_name == _name_company_key(current):
                return idx
            if cand_title and cand_title == _name_title_company_key(current):
                return idx
        return None

    # -------------------------------------------------------------------------
    # Persist
    # -------------------------------------------------------------------------

    def _persist(self, contacts: List[FinanceContact]) -> None:
        if self.db is None:
            return
        for contact in contacts:
            self.db.upsert_contact(contact)
            try:
                self.db.insert_audit_event(
                    actor=self.audit_actor,
                    action="contact_discover",
                    entity_type="contact",
                    entity_id=contact.id or contact.full_name,
                    metadata={"company": contact.company_name, "provider": contact.provider},
                )
            except Exception:
                self.logger.debug("audit insert skipped", exc_info=True)

    def _resolve_titles(self, target_titles: Optional[List[str]]) -> List[str]:
        if target_titles is None:
            return list(get_config().company.target_titles)
        return [t.strip() for t in target_titles if t and str(t).strip()]


def _current_employer_domain(contact: FinanceContact) -> Optional[str]:
    data = contact.enrichment_data or {}
    return (
        data.get("organization_primary_domain")
        or data.get("primary_domain")
        or data.get("organization_domain")
    )


def _dedupe_email(contact: FinanceContact) -> Optional[str]:
    if not contact.email:
        return None
    if (contact.email_status or "").lower() == "pattern_guess":
        return None
    if (getattr(contact, "email_source", None) or "") == "pattern_guess":
        return None
    return contact.email.strip().lower()


def _name_company_key(contact: FinanceContact) -> str:
    return f"{(contact.full_name or '').strip().lower()}|{(contact.company_name or '').strip().lower()}"


def _name_title_company_key(contact: FinanceContact) -> str:
    return (
        f"{(contact.full_name or '').strip().lower()}|"
        f"{(contact.title or '').strip().lower()}|"
        f"{(contact.company_name or '').strip().lower()}"
    )


def _prefer_contact(left: FinanceContact, right: FinanceContact) -> FinanceContact:
    """Prefer Prospeo-enriched records; fill gaps from the other side."""
    primary, secondary = left, right
    if (right.provider or "") == PROSPEO_PROVIDER and (left.provider or "") != PROSPEO_PROVIDER:
        primary, secondary = right, left
    elif (left.provider or "") == PROSPEO_PROVIDER:
        primary, secondary = left, right

    if not primary.linkedin_url and secondary.linkedin_url:
        primary.linkedin_url = secondary.linkedin_url
    if not primary.email and secondary.email:
        primary.email = secondary.email
        primary.email_status = secondary.email_status
        primary.email_confidence = secondary.email_confidence
        primary.email_source = getattr(secondary, "email_source", None)
    elif primary.email and secondary.email:
        if EMAIL_RANK.get((secondary.email_status or ""), 0) > EMAIL_RANK.get((primary.email_status or ""), 0):
            if (primary.email_status or "") != "verified":
                primary.email = secondary.email
                primary.email_status = secondary.email_status
                primary.email_confidence = secondary.email_confidence
                primary.email_source = getattr(secondary, "email_source", None)
    if not primary.provider_id and secondary.provider_id:
        primary.provider_id = secondary.provider_id
        if (secondary.provider or "") == PROSPEO_PROVIDER:
            primary.provider = PROSPEO_PROVIDER
    if not primary.bio and secondary.bio:
        primary.bio = secondary.bio
    return primary


def _unique_warnings(warnings: List[str]) -> List[str]:
    seen = set()
    out = []
    for warning in warnings:
        if warning and warning not in seen:
            seen.add(warning)
            out.append(warning)
    return out
