"""Phase 1 contact search contracts: validation, title matching, email status."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.lead_generation.contacts.discovery import ContactDiscoveryService
from app.lead_generation.contacts.email import EmailDiscoveryService
from app.lead_generation.models import Company, FinanceContact


def _load_lead_gen_routes():
    """Load the route module without importing app.api.routes.__init__ (pulls chroma/RAG)."""
    path = Path(__file__).resolve().parents[1] / "app" / "api" / "routes" / "lead_generation.py"
    spec = importlib.util.spec_from_file_location("lead_generation_routes_phase1", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_routes = _load_lead_gen_routes()
ContactSearchRequest = _routes.ContactSearchRequest
router = _routes.router


LEADERSHIP_HTML = """
<html>
  <body>
    <div class="team-member">
      <h3>Jane Doe</h3>
      <p class="title">Senior IT Director</p>
    </div>
    <div class="team-member">
      <h3>John Smith</h3>
      <p class="title">Head of IT Infrastructure</p>
    </div>
    <div class="team-member">
      <h3>Alice Brown</h3>
      <p class="title">Chief Financial Officer</p>
    </div>
    <div class="team-member">
      <h3>Bob Lee</h3>
      <p class="title">Security Director</p>
    </div>
  </body>
</html>
"""


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/lead-gen")
    return TestClient(app)


def _contact(**overrides) -> FinanceContact:
    data = dict(
        full_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        title="IT Director",
        company_name="Microsoft",
        company_domain="microsoft.com",
        provider="company_website",
    )
    data.update(overrides)
    return FinanceContact(**data)


# ---------------------------------------------------------------------------
# A. Request validation
# ---------------------------------------------------------------------------

def test_valid_contact_search_request():
    req = ContactSearchRequest(
        company_name="Microsoft",
        target_titles=["Head of IT"],
        max_results=10,
    )
    assert req.company_name == "Microsoft"
    assert req.target_titles == ["Head of IT"]
    assert req.max_results == 10
    assert req.find_emails is True


def test_company_name_is_trimmed():
    req = ContactSearchRequest(company_name="  Microsoft  ", target_titles=["IT Director"])
    assert req.company_name == "Microsoft"


def test_blank_company_name_rejected():
    with pytest.raises(ValidationError):
        ContactSearchRequest(company_name="   ", target_titles=["IT Director"])


def test_empty_target_titles_rejected():
    with pytest.raises(ValidationError):
        ContactSearchRequest(company_name="Microsoft", target_titles=[])


def test_whitespace_only_target_titles_rejected():
    with pytest.raises(ValidationError):
        ContactSearchRequest(company_name="Microsoft", target_titles=["", "   "])


def test_duplicate_target_titles_normalized():
    req = ContactSearchRequest(
        company_name="Microsoft",
        target_titles=["IT Director", "it director", "  Head of IT  "],
    )
    assert req.target_titles == ["IT Director", "Head of IT"]


def test_omitted_target_titles_allowed_for_back_compat():
    req = ContactSearchRequest(company_name="Microsoft")
    assert req.target_titles is None


def test_max_results_zero_rejected():
    with pytest.raises(ValidationError):
        ContactSearchRequest(company_name="Microsoft", target_titles=["IT Director"], max_results=0)


def test_max_results_over_fifty_rejected():
    with pytest.raises(ValidationError):
        ContactSearchRequest(company_name="Microsoft", target_titles=["IT Director"], max_results=51)


def test_api_rejects_empty_target_titles_with_422():
    client = _client()
    response = client.post(
        "/api/v1/lead-gen/contacts/discover",
        json={"company_name": "Microsoft", "target_titles": []},
    )
    assert response.status_code == 422


def test_api_rejects_max_results_out_of_range():
    client = _client()
    low = client.post(
        "/api/v1/lead-gen/contacts/discover",
        json={"company_name": "Microsoft", "target_titles": ["IT Director"], "max_results": 0},
    )
    high = client.post(
        "/api/v1/lead-gen/contacts/discover",
        json={"company_name": "Microsoft", "target_titles": ["IT Director"], "max_results": 51},
    )
    assert low.status_code == 422
    assert high.status_code == 422


# ---------------------------------------------------------------------------
# B. Title matching
# ---------------------------------------------------------------------------

def test_title_matching_senior_it_director():
    service = ContactDiscoveryService()
    assert service._matches_target_title("Senior IT Director", ["IT Director"]) is True


def test_title_matching_head_of_it_infrastructure():
    service = ContactDiscoveryService()
    assert service._matches_target_title("Head of IT Infrastructure", ["Head of IT"]) is True


def test_title_matching_security_director_does_not_match_cfo():
    service = ContactDiscoveryService()
    assert service._matches_target_title("Chief Financial Officer", ["Security Director"]) is False


# ---------------------------------------------------------------------------
# C / F. Max results + mocked website discovery
# ---------------------------------------------------------------------------

def _mock_leadership_get(html: str):
    response = MagicMock()
    response.status_code = 200
    response.text = html
    response.raise_for_status = MagicMock()
    return response


@patch("app.lead_generation.contacts.discovery.time.sleep", return_value=None)
def test_website_discovery_filters_titles_and_respects_max_results(_sleep):
    service = ContactDiscoveryService()
    service._find_leadership_pages = MagicMock(return_value=["https://microsoft.com/leadership"])
    service.session.get = MagicMock(return_value=_mock_leadership_get(LEADERSHIP_HTML))

    company = Company(name="Microsoft", domain="microsoft.com", website="https://microsoft.com")
    contacts = service.discover_contacts(
        company,
        target_titles=["IT Director", "Head of IT"],
        max_results=10,
    )

    titles = {c.title for c in contacts}
    assert "Senior IT Director" in titles
    assert "Head of IT Infrastructure" in titles
    assert "Chief Financial Officer" not in titles
    assert all(c.provider == "company_website" for c in contacts)
    assert len(contacts) <= 10


@patch("app.lead_generation.contacts.discovery.time.sleep", return_value=None)
def test_max_results_applied_after_dedup(_sleep):
    members = "\n".join(
        f'<div class="team-member"><h3>Alex {chr(65 + i)} Lastname</h3><p class="title">IT Director</p></div>'
        for i in range(15)
    )
    html = f"<html><body>{members}</body></html>"

    service = ContactDiscoveryService()
    service._find_leadership_pages = MagicMock(return_value=["https://microsoft.com/leadership"])
    service.session.get = MagicMock(return_value=_mock_leadership_get(html))

    company = Company(name="Microsoft", domain="microsoft.com", website="https://microsoft.com")
    contacts = service.discover_contacts(
        company,
        target_titles=["IT Director"],
        max_results=5,
    )
    assert len(contacts) == 5
    assert all("IT Director" in c.title for c in contacts)


# ---------------------------------------------------------------------------
# D. find_emails false skips EmailDiscoveryService
# ---------------------------------------------------------------------------

@patch.object(_routes, "db")
@patch.object(_routes, "ContactDiscoveryOrchestrator")
def test_find_emails_false_does_not_run_email_discovery(mock_orch_cls, mock_db):
    contact = _contact(email=None, email_status="not_found")
    outcome = MagicMock()
    outcome.contacts = [contact]
    outcome.warnings = []
    mock_orch_cls.return_value.discover.return_value = outcome

    client = _client()
    response = client.post(
        "/api/v1/lead-gen/contacts/discover",
        json={
            "company_name": "Microsoft",
            "company_domain": "microsoft.com",
            "target_titles": ["IT Director"],
            "max_results": 10,
            "find_emails": False,
        },
    )

    assert response.status_code == 200
    kwargs = mock_orch_cls.return_value.discover.call_args.kwargs
    assert kwargs["find_emails"] is False
    payload = response.json()
    assert payload["contacts_found"] == 1
    assert payload["contacts"][0]["email"] is None
    assert payload["contacts"][0]["email_status"] == "not_found"


@patch.object(_routes, "db")
@patch.object(_routes, "ContactDiscoveryOrchestrator")
def test_find_emails_true_runs_email_discovery(mock_orch_cls, mock_db):
    contact = _contact()
    outcome = MagicMock()
    outcome.contacts = [contact]
    outcome.warnings = []
    mock_orch_cls.return_value.discover.return_value = outcome

    client = _client()
    response = client.post(
        "/api/v1/lead-gen/contacts/discover",
        json={
            "company_name": "Microsoft",
            "company_domain": "microsoft.com",
            "target_titles": ["IT Director"],
            "find_emails": True,
        },
    )

    assert response.status_code == 200
    kwargs = mock_orch_cls.return_value.discover.call_args.kwargs
    assert kwargs["find_emails"] is True
    mock_orch_cls.return_value.discover.assert_called_once()


# ---------------------------------------------------------------------------
# E. Pattern-generated emails are pattern_guess, never verified
# ---------------------------------------------------------------------------

def test_pattern_generated_email_status_is_pattern_guess():
    contact = FinanceContact(
        full_name="John Smith",
        first_name="John",
        last_name="Smith",
        title="IT Director",
        company_name="Example",
        company_domain="example.com",
    )
    result = EmailDiscoveryService().discover_email(contact)
    assert result.email == "john.smith@example.com"
    assert result.email_status == "pattern_guess"
    assert result.email_status != "verified"
    assert result.email_confidence is not None


def test_incomplete_contact_email_status_is_not_found():
    contact = FinanceContact(
        full_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        title="IT Director",
        company_name="Example",
        company_domain=None,
    )
    result = EmailDiscoveryService().discover_email(contact)
    assert result.email is None
    assert result.email_status == "not_found"
