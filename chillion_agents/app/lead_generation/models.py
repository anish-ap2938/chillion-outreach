"""
Lead Generation Data Models

Pydantic models for all lead generation entities including:
- Social leads from Twitter, Reddit, forums
- Company information
- Finance contacts
- Email discovery results
"""

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class Platform(str, Enum):
    """Social media platforms"""
    TWITTER = "twitter"
    REDDIT = "reddit"
    QUORA = "quora"
    LINKEDIN = "linkedin"
    FORUM = "forum"
    OTHER = "other"


class IntentLevel(str, Enum):
    """Buying intent classification"""
    HIGH = "high"      # Strong buying signals
    MEDIUM = "medium"  # Moderate interest
    LOW = "low"        # General discussion
    NONE = "none"      # Not relevant


class LeadStatus(str, Enum):
    """Lead processing status"""
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"
    DISQUALIFIED = "disqualified"


class ContactSource(str, Enum):
    """Source of contact information"""
    WEBSITE = "website"
    LINKEDIN = "linkedin"
    PUBLIC_FILING = "public_filing"
    PRESS_RELEASE = "press_release"
    ENRICHMENT_API = "enrichment_api"
    MANUAL = "manual"


# =============================================================================
# Social Lead Models
# =============================================================================

class SocialLead(BaseModel):
    """
    Unified model for leads captured from social media and forums.
    
    This model normalizes data from Twitter, Reddit, Quora, and other forums
    into a consistent structure for analysis and outreach.
    """
    
    # Unique identifier (generated)
    id: Optional[str] = None
    
    # Platform and source
    platform: Platform
    url: str
    source_id: Optional[str] = None  # Platform-specific ID (tweet_id, post_id, etc.)
    
    # Author information
    author_username: Optional[str] = None
    author_display_name: Optional[str] = None
    author_profile_url: Optional[str] = None
    author_bio: Optional[str] = None
    author_company: Optional[str] = None  # If self-reported
    author_title: Optional[str] = None    # If self-reported
    author_followers: Optional[int] = None
    
    # Content
    title: Optional[str] = None  # For posts/questions
    text: str
    text_excerpt: Optional[str] = None  # Truncated version
    
    # Metadata
    created_at: Optional[datetime] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Platform-specific metadata
    source_meta: Dict[str, Any] = Field(default_factory=dict)
    # Examples: subreddit, retweet_count, upvotes, etc.
    
    # Intent scoring
    intent_score: float = 0.0  # 0.0 to 1.0
    intent_level: IntentLevel = IntentLevel.NONE
    intent_keywords_matched: List[str] = Field(default_factory=list)
    product_keywords_matched: List[str] = Field(default_factory=list)
    reason_for_relevance: Optional[str] = None
    
    # Processing status
    status: LeadStatus = LeadStatus.NEW
    notes: Optional[str] = None
    
    class Config:
        use_enum_values = True


class TwitterLead(SocialLead):
    """Twitter/X specific lead with additional fields"""
    platform: Platform = Platform.TWITTER
    
    # Twitter-specific fields in source_meta:
    # - tweet_id: str
    # - retweet_count: int
    # - like_count: int
    # - reply_count: int
    # - is_retweet: bool
    # - in_reply_to: Optional[str]
    # - hashtags: List[str]
    # - mentions: List[str]


class RedditLead(SocialLead):
    """Reddit specific lead with additional fields"""
    platform: Platform = Platform.REDDIT
    
    # Reddit-specific fields in source_meta:
    # - subreddit: str
    # - post_id: str
    # - comment_id: Optional[str]
    # - score: int
    # - upvote_ratio: float
    # - num_comments: int
    # - is_comment: bool
    # - parent_post_url: Optional[str]


class ForumLead(SocialLead):
    """Generic forum/Q&A lead"""
    platform: Platform = Platform.FORUM
    
    # Forum-specific fields in source_meta:
    # - forum_name: str
    # - forum_url: str
    # - thread_title: str
    # - reply_count: int


# =============================================================================
# Company Models
# =============================================================================

class Company(BaseModel):
    """
    Company information model.
    
    Stores discovered company data including basic info,
    industry classification, and financial indicators.
    """
    
    id: Optional[str] = None
    
    # Basic info
    name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    
    # Classification
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    
    # Size indicators
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None  # e.g., "100-500"
    revenue_usd: Optional[int] = None
    revenue_range: Optional[str] = None  # e.g., "$50M-$100M"
    
    # Location
    headquarters_city: Optional[str] = None
    headquarters_state: Optional[str] = None
    headquarters_country: Optional[str] = None
    
    # Additional info
    description: Optional[str] = None
    founded_year: Optional[int] = None
    stock_symbol: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    source_url: Optional[str] = None
    
    # Enrichment data
    enrichment_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing
    is_target_profile: bool = False  # Matches our ideal customer profile
    target_score: float = 0.0  # How well it matches (0-1)
    
    class Config:
        use_enum_values = True


# =============================================================================
# Contact Models
# =============================================================================

class FinanceContact(BaseModel):
    """
    Finance decision maker contact model.
    
    Stores information about finance leaders at target companies
    including CFOs, VPs, Directors, and other key stakeholders.
    """
    
    id: Optional[str] = None
    
    # Company reference
    company_id: Optional[str] = None
    company_name: str
    company_domain: Optional[str] = None
    
    # Person info
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: str
    
    # Contact details
    email: Optional[str] = None
    email_status: Optional[str] = None  # verified, unverified, invalid
    phone: Optional[str] = None
    
    # Social profiles
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    
    # Discovery info
    source: ContactSource = ContactSource.WEBSITE
    source_url: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional context
    bio: Optional[str] = None
    seniority_level: Optional[str] = None  # C-Level, VP, Director, Manager
    department: str = "Finance"
    
    # Enrichment data
    enrichment_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing
    is_decision_maker: bool = False
    relevance_score: float = 0.0
    
    class Config:
        use_enum_values = True


# =============================================================================
# Email Discovery Models
# =============================================================================

class EmailPattern(BaseModel):
    """Email pattern template"""
    pattern_name: str  # e.g., "first.last", "firstlast", "first"
    template: str  # e.g., "{first}.{last}@{domain}"
    priority: int = 0  # Higher = more common


class EmailCandidate(BaseModel):
    """A generated email candidate"""
    email: str
    pattern_used: str
    confidence: float = 0.5  # 0-1, how likely this pattern is correct
    is_validated: bool = False
    validation_result: Optional[str] = None  # valid, invalid, unknown


class EmailDiscoveryResult(BaseModel):
    """Result of email discovery for a contact"""
    contact_name: str
    company_domain: str
    candidates: List[EmailCandidate] = Field(default_factory=list)
    best_guess: Optional[str] = None
    publicly_found_email: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Aggregated Results
# =============================================================================

class SocialSearchResults(BaseModel):
    """Aggregated results from social media searches"""
    query: str
    platforms_searched: List[str]
    total_results: int
    leads: List[SocialLead]
    high_intent_count: int
    medium_intent_count: int
    search_timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompanyDiscoveryResults(BaseModel):
    """Results from company discovery process"""
    input_count: int
    companies_found: int
    companies: List[Company]
    matching_target_profile: int
    discovery_timestamp: datetime = Field(default_factory=datetime.utcnow)


class ContactDiscoveryResults(BaseModel):
    """Results from contact discovery process"""
    company_name: str
    company_domain: Optional[str]
    contacts_found: int
    contacts: List[FinanceContact]
    decision_makers_found: int
    discovery_timestamp: datetime = Field(default_factory=datetime.utcnow)

