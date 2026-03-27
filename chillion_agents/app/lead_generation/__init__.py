"""
Chillion Lead Generation System

A modular Python system for:
- Social media and forum monitoring for buying intent signals
- Company and finance decision maker discovery
- Email address generation and validation

Key Components:
- social/: Twitter, Reddit, and forum scrapers
- company/: Company discovery and enrichment
- contacts/: Contact discovery and email generation
- storage/: SQLite database and CSV export

Example usage:
    from app.lead_generation.social.twitter import TwitterScraper
    from app.lead_generation.social.reddit import RedditScraper
    from app.lead_generation.company.discovery import CompanyDiscoveryService
    from app.lead_generation.contacts.discovery import ContactDiscoveryService
    from app.lead_generation.storage.database import LeadDatabase
    
    # Run social monitoring
    twitter = TwitterScraper()
    leads = twitter.search_all_queries()
    
    # Discover companies
    company_service = CompanyDiscoveryService()
    companies = company_service.load_from_csv("companies.csv")
    
    # Discover contacts
    contact_service = ContactDiscoveryService()
    contacts = contact_service.discover_contacts(company)
    
    # Persist data
    db = LeadDatabase()
    db.initialize()
    db.insert_social_leads_batch(leads)
"""

from .config import (
    get_config,
    load_config,
    set_config,
    LeadGenerationConfig,
)

from .models import (
    SocialLead,
    TwitterLead,
    RedditLead,
    ForumLead,
    Company,
    FinanceContact,
    EmailCandidate,
    EmailDiscoveryResult,
    Platform,
    IntentLevel,
    LeadStatus,
)

__version__ = "1.0.0"
__all__ = [
    # Config
    "get_config",
    "load_config", 
    "set_config",
    "LeadGenerationConfig",
    # Models
    "SocialLead",
    "TwitterLead",
    "RedditLead", 
    "ForumLead",
    "Company",
    "FinanceContact",
    "EmailCandidate",
    "EmailDiscoveryResult",
    "Platform",
    "IntentLevel",
    "LeadStatus",
]

