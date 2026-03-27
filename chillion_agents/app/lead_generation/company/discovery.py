"""
Company Discovery Module

Discovers and enriches company information from various sources.
Provides interfaces for external data providers and search APIs.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import re
import csv
from pathlib import Path
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from ..models import Company
from ..config import get_config, CompanyTargetConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Abstract Interfaces for External Services
# =============================================================================

class SearchProvider(ABC):
    """
    Abstract interface for web search providers.
    
    Implement this interface to integrate with:
    - Google Custom Search API
    - Bing Search API
    - SerpApi
    - Other search services
    """
    
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        Search the web for a query.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            
        Returns:
            List of dicts with 'title', 'url', 'snippet' keys
        """
        pass


class CompanyEnrichmentProvider(ABC):
    """
    Abstract interface for company data enrichment providers.
    
    Implement this interface to integrate with:
    - Clearbit
    - ZoomInfo
    - Apollo.io
    - LinkedIn Sales Navigator
    - D&B Hoovers
    """
    
    @abstractmethod
    def enrich_company(self, company_name: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich company data with additional information.
        
        Args:
            company_name: Name of the company
            domain: Optional company website domain
            
        Returns:
            Dict with enriched company data
        """
        pass
    
    @abstractmethod
    def enrich_person(self, name: str, company: str) -> Dict[str, Any]:
        """
        Enrich person data with additional information.
        
        Args:
            name: Person's full name
            company: Company name
            
        Returns:
            Dict with enriched person data
        """
        pass


# =============================================================================
# Dummy Implementations (for development/testing)
# =============================================================================

class DummySearchProvider(SearchProvider):
    """
    Dummy search provider that returns placeholder results.
    
    Replace with actual search API implementation for production.
    """
    
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """Returns placeholder search results"""
        logger.info(f"[PLACEHOLDER] Search API call: {query}")
        
        # Return mock result suggesting where company website might be
        company_name = query.replace('"', '').replace('company', '').strip()
        domain_guess = company_name.lower().replace(' ', '') + '.com'
        
        return [
            {
                "title": f"{company_name} - Official Website",
                "url": f"https://www.{domain_guess}",
                "snippet": f"Official website for {company_name}. Learn about our products and services.",
            },
            {
                "title": f"{company_name} | LinkedIn",
                "url": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}",
                "snippet": f"{company_name} on LinkedIn. See employees, updates, and more.",
            },
        ][:num_results]


class DummyEnrichmentProvider(CompanyEnrichmentProvider):
    """
    Dummy enrichment provider that echoes input data.
    
    Replace with actual enrichment API (Clearbit, Apollo, etc.) for production.
    """
    
    def enrich_company(self, company_name: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Returns placeholder enrichment data"""
        logger.info(f"[PLACEHOLDER] Company enrichment API call: {company_name}")
        
        return {
            "company_name": company_name,
            "domain": domain or f"{company_name.lower().replace(' ', '')}.com",
            "industry": "Technology",  # Would come from API
            "employee_range": "100-500",
            "revenue_range": "$50M-$100M",
            "headquarters": {
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
            },
            "description": f"[Placeholder] {company_name} is a company in the technology sector.",
            "linkedin_url": f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
            "source": "placeholder",
            "enriched_at": datetime.utcnow().isoformat(),
        }
    
    def enrich_person(self, name: str, company: str) -> Dict[str, Any]:
        """Returns placeholder person enrichment data"""
        logger.info(f"[PLACEHOLDER] Person enrichment API call: {name} at {company}")
        
        first_name = name.split()[0] if name else "Unknown"
        last_name = name.split()[-1] if len(name.split()) > 1 else ""
        
        return {
            "full_name": name,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "title": "Finance Executive",  # Would come from API
            "email": None,  # Would come from API
            "linkedin_url": None,  # Would come from API
            "source": "placeholder",
            "enriched_at": datetime.utcnow().isoformat(),
        }


# =============================================================================
# Company Discovery Service
# =============================================================================

class CompanyDiscoveryService:
    """
    Service for discovering and validating company information.
    
    Provides functionality to:
    - Load companies from CSV input
    - Discover company websites via search
    - Validate and normalize company data
    - Match companies against target profile
    
    Example usage:
        service = CompanyDiscoveryService()
        
        # Load from CSV
        companies = service.load_from_csv("companies.csv")
        
        # Discover website for a company
        company = service.discover_company_website("Acme Corp")
        
        # Check if company matches target profile
        is_target = service.matches_target_profile(company)
    """
    
    def __init__(
        self,
        search_provider: Optional[SearchProvider] = None,
        enrichment_provider: Optional[CompanyEnrichmentProvider] = None,
        config: Optional[CompanyTargetConfig] = None,
    ):
        """
        Initialize the company discovery service.
        
        Args:
            search_provider: Provider for web searches (uses dummy if None)
            enrichment_provider: Provider for data enrichment (uses dummy if None)
            config: Company targeting configuration
        """
        self.search = search_provider or DummySearchProvider()
        self.enrichment = enrichment_provider or DummyEnrichmentProvider()
        self.config = config or get_config().company
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # HTTP session for website fetching
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": get_config().rate_limit.user_agent,
        })
    
    # =========================================================================
    # CSV Input/Output
    # =========================================================================
    
    def load_from_csv(self, filepath: str) -> List[Company]:
        """
        Load companies from a CSV file.
        
        Expected CSV columns (all optional except name):
        - name: Company name (required)
        - domain: Company website domain
        - industry: Industry classification
        - employee_count: Number of employees
        - revenue_usd: Annual revenue in USD
        - city: Headquarters city
        - state: Headquarters state
        - country: Headquarters country
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of Company objects
        """
        companies = []
        path = Path(filepath)
        
        if not path.exists():
            self.logger.error(f"CSV file not found: {filepath}")
            return companies
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    company = self._row_to_company(row)
                    if company:
                        companies.append(company)
            
            self.logger.info(f"Loaded {len(companies)} companies from {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error reading CSV: {e}")
        
        return companies
    
    def _row_to_company(self, row: Dict[str, str]) -> Optional[Company]:
        """Convert CSV row to Company object"""
        name = row.get('name', '').strip()
        if not name:
            return None
        
        # Parse numeric fields
        employee_count = None
        if row.get('employee_count'):
            try:
                employee_count = int(row['employee_count'].replace(',', ''))
            except ValueError:
                pass
        
        revenue = None
        if row.get('revenue_usd'):
            try:
                revenue = int(row['revenue_usd'].replace(',', '').replace('$', ''))
            except ValueError:
                pass
        
        return Company(
            name=name,
            domain=row.get('domain', '').strip() or None,
            website=row.get('website', '').strip() or None,
            industry=row.get('industry', '').strip() or None,
            employee_count=employee_count,
            revenue_usd=revenue,
            headquarters_city=row.get('city', '').strip() or None,
            headquarters_state=row.get('state', '').strip() or None,
            headquarters_country=row.get('country', '').strip() or None,
            source='csv_import',
        )
    
    def export_to_csv(self, companies: List[Company], filepath: str) -> None:
        """
        Export companies to CSV file.
        
        Args:
            companies: List of Company objects
            filepath: Output file path
        """
        fieldnames = [
            'name', 'domain', 'website', 'industry', 'employee_count',
            'revenue_usd', 'city', 'state', 'country', 'is_target_profile',
            'target_score', 'source'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for company in companies:
                writer.writerow({
                    'name': company.name,
                    'domain': company.domain,
                    'website': company.website,
                    'industry': company.industry,
                    'employee_count': company.employee_count,
                    'revenue_usd': company.revenue_usd,
                    'city': company.headquarters_city,
                    'state': company.headquarters_state,
                    'country': company.headquarters_country,
                    'is_target_profile': company.is_target_profile,
                    'target_score': company.target_score,
                    'source': company.source,
                })
        
        self.logger.info(f"Exported {len(companies)} companies to {filepath}")
    
    # =========================================================================
    # Website Discovery
    # =========================================================================
    
    def discover_company_website(self, company_name: str) -> Company:
        """
        Discover company website using search.
        
        Args:
            company_name: Name of the company
            
        Returns:
            Company object with discovered website
        """
        self.logger.info(f"Discovering website for: {company_name}")
        
        # Search for company website
        query = f'"{company_name}" company official website'
        results = self.search.search(query, num_results=5)
        
        domain = None
        website = None
        linkedin_url = None
        
        for result in results:
            url = result.get('url', '')
            
            # Look for company website (not social media)
            if not domain and self._is_likely_company_website(url, company_name):
                website = url
                domain = self._extract_domain(url)
            
            # Also capture LinkedIn if found
            if 'linkedin.com/company' in url:
                linkedin_url = url
        
        company = Company(
            name=company_name,
            domain=domain,
            website=website,
            linkedin_url=linkedin_url,
            source='web_discovery',
        )
        
        return company
    
    def _is_likely_company_website(self, url: str, company_name: str) -> bool:
        """Check if URL is likely the company's official website"""
        if not url:
            return False
        
        # Exclude common non-company sites
        exclude_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'wikipedia.org', 'crunchbase.com', 'bloomberg.com',
            'glassdoor.com', 'yelp.com', 'bbb.org'
        ]
        
        url_lower = url.lower()
        if any(domain in url_lower for domain in exclude_domains):
            return False
        
        # Check if company name appears in domain
        company_words = company_name.lower().split()
        domain = self._extract_domain(url)
        if domain:
            domain_lower = domain.lower()
            if any(word in domain_lower for word in company_words if len(word) > 2):
                return True
        
        return False
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain if domain else None
        except Exception:
            return None
    
    # =========================================================================
    # Company Enrichment
    # =========================================================================
    
    def enrich_company(self, company: Company) -> Company:
        """
        Enrich company data using external provider.
        
        Args:
            company: Company to enrich
            
        Returns:
            Company with enriched data
        """
        self.logger.info(f"Enriching company: {company.name}")
        
        enrichment_data = self.enrichment.enrich_company(
            company.name,
            company.domain
        )
        
        # Update company with enriched data
        if enrichment_data:
            if not company.domain and enrichment_data.get('domain'):
                company.domain = enrichment_data['domain']
            
            if not company.industry and enrichment_data.get('industry'):
                company.industry = enrichment_data['industry']
            
            if not company.employee_count and enrichment_data.get('employee_range'):
                company.employee_range = enrichment_data['employee_range']
            
            if not company.revenue_usd and enrichment_data.get('revenue_range'):
                company.revenue_range = enrichment_data['revenue_range']
            
            headquarters = enrichment_data.get('headquarters', {})
            if headquarters:
                company.headquarters_city = company.headquarters_city or headquarters.get('city')
                company.headquarters_state = company.headquarters_state or headquarters.get('state')
                company.headquarters_country = company.headquarters_country or headquarters.get('country')
            
            if not company.linkedin_url and enrichment_data.get('linkedin_url'):
                company.linkedin_url = enrichment_data['linkedin_url']
            
            if not company.description and enrichment_data.get('description'):
                company.description = enrichment_data['description']
            
            company.enrichment_data = enrichment_data
        
        return company
    
    # =========================================================================
    # Target Profile Matching
    # =========================================================================
    
    def matches_target_profile(self, company: Company) -> bool:
        """
        Check if company matches our ideal customer profile.
        
        Args:
            company: Company to evaluate
            
        Returns:
            True if company matches target profile
        """
        score = self.calculate_target_score(company)
        company.target_score = score
        company.is_target_profile = score >= 0.5
        return company.is_target_profile
    
    def calculate_target_score(self, company: Company) -> float:
        """
        Calculate how well company matches target profile.
        
        Scoring factors:
        - Industry match: 0.3
        - Revenue match: 0.3
        - Employee count match: 0.2
        - Geographic match: 0.2
        
        Args:
            company: Company to score
            
        Returns:
            Score between 0 and 1
        """
        score = 0.0
        
        # Industry match (0.3)
        if company.industry:
            for target_industry in self.config.target_industries:
                if target_industry.lower() in company.industry.lower():
                    score += 0.3
                    break
        
        # Revenue match (0.3)
        if company.revenue_usd:
            if company.revenue_usd >= self.config.min_revenue_usd:
                if not self.config.max_revenue_usd or company.revenue_usd <= self.config.max_revenue_usd:
                    score += 0.3
        elif company.revenue_range:
            # Partial match if revenue range suggests target size
            if any(x in company.revenue_range for x in ['50M', '100M', '500M', 'billion']):
                score += 0.2
        
        # Employee count match (0.2)
        if company.employee_count:
            if company.employee_count >= self.config.min_employees:
                if not self.config.max_employees or company.employee_count <= self.config.max_employees:
                    score += 0.2
        elif company.employee_range:
            # Partial match for employee range
            if any(x in company.employee_range for x in ['100', '500', '1000']):
                score += 0.1
        
        # Geographic match (0.2)
        if company.headquarters_country:
            if company.headquarters_country in self.config.target_countries:
                score += 0.2
        
        return min(score, 1.0)
    
    # =========================================================================
    # Batch Processing
    # =========================================================================
    
    def process_companies(
        self,
        companies: List[Company],
        discover_websites: bool = True,
        enrich: bool = True,
        filter_targets: bool = True,
    ) -> List[Company]:
        """
        Process a list of companies through the discovery pipeline.
        
        Args:
            companies: List of companies to process
            discover_websites: Whether to discover missing websites
            enrich: Whether to enrich company data
            filter_targets: Whether to filter to only target profile matches
            
        Returns:
            Processed (and optionally filtered) list of companies
        """
        processed = []
        
        for company in companies:
            self.logger.info(f"Processing: {company.name}")
            
            # Discover website if missing
            if discover_websites and not company.domain:
                discovered = self.discover_company_website(company.name)
                company.domain = discovered.domain
                company.website = discovered.website
                company.linkedin_url = company.linkedin_url or discovered.linkedin_url
            
            # Enrich company data
            if enrich:
                company = self.enrich_company(company)
            
            # Score against target profile
            self.matches_target_profile(company)
            
            # Filter if requested
            if filter_targets and not company.is_target_profile:
                self.logger.debug(f"Skipping non-target: {company.name}")
                continue
            
            processed.append(company)
        
        self.logger.info(f"Processed {len(processed)} companies ({len(companies)} input)")
        return processed

