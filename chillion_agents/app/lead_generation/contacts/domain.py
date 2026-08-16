"""Trusted domain normalization and comparison."""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
import re

ORIGIN_USER = "user"
ORIGIN_DUMMY = "dummy"
ORIGIN_NONE = "none"

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_domain(value: Optional[str]) -> Optional[str]:
    """
    Normalize a hostname or URL to a bare domain.

    https://www.microsoft.com/ → microsoft.com
    Does not invent {company}.com from a company name.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or parsed.netloc or "").strip().lower()
    if not host:
        host = str(value).strip().lower()
        host = re.sub(r"^https?://", "", host)
        host = host.split("/")[0]
        host = host.split("?")[0]
        host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    host = host.strip(".")
    return host or None


def is_valid_domain(value: Optional[str]) -> bool:
    """Reject company names and other clearly malformed hostnames."""
    domain = normalize_domain(value)
    if not domain or "." not in domain or " " in domain:
        return False
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    tld = labels[-1]
    if not tld.isalpha() or len(tld) < 2:
        return False
    return all(_LABEL.fullmatch(label) for label in labels)


def domains_match(left: Optional[str], right: Optional[str]) -> bool:
    """
    Compare employer domains.

    microsoft.com, www.microsoft.com, https://microsoft.com are equivalent.
    careers.microsoft.com matches microsoft.com.
    notmicrosoft.com does not match microsoft.com.
    """
    a = normalize_domain(left)
    b = normalize_domain(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return a.endswith("." + b) or b.endswith("." + a)


@dataclass(frozen=True)
class TrustedDomain:
    domain: Optional[str]
    origin: str = ORIGIN_NONE
    website: Optional[str] = None

    @property
    def is_trusted(self) -> bool:
        return self.origin == ORIGIN_USER and bool(self.domain)


def resolve_trusted_domain(
    company_domain: Optional[str] = None,
    company_website: Optional[str] = None,
) -> TrustedDomain:
    """
    Only user-supplied domain/website values are trusted.

    DummySearchProvider guesses such as companyname.com must never be passed in here.
    """
    if is_valid_domain(company_domain):
        domain = normalize_domain(company_domain)
        website = company_website.strip() if company_website and str(company_website).strip() else None
        if not website:
            website = f"https://www.{domain}"
        return TrustedDomain(domain=domain, origin=ORIGIN_USER, website=website)

    if company_website and is_valid_domain(company_website):
        domain = normalize_domain(company_website)
        website = str(company_website).strip()
        if "://" not in website:
            website = f"https://{website}"
        return TrustedDomain(domain=domain, origin=ORIGIN_USER, website=website)

    if company_domain or company_website:
        return TrustedDomain(domain=None, origin=ORIGIN_NONE, website=None)

    return TrustedDomain(domain=None, origin=ORIGIN_NONE, website=None)


def normalize_linkedin_url(value: Optional[str]) -> Optional[str]:
    """String-only LinkedIn URL normalize for dedupe. Does not fetch."""
    if not value:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    raw = re.sub(r"^https?://", "", raw)
    raw = re.sub(r"^www\.", "", raw)
    raw = raw.split("?")[0].split("#")[0].rstrip("/")
    return raw or None
