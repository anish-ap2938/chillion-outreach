"""
Reddit Scraper Module

Searches Reddit for posts and comments indicating buying intent for AR/O2C software.
Uses PRAW (Python Reddit API Wrapper) or Reddit's JSON API.

Note: For production use, register an app at https://www.reddit.com/prefs/apps
and provide credentials for higher rate limits.
"""

from typing import List, Optional
from datetime import datetime, timedelta
import logging
import time
import requests

from .base import BaseSocialScraper
from ..models import SocialLead, RedditLead, Platform
from ..config import SocialSearchConfig, get_config

logger = logging.getLogger(__name__)

# Try to import PRAW
PRAW_AVAILABLE = False
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    logger.info("PRAW not installed. Using Reddit JSON API instead.")


class RedditScraper(BaseSocialScraper):
    """
    Reddit scraper for finding buying intent signals.
    
    Can use either PRAW (if installed and configured) or Reddit's
    public JSON API which doesn't require authentication.
    
    Example usage:
        scraper = RedditScraper()
        leads = scraper.search('"accounts receivable" automation', max_results=50)
        
        # Search specific subreddits
        leads = scraper.search_subreddit('accounting', 'AR automation')
        
        # Or search all configured queries
        all_leads = scraper.search_all_queries()
    """
    
    platform = Platform.REDDIT
    
    def __init__(
        self,
        config: Optional[SocialSearchConfig] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize Reddit scraper.
        
        Args:
            config: Social search configuration
            client_id: Reddit API client ID (for PRAW)
            client_secret: Reddit API client secret (for PRAW)
            user_agent: Custom user agent string
        """
        super().__init__(config)
        
        cfg = get_config()
        self.user_agent = user_agent or cfg.rate_limit.user_agent
        self.subreddits = self.config.reddit_subreddits
        self.time_filter = self.config.reddit_time_filter
        
        # Try to initialize PRAW if requested in config or explicitly provided
        self.reddit = None
        praw_id = client_id or self.config.reddit_client_id
        praw_secret = client_secret or self.config.reddit_client_secret
        if PRAW_AVAILABLE and (self.config.reddit_use_praw or (praw_id and praw_secret)):
            if praw_id and praw_secret:
                try:
                    self.reddit = praw.Reddit(
                        client_id=praw_id,
                        client_secret=praw_secret,
                        user_agent=self.user_agent,
                    )
                    self.logger.info("Initialized PRAW Reddit client")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize PRAW: {e}")
            else:
                self.logger.warning("PRAW enabled but no credentials provided; falling back to JSON API")
    
    def search(self, query: str, max_results: int = 100) -> List[SocialLead]:
        """
        Search Reddit for posts/comments matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum results to return
            
        Returns:
            List of RedditLead objects
        """
        if self.reddit:
            return self._search_with_praw(query, max_results)
        else:
            return self._search_with_json_api(query, max_results)
    
    def search_subreddit(
        self,
        subreddit: str,
        query: str,
        max_results: int = 50
    ) -> List[SocialLead]:
        """
        Search within a specific subreddit.
        
        Args:
            subreddit: Subreddit name (without r/)
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of RedditLead objects
        """
        if self.reddit:
            return self._search_subreddit_praw(subreddit, query, max_results)
        else:
            return self._search_subreddit_json(subreddit, query, max_results)
    
    def get_post_by_id(self, post_id: str) -> Optional[SocialLead]:
        """
        Fetch a specific Reddit post by ID.
        
        Args:
            post_id: Reddit post ID (without t3_ prefix)
            
        Returns:
            RedditLead if found, None otherwise
        """
        try:
            url = f"https://www.reddit.com/comments/{post_id}.json"
            headers = {"User-Agent": self.user_agent}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                post_data = data[0]["data"]["children"][0]["data"]
                return self._json_post_to_lead(post_data)
        except Exception as e:
            self.logger.error(f"Error fetching post {post_id}: {e}")
        
        return None
    
    # =========================================================================
    # PRAW-based methods
    # =========================================================================
    
    def _search_with_praw(self, query: str, max_results: int) -> List[RedditLead]:
        """Search using PRAW library"""
        leads = []
        
        try:
            results = self.reddit.subreddit("all").search(
                query,
                time_filter=self.time_filter,
                limit=max_results,
            )
            
            for submission in results:
                lead = self._praw_submission_to_lead(submission)
                leads.append(lead)
        
        except Exception as e:
            self.logger.error(f"PRAW search error: {e}")
        
        return leads
    
    def _search_subreddit_praw(
        self,
        subreddit: str,
        query: str,
        max_results: int
    ) -> List[RedditLead]:
        """Search specific subreddit using PRAW"""
        leads = []
        
        try:
            sub = self.reddit.subreddit(subreddit)
            results = sub.search(query, time_filter=self.time_filter, limit=max_results)
            
            for submission in results:
                lead = self._praw_submission_to_lead(submission)
                leads.append(lead)
        
        except Exception as e:
            self.logger.error(f"PRAW subreddit search error: {e}")
        
        return leads
    
    def _praw_submission_to_lead(self, submission) -> RedditLead:
        """Convert PRAW submission to RedditLead"""
        author_name = submission.author.name if submission.author else "[deleted]"
        
        source_meta = {
            "subreddit": submission.subreddit.display_name,
            "post_id": submission.id,
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "is_comment": False,
            "flair": submission.link_flair_text,
        }
        
        return RedditLead(
            id=self.generate_lead_id("reddit", submission.id),
            url=f"https://reddit.com{submission.permalink}",
            source_id=submission.id,
            author_username=author_name,
            author_profile_url=f"https://reddit.com/user/{author_name}",
            title=submission.title,
            text=submission.selftext or submission.title,
            text_excerpt=self.truncate_text(submission.selftext or submission.title),
            created_at=datetime.fromtimestamp(submission.created_utc),
            source_meta=source_meta,
        )
    
    # =========================================================================
    # JSON API-based methods (no auth required)
    # =========================================================================
    
    def _search_with_json_api(self, query: str, max_results: int) -> List[RedditLead]:
        """Search using Reddit's public JSON API"""
        leads = []
        
        # Search across all configured subreddits
        for subreddit in self.subreddits:
            try:
                sub_leads = self._search_subreddit_json(subreddit, query, max_results // len(self.subreddits))
                leads.extend(sub_leads)
            except Exception as e:
                self.logger.error(f"Error searching r/{subreddit}: {e}")
            
            # Rate limiting
            time.sleep(1)
        
        return leads[:max_results]
    
    def _search_subreddit_json(
        self,
        subreddit: str,
        query: str,
        max_results: int
    ) -> List[RedditLead]:
        """Search subreddit using JSON API"""
        leads = []
        
        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                "q": query,
                "restrict_sr": "true",
                "sort": "relevance",
                "t": self.time_filter,
                "limit": min(max_results, 100),
            }
            headers = {"User-Agent": self.user_agent}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            for post in posts:
                lead = self._json_post_to_lead(post["data"])
                leads.append(lead)
            
            self.logger.info(f"Found {len(leads)} posts in r/{subreddit}")
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for r/{subreddit}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing r/{subreddit}: {e}")
        
        return leads
    
    def _json_post_to_lead(self, post_data: dict) -> RedditLead:
        """Convert JSON API post data to RedditLead"""
        author = post_data.get("author", "[deleted]")
        subreddit = post_data.get("subreddit", "")
        post_id = post_data.get("id", "")
        
        source_meta = {
            "subreddit": subreddit,
            "post_id": post_id,
            "score": post_data.get("score", 0),
            "upvote_ratio": post_data.get("upvote_ratio", 0),
            "num_comments": post_data.get("num_comments", 0),
            "is_comment": False,
            "flair": post_data.get("link_flair_text"),
            "is_self": post_data.get("is_self", True),
        }
        
        title = post_data.get("title", "")
        selftext = post_data.get("selftext", "")
        
        return RedditLead(
            id=self.generate_lead_id("reddit", post_id),
            url=f"https://reddit.com{post_data.get('permalink', '')}",
            source_id=post_id,
            author_username=author,
            author_profile_url=f"https://reddit.com/user/{author}" if author != "[deleted]" else None,
            title=title,
            text=selftext or title,
            text_excerpt=self.truncate_text(selftext or title),
            created_at=datetime.fromtimestamp(post_data.get("created_utc", 0)),
            source_meta=source_meta,
        )
    
    # =========================================================================
    # Query Building
    # =========================================================================
    
    def build_search_queries(self):
        """
        Build Reddit-optimized search queries.
        
        Reddit search is simpler than Twitter - basic keyword matching.
        """
        queries = []
        
        # Product-focused queries
        for product in self.config.product_keywords[:8]:
            queries.append(f'"{product}"')
        
        # Intent + product combinations (limited to avoid rate limits)
        intent_keywords = ["looking for", "recommend", "best", "what tool"]
        for intent in intent_keywords:
            for product in self.config.product_keywords[:4]:
                queries.append(f'{intent} {product}')
        
        for query in queries:
            yield query
    
    def search_all_subreddits(self, query: str, max_per_sub: int = 25) -> List[SocialLead]:
        """
        Search all configured subreddits for a single query.
        
        Args:
            query: Search query
            max_per_sub: Max results per subreddit
            
        Returns:
            Aggregated list of leads
        """
        all_leads = []
        seen_ids = set()
        
        for subreddit in self.subreddits:
            self.logger.info(f"Searching r/{subreddit} for: {query}")
            try:
                leads = self.search_subreddit(subreddit, query, max_per_sub)
                for lead in leads:
                    if lead.source_id not in seen_ids:
                        seen_ids.add(lead.source_id)
                        scored = self.score_lead(lead)
                        all_leads.append(scored)
            except Exception as e:
                self.logger.error(f"Error searching r/{subreddit}: {e}")
            
            # Rate limiting between subreddits
            time.sleep(1)
        
        # Sort by intent score
        all_leads.sort(key=lambda x: x.intent_score, reverse=True)
        
        return all_leads
    
    def get_mock_results(self, max_results: int = 10) -> List[RedditLead]:
        """
        Generate mock Reddit results for testing.
        
        Returns:
            List of mock RedditLead objects
        """
        mock_posts = [
            {
                "id": "abc123",
                "subreddit": "accounting",
                "title": "Looking for accounts receivable automation software recommendations",
                "text": "We're a mid-sized company and our AR process is completely manual. Looking for recommendations for software that can help automate collections and reduce DSO. Budget is flexible for the right solution. What are you all using?",
                "author": "CFO_SeekingHelp",
                "score": 45,
            },
            {
                "id": "def456",
                "subreddit": "cfo",
                "title": "Best O2C software for consumer goods company?",
                "text": "We're evaluating order-to-cash solutions for our $200M revenue consumer goods business. Currently using SAP but need better AR automation. Anyone have experience with modern O2C platforms?",
                "author": "RetailFinanceGuy",
                "score": 32,
            },
            {
                "id": "ghi789",
                "subreddit": "finance",
                "title": "Cash application automation - worth the investment?",
                "text": "Considering implementing AI-powered cash application. Currently takes our team 3 days to match payments. Has anyone implemented automation here? What was the ROI?",
                "author": "TreasuryManager",
                "score": 67,
            },
            {
                "id": "jkl012",
                "subreddit": "Bookkeeping",
                "title": "Help with deductions management",
                "text": "We have a huge backlog of customer deductions that we can't keep up with. Manual research is killing us. Any software recommendations for deduction management?",
                "author": "ARTeamLead",
                "score": 28,
            },
            {
                "id": "mno345",
                "subreddit": "smallbusiness",
                "title": "Invoicing and collections software for growing business",
                "text": "Our business has grown to $50M and we're drowning in manual invoicing and collections. Looking for an all-in-one solution. What do larger companies use?",
                "author": "GrowingBizOwner",
                "score": 89,
            },
        ]
        
        leads = []
        for i, mock in enumerate(mock_posts[:max_results]):
            lead = RedditLead(
                id=self.generate_lead_id("reddit", mock["id"]),
                url=f"https://reddit.com/r/{mock['subreddit']}/comments/{mock['id']}",
                source_id=mock["id"],
                author_username=mock["author"],
                author_profile_url=f"https://reddit.com/user/{mock['author']}",
                title=mock["title"],
                text=mock["text"],
                text_excerpt=self.truncate_text(mock["text"]),
                created_at=datetime.now() - timedelta(hours=i * 12),
                source_meta={
                    "subreddit": mock["subreddit"],
                    "post_id": mock["id"],
                    "score": mock["score"],
                    "upvote_ratio": 0.85 + (i * 0.02),
                    "num_comments": 10 + i * 5,
                    "is_comment": False,
                    "is_mock": True,
                },
            )
            leads.append(lead)
        
        return leads

