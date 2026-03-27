"""
Base Social Media Scraper

Abstract base class for social media and forum scrapers.
Provides common functionality for intent scoring and result normalization.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Generator
import logging
import re
from datetime import datetime

from ..models import SocialLead, IntentLevel, Platform
from ..config import get_config, SocialSearchConfig


logger = logging.getLogger(__name__)


class BaseSocialScraper(ABC):
    """
    Abstract base class for social media scrapers.
    
    Provides common functionality including:
    - Search query building
    - Intent scoring
    - Rate limiting helpers
    - Result normalization
    """
    
    platform: Platform = Platform.OTHER
    
    def __init__(self, config: Optional[SocialSearchConfig] = None):
        """
        Initialize the scraper.
        
        Args:
            config: Optional social search configuration. Uses global config if not provided.
        """
        self.config = config or get_config().social
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for this scraper"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    def search(self, query: str, max_results: int = 100) -> List[SocialLead]:
        """
        Search the platform for posts matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of SocialLead objects
        """
        pass
    
    @abstractmethod
    def get_post_by_id(self, post_id: str) -> Optional[SocialLead]:
        """
        Fetch a specific post by its platform ID.
        
        Args:
            post_id: Platform-specific post identifier
            
        Returns:
            SocialLead if found, None otherwise
        """
        pass
    
    # =========================================================================
    # Query Building
    # =========================================================================
    
    def build_search_queries(self) -> Generator[str, None, None]:
        """
        Generate search queries by combining intent and product keywords.
        
        Yields:
            Search query strings
        """
        for intent in self.config.intent_keywords[:5]:  # Limit intent keywords
            for product in self.config.product_keywords[:5]:  # Limit product keywords
                query = f'"{intent}" "{product}"'
                yield query
    
    def build_simple_queries(self) -> Generator[str, None, None]:
        """
        Generate simpler search queries using product keywords alone.
        
        Yields:
            Search query strings
        """
        for product in self.config.product_keywords:
            yield f'"{product}"'
    
    # =========================================================================
    # Intent Scoring
    # =========================================================================
    
    def calculate_intent_score(self, text: str) -> tuple[float, IntentLevel, List[str], List[str], str]:
        """
        Calculate buying intent score based on keyword analysis.
        
        Uses a simple heuristic scoring system:
        - Base score from product keyword matches
        - Bonus for intent keyword matches
        - Higher score = stronger buying intent
        
        Args:
            text: The post/comment text to analyze
            
        Returns:
            Tuple of (score, intent_level, intent_keywords_matched, product_keywords_matched)
        """
        text_lower = text.lower()
        
        # Find matching keywords
        intent_matches = []
        product_matches = []
        
        for keyword in self.config.intent_keywords:
            if keyword.lower() in text_lower:
                intent_matches.append(keyword)
        
        for keyword in self.config.product_keywords:
            if keyword.lower() in text_lower:
                product_matches.append(keyword)
        
        # Calculate score
        # Product keyword match: 0.3 each (max 0.6)
        # Intent keyword match: 0.2 each (max 0.4)
        product_score = min(len(product_matches) * 0.3, 0.6)
        intent_score = min(len(intent_matches) * 0.2, 0.4)
        
        total_score = product_score + intent_score
        
        # Classify intent level
        if total_score >= 0.7:
            intent_level = IntentLevel.HIGH
        elif total_score >= 0.4:
            intent_level = IntentLevel.MEDIUM
        elif total_score > 0:
            intent_level = IntentLevel.LOW
        else:
            intent_level = IntentLevel.NONE
        
        reason_parts = []
        if intent_matches:
            reason_parts.append(f"Intent: {', '.join(intent_matches[:3])}")
        if product_matches:
            reason_parts.append(f"Product: {', '.join(product_matches[:3])}")
        reason = " | ".join(reason_parts) if reason_parts else "Matched keywords"

        return total_score, intent_level, intent_matches, product_matches, reason
    
    def score_lead(self, lead: SocialLead) -> SocialLead:
        """
        Calculate and set intent score for a lead.
        
        Args:
            lead: SocialLead to score
            
        Returns:
            The same lead with scores populated
        """
        text_to_analyze = f"{lead.title or ''} {lead.text}"
        
        score, level, intent_kw, product_kw, reason = self.calculate_intent_score(text_to_analyze)
        
        lead.intent_score = score
        lead.intent_level = level
        lead.intent_keywords_matched = intent_kw
        lead.product_keywords_matched = product_kw
        lead.reason_for_relevance = reason
        
        return lead
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def is_noise(self, lead: SocialLead) -> bool:
        """Filter out obvious noise (jobs, hiring, crypto, giveaways)"""
        text = (lead.text or "").lower()
        noise_terms = [
            "hiring",
            "job opening",
            "we are hiring",
            "looking for a job",
            "giveaway",
            "airdrop",
            "nft",
            "crypto",
            "bitcoin",
            "token",
        ]
        return any(term in text for term in noise_terms)

    def extract_company_from_bio(self, bio: Optional[str]) -> Optional[str]:
        """
        Attempt to extract company name from user bio.
        
        Args:
            bio: User biography text
            
        Returns:
            Company name if found, None otherwise
        """
        if not bio:
            return None
        
        # Common patterns
        patterns = [
            r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s*[|,.]|$)',
            r'(?:work(?:s|ing)?\s+(?:at|for))\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s*[|,.]|$)',
            r'^([A-Z][A-Za-z0-9\s&]+?)\s*[|]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, bio)
            if match:
                company = match.group(1).strip()
                # Filter out common false positives
                if company.lower() not in ['the', 'a', 'an', 'my', 'our']:
                    return company
        
        return None
    
    def extract_title_from_bio(self, bio: Optional[str]) -> Optional[str]:
        """
        Attempt to extract job title from user bio.
        
        Args:
            bio: User biography text
            
        Returns:
            Job title if found, None otherwise
        """
        if not bio:
            return None
        
        # Common finance titles
        title_patterns = [
            r'(CFO|Chief Financial Officer)',
            r'(VP\s+(?:of\s+)?Finance)',
            r'(Director\s+(?:of\s+)?Finance)',
            r'(Controller)',
            r'(Finance\s+(?:Manager|Director|VP))',
            r'(Head\s+of\s+(?:Finance|AR|Accounts\s+Receivable))',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, bio, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def truncate_text(self, text: str, max_length: int = 500) -> str:
        """
        Truncate text to max length, preserving word boundaries.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + '...'
    
    def generate_lead_id(self, platform: str, source_id: str) -> str:
        """
        Generate a unique lead ID.
        
        Args:
            platform: Platform name
            source_id: Platform-specific ID
            
        Returns:
            Unique lead ID string
        """
        return f"{platform}_{source_id}"
    
    # =========================================================================
    # Batch Processing
    # =========================================================================
    
    def search_all_queries(self, max_results_per_query: int = 50) -> List[SocialLead]:
        """
        Run searches for all generated queries and aggregate results.
        
        Args:
            max_results_per_query: Max results per individual query
            
        Returns:
            Aggregated list of unique SocialLead objects
        """
        all_leads = []
        seen_urls = set()
        
        for query in self.build_search_queries():
            self.logger.info(f"Searching: {query}")
            try:
                results = self.search(query, max_results_per_query)
                for lead in results:
                    if lead.url not in seen_urls:
                        seen_urls.add(lead.url)
                        scored_lead = self.score_lead(lead)
                        if not self.is_noise(scored_lead):
                            all_leads.append(scored_lead)
            except Exception as e:
                self.logger.error(f"Error searching '{query}': {e}")
                continue
        
        # Sort by intent score descending
        all_leads.sort(key=lambda x: x.intent_score, reverse=True)
        
        self.logger.info(f"Found {len(all_leads)} unique leads across all queries")
        return all_leads
    
    def filter_high_intent(self, leads: List[SocialLead], min_score: float = 0.5) -> List[SocialLead]:
        """
        Filter leads to only those with high buying intent.
        
        Args:
            leads: List of leads to filter
            min_score: Minimum intent score threshold
            
        Returns:
            Filtered list of high-intent leads
        """
        return [lead for lead in leads if lead.intent_score >= min_score]

