"""
Lead Generation API Routes

FastAPI endpoints for the lead generation system.
Integrates social monitoring, company discovery, and contact discovery.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import time
import statistics

from app.lead_generation.models import (
    SocialLead, Company, FinanceContact, Platform, IntentLevel
)
from app.lead_generation.social.twitter import TwitterScraper
from app.lead_generation.social.reddit import RedditScraper
from app.lead_generation.social.forums import ForumScraper
from app.lead_generation.company.discovery import CompanyDiscoveryService
from app.lead_generation.contacts.orchestrator import ContactDiscoveryOrchestrator
from app.lead_generation.contacts.email import EmailPatternGenerator
from app.lead_generation.storage.database import LeadDatabase
from app.lead_generation.config import get_config, set_config
from app.lead_generation.social.base import BaseSocialScraper

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
db = LeadDatabase()
db.initialize()
AUDIT_ACTOR = "system"

# Basic in-memory metrics
metrics: Dict[str, Any] = {
    "request_count": 0,
    "error_count": 0,
    "high_intent_count": 0,
    "latency_ms": [],  # rolling store
}


def record_metrics(latency_ms: float, success: bool = True, high_intent: int = 0):
    """Record simple metrics for observability."""
    metrics["request_count"] += 1
    if not success:
        metrics["error_count"] += 1
    metrics["high_intent_count"] += high_intent
    metrics["latency_ms"].append(latency_ms)
    # Trim to last 500 samples to avoid unbounded growth
    if len(metrics["latency_ms"]) > 500:
        metrics["latency_ms"] = metrics["latency_ms"][-500:]


# =============================================================================
# Request/Response Models
# =============================================================================

class SocialSearchRequest(BaseModel):
    """Request for social media search"""
    platforms: List[str] = Field(default=["twitter", "reddit"])
    keywords: Optional[List[str]] = None
    max_results: int = Field(default=50, ge=1, le=500)


class SocialSearchResponse(BaseModel):
    """Response from social search"""
    success: bool
    total_results: int
    high_intent_count: int
    leads: List[Dict[str, Any]]
    platforms_searched: List[str]
    search_timestamp: str


class CompanySearchRequest(BaseModel):
    """Request for company discovery"""
    company_names: List[str]
    discover_websites: bool = True
    enrich: bool = True


class CompanySearchResponse(BaseModel):
    """Response from company search"""
    success: bool
    total_found: int
    target_matches: int
    companies: List[Dict[str, Any]]


class ContactSearchRequest(BaseModel):
    """Request for contact discovery"""
    company_name: str
    company_domain: Optional[str] = None
    company_website: Optional[str] = None
    # Omit entirely to fall back to config.company.target_titles (CLI / older callers).
    # An explicit empty list is invalid and must not be replaced with defaults.
    target_titles: Optional[List[str]] = None
    max_results: int = Field(default=10, ge=1, le=50)
    find_emails: bool = True

    @field_validator("company_name")
    @classmethod
    def company_name_must_be_non_blank(cls, value: str) -> str:
        trimmed = (value or "").strip()
        if not trimmed:
            raise ValueError("company_name cannot be blank")
        return trimmed

    @field_validator("company_domain", "company_website", mode="before")
    @classmethod
    def empty_optional_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = str(value).strip()
        return trimmed or None

    @field_validator("target_titles", mode="before")
    @classmethod
    def normalize_target_titles(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("target_titles must be a list of strings")
        cleaned: List[str] = []
        seen = set()
        for item in value:
            if item is None:
                continue
            title = str(item).strip()
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(title)
        return cleaned

    @field_validator("target_titles")
    @classmethod
    def target_titles_must_not_be_empty_if_provided(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is not None and len(value) == 0:
            raise ValueError("target_titles must contain at least one meaningful title")
        return value


class ContactSearchResponse(BaseModel):
    """Response from contact search"""
    success: bool
    company_name: str
    contacts_found: int
    contacts: List[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)


class EmailGenerateRequest(BaseModel):
    """Request for email generation"""
    first_name: str
    last_name: str
    company_domain: str
    num_patterns: int = Field(default=5, ge=1, le=10)


class EmailGenerateResponse(BaseModel):
    """Response from email generation"""
    success: bool
    contact_name: str
    company_domain: str
    best_guess: Optional[str]
    candidates: List[Dict[str, Any]]


class LeadStatsResponse(BaseModel):
    """Lead generation statistics"""
    total_social_leads: int
    high_intent_leads: int
    total_companies: int
    target_companies: int
    total_contacts: int
    contacts_with_email: int


class SearchProviderUpdate(BaseModel):
    """Update search provider (serpapi, google_cse, dummy)"""
    provider: str = Field(..., pattern="^(serpapi|google_cse|dummy)$")


# =============================================================================
# Social Monitoring Endpoints
# =============================================================================

@router.post("/social/search", response_model=SocialSearchResponse)
async def search_social_media(request: SocialSearchRequest):
    """
    Search social media platforms for buying intent signals.
    
    Searches Twitter, Reddit, and forums for posts mentioning
    AR automation, O2C software, and related topics.
    """
    all_leads = []
    platforms_searched = []
    start_time = time.perf_counter()
    success = True
    
    try:
        if "twitter" in request.platforms:
            platforms_searched.append("twitter")
            scraper = TwitterScraper()
            
            if request.keywords:
                for keyword in request.keywords[:3]:  # Limit keywords
                    leads = scraper.search(keyword, request.max_results // 3)
                    leads = [scraper.score_lead(l) for l in leads]
                    all_leads.extend(leads)
            else:
                leads = scraper.search_all_queries(request.max_results // 5)
                all_leads.extend(leads)
        
        if "reddit" in request.platforms:
            platforms_searched.append("reddit")
            scraper = RedditScraper()
            
            queries = request.keywords or ["accounts receivable", "order to cash"]
            for query in queries[:2]:
                leads = scraper.search_all_subreddits(query, max_per_sub=10)
                all_leads.extend(leads)
        
        if "forums" in request.platforms:
            platforms_searched.append("forums")
            scraper = ForumScraper()
            
            query = " ".join(request.keywords) if request.keywords else "AR automation software"
            leads = scraper.search(query, request.max_results)
            leads = [scraper.score_lead(l) for l in leads]
            all_leads.extend(leads)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_leads = []
        for lead in all_leads:
            if lead.url not in seen_urls:
                seen_urls.add(lead.url)
                unique_leads.append(lead)
        
        # Sort by intent score
        unique_leads.sort(key=lambda x: x.intent_score, reverse=True)
        
        # Save to database
        db.insert_social_leads_batch(unique_leads)
        
        high_intent = [l for l in unique_leads if l.intent_score >= 0.5]

        # Audit
        db.insert_audit_event(actor=AUDIT_ACTOR, action="social_search", entity_type="social_leads", entity_id=None, metadata={
            "platforms": platforms_searched,
            "total": len(unique_leads),
            "high_intent": len(high_intent),
        })
        
        return SocialSearchResponse(
            success=True,
            total_results=len(unique_leads),
            high_intent_count=len(high_intent),
            leads=[lead.model_dump() for lead in unique_leads[:100]],  # Limit response
            platforms_searched=platforms_searched,
            search_timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        success = False
        logger.error(f"Social search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        # Capture high intent count if available
        high_intent_count = len([l for l in all_leads if getattr(l, "intent_score", 0) >= 0.5]) if all_leads else 0
        record_metrics(duration_ms, success=success, high_intent=high_intent_count)


@router.get("/social/leads")
async def get_social_leads(
    platform: Optional[str] = None,
    min_intent: Optional[float] = Query(None, ge=0, le=1),
    status: Optional[str] = None,
    since_days: Optional[int] = Query(None, ge=1, le=90),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("intent_score"),
    sort_order: str = Query("desc")
):
    """
    Get stored social leads with optional filters.
    """
    try:
        data = db.get_social_leads(
            platform=platform,
            min_intent_score=min_intent,
            status=status,
            since_days=since_days,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return {"success": True, "count": data["total"], "leads": data["leads"]}
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Company Discovery Endpoints
# =============================================================================

@router.post("/companies/discover", response_model=CompanySearchResponse)
async def discover_companies(request: CompanySearchRequest):
    """
    Discover company information including websites and enrichment.
    """
    try:
        service = CompanyDiscoveryService()
        
        companies = []
        for name in request.company_names:
            company = Company(name=name, source="api_request")
            
            if request.discover_websites:
                discovered = service.discover_company_website(name)
                company.domain = discovered.domain
                company.website = discovered.website
                company.linkedin_url = discovered.linkedin_url
            
            if request.enrich:
                company = service.enrich_company(company)
            
            service.matches_target_profile(company)
            companies.append(company)
            
            # Save to database
            db.insert_company(company)
            db.insert_audit_event(actor=AUDIT_ACTOR, action="company_discover", entity_type="company", entity_id=company.id or company.name, metadata={"is_target": company.is_target_profile})
        
        target_matches = len([c for c in companies if c.is_target_profile])
        
        return CompanySearchResponse(
            success=True,
            total_found=len(companies),
            target_matches=target_matches,
            companies=[c.model_dump() for c in companies]
        )
    
    except Exception as e:
        logger.error(f"Company discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies")
async def get_companies(
    industry: Optional[str] = None,
    is_target: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("target_score"),
    sort_order: str = Query("desc")
):
    """
    Get stored companies with optional filters.
    """
    try:
        data = db.get_companies(
            industry=industry,
            is_target=is_target,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return {"success": True, "count": data["total"], "companies": data["companies"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Contact Discovery Endpoints
# =============================================================================

@router.post("/contacts/discover", response_model=ContactSearchResponse)
async def discover_contacts(request: ContactSearchRequest):
    """
    Discover contacts for a company using the production pipeline:
    trusted domain → Prospeo (when available) → employer/title checks →
    website fallback → email strategy → persist.
    """
    try:
        orchestrator = ContactDiscoveryOrchestrator(db=db)
        outcome = orchestrator.discover(
            company_name=request.company_name,
            company_domain=request.company_domain,
            company_website=request.company_website,
            target_titles=request.target_titles,
            max_results=request.max_results,
            find_emails=request.find_emails,
        )
        return ContactSearchResponse(
            success=True,
            company_name=request.company_name,
            contacts_found=len(outcome.contacts),
            contacts=[c.model_dump() for c in outcome.contacts],
            warnings=outcome.warnings,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Contact discovery error: {e}")
        raise HTTPException(status_code=500, detail="Contact discovery failed")


@router.get("/contacts")
async def get_contacts(
    company: Optional[str] = None,
    seniority: Optional[str] = None,
    has_email: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("relevance_score"),
    sort_order: str = Query("desc")
):
    """
    Get stored contacts with optional filters.
    """
    try:
        data = db.get_contacts(
            company_name=company,
            seniority=seniority,
            has_email=has_email,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return {"success": True, "count": data["total"], "contacts": data["contacts"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Email Generation Endpoint
# =============================================================================

@router.post("/email/generate", response_model=EmailGenerateResponse)
async def generate_email_candidates(request: EmailGenerateRequest):
    """
    Generate email address candidates for a contact.
    
    Uses common corporate email patterns to generate likely addresses.
    """
    try:
        generator = EmailPatternGenerator()
        
        result = generator.generate_and_validate(
            first_name=request.first_name,
            last_name=request.last_name,
            domain=request.company_domain,
            num_patterns=request.num_patterns
        )
        db.insert_audit_event(actor=AUDIT_ACTOR, action="email_generate", entity_type="contact", entity_id=None, metadata={"company_domain": request.company_domain})
        
        return EmailGenerateResponse(
            success=True,
            contact_name=f"{request.first_name} {request.last_name}",
            company_domain=request.company_domain,
            best_guess=result.best_guess,
            candidates=[c.model_dump() for c in result.candidates]
        )
    
    except Exception as e:
        logger.error(f"Email generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Statistics Endpoint
# =============================================================================

@router.get("/stats", response_model=LeadStatsResponse)
async def get_lead_generation_stats():
    """
    Get lead generation statistics.
    """
    try:
        stats = db.get_stats()
        return LeadStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Configuration Endpoint
# =============================================================================

@router.get("/config")
async def get_lead_generation_config():
    """
    Get current lead generation configuration.
    """
    config = get_config()
    return {
        "intent_keywords": config.social.intent_keywords,
        "product_keywords": config.social.product_keywords,
        "reddit_subreddits": config.social.reddit_subreddits,
        "target_industries": config.company.target_industries,
        "target_titles": config.company.target_titles,
        "min_revenue_usd": config.company.min_revenue_usd,
        "search_provider": config.social.search_provider,
        "enable_serpapi": getattr(config, "enable_serpapi", False),
        "enable_google_cse": getattr(config, "enable_google_cse", False),
        "has_serpapi_key": bool(config.social.serpapi_api_key),
        "has_google_cse": bool(config.social.google_cse_key and config.social.google_cse_cx),
    }


@router.post("/config/search-provider")
async def update_search_provider(update: SearchProviderUpdate):
    """
    Update the search provider used for forum/intent search.
    Allowed: serpapi, google_cse, dummy.
    """
    config = get_config()
    config.social.search_provider = update.provider
    set_config(config)
    return {"success": True, "search_provider": config.social.search_provider}


@router.get("/metrics")
async def get_metrics():
    """Expose lightweight in-memory metrics."""
    latency = metrics.get("latency_ms", [])
    avg_latency = statistics.mean(latency) if latency else 0
    p95_latency = statistics.quantiles(latency, n=20)[18] if len(latency) >= 20 else (max(latency) if latency else 0)
    return {
        "request_count": metrics.get("request_count", 0),
        "error_count": metrics.get("error_count", 0),
        "high_intent_count": metrics.get("high_intent_count", 0),
        "avg_latency_ms": round(avg_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "samples": len(latency),
    }

