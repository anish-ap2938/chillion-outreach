"""
Lead Generation Configuration Module

Centralizes all configuration for the lead generation system including:
- Search keywords and phrases
- Target industries and company profiles
- Rate limits and proxy settings
- Database paths
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from pathlib import Path
import os


class SocialSearchConfig(BaseModel):
    """Configuration for social media and forum searches"""
    
    # Intent keywords - phrases that indicate buying intent
    intent_keywords: List[str] = Field(default=[
        "looking for",
        "recommend",
        "recommendations for",
        "what tool do you use",
        "need a better system",
        "best software for",
        "tool for",
        "anyone use",
        "suggestions for",
        "switching from",
        "alternative to",
        "considering",
        "evaluating",
        "in the market for",
    ])
    
    # Product category keywords - Chillion's domain
    product_keywords: List[str] = Field(default=[
        "IT infrastructure",
        "enterprise servers",
        "data center",
        "cloud migration",
        "cyber security",
        "network monitoring",
        "managed services",
        "AMC support",
        "CAD CAM",
        "ANSYS simulation",
        "defense electronics",
        "PCB design",
        "optics photonics",
        "RF microwave",
        "antenna systems",
        "software licensing",
        "HPC computing",
        "government IT procurement",
        "GeM portal",
        "surveillance systems",
    ])
    
    # Reddit subreddits to monitor
    reddit_subreddits: List[str] = Field(default=[
        "sysadmin",
        "networking",
        "cybersecurity",
        "devops",
        "engineering",
        "MechanicalEngineering",
        "ElectricalEngineering",
        "IndiaTech",
        "smallbusiness",
        "Entrepreneur",
    ])
    
    # Twitter/X search settings
    twitter_max_results: int = 100
    twitter_days_back: int = 7
    
    # Reddit search settings
    reddit_max_results: int = 100
    reddit_time_filter: str = "week"  # hour, day, week, month, year, all
    
    # Generic forum/search settings
    generic_search_max_results: int = 50

    # Provider toggles
    twitter_provider: str = "snscrape"  # options: snscrape, api, provider
    reddit_use_praw: bool = False
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None

    # Optional external search providers (placeholders; kept off by default)
    search_provider: str = "dummy"  # options: dummy, serpapi, google_cse
    serpapi_api_key: Optional[str] = None
    google_cse_key: Optional[str] = None
    google_cse_cx: Optional[str] = None


class CompanyTargetConfig(BaseModel):
    """Configuration for target company profile"""
    
    # Target industries
    target_industries: List[str] = Field(default=[
        "Defense",
        "Government",
        "Aerospace",
        "Manufacturing",
        "Telecom",
        "Industrial",
        "Enterprise IT",
        "Research",
        "Healthcare",
        "Energy",
    ])
    
    # Target company size (revenue in USD)
    min_revenue_usd: int = 50_000_000  # $50M
    max_revenue_usd: Optional[int] = None  # No upper limit
    
    # Target employee count
    min_employees: int = 100
    max_employees: Optional[int] = None
    
    # Geographic focus
    target_countries: List[str] = Field(default=["India", "IN"])
    
    # Decision-maker titles to look for
    target_titles: List[str] = Field(default=[
        "Chief Technology Officer",
        "CTO",
        "Chief Information Officer",
        "CIO",
        "IT Director",
        "Director IT",
        "Head of IT",
        "VP Infrastructure",
        "Infrastructure Manager",
        "Network Manager",
        "Security Manager",
        "Procurement Manager",
        "Program Manager",
        "Project Manager",
        "Director Engineering",
        "Head of Engineering",
        "Defense Program Manager",
        "Technical Director",
    ])


class RateLimitConfig(BaseModel):
    """Rate limiting and request settings"""
    
    # Delay between requests (seconds)
    request_delay_seconds: float = 1.0
    
    # Max requests per minute
    max_requests_per_minute: int = 30
    
    # Timeout for HTTP requests
    request_timeout_seconds: int = 30
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    
    # User agent for requests
    user_agent: str = "Mozilla/5.0 (compatible; ChillionLeadGen/1.0; Research Bot)"
    
    # Proxy settings (optional)
    proxy_url: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None

    # Scheduler toggle
    enable_scheduler: bool = False
    scheduler_interval_minutes: int = 60


class StorageConfig(BaseModel):
    """Database and storage configuration"""
    
    # SQLite database path
    database_path: Path = Field(default=Path("./data/leads.db"))
    
    # CSV export directory
    csv_export_dir: Path = Field(default=Path("./data/exports"))
    
    # Enable deduplication
    deduplicate_leads: bool = True
    
    # Max records per CSV file
    csv_max_records: int = 10000


class LeadGenerationConfig(BaseModel):
    """Master configuration for the lead generation system"""
    
    social: SocialSearchConfig = Field(default_factory=SocialSearchConfig)
    company: CompanyTargetConfig = Field(default_factory=CompanyTargetConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    
    # Logging level
    log_level: str = "INFO"
    
    # Enable/disable specific modules
    enable_twitter: bool = True
    enable_reddit: bool = True
    enable_forums: bool = True
    enable_serpapi: bool = False
    enable_google_cse: bool = False
    enable_company_discovery: bool = True
    
    class Config:
        env_prefix = "LEADGEN_"


def load_config(config_path: Optional[str] = None) -> LeadGenerationConfig:
    """
    Load configuration from file or environment variables.
    
    Args:
        config_path: Optional path to JSON/YAML config file
        
    Returns:
        LeadGenerationConfig instance
    """
    if config_path and os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            data = json.load(f)
        return LeadGenerationConfig(**data)
    
    # Return default config
    return LeadGenerationConfig()


# Default global config instance
_config: Optional[LeadGenerationConfig] = None


def get_config() -> LeadGenerationConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: LeadGenerationConfig) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config

