"""
Generic Forum Scraper Module

Searches Quora, forums, and uses Google site search for intent signals.
Uses requests + BeautifulSoup for parsing.

This module provides a flexible framework for scraping various forums
and Q&A sites where finance professionals discuss their needs.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import time
import re
from urllib.parse import urljoin, urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

from .base import BaseSocialScraper
from ..models import SocialLead, ForumLead, Platform
from ..config import SocialSearchConfig, get_config

logger = logging.getLogger(__name__)


class ForumScraper(BaseSocialScraper):
    """
    Generic forum and Q&A site scraper.
    
    Supports:
    - Quora (limited public scraping)
    - Generic forum sites
    - Google site search results
    
    Example usage:
        scraper = ForumScraper()
        
        # Search Quora
        leads = scraper.search_quora("accounts receivable automation")
        
        # Search any forum via Google
        leads = scraper.google_site_search("site:quora.com", "AR software recommendation")
        
        # Search a list of forum URLs
        leads = scraper.search_forum_urls(url_list, keywords)
    """
    
    platform = Platform.FORUM
    
    def __init__(self, config: Optional[SocialSearchConfig] = None):
        super().__init__(config)
        
        rate_config = get_config().rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": rate_config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        
        self.request_delay = rate_config.request_delay_seconds
        self.timeout = rate_config.request_timeout_seconds
    
    def search(self, query: str, max_results: int = 50) -> List[SocialLead]:
        """
        Search across all configured forum sources.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of ForumLead objects
        """
        all_leads = []

        # Search Quora
        quora_leads = self.search_quora(query, max_results // 2)
        all_leads.extend(quora_leads)

        # External provider selection (SerpAPI / Google CSE / mock)
        provider_leads = self._search_with_provider(query, max_results - len(all_leads))
        all_leads.extend(provider_leads)

        return all_leads[:max_results]
    
    def get_post_by_id(self, post_id: str) -> Optional[SocialLead]:
        """
        Fetch post by ID - not supported for generic forums.
        
        Returns None as forum posts don't have universal IDs.
        """
        return None
    
    # =========================================================================
    # Quora Search
    # =========================================================================
    
    def search_quora(self, query: str, max_results: int = 25) -> List[ForumLead]:
        """
        Search Quora for questions related to the query.
        
        Note: Quora has aggressive anti-scraping measures.
        This uses their public search which may have limitations.
        For production, consider using Quora's API (if available)
        or a data provider.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of ForumLead objects from Quora
        """
        leads = []
        
        try:
            # Quora search URL
            search_url = f"https://www.quora.com/search?q={quote_plus(query)}"
            
            self.logger.info(f"Searching Quora: {query}")
            
            response = self.session.get(search_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse question links
            # Note: Quora's HTML structure changes frequently
            question_links = soup.select('a[href*="/"]')
            
            for link in question_links[:max_results * 2]:  # Get extra in case of filtering
                href = link.get('href', '')
                if self._is_quora_question_url(href):
                    lead = self._parse_quora_question(link, href)
                    if lead and len(leads) < max_results:
                        leads.append(lead)
            
            self.logger.info(f"Found {len(leads)} Quora questions")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Quora request error: {e}")
            # Return mock data on error
            return self._get_mock_quora_results(query, max_results)
        except Exception as e:
            self.logger.error(f"Quora parsing error: {e}")
            return self._get_mock_quora_results(query, max_results)
        
        # If no results found, return mock data
        if not leads:
            return self._get_mock_quora_results(query, max_results)
        
        return leads
    
    def _is_quora_question_url(self, href: str) -> bool:
        """Check if URL is a Quora question page"""
        if not href:
            return False
        # Quora questions typically have format: /What-is-the-best-...
        return bool(re.match(r'^/[A-Z][a-zA-Z\-]+', href)) and 'profile' not in href.lower()
    
    def _parse_quora_question(self, element, href: str) -> Optional[ForumLead]:
        """Parse a Quora question element into a ForumLead"""
        try:
            # Get question text from link
            question_text = element.get_text(strip=True)
            
            if not question_text or len(question_text) < 10:
                return None
            
            # Build full URL
            full_url = urljoin("https://www.quora.com", href)
            
            # Generate ID from URL
            question_id = href.strip('/').replace('-', '_')[:50]
            
            return ForumLead(
                id=self.generate_lead_id("quora", question_id),
                platform=Platform.QUORA,
                url=full_url,
                source_id=question_id,
                title=question_text,
                text=question_text,
                text_excerpt=self.truncate_text(question_text, 200),
                source_meta={
                    "forum_name": "Quora",
                    "forum_url": "https://www.quora.com",
                    "question_type": "question",
                },
            )
        except Exception as e:
            self.logger.debug(f"Error parsing Quora element: {e}")
            return None
    
    def _get_mock_quora_results(self, query: str, max_results: int) -> List[ForumLead]:
        """Generate mock Quora results for testing"""
        mock_questions = [
            {
                "title": "What is the best accounts receivable automation software for mid-sized companies?",
                "url": "What-is-the-best-accounts-receivable-automation-software",
            },
            {
                "title": "How do large enterprises manage their order-to-cash process?",
                "url": "How-do-large-enterprises-manage-order-to-cash",
            },
            {
                "title": "What software do you recommend for cash application automation?",
                "url": "What-software-recommend-cash-application-automation",
            },
            {
                "title": "What are the best practices for reducing DSO in a retail business?",
                "url": "Best-practices-reducing-DSO-retail",
            },
            {
                "title": "Which deductions management software is used by Fortune 500 companies?",
                "url": "Deductions-management-software-Fortune-500",
            },
        ]
        
        leads = []
        for i, mock in enumerate(mock_questions[:max_results]):
            lead = ForumLead(
                id=self.generate_lead_id("quora", mock["url"]),
                platform=Platform.QUORA,
                url=f"https://www.quora.com/{mock['url']}",
                source_id=mock["url"],
                title=mock["title"],
                text=mock["title"],
                text_excerpt=mock["title"],
                created_at=datetime.now(),
                source_meta={
                    "forum_name": "Quora",
                    "forum_url": "https://www.quora.com",
                    "is_mock": True,
                },
            )
            leads.append(lead)
        
        return leads
    
    # =========================================================================
    # Google Site Search
    # =========================================================================
    
    def google_site_search(
        self,
        site_filter: str,
        query: str,
        max_results: int = 20
    ) -> List[ForumLead]:
        """
        Search via Google with site filter.
        Uses the same provider selection as general search.
        """
        combined_query = f"{site_filter} {query}"
        return self._search_with_provider(combined_query, max_results)

    # =========================================================================
    # Provider-backed search (SerpAPI / Google CSE / Mock)
    # =========================================================================

    def _search_with_provider(self, query: str, max_results: int) -> List[ForumLead]:
        """Select provider based on config and fall back to mock."""
        if max_results <= 0:
            return []

        cfg = get_config()
        provider = cfg.social.search_provider

        if provider == "serpapi" and cfg.enable_serpapi and cfg.social.serpapi_api_key:
            leads = self._search_serpapi(query, max_results, cfg.social.serpapi_api_key)
            if leads:
                return leads

        if (
            provider == "google_cse"
            and cfg.enable_google_cse
            and cfg.social.google_cse_key
            and cfg.social.google_cse_cx
        ):
            leads = self._search_google_cse(
                query,
                max_results,
                cfg.social.google_cse_key,
                cfg.social.google_cse_cx,
            )
            if leads:
                return leads

        # Default mock fallback
        return self._get_mock_google_results(query, max_results)

    def _search_serpapi(self, query: str, max_results: int, api_key: str) -> List[ForumLead]:
        """Search via SerpAPI (Google engine)."""
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": min(max_results, 10),
            }
            self.logger.info(f"SerpAPI search: {query}")
            resp = self.session.get("https://serpapi.com/search.json", params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("organic_results", []) or []
            leads: List[ForumLead] = []
            for item in results[:max_results]:
                url = item.get("link") or item.get("url")
                title = item.get("title") or "Result"
                snippet = item.get("snippet") or item.get("snippet_highlighted_words", [""])[0] if isinstance(item.get("snippet_highlighted_words"), list) else ""
                if not url:
                    continue
                leads.append(
                    ForumLead(
                        id=self.generate_lead_id("serpapi", str(hash(url))),
                        platform=Platform.FORUM,
                        url=url,
                        title=title,
                        text=snippet,
                        text_excerpt=self.truncate_text(snippet or title, 280),
                        created_at=datetime.now(),
                        source_meta={
                            "provider": "serpapi",
                            "search_query": query,
                        },
                    )
                )
            return leads
        except Exception as e:
            self.logger.error(f"SerpAPI search failed, falling back to mock: {e}")
            return []

    def _search_google_cse(self, query: str, max_results: int, api_key: str, cx: str) -> List[ForumLead]:
        """Search via Google Custom Search API."""
        try:
            params = {
                "key": api_key,
                "cx": cx,
                "q": query,
                "num": min(max_results, 10),
            }
            self.logger.info(f"Google CSE search: {query}")
            resp = self.session.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", []) or []
            leads: List[ForumLead] = []
            for item in items[:max_results]:
                url = item.get("link") or item.get("formattedUrl")
                title = item.get("title") or "Result"
                snippet = item.get("snippet") or ""
                if not url:
                    continue
                leads.append(
                    ForumLead(
                        id=self.generate_lead_id("google_cse", str(hash(url))),
                        platform=Platform.FORUM,
                        url=url,
                        title=title,
                        text=snippet,
                        text_excerpt=self.truncate_text(snippet or title, 280),
                        created_at=datetime.now(),
                        source_meta={
                            "provider": "google_cse",
                            "search_query": query,
                        },
                    )
                )
            return leads
        except Exception as e:
            self.logger.error(f"Google CSE search failed, falling back to mock: {e}")
            return []
    
    def _get_mock_google_results(self, query: str, max_results: int) -> List[ForumLead]:
        """Mock Google search results"""
        mock_results = [
            {
                "title": "Best AR Automation Tools 2024 - Finance Forum Discussion",
                "url": "https://financeforum.example.com/thread/ar-automation-tools-2024",
                "snippet": "Looking for recommendations on AR automation software. We're a $100M retail company struggling with manual collections...",
                "forum": "Finance Forum",
            },
            {
                "title": "Order to Cash Software Comparison - CFO Network",
                "url": "https://cfonetwork.example.com/discussions/o2c-comparison",
                "snippet": "Has anyone compared the leading O2C platforms? We need to reduce DSO and improve cash flow visibility...",
                "forum": "CFO Network",
            },
            {
                "title": "AI in Collections - Treasury Management Community",
                "url": "https://treasury.example.com/forum/ai-collections",
                "snippet": "Exploring AI-powered collections solutions. What's your experience with automated dunning and payment prediction?",
                "forum": "Treasury Community",
            },
        ]
        
        leads = []
        for i, mock in enumerate(mock_results[:max_results]):
            lead = ForumLead(
                id=self.generate_lead_id("forum", str(hash(mock["url"]))),
                platform=Platform.FORUM,
                url=mock["url"],
                title=mock["title"],
                text=mock["snippet"],
                text_excerpt=mock["snippet"],
                created_at=datetime.now(),
                source_meta={
                    "forum_name": mock["forum"],
                    "search_query": query,
                    "is_mock": True,
                },
            )
            leads.append(lead)
        
        return leads
    
    # =========================================================================
    # Generic Forum URL Search
    # =========================================================================
    
    def search_forum_urls(
        self,
        urls: List[str],
        keywords: List[str],
        max_per_url: int = 10
    ) -> List[ForumLead]:
        """
        Search a list of forum URLs for content matching keywords.
        
        Args:
            urls: List of forum page URLs to scrape
            keywords: Keywords to look for
            max_per_url: Max leads per URL
            
        Returns:
            List of ForumLead objects
        """
        all_leads = []
        
        for url in urls:
            self.logger.info(f"Scraping forum URL: {url}")
            try:
                leads = self._scrape_forum_page(url, keywords, max_per_url)
                all_leads.extend(leads)
                
                # Rate limiting
                time.sleep(self.request_delay)
                
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
                continue
        
        return all_leads
    
    def _scrape_forum_page(
        self,
        url: str,
        keywords: List[str],
        max_results: int
    ) -> List[ForumLead]:
        """
        Scrape a single forum page for relevant content.
        
        Args:
            url: Page URL
            keywords: Keywords to match
            max_results: Maximum results
            
        Returns:
            List of ForumLead objects
        """
        leads = []
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Common forum content selectors
            content_selectors = [
                'article',
                '.post',
                '.thread',
                '.discussion',
                '.question',
                '.topic',
                'div[class*="post"]',
                'div[class*="thread"]',
            ]
            
            # Parse hostname for forum name
            parsed = urlparse(url)
            forum_name = parsed.netloc.replace('www.', '')
            
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    
                    # Check if text matches any keyword
                    if self._text_matches_keywords(text, keywords):
                        # Extract title if available
                        title_elem = element.select_one('h1, h2, h3, .title, .subject')
                        title = title_elem.get_text(strip=True) if title_elem else None
                        
                        # Extract link if available
                        link_elem = element.select_one('a[href]')
                        post_url = urljoin(url, link_elem['href']) if link_elem else url
                        
                        lead = ForumLead(
                            id=self.generate_lead_id("forum", str(hash(post_url))),
                            platform=Platform.FORUM,
                            url=post_url,
                            title=title or self.truncate_text(text, 100),
                            text=text,
                            text_excerpt=self.truncate_text(text, 300),
                            source_meta={
                                "forum_name": forum_name,
                                "forum_url": f"{parsed.scheme}://{parsed.netloc}",
                                "source_page": url,
                            },
                        )
                        leads.append(lead)
                        
                        if len(leads) >= max_results:
                            return leads
            
        except Exception as e:
            self.logger.error(f"Error scraping page: {e}")
        
        return leads
    
    def _text_matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)
    
    # =========================================================================
    # Intent Classification
    # =========================================================================
    
    def classify_intent(self, text: str) -> Dict[str, Any]:
        """
        Classify whether text indicates buying intent.
        
        Uses simple rule-based classification:
        - Strong intent: explicit buying/looking signals
        - Medium intent: problem statements
        - Low intent: general discussion
        
        Args:
            text: Text to classify
            
        Returns:
            Dict with classification details
        """
        text_lower = text.lower()
        
        # Strong intent signals
        strong_signals = [
            "looking for",
            "recommend",
            "recommendations",
            "what tool",
            "what software",
            "best option for",
            "evaluating",
            "in the market",
            "need a solution",
            "switching from",
        ]
        
        # Medium intent (problem statements)
        medium_signals = [
            "struggling with",
            "pain point",
            "challenge with",
            "problem with",
            "manual process",
            "taking too long",
            "need to improve",
            "looking to reduce",
        ]
        
        strong_count = sum(1 for s in strong_signals if s in text_lower)
        medium_count = sum(1 for s in medium_signals if s in text_lower)
        
        if strong_count >= 2:
            intent = "high"
            confidence = 0.9
        elif strong_count >= 1:
            intent = "high"
            confidence = 0.75
        elif medium_count >= 2:
            intent = "medium"
            confidence = 0.6
        elif medium_count >= 1 or strong_count >= 1:
            intent = "medium"
            confidence = 0.5
        else:
            intent = "low"
            confidence = 0.3
        
        return {
            "intent_level": intent,
            "confidence": confidence,
            "strong_signals_matched": strong_count,
            "medium_signals_matched": medium_count,
        }

