"""Intent Search API Routes - Web scraping for intent signals"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.services.web_search import web_search_service, SearchResult

router = APIRouter()


class IntentSearchRequest(BaseModel):
    """Request for intent search"""
    keywords: List[str]
    time_range: str = "24h"  # 24h, 7d, 30d
    max_results: int = 20


class IntentSearchResponse(BaseModel):
    """Response with search results"""
    success: bool
    query: str
    results: List[SearchResult]
    total_results: int
    sources: List[str]


@router.post("/search", response_model=IntentSearchResponse)
async def search_intent_signals(request: IntentSearchRequest):
    """
    Search the web for intent signals based on keywords.
    Returns posts, articles, and discussions from the last 24 hours.
    """
    try:
        # Map time range to API params
        date_restrict_map = {
            "24h": "d1",
            "7d": "w1",
            "30d": "m1",
        }
        date_restrict = date_restrict_map.get(request.time_range, "d1")
        
        # Add Chillion-specific keywords to improve relevance
        enhanced_keywords = request.keywords + [
            "IT infrastructure",
            "cyber security",
            "cloud migration",
            "managed services",
            "defense electronics",
            "network monitoring",
        ]
        
        # Search across sources
        results = await web_search_service.search_all(
            keywords=enhanced_keywords[:10],  # Limit keywords
            num_results=request.max_results,
        )
        
        # Get unique sources
        sources = list(set(r.source for r in results if r.source))
        
        return IntentSearchResponse(
            success=True,
            query=" OR ".join(request.keywords),
            results=results,
            total_results=len(results),
            sources=sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending_topics():
    """
    Get trending topics related to enterprise IT and engineering programs.
    Pre-defined search for common Chillion-related signals.
    """
    default_keywords = [
        "IT infrastructure upgrade",
        "cyber security managed services",
        "cloud migration government",
        "network monitoring AMC",
        "defense electronics procurement",
        "CAD CAM software licensing",
        "data center modernization",
    ]
    
    results = await web_search_service.search_all(
        keywords=default_keywords,
        num_results=15,
    )
    
    return {
        "success": True,
        "trending_keywords": default_keywords,
        "results": results,
        "total": len(results),
    }


@router.get("/keywords/suggestions")
async def get_keyword_suggestions():
    """
    Get suggested keywords for intent monitoring.
    """
    return {
        "categories": {
            "products": [
                "IT infrastructure AMC",
                "cyber security IDS IPS",
                "cloud data center migration",
                "ANSYS simulation licensing",
                "defense PCB engineering",
                "optics photonics manufacturing",
                "RF microwave antenna systems",
            ],
            "pain_points": [
                "infrastructure downtime",
                "vendor fragmentation",
                "security compliance gaps",
                "slow cloud adoption",
                "engineering capacity constraints",
                "long procurement cycles",
            ],
            "buyer_signals": [
                "looking for IT infrastructure partner",
                "evaluating cyber security vendors",
                "government IT tender",
                "defense program sourcing",
                "software licensing RFP",
                "AMC contract renewal",
            ],
            "competitors": [
                "system integrator alternative",
                "managed services provider",
                "infrastructure vendor comparison",
            ],
        }
    }

