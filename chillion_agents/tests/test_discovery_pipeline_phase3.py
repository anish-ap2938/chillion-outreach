"""Phase 3 contact discovery pipeline — mocked providers only."""

from unittest.mock import MagicMock

from app.lead_generation.contacts.domain import domains_match, normalize_domain, resolve_trusted_domain
from app.lead_generation.contacts.email import EmailDiscoveryService
from app.lead_generation.contacts.orchestrator import ContactDiscoveryOrchestrator
from app.lead_generation.models import FinanceContact
from app.lead_generation.providers.errors import (
    ProspeoAPIError,
    ProspeoAuthenticationError,
    ProspeoRateLimitError,
)
from app.lead_generation.storage.database import LeadDatabase


def _prospeo(**overrides) -> FinanceContact:
    data = dict(
        full_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        title="Senior IT Director",
        company_name="Microsoft",
        company_domain="microsoft.com",
        provider="prospeo",
        provider_id="person_1",
        source="prospeo",
        linkedin_url="https://www.linkedin.com/in/jane-doe/",
        enrichment_data={"organization_primary_domain": "microsoft.com"},
    )
    data.update(overrides)
    return FinanceContact(**data)


def _website(**overrides) -> FinanceContact:
    data = dict(
        full_name="Web Person",
        first_name="Web",
        last_name="Person",
        title="IT Director",
        company_name="Microsoft",
        company_domain="microsoft.com",
        provider="company_website",
        source="website",
    )
    data.update(overrides)
    return FinanceContact(**data)


def _orch(provider, website=None, email=None, db=None, persist=False, prospeo_configured=True):
    website_service = website or MagicMock()
    if website is None:
        website_service.discover_contacts.return_value = []
    return ContactDiscoveryOrchestrator(
        people_provider=provider,
        website_service=website_service,
        email_service=email or EmailDiscoveryService(),
        db=db,
        persist=persist,
        prospeo_configured=prospeo_configured,
    )


def _run(orch, domain="microsoft.com", titles=None, max_results=10, find_emails=True, name="Microsoft"):
    return orch.discover(
        company_name=name,
        company_domain=domain,
        company_website=None,
        target_titles=titles or ["IT Director"],
        max_results=max_results,
        find_emails=find_emails,
    )


def test_normalize_user_supplied_domains():
    assert normalize_domain("https://www.microsoft.com/") == "microsoft.com"
    assert normalize_domain("www.microsoft.com") == "microsoft.com"
    assert normalize_domain("microsoft.com/") == "microsoft.com"


def test_does_not_invent_domain_from_company_name():
    trusted = resolve_trusted_domain(None, None)
    assert trusted.is_trusted is False
    assert trusted.domain is None


def test_domains_match_www_and_reject_lookalike():
    assert domains_match("www.microsoft.com", "microsoft.com") is True
    assert domains_match("https://microsoft.com", "microsoft.com") is True
    assert domains_match("careers.microsoft.com", "microsoft.com") is True
    assert domains_match("notmicrosoft.com", "microsoft.com") is False


def test_former_employee_at_google_is_excluded():
    provider = MagicMock()
    provider.search_people.return_value = [
        _prospeo(enrichment_data={"organization_primary_domain": "google.com"})
    ]
    website = MagicMock()
    website.discover_contacts.return_value = []
    outcome = _run(_orch(provider, website=website))
    assert all(c.full_name != "Jane Doe" for c in outcome.contacts)
    website.discover_contacts.assert_called()


def test_current_microsoft_employee_is_included():
    provider = MagicMock()
    provider.search_people.return_value = [_prospeo()]
    outcome = _run(_orch(provider), max_results=1)
    assert len(outcome.contacts) == 1
    assert outcome.contacts[0].full_name == "Jane Doe"


def test_www_primary_domain_matches_requested_domain():
    provider = MagicMock()
    provider.search_people.return_value = [
        _prospeo(enrichment_data={"organization_primary_domain": "www.microsoft.com"})
    ]
    outcome = _run(_orch(provider), max_results=1)
    assert len(outcome.contacts) == 1


def test_current_title_senior_it_director_included():
    provider = MagicMock()
    provider.search_people.return_value = [_prospeo(title="Senior IT Director")]
    outcome = _run(_orch(provider), titles=["IT Director"], max_results=1)
    assert len(outcome.contacts) == 1


def test_current_title_vp_sales_excluded():
    provider = MagicMock()
    provider.search_people.return_value = [_prospeo(title="VP Sales")]
    website = MagicMock()
    website.discover_contacts.return_value = []
    outcome = _run(_orch(provider, website=website), titles=["IT Director"])
    assert outcome.contacts == []
    website.discover_contacts.assert_called()


def test_prospeo_success_skips_website_when_full():
    provider = MagicMock()
    provider.search_people.return_value = [_prospeo(), _prospeo(full_name="John Smith", provider_id="p2")]
    website = MagicMock()
    _run(_orch(provider, website=website), max_results=2)
    website.discover_contacts.assert_not_called()


def test_prospeo_zero_runs_website_fallback():
    provider = MagicMock()
    provider.search_people.return_value = []
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _run(_orch(provider, website=website))
    assert len(outcome.contacts) == 1
    assert outcome.contacts[0].provider == "company_website"
    website.discover_contacts.assert_called()
    assert any("no contacts matching" in w.lower() for w in outcome.warnings)


def test_all_wrong_current_employer_runs_website():
    provider = MagicMock()
    provider.search_people.return_value = [
        _prospeo(enrichment_data={"organization_primary_domain": "google.com"})
    ]
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _run(_orch(provider, website=website))
    assert outcome.contacts[0].provider == "company_website"


def test_prospeo_rate_limit_falls_back_to_website():
    provider = MagicMock()
    provider.search_people.side_effect = ProspeoRateLimitError("rate")
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _run(_orch(provider, website=website))
    assert len(outcome.contacts) == 1
    assert any("rate limited" in w.lower() for w in outcome.warnings)
    assert not any("no contacts matching" in w.lower() for w in outcome.warnings)


def test_prospeo_auth_failure_falls_back_to_website():
    provider = MagicMock()
    provider.search_people.side_effect = ProspeoAuthenticationError("nope", status_code=400)
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _run(_orch(provider, website=website))
    assert len(outcome.contacts) == 1
    assert any("authentication" in w.lower() for w in outcome.warnings)
    assert not any("no contacts matching" in w.lower() for w in outcome.warnings)


def test_prospeo_timeout_falls_back_to_website():
    provider = MagicMock()
    provider.search_people.side_effect = ProspeoAPIError("Prospeo request timed out")
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    outcome = _run(_orch(provider, website=website))
    assert len(outcome.contacts) == 1
    assert any("unavailable" in w.lower() for w in outcome.warnings)
    assert not any("no contacts matching" in w.lower() for w in outcome.warnings)


def test_missing_prospeo_key_uses_website():
    website = MagicMock()
    website.discover_contacts.return_value = [_website()]
    orch = _orch(provider=None, website=website, prospeo_configured=False)
    outcome = _run(orch)
    assert len(outcome.contacts) == 1
    assert any("not configured" in w.lower() for w in outcome.warnings)
    assert not any("no contacts matching" in w.lower() for w in outcome.warnings)


def test_missing_trusted_domain_skips_prospeo():
    provider = MagicMock()
    website = MagicMock()
    website.discover_contacts.return_value = []
    orch = _orch(provider, website=website)
    outcome = _run(orch, domain=None, name="Example Fake Corp")
    provider.search_people.assert_not_called()
    website.discover_contacts.assert_called()
    assert any("trusted company domain" in w.lower() for w in outcome.warnings)


def test_partial_fill_prioritizes_prospeo():
    provider = MagicMock()
    provider.search_people.return_value = [
        _prospeo(full_name=f"Prospeo {i}", provider_id=f"a{i}", linkedin_url=None)
        for i in range(4)
    ]
    website = MagicMock()
    website.discover_contacts.return_value = [
        _website(full_name=f"Web {i}") for i in range(10)
    ]
    outcome = _run(_orch(provider, website=website), max_results=10)
    assert len(outcome.contacts) == 10
    assert sum(1 for c in outcome.contacts if (c.provider or "") == "prospeo") == 4


def test_cross_provider_duplicate_prefers_prospeo():
    provider = MagicMock()
    provider.search_people.return_value = [_prospeo()]
    website = MagicMock()
    website.discover_contacts.return_value = [
        _website(full_name="Jane Doe", title="IT Director", linkedin_url=None)
    ]
    outcome = _run(_orch(provider, website=website), max_results=10)
    janes = [c for c in outcome.contacts if c.full_name == "Jane Doe"]
    assert len(janes) == 1
    assert janes[0].provider == "prospeo"
    assert janes[0].linkedin_url


def test_prospeo_missing_email_uses_pattern_guess():
    provider = MagicMock()
    provider.search_people.return_value = [_prospeo(email=None, email_status="not_found")]
    outcome = _run(_orch(provider, email=EmailDiscoveryService()), max_results=1)
    contact = outcome.contacts[0]
    assert contact.provider == "prospeo"
    assert contact.email == "jane.doe@microsoft.com"
    assert contact.email_status == "pattern_guess"
    assert contact.email_source == "pattern_guess"


def test_verified_prospeo_email_not_replaced_by_pattern():
    email_service = MagicMock()
    provider = MagicMock()
    provider.search_people.return_value = [
        _prospeo(email="jane@microsoft.com", email_status="verified", email_source="prospeo")
    ]
    outcome = _run(_orch(provider, email=email_service), max_results=1)
    email_service.discover_email.assert_not_called()
    assert outcome.contacts[0].email == "jane@microsoft.com"
    assert outcome.contacts[0].email_status == "verified"


def test_find_emails_false_strips_prospeo_email():
    email_service = MagicMock()
    provider = MagicMock()
    provider.search_people.return_value = [
        _prospeo(email="jane@microsoft.com", email_status="verified")
    ]
    outcome = _run(_orch(provider, email=email_service), max_results=1, find_emails=False)
    email_service.discover_email.assert_not_called()
    assert outcome.contacts[0].email is None
    assert outcome.contacts[0].email_status == "not_found"


def test_dummy_domain_not_used_for_prospeo_or_pattern():
    provider = MagicMock()
    email_service = MagicMock()
    website = MagicMock()
    website.discover_contacts.return_value = [
        _website(full_name="Pat Fake", first_name="Pat", last_name="Fake", company_domain=None)
    ]
    orch = _orch(provider, website=website, email=email_service)
    outcome = _run(orch, domain=None, name="Example Fake Corp")
    provider.search_people.assert_not_called()
    email_service.discover_email.assert_not_called()
    assert outcome.contacts[0].email is None
    assert outcome.contacts[0].email_status == "not_found"
    company = website.discover_contacts.call_args.args[0]
    assert company.domain is None


def test_upsert_upgrades_pattern_guess_to_verified_prospeo(tmp_path):
    db = LeadDatabase(str(tmp_path / "leads.db"))
    db.initialize()
    existing = _website(
        full_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@microsoft.com",
        email_status="pattern_guess",
        linkedin_url=None,
        provider="company_website",
    )
    assert db.insert_contact(existing) is True

    incoming = _prospeo(
        email="jane@microsoft.com",
        email_status="verified",
        email_source="prospeo",
        linkedin_url="https://www.linkedin.com/in/jane-doe",
        provider_id="abc123",
    )
    website = MagicMock()
    website.discover_contacts.return_value = []
    provider = MagicMock()
    provider.search_people.return_value = [incoming]
    _run(_orch(provider, website=website, db=db, persist=True), max_results=1)

    stored = db.get_contacts(company_name="Microsoft")
    assert stored["total"] == 1
    row = stored["contacts"][0]
    assert row["email"] == "jane@microsoft.com"
    assert row["email_status"] == "verified"
    assert row["linkedin_url"]
    assert row["provider"] == "prospeo"
    assert row["provider_id"] == "abc123"


def test_find_emails_false_does_not_destroy_stored_verified_email(tmp_path):
    db = LeadDatabase(str(tmp_path / "leads.db"))
    db.initialize()
    existing = _prospeo(
        email="jane@microsoft.com",
        email_status="verified",
        email_source="prospeo",
    )
    assert db.insert_contact(existing) is True

    provider = MagicMock()
    provider.search_people.return_value = [_prospeo(email="secret@microsoft.com", email_status="verified")]
    outcome = _run(
        _orch(provider, db=db, persist=True),
        max_results=1,
        find_emails=False,
    )
    assert outcome.contacts[0].email is None

    stored = db.get_contacts(company_name="Microsoft")["contacts"][0]
    assert stored["email"] == "jane@microsoft.com"
    assert stored["email_status"] == "verified"
