"""Web Search Service - Real-time intent signal discovery"""
import httpx
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.config import settings


class SearchResult(BaseModel):
    """Search result model"""
    title: str
    url: str
    snippet: str
    source: str
    published_date: Optional[str] = None
    platform: str = "web"


class WebSearchService:
    """Service for searching the web for intent signals"""
    
    def __init__(self):
        self.google_api_key = settings.google_api_key
        self.google_cx = settings.google_search_cx  # Custom Search Engine ID
        self.news_api_key = settings.news_api_key
    
    async def search_google(
        self,
        query: str,
        num_results: int = 10,
        date_restrict: str = "d1"  # d1 = last 24 hours
    ) -> List[SearchResult]:
        """
        Search using Google Custom Search API
        date_restrict: d1 (1 day), w1 (1 week), m1 (1 month)
        """
        if not self.google_api_key or not self.google_cx:
            print("Google Search API not configured, using mock data")
            return self._get_mock_results(query)
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": query,
            "num": min(num_results, 10),
            "dateRestrict": date_restrict,
            "sort": "date",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("items", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("displayLink", ""),
                        platform="google"
                    ))
                return results
            except Exception as e:
                print(f"Google Search error: {e}")
                return self._get_mock_results(query)
    
    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        from_date: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search using News API for recent articles
        """
        if not self.news_api_key:
            print("News API not configured, using mock data")
            return self._get_mock_news_results(query)
        
        if not from_date:
            from_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": self.news_api_key,
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "pageSize": num_results,
            "language": "en",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for article in data.get("articles", []):
                    results.append(SearchResult(
                        title=article.get("title", ""),
                        url=article.get("url", ""),
                        snippet=article.get("description", ""),
                        source=article.get("source", {}).get("name", ""),
                        published_date=article.get("publishedAt"),
                        platform="news"
                    ))
                return results
            except Exception as e:
                print(f"News API error: {e}")
                return self._get_mock_news_results(query)
    
    async def search_all(
        self,
        keywords: List[str],
        num_results: int = 20
    ) -> List[SearchResult]:
        """
        Search across all sources for intent signals
        """
        all_results = []
        query = " OR ".join(keywords)
        
        # Search Google
        google_results = await self.search_google(query, num_results // 2)
        all_results.extend(google_results)
        
        # Search News
        news_results = await self.search_news(query, num_results // 2)
        all_results.extend(news_results)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        return unique_results[:num_results]
    
    def _get_mock_results(self, query: str) -> List[SearchResult]:
        """Return mock results for testing without API keys"""
        return [
            SearchResult(
                title="CFO discusses AR automation challenges at Finance Summit 2024",
                url="https://example.com/finance-summit-ar",
                snippet="Leading CFOs are struggling with manual accounts receivable processes. Many are looking at AI-powered solutions to reduce DSO and improve cash flow...",
                source="finance-weekly.com",
                platform="google"
            ),
            SearchResult(
                title="Enterprise companies seek order-to-cash automation solutions",
                url="https://example.com/o2c-automation",
                snippet="Survey shows 78% of finance leaders plan to invest in order-to-cash automation within the next 12 months. Key pain points include manual invoice processing...",
                source="business-tech.com",
                platform="google"
            ),
            SearchResult(
                title="LinkedIn post: 'Tired of spreadsheet-based collections'",
                url="https://linkedin.com/posts/cfo-john-doe",
                snippet="Our AR team spends 60% of their time on manual follow-ups. There has to be a better way. Anyone using AI for collections? #FinanceAutomation #AR",
                source="linkedin.com",
                platform="google"
            ),
            SearchResult(
                title="Deductions management: The hidden cost in enterprise finance",
                url="https://example.com/deductions-cost",
                snippet="Companies lose an average of 2-3% of revenue to unresolved deductions. Automated deductions management can recover up to 80% of this lost revenue...",
                source="cfo-magazine.com",
                platform="google"
            ),
            SearchResult(
                title="Reddit: Best practices for reducing DSO?",
                url="https://reddit.com/r/accounting/dso-reduction",
                snippet="We're a mid-market company with DSO hovering around 55 days. Looking for tools or strategies to bring this down. Manual follow-ups aren't scaling...",
                source="reddit.com",
                platform="google"
            ),
        ]
    
    def _get_mock_news_results(self, query: str) -> List[SearchResult]:
        """Return mock news results for testing"""
        return [
            SearchResult(
                title="AI transforms accounts receivable: 2024 trends report",
                url="https://news.example.com/ai-ar-trends",
                snippet="New research shows AI-powered AR solutions can reduce DSO by 25-40% and improve cash application accuracy to over 90%...",
                source="Finance News Today",
                published_date=datetime.utcnow().isoformat(),
                platform="news"
            ),
            SearchResult(
                title="Major retailer implements order-to-cash automation",
                url="https://news.example.com/retailer-o2c",
                snippet="Fortune 500 retailer reports 35% improvement in collections efficiency after deploying AI-powered order-to-cash platform...",
                source="Enterprise Tech Weekly",
                published_date=datetime.utcnow().isoformat(),
                platform="news"
            ),
        ]


# Singleton instance
web_search_service = WebSearchService()

