"""Phase 3.5 Prospeo people provider — mocked HTTP only."""

from unittest.mock import MagicMock

import pytest
import requests

from app.lead_generation.contacts.email import EmailDiscoveryService
from app.lead_generation.contacts.orchestrator import ContactDiscoveryOrchestrator
from app.lead_generation.models import FinanceContact
from app.lead_generation.providers.errors import (
    ProspeoAPIError,
    ProspeoAuthenticationError,
    ProspeoInsufficientCreditsError,
    ProspeoNotConfiguredError,
    ProspeoPlanRequiredError,
    ProspeoRateLimitError,
)
from app.lead_generation.providers.prospeo import ProspeoPeopleProvider
from app.lead_generation.storage.database import LeadDatabase


MICROSOFT = {
    "name": "Microsoft",
    "website": "https://www.microsoft.com",
    "domain": "microsoft.com",
}

SEARCH_PERSON_A = {
    "person": {
        "person_id": "abc123",
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
        "linkedin_url": "https://www.linkedin.com/in/jane-doe",
        "current_job_title": "Senior Technical Recruiter",
        "email": {"status": "VERIFIED", "revealed": False, "email": "jane.*****@microsoft.com"},
    },
    "company": dict(MICROSOFT),
}

SEARCH_PERSON_B = {
    "person": {
        "person_id": "def456",
        "first_name": "John",
        "last_name": "Smith",
        "full_name": "John Smith",
        "linkedin_url": "https://www.linkedin.com/in/john-smith",
        "current_job_title": "Technical Recruiter",
        "email": {"status": "VERIFIED", "revealed": False, "email": "john.*****@microsoft.com"},
    },
    "company": dict(MICROSOFT),
}


def _json_response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    return response


def _error_response(error_code, status=400):
    return _json_response({"error": True, "error_code": error_code}, status=status)


def _provider(session) -> ProspeoPeopleProvider:
    return ProspeoPeopleProvider(api_key="test-key", session=session, timeout_seconds=5)


def _search_success(*rows):
    return {
        "error": False,
        "results": list(rows),
        "pagination": {"current_page": 1, "per_page": 25, "total_page": 1, "total_count": len(rows)},
    }


def _enriched_person(person_id, email, company=None, **person_overrides):
    person = {
        "person_id": person_id,
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
        "linkedin_url": "https://www.linkedin.com/in/jane-doe",
        "current_job_title": "Senior Technical Recruiter",
        "email": {"status": "VERIFIED", "revealed": True, "email": email} if email else {"status": "UNAVAILABLE", "revealed": False},
    }
    person.update(person_overrides)
    return {
        "person": person,
        "company": company or dict(MICROSOFT),
    }


def _enrich_response(matched=None, not_matched=None, invalid=None):
    return {
        "error": False,
        "matched": matched or [],
        "not_matched": not_matched or [],
        "invalid_datapoints": invalid or [],
    }


def _website(**overrides) -> FinanceContact:
    data = dict(
        full_name="Web Person",
        first_name="Web",
        last_name="Person",
        title="Technical Recruiter",
        company_name="Microsoft",
        company_domain="microsoft.com",
        provider="company_website",
        source="website",
    )
    data.update(overrides)
    return FinanceContact(**data)


def _orch(people_provider, website=None, email=None, db=None, persist=False):
    website_service = website or MagicMock()
    if website is None:
        website_service.discover_contacts.return_value = []
    return ContactDiscoveryOrchestrator(
        people_provider=people_provider,
        website_service=website_service,
        email_service=email or EmailDiscoveryService(),
        db=db,
        persist=persist,
        prospeo_configured=True,
    )


# -----------------------------------------------------------------------------
# TEST 1 — API key
# -----------------------------------------------------------------------------

def test_missing_api_key_raises_not_configured():
    with pytest.raises(ProspeoNotConfiguredError):
        ProspeoPeopleProvider(api_key="")
    with pytest.raises(ProspeoNotConfiguredError):
        ProspeoPeopleProvider(api_key="   ")


def test_provider_initializes_with_key():
    provider = ProspeoPeopleProvider(api_key="test-key", timeout_seconds=5)
    assert bool(provider.api_key) is True
    assert str(provider.api_key) != ""


# -----------------------------------------------------------------------------
# TEST 2 — Search request
# -----------------------------------------------------------------------------

def test_search_request_mapping():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A)),
        _json_response(_enrich_response(matched=[{
            "identifier": "contact-0",
            **_enriched_person("abc123", "jane.doe@microsoft.com"),
        }])),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=True,
    )
    assert contacts

    method, url = session.request.call_args_list[0][0][:2]
    kwargs = session.request.call_args_list[0][1]
    assert method == "POST"
    assert url == "https://api.prospeo.io/search-person"
    body = kwargs["json"]
    assert body["page"] == 1
    assert body["filters"]["company"]["websites"]["include"] == ["microsoft.com"]
    assert body["filters"]["person_job_title"]["include"] == ["Technical Recruiter"]
    assert body["filters"]["person_job_title"]["match_mode"] == "CONTAINS"
    assert kwargs["headers"]["X-KEY"] == "test-key"
    assert kwargs["headers"]["Content-Type"] == "application/json"


def test_max_results_five_does_not_request_extra_pages():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A)),
        _json_response(_enrich_response(matched=[{
            "identifier": "contact-0",
            **_enriched_person("abc123", "jane.doe@microsoft.com"),
        }])),
    ]
    _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
    )
    search_calls = [c for c in session.request.call_args_list if c[0][1].endswith("/search-person")]
    assert len(search_calls) == 1


# -----------------------------------------------------------------------------
# TEST 3 — Search result mapping
# -----------------------------------------------------------------------------

def test_search_result_mapping():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A)),
        _json_response(_enrich_response(matched=[{
            "identifier": "contact-0",
            **_enriched_person("abc123", "jane.doe@microsoft.com"),
        }])),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
    )
    assert len(contacts) == 1
    contact = contacts[0]
    assert contact.provider_id == "abc123"
    assert contact.provider == "prospeo"
    assert (getattr(contact.source, "value", None) or contact.source) == "prospeo"
    assert contact.full_name == "Jane Doe"
    assert contact.first_name == "Jane"
    assert contact.last_name == "Doe"
    assert contact.title == "Senior Technical Recruiter"
    assert contact.company_name == "Microsoft"
    assert contact.company_domain == "microsoft.com"
    assert contact.linkedin_url == "https://www.linkedin.com/in/jane-doe"
    assert contact.enrichment_data["organization_primary_domain"] == "microsoft.com"


# -----------------------------------------------------------------------------
# TEST 4 — Employer validation
# -----------------------------------------------------------------------------

def test_google_employer_excluded_www_microsoft_included():
    google_person = {
        "person": {
            "person_id": "google-1",
            "first_name": "Former",
            "last_name": "Employee",
            "full_name": "Former Employee",
            "current_job_title": "Technical Recruiter",
        },
        "company": {"name": "Google", "website": "https://google.com", "domain": "google.com"},
    }
    www_person = {
        "person": {
            "person_id": "ms-1",
            "first_name": "Current",
            "last_name": "Hire",
            "full_name": "Current Hire",
            "current_job_title": "Technical Recruiter",
        },
        "company": {"name": "Microsoft", "website": "https://www.microsoft.com", "domain": "www.microsoft.com"},
    }
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(google_person, www_person)),
        _json_response(_enrich_response(matched=[{
            "identifier": "contact-0",
            **_enriched_person(
                "ms-1",
                "current.hire@microsoft.com",
                company={"name": "Microsoft", "website": "https://www.microsoft.com", "domain": "www.microsoft.com"},
                first_name="Current",
                last_name="Hire",
                full_name="Current Hire",
                current_job_title="Technical Recruiter",
                linkedin_url=None,
            ),
        }])),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
    )
    names = [c.full_name for c in contacts]
    assert "Former Employee" not in names
    assert "Current Hire" in names

    website = MagicMock()
    website.discover_contacts.return_value = []
    orch = _orch(MagicMock(search_people=MagicMock(return_value=[
        FinanceContact(
            full_name="Former Employee",
            title="Technical Recruiter",
            company_name="Microsoft",
            company_domain="microsoft.com",
            provider="prospeo",
            provider_id="google-1",
            source="prospeo",
            enrichment_data={"organization_primary_domain": "google.com"},
        ),
        FinanceContact(
            full_name="Current Hire",
            title="Technical Recruiter",
            company_name="Microsoft",
            company_domain="microsoft.com",
            provider="prospeo",
            provider_id="ms-1",
            source="prospeo",
            enrichment_data={"organization_primary_domain": "www.microsoft.com"},
        ),
    ])), website=website)
    outcome = orch.discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=False,
    )
    assert [c.full_name for c in outcome.contacts] == ["Current Hire"]


# -----------------------------------------------------------------------------
# TEST 5 — Title validation
# -----------------------------------------------------------------------------

def test_title_senior_kept_account_executive_dropped():
    ae = {
        "person": {
            "person_id": "ae-1",
            "first_name": "Sales",
            "last_name": "Person",
            "full_name": "Sales Person",
            "current_job_title": "Account Executive",
        },
        "company": dict(MICROSOFT),
    }
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A, ae)),
        _json_response(_enrich_response(matched=[{
            "identifier": "contact-0",
            **_enriched_person("abc123", "jane.doe@microsoft.com"),
        }])),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
    )
    names = [c.full_name for c in contacts]
    assert "Jane Doe" in names
    assert "Sales Person" not in names


# -----------------------------------------------------------------------------
# TEST 6 — Bulk enrich body
# -----------------------------------------------------------------------------

def test_bulk_enrich_body_uses_verified_email_and_unique_ids():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A, SEARCH_PERSON_B)),
        _json_response(_enrich_response(matched=[
            {"identifier": "contact-0", **_enriched_person("abc123", "jane.doe@microsoft.com")},
            {
                "identifier": "contact-1",
                **_enriched_person(
                    "def456",
                    "john.smith@microsoft.com",
                    first_name="John",
                    last_name="Smith",
                    full_name="John Smith",
                    current_job_title="Technical Recruiter",
                    linkedin_url="https://www.linkedin.com/in/john-smith",
                ),
            },
        ])),
    ]
    _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=True,
    )
    method, url = session.request.call_args_list[1][0][:2]
    kwargs = session.request.call_args_list[1][1]
    assert method == "POST"
    assert url == "https://api.prospeo.io/bulk-enrich-person"
    body = kwargs["json"]
    assert body["only_verified_email"] is True
    assert body["enrich_mobile"] is False
    identifiers = [row["identifier"] for row in body["data"]]
    person_ids = [row["person_id"] for row in body["data"]]
    assert identifiers == ["contact-0", "contact-1"]
    assert person_ids == ["abc123", "def456"]
    assert len(set(identifiers)) == 2


# -----------------------------------------------------------------------------
# TEST 7 — Verified email skips pattern fallback
# -----------------------------------------------------------------------------

def test_verified_email_skips_pattern_fallback():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A)),
        _json_response(_enrich_response(matched=[{
            "identifier": "contact-0",
            **_enriched_person("abc123", "jane.doe@microsoft.com"),
        }])),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
    )
    assert contacts[0].email == "jane.doe@microsoft.com"
    assert contacts[0].email_status == "verified"
    assert contacts[0].email_source == "prospeo"

    email_service = MagicMock()
    website = MagicMock()
    website.discover_contacts.return_value = []
    people = MagicMock()
    people.search_people.return_value = contacts
    outcome = _orch(people, website=website, email=email_service).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=1,
        find_emails=True,
    )
    email_service.discover_email.assert_not_called()
    assert outcome.contacts[0].email_status == "verified"
    assert outcome.contacts[0].email_source == "prospeo"


# -----------------------------------------------------------------------------
# TEST 8 — not_matched keeps person and allows pattern fallback
# -----------------------------------------------------------------------------

def test_not_matched_keeps_person_and_allows_pattern():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A)),
        _json_response(_enrich_response(not_matched=["contact-0"])),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=True,
    )
    assert len(contacts) == 1
    assert contacts[0].full_name == "Jane Doe"
    assert contacts[0].email is None
    assert contacts[0].email_status == "not_found"
    assert contacts[0].provider == "prospeo"

    website = MagicMock()
    website.discover_contacts.return_value = []
    people = MagicMock()
    people.search_people.return_value = contacts
    outcome = _orch(people, website=website, email=EmailDiscoveryService()).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=1,
        find_emails=True,
    )
    contact = outcome.contacts[0]
    assert contact.provider == "prospeo"
    assert contact.email == "jane.doe@microsoft.com"
    assert contact.email_status == "pattern_guess"
    assert contact.email_source == "pattern_guess"


# -----------------------------------------------------------------------------
# TEST 9 — find_emails false
# -----------------------------------------------------------------------------

def test_find_emails_false_skips_bulk_enrich():
    session = MagicMock()
    session.request.side_effect = [
        _json_response(_search_success(SEARCH_PERSON_A)),
    ]
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=False,
    )
    assert len(contacts) == 1
    assert contacts[0].email is None
    assert contacts[0].email_status == "not_found"
    assert contacts[0].email_source == "none"
    assert contacts[0].linkedin_url
    urls = [c[0][1] for c in session.request.call_args_list]
    assert any(url.endswith("/search-person") for url in urls)
    assert not any(url.endswith("/bulk-enrich-person") for url in urls)


# -----------------------------------------------------------------------------
# TEST 10 — error handling
# -----------------------------------------------------------------------------

def test_invalid_api_key_raises_authentication():
    session = MagicMock()
    session.request.return_value = _error_response("INVALID_API_KEY")
    with pytest.raises(ProspeoAuthenticationError):
        _provider(session).search_people(
            company_name="Microsoft",
            company_domain="microsoft.com",
            target_titles=["Technical Recruiter"],
            max_results=5,
            find_emails=False,
        )


def test_insufficient_credits_raises():
    session = MagicMock()
    session.request.return_value = _error_response("INSUFFICIENT_CREDITS")
    with pytest.raises(ProspeoInsufficientCreditsError):
        _provider(session).search_people(
            company_name="Microsoft",
            company_domain="microsoft.com",
            target_titles=["Technical Recruiter"],
            max_results=5,
            find_emails=False,
        )


def test_plan_required_raises():
    session = MagicMock()
    session.request.return_value = _error_response("PLAN_REQUIRED")
    with pytest.raises(ProspeoPlanRequiredError):
        _provider(session).search_people(
            company_name="Microsoft",
            company_domain="microsoft.com",
            target_titles=["Technical Recruiter"],
            max_results=5,
            find_emails=False,
        )


def test_no_results_returns_empty_list():
    session = MagicMock()
    session.request.return_value = _error_response("NO_RESULTS")
    contacts = _provider(session).search_people(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=False,
    )
    assert contacts == []


def test_http_429_raises_rate_limit():
    session = MagicMock()
    session.request.return_value = _json_response({"error": True, "error_code": "Rate limit exceeded"}, status=429)
    with pytest.raises(ProspeoRateLimitError):
        _provider(session).search_people(
            company_name="Microsoft",
            company_domain="microsoft.com",
            target_titles=["Technical Recruiter"],
            max_results=5,
            find_emails=False,
        )


def test_timeout_raises_api_error():
    session = MagicMock()
    session.request.side_effect = requests.Timeout("timed out")
    with pytest.raises(ProspeoAPIError, match="timed out"):
        _provider(session).search_people(
            company_name="Microsoft",
            company_domain="microsoft.com",
            target_titles=["Technical Recruiter"],
            max_results=5,
            find_emails=False,
        )


def test_http_5xx_raises_api_error():
    session = MagicMock()
    session.request.return_value = _json_response({"error": True, "error_code": "INTERNAL_ERROR"}, status=500)
    with pytest.raises(ProspeoAPIError):
        _provider(session).search_people(
            company_name="Microsoft",
            company_domain="microsoft.com",
            target_titles=["Technical Recruiter"],
            max_results=5,
            find_emails=False,
        )


# -----------------------------------------------------------------------------
# TEST 11 — Prospeo failure → website, no Apollo
# -----------------------------------------------------------------------------

def test_prospeo_failure_runs_website_no_apollo():
    people = MagicMock()
    people.search_people.side_effect = ProspeoAuthenticationError("bad key")
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _orch(people, website=website).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=True,
    )
    website.discover_contacts.assert_called()
    assert outcome.contacts[0].provider == "company_website"
    assert any("authentication failed" in w.lower() for w in outcome.warnings)
    assert not any("no contacts matching" in w.lower() for w in outcome.warnings)
    assert not any("apollo" in w.lower() for w in outcome.warnings)
    assert "apollo" not in [c.provider for c in outcome.contacts]


# -----------------------------------------------------------------------------
# TEST 12 — Prospeo zero → website
# -----------------------------------------------------------------------------

def test_prospeo_zero_runs_website_with_zero_warning():
    people = MagicMock()
    people.search_people.return_value = []
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _orch(people, website=website).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=5,
        find_emails=True,
    )
    website.discover_contacts.assert_called()
    assert any("no contacts matching" in w.lower() for w in outcome.warnings)
    assert any("company website fallback" in w.lower() for w in outcome.warnings)


# -----------------------------------------------------------------------------
# TEST 13 — Partial fill
# -----------------------------------------------------------------------------

def test_partial_fill_keeps_prospeo_and_caps_at_max():
    people = MagicMock()
    people.search_people.return_value = [
        FinanceContact(
            full_name=f"Prospeo {i}",
            first_name="Prospeo",
            last_name=str(i),
            title="Technical Recruiter",
            company_name="Microsoft",
            company_domain="microsoft.com",
            provider="prospeo",
            provider_id=f"p{i}",
            source="prospeo",
            enrichment_data={"organization_primary_domain": "microsoft.com"},
        )
        for i in range(6)
    ]
    website = MagicMock()
    website.discover_contacts.return_value = [
        _website(full_name=f"Web {i}") for i in range(7)
    ]
    outcome = _orch(people, website=website).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=10,
        find_emails=False,
    )
    assert len(outcome.contacts) <= 10
    assert len(outcome.contacts) == 10
    assert sum(1 for c in outcome.contacts if c.provider == "prospeo") == 6
    assert sum(1 for c in outcome.contacts if c.provider == "company_website") == 4


# -----------------------------------------------------------------------------
# TEST 14 — Dedupe prefers Prospeo
# -----------------------------------------------------------------------------

def test_dedupe_prefers_prospeo_over_website_pattern():
    people = MagicMock()
    people.search_people.return_value = [
        FinanceContact(
            full_name="Jane Doe",
            first_name="Jane",
            last_name="Doe",
            title="Technical Recruiter",
            company_name="Microsoft",
            company_domain="microsoft.com",
            email="jane@microsoft.com",
            email_status="verified",
            email_source="prospeo",
            linkedin_url="https://www.linkedin.com/in/jane",
            provider="prospeo",
            provider_id="xyz",
            source="prospeo",
            enrichment_data={"organization_primary_domain": "microsoft.com"},
        )
    ]
    website = MagicMock()
    website.discover_contacts.return_value = [
        _website(
            full_name="Jane Doe",
            first_name="Jane",
            last_name="Doe",
            title="Technical Recruiter",
            email="jane.doe@microsoft.com",
            email_status="pattern_guess",
            email_source="pattern_guess",
            linkedin_url=None,
        )
    ]
    outcome = _orch(people, website=website).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=10,
        find_emails=True,
    )
    janes = [c for c in outcome.contacts if c.full_name == "Jane Doe"]
    assert len(janes) == 1
    assert janes[0].provider == "prospeo"
    assert janes[0].email_status == "verified"
    assert janes[0].linkedin_url
    assert janes[0].provider_id == "xyz"


# -----------------------------------------------------------------------------
# TEST 15 — Upsert upgrade
# -----------------------------------------------------------------------------

def test_upsert_upgrades_website_pattern_to_prospeo(tmp_path):
    db = LeadDatabase(str(tmp_path / "leads.db"))
    db.initialize()
    existing = _website(
        full_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        title="Technical Recruiter",
        email="jane.doe@microsoft.com",
        email_status="pattern_guess",
        linkedin_url=None,
        provider="company_website",
    )
    assert db.insert_contact(existing) is True

    people = MagicMock()
    people.search_people.return_value = [
        FinanceContact(
            full_name="Jane Doe",
            first_name="Jane",
            last_name="Doe",
            title="Technical Recruiter",
            company_name="Microsoft",
            company_domain="microsoft.com",
            email="jane@microsoft.com",
            email_status="verified",
            email_source="prospeo",
            linkedin_url="https://www.linkedin.com/in/jane-doe",
            provider="prospeo",
            provider_id="xyz",
            source="prospeo",
            enrichment_data={"organization_primary_domain": "microsoft.com"},
        )
    ]
    website = MagicMock()
    website.discover_contacts.return_value = []
    _orch(people, website=website, db=db, persist=True).discover(
        company_name="Microsoft",
        company_domain="microsoft.com",
        target_titles=["Technical Recruiter"],
        max_results=1,
        find_emails=True,
    )
    stored = db.get_contacts(company_name="Microsoft")
    assert stored["total"] == 1
    row = stored["contacts"][0]
    assert row["email"] == "jane@microsoft.com"
    assert row["email_status"] == "verified"
    assert row["provider"] == "prospeo"
    assert row["provider_id"] == "xyz"
    assert row["linkedin_url"]
