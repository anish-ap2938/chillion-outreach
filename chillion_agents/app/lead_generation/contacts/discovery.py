"""
Contact Discovery Module

Discovers finance decision makers from company websites and other sources.
Parses leadership pages, investor relations, and team pages.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..models import FinanceContact, Company, ContactSource
from ..config import get_config, CompanyTargetConfig
from ..providers.base import PeopleSearchProvider
from .titles import matches_target_title

logger = logging.getLogger(__name__)


class ContactDiscoveryService:
    """
    Service for discovering finance contacts from company websites.
    
    Parses leadership, about, and team pages to find:
    - CFO and finance executives
    - VP and Director level finance roles
    - AR, O2C, Treasury leads
    
    Example usage:
        service = ContactDiscoveryService()
        
        # Discover contacts from a company
        contacts = service.discover_contacts(company)
        
        # Parse a specific leadership page
        contacts = service.parse_leadership_page("https://company.com/leadership")
    """
    
    # Common leadership page paths to check
    LEADERSHIP_PATHS = [
        '/about/leadership',
        '/about/team',
        '/about/management',
        '/leadership',
        '/team',
        '/management',
        '/about-us/leadership',
        '/about-us/team',
        '/company/leadership',
        '/company/team',
        '/corporate/leadership',
        '/investor-relations/leadership',
        '/investors/leadership',
        '/our-team',
        '/executives',
    ]
    
    def __init__(
        self,
        config: Optional[CompanyTargetConfig] = None,
        people_provider: Optional[PeopleSearchProvider] = None,
    ):
        """
        Initialize the contact discovery service.
        
        Args:
            config: Company targeting configuration
            people_provider: Optional PeopleSearchProvider. When set, people
                lookup is delegated to that provider. Website scraping
                remains the default when no provider is injected.
        """
        self.config = config or get_config().company
        self.target_titles = [t.lower() for t in self.config.target_titles]
        self.people_provider = people_provider
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # HTTP session
        rate_config = get_config().rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": rate_config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.request_delay = rate_config.request_delay_seconds
        self.timeout = rate_config.request_timeout_seconds
    
    # =========================================================================
    # Main Discovery Methods
    # =========================================================================
    
    def discover_contacts(
        self,
        company: Company,
        target_titles: Optional[List[str]] = None,
        max_results: Optional[int] = None,
        find_emails: bool = True,
    ) -> List[FinanceContact]:
        """
        Discover contacts for a company.

        When a people_provider is injected, lookup is delegated to it.
        Otherwise the existing public-website scraper is used.
        """
        contacts = []
        active_titles = self._resolve_target_titles(target_titles)

        if self.people_provider:
            provider_titles = target_titles if target_titles is not None else list(self.config.target_titles)
            return self.people_provider.search_people(
                company_name=company.name,
                company_domain=company.domain,
                target_titles=provider_titles,
                max_results=max_results if max_results is not None else 10,
                find_emails=find_emails,
            )
        
        if not company.domain and not company.website:
            self.logger.warning(f"No domain/website for {company.name}, cannot discover contacts")
            return contacts
        
        base_url = company.website or f"https://www.{company.domain}"
        
        self.logger.info(f"Discovering contacts for {company.name} ({base_url})")
        
        # Find leadership pages
        leadership_urls = self._find_leadership_pages(base_url)
        
        if not leadership_urls:
            self.logger.info(f"No leadership pages found for {company.name}")
            return contacts
        
        # Parse each leadership page
        for url in leadership_urls:
            try:
                page_contacts = self.parse_leadership_page(url, company, target_titles=active_titles)
                contacts.extend(page_contacts)
                time.sleep(self.request_delay)
            except Exception as e:
                self.logger.error(f"Error parsing {url}: {e}")
        
        # Deduplicate by name, then apply the requested quota
        contacts = self._deduplicate_contacts(contacts)
        if max_results is not None:
            contacts = contacts[:max_results]
        
        self.logger.info(f"Found {len(contacts)} contacts for {company.name}")
        return contacts

    def _resolve_target_titles(self, target_titles: Optional[List[str]]) -> List[str]:
        """
        Normalize titles for a single request without mutating global config.

        None → config defaults (already lowercased on the service).
        Provided list → trimmed, de-duplicated, lowercased (may be empty).
        """
        if target_titles is None:
            return list(self.target_titles)

        seen = set()
        resolved: List[str] = []
        for title in target_titles:
            cleaned = (title or "").strip().lower()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            resolved.append(cleaned)
        return resolved
    
    def _find_leadership_pages(self, base_url: str) -> List[str]:
        """
        Find leadership/team pages on a company website.
        
        Args:
            base_url: Company website URL
            
        Returns:
            List of leadership page URLs
        """
        found_urls = []
        
        # Try common paths
        for path in self.LEADERSHIP_PATHS:
            url = urljoin(base_url, path)
            try:
                response = self.session.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    found_urls.append(url)
                    self.logger.debug(f"Found leadership page: {url}")
            except Exception:
                pass
        
        # If no direct paths work, parse homepage for leadership links
        if not found_urls:
            found_urls = self._find_leadership_links_from_homepage(base_url)

        # Fallback: parse sitemap.xml for leadership-like URLs
        if not found_urls:
            sitemap_urls = self._find_leadership_links_from_sitemap(base_url)
            found_urls.extend(sitemap_urls)
        
        return found_urls[:3]  # Limit to top 3 pages
    
    def _find_leadership_links_from_homepage(self, base_url: str) -> List[str]:
        """
        Parse homepage to find links to leadership pages.
        
        Args:
            base_url: Company website URL
            
        Returns:
            List of found leadership page URLs
        """
        found_urls = []
        
        try:
            response = self.session.get(base_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for links with leadership-related text
            leadership_keywords = ['leadership', 'team', 'management', 'executives', 'about']
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                for keyword in leadership_keywords:
                    if keyword in href.lower() or keyword in text:
                        full_url = urljoin(base_url, href)
                        if full_url not in found_urls:
                            found_urls.append(full_url)
                            break
        
        except Exception as e:
            self.logger.debug(f"Error parsing homepage: {e}")
        
        return found_urls

    def _find_leadership_links_from_sitemap(self, base_url: str) -> List[str]:
        """
        Parse sitemap.xml to locate leadership/team pages.
        """
        urls: List[str] = []
        try:
            # Normalize base url
            if not base_url.startswith("http"):
                base_url = f"https://{base_url.lstrip('/')}"
            sitemap_url = urljoin(base_url, "/sitemap.xml")
            resp = self.session.get(sitemap_url, timeout=self.timeout)
            if resp.status_code != 200 or "xml" not in resp.headers.get("Content-Type", ""):
                return urls

            soup = BeautifulSoup(resp.text, "xml")
            loc_tags = soup.find_all("loc")
            leadership_keywords = ["leadership", "team", "management", "executive", "about"]
            for loc in loc_tags:
                loc_text = loc.get_text()
                if any(k in loc_text.lower() for k in leadership_keywords):
                    urls.append(loc_text)
                    if len(urls) >= 5:
                        break
        except Exception as e:
            self.logger.debug(f"Sitemap parse failed: {e}")
        return urls
    
    # =========================================================================
    # Page Parsing
    # =========================================================================
    
    def parse_leadership_page(
        self,
        url: str,
        company: Optional[Company] = None,
        target_titles: Optional[List[str]] = None,
    ) -> List[FinanceContact]:
        """
        Parse a leadership page for contact information.
        
        Args:
            url: URL of the leadership page
            company: Optional company context
            target_titles: Lowercased titles to match. None uses config defaults.
            
        Returns:
            List of FinanceContact objects
        """
        contacts = []
        active_titles = self._resolve_target_titles(target_titles)
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different parsing strategies
            contacts = self._parse_structured_bios(soup, url, company, target_titles=active_titles)
            
            if not contacts:
                contacts = self._parse_unstructured_page(soup, url, company, target_titles=active_titles)
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for {url}: {e}")
        except Exception as e:
            self.logger.error(f"Parsing error for {url}: {e}")
        
        return [c for c in contacts if self._matches_target_title(c.title, active_titles)]
    
    def _parse_structured_bios(
        self,
        soup: BeautifulSoup,
        url: str,
        company: Optional[Company],
        target_titles: Optional[List[str]] = None,
    ) -> List[FinanceContact]:
        """
        Parse structured bio sections (common on leadership pages).
        
        Looks for elements with class names like:
        - bio, executive, team-member, leader, person
        """
        contacts = []
        
        # Common selectors for bio blocks
        bio_selectors = [
            '.bio',
            '.executive',
            '.team-member',
            '.leader',
            '.person',
            '.profile',
            'article[class*="team"]',
            'div[class*="executive"]',
            'div[class*="leader"]',
            'div[class*="bio"]',
            'li[class*="team"]',
        ]
        
        for selector in bio_selectors:
            elements = soup.select(selector)
            for element in elements:
                contact = self._parse_bio_element(element, url, company, target_titles=target_titles)
                if contact:
                    contacts.append(contact)
        
        return contacts
    
    def _parse_bio_element(
        self,
        element: BeautifulSoup,
        url: str,
        company: Optional[Company],
        target_titles: Optional[List[str]] = None,
    ) -> Optional[FinanceContact]:
        """
        Parse a single bio element for contact information.
        
        Args:
            element: BeautifulSoup element containing bio
            url: Source page URL
            company: Company context
            
        Returns:
            FinanceContact if valid name and title found
        """
        # Try to find name
        name = None
        name_selectors = ['h2', 'h3', 'h4', '.name', '.title', 'strong']
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                candidate = name_elem.get_text(strip=True)
                if self._is_valid_name(candidate):
                    name = candidate
                    break
        
        if not name:
            return None
        
        # Try to find title
        title = None
        title_selectors = ['.title', '.position', '.role', 'p', 'span']
        for selector in title_selectors:
            title_elems = element.select(selector)
            for elem in title_elems:
                candidate = elem.get_text(strip=True)
                if self._looks_like_title(candidate) and candidate != name:
                    title = candidate
                    break
            if title:
                break
        
        if not title:
            # Try to extract title from the full text
            full_text = element.get_text(strip=True)
            title = self._extract_title_from_text(full_text, target_titles)
        
        if not title:
            return None
        
        # Parse name into parts
        first_name, last_name = self._parse_name(name)
        
        # Get company info
        company_name = company.name if company else "Unknown"
        company_domain = company.domain if company else None
        
        return FinanceContact(
            company_name=company_name,
            company_domain=company_domain,
            full_name=name,
            first_name=first_name,
            last_name=last_name,
            title=title,
            source=ContactSource.WEBSITE,
            source_url=url,
            seniority_level=self._determine_seniority(title),
            department=None,
            provider="company_website",
        )
    
    def _parse_unstructured_page(
        self,
        soup: BeautifulSoup,
        url: str,
        company: Optional[Company],
        target_titles: Optional[List[str]] = None,
    ) -> List[FinanceContact]:
        """
        Parse unstructured page content for contacts.
        
        Falls back to text analysis when structured parsing fails.
        """
        contacts = []
        
        # Get all text content
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Look for name + title patterns
        i = 0
        while i < len(lines) - 1:
            line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            
            # Check if current line is a name
            if self._is_valid_name(line):
                # Check if next line is a title
                if self._looks_like_title(next_line):
                    if self._matches_target_title(next_line, target_titles):
                        first_name, last_name = self._parse_name(line)
                        
                        contact = FinanceContact(
                            company_name=company.name if company else "Unknown",
                            company_domain=company.domain if company else None,
                            full_name=line,
                            first_name=first_name,
                            last_name=last_name,
                            title=next_line,
                            source=ContactSource.WEBSITE,
                            source_url=url,
                            seniority_level=self._determine_seniority(next_line),
                            department=None,
                            provider="company_website",
                        )
                        contacts.append(contact)
                        i += 2
                        continue
            
            i += 1
        
        return contacts
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _is_valid_name(self, text: str) -> bool:
        """Check if text looks like a person's name"""
        if not text or len(text) < 3 or len(text) > 50:
            return False
        
        # Should have at least 2 words (first and last name)
        words = text.split()
        if len(words) < 2 or len(words) > 5:
            return False
        
        # First letter should be capitalized
        if not text[0].isupper():
            return False
        
        # Should not contain common non-name patterns
        non_name_patterns = [
            r'\d',  # Numbers
            r'@',   # Email
            r'http', # URL
            r'©',   # Copyright
            r'\|',  # Separator
        ]
        for pattern in non_name_patterns:
            if re.search(pattern, text):
                return False
        
        return True
    
    def _looks_like_title(self, text: str) -> bool:
        """Check if text looks like a job title"""
        if not text or len(text) < 3 or len(text) > 100:
            return False
        
        title_keywords = [
            'ceo', 'cfo', 'coo', 'cto', 'cmo', 'cio',
            'chief', 'president', 'vice president', 'vp',
            'director', 'manager', 'head', 'lead', 'officer',
            'controller', 'treasurer', 'partner'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in title_keywords)
    
    def _matches_target_title(self, title: str, target_titles: Optional[List[str]] = None) -> bool:
        """
        Case-insensitive substring match of requested titles against a scraped title.

        "IT Director" matches "Senior IT Director".
        "Head of IT" matches "Head of IT Infrastructure".
        """
        if not title:
            return False

        active_titles = target_titles if target_titles is not None else self.target_titles
        return matches_target_title(title, active_titles)
    
    def _extract_title_from_text(self, text: str, target_titles: Optional[List[str]] = None) -> Optional[str]:
        """Extract a title from a block of text using the active title list."""
        active_titles = target_titles if target_titles is not None else self.config.target_titles
        text_lower = text.lower()
        for target_title in active_titles:
            target_lower = target_title.lower()
            if target_lower in text_lower:
                pattern = rf'({re.escape(target_title)}[^,.\n]*)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None
    
    def _parse_name(self, full_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse full name into first and last name"""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return parts[0], parts[-1]
        elif len(parts) == 1:
            return parts[0], None
        return None, None
    
    def _determine_seniority(self, title: str) -> str:
        """Determine seniority level from title"""
        title_lower = title.lower()
        
        if any(x in title_lower for x in ['chief', 'cfo', 'ceo', 'coo', 'cto', 'cmo']):
            return 'C-Level'
        elif any(x in title_lower for x in ['vp', 'vice president']):
            return 'VP'
        elif 'director' in title_lower:
            return 'Director'
        elif any(x in title_lower for x in ['manager', 'head', 'lead']):
            return 'Manager'
        else:
            return 'Other'
    
    def _deduplicate_contacts(self, contacts: List[FinanceContact]) -> List[FinanceContact]:
        """Remove duplicate contacts by name"""
        seen_names = set()
        unique = []
        
        for contact in contacts:
            name_key = contact.full_name.lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique.append(contact)
        
        return unique

