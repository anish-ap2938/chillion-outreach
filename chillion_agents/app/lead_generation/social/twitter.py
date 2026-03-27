"""
Twitter/X Scraper Module

Searches Twitter/X for posts indicating buying intent for AR/O2C software.
Uses snscrape library which doesn't require API authentication.

Note: snscrape may have rate limits. For production use, consider:
- Twitter API v2 with proper authentication
- Third-party data providers
"""

from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .base import BaseSocialScraper
from ..models import SocialLead, TwitterLead, Platform
from ..config import SocialSearchConfig

logger = logging.getLogger(__name__)

# Flag to track if snscrape is available
SNSCRAPE_AVAILABLE = False

try:
    import snscrape.modules.twitter as sntwitter
    SNSCRAPE_AVAILABLE = True
except ImportError:
    logger.warning(
        "snscrape not installed. Twitter scraping will use mock data. "
        "Install with: pip install snscrape"
    )


class TwitterScraper(BaseSocialScraper):
    """
    Twitter/X scraper for finding buying intent signals.
    
    Uses snscrape library for searching public tweets without API keys.
    Falls back to mock data if snscrape is not available.
    
    Example usage:
        scraper = TwitterScraper()
        leads = scraper.search('"looking for" "accounts receivable"', max_results=50)
        
        # Or search all configured queries
        all_leads = scraper.search_all_queries()
    """
    
    platform = Platform.TWITTER
    
    def __init__(self, config: Optional[SocialSearchConfig] = None):
        super().__init__(config)
        self.max_results = self.config.twitter_max_results
        self.days_back = self.config.twitter_days_back
    
    def search(self, query: str, max_results: int = 100) -> List[SocialLead]:
        """
        Search Twitter for tweets matching the query.
        
        Args:
            query: Search query (supports Twitter search operators)
            max_results: Maximum number of results to return
            
        Returns:
            List of TwitterLead objects
        """
        if not SNSCRAPE_AVAILABLE:
            self.logger.warning("Using mock Twitter data - snscrape not installed")
            return self._get_mock_results(query, max_results)
        
        leads = []
        
        try:
            # Add date filter to query
            since_date = datetime.now() - timedelta(days=self.days_back)
            date_filter = f" since:{since_date.strftime('%Y-%m-%d')}"
            full_query = query + date_filter
            
            self.logger.info(f"Searching Twitter: {full_query}")
            
            # Use snscrape to search
            scraper = sntwitter.TwitterSearchScraper(full_query)
            
            for i, tweet in enumerate(scraper.get_items()):
                if i >= max_results:
                    break
                
                lead = self._tweet_to_lead(tweet)
                leads.append(lead)
            
            self.logger.info(f"Found {len(leads)} tweets for query: {query}")
            
        except Exception as e:
            self.logger.error(f"Error searching Twitter: {e}")
            # Return mock data on error for development
            return self._get_mock_results(query, min(max_results, 5))
        
        return leads
    
    def get_post_by_id(self, post_id: str) -> Optional[SocialLead]:
        """
        Fetch a specific tweet by ID.
        
        Args:
            post_id: Twitter tweet ID
            
        Returns:
            TwitterLead if found, None otherwise
        """
        if not SNSCRAPE_AVAILABLE:
            return None
        
        try:
            scraper = sntwitter.TwitterTweetScraper(int(post_id))
            tweet = next(scraper.get_items(), None)
            if tweet:
                return self._tweet_to_lead(tweet)
        except Exception as e:
            self.logger.error(f"Error fetching tweet {post_id}: {e}")
        
        return None
    
    def _tweet_to_lead(self, tweet) -> TwitterLead:
        """
        Convert a snscrape tweet object to TwitterLead model.
        
        Args:
            tweet: snscrape Tweet object
            
        Returns:
            TwitterLead model instance
        """
        # Extract user info
        user = tweet.user
        
        # Build source metadata
        source_meta = {
            "tweet_id": str(tweet.id),
            "retweet_count": tweet.retweetCount or 0,
            "like_count": tweet.likeCount or 0,
            "reply_count": tweet.replyCount or 0,
            "is_retweet": tweet.retweetedTweet is not None,
            "hashtags": [h.text for h in (tweet.hashtags or [])],
            "mentions": [m.username for m in (tweet.mentionedUsers or [])],
            "language": tweet.lang,
        }
        
        if tweet.inReplyToTweetId:
            source_meta["in_reply_to"] = str(tweet.inReplyToTweetId)
        
        # Extract company/title from bio if available
        bio = user.description if hasattr(user, 'description') else None
        
        lead = TwitterLead(
            id=self.generate_lead_id("twitter", str(tweet.id)),
            url=tweet.url,
            source_id=str(tweet.id),
            author_username=user.username,
            author_display_name=user.displayname,
            author_profile_url=f"https://twitter.com/{user.username}",
            author_bio=bio,
            author_company=self.extract_company_from_bio(bio),
            author_title=self.extract_title_from_bio(bio),
            author_followers=user.followersCount if hasattr(user, 'followersCount') else None,
            text=tweet.rawContent,
            text_excerpt=self.truncate_text(tweet.rawContent, 280),
            created_at=tweet.date,
            source_meta=source_meta,
        )
        
        return lead
    
    def _get_mock_results(self, query: str, max_results: int) -> List[TwitterLead]:
        """
        Generate mock Twitter results for development/testing.
        
        Args:
            query: Original search query
            max_results: Number of mock results to generate
            
        Returns:
            List of mock TwitterLead objects
        """
        mock_tweets = [
            {
                "id": "1234567890123456789",
                "text": "Looking for recommendations for accounts receivable automation software. Our current process is manual and painful. Any suggestions? #ARautomation #finance",
                "username": "finance_leader",
                "display_name": "Sarah Johnson",
                "bio": "CFO at TechCorp | Finance transformation enthusiast",
                "followers": 1250,
            },
            {
                "id": "1234567890123456790",
                "text": "What tool do you use for order to cash? We need to reduce our DSO and improve collections efficiency. Open to recommendations!",
                "username": "cfo_network",
                "display_name": "Michael Chen",
                "bio": "VP Finance @ RetailBrand | Previously at BigCo",
                "followers": 890,
            },
            {
                "id": "1234567890123456791",
                "text": "Evaluating cash application solutions for our enterprise. Anyone have experience with AI-powered cash application? #fintech #AP #AR",
                "username": "treasury_pro",
                "display_name": "Amanda Williams",
                "bio": "Director of Treasury | Consumer Goods | Automation advocate",
                "followers": 2100,
            },
            {
                "id": "1234567890123456792",
                "text": "Need a better system for deductions management. Current spreadsheet approach isn't scaling. Looking for software recommendations.",
                "username": "ar_manager",
                "display_name": "David Kim",
                "bio": "AR Manager at FastGrowth Inc | Streamlining collections",
                "followers": 450,
            },
            {
                "id": "1234567890123456793",
                "text": "Interesting discussion on AR automation trends. We're seeing more companies invest in O2C transformation. #FinanceTransformation",
                "username": "industry_analyst",
                "display_name": "Industry Watcher",
                "bio": "Following fintech trends",
                "followers": 5600,
            },
        ]
        
        leads = []
        for i, mock in enumerate(mock_tweets[:max_results]):
            lead = TwitterLead(
                id=self.generate_lead_id("twitter", mock["id"]),
                url=f"https://twitter.com/{mock['username']}/status/{mock['id']}",
                source_id=mock["id"],
                author_username=mock["username"],
                author_display_name=mock["display_name"],
                author_profile_url=f"https://twitter.com/{mock['username']}",
                author_bio=mock["bio"],
                author_company=self.extract_company_from_bio(mock["bio"]),
                author_title=self.extract_title_from_bio(mock["bio"]),
                author_followers=mock["followers"],
                text=mock["text"],
                text_excerpt=self.truncate_text(mock["text"], 280),
                created_at=datetime.now() - timedelta(hours=i * 6),
                source_meta={
                    "tweet_id": mock["id"],
                    "retweet_count": 5 + i * 2,
                    "like_count": 15 + i * 5,
                    "reply_count": 2 + i,
                    "is_retweet": False,
                    "is_mock": True,
                },
            )
            leads.append(lead)
        
        return leads
    
    def build_search_queries(self):
        """
        Build Twitter-optimized search queries.
        
        Twitter search supports operators like:
        - Phrase matching with quotes
        - OR for alternatives
        - -filter:retweets to exclude retweets
        - lang:en for English only
        """
        # Simplified queries for Twitter's search limits
        base_queries = [
            '"looking for" ("accounts receivable" OR "AR automation" OR "order to cash")',
            '"recommend" ("collections software" OR "cash application" OR "O2C")',
            '"need" ("invoicing software" OR "billing automation" OR "deductions management")',
            '"what tool" ("AR" OR "receivables" OR "collections")',
            '"suggestions" ("finance automation" OR "DSO reduction")',
        ]
        
        for query in base_queries:
            # Add filters for quality
            yield f"{query} lang:en -filter:retweets"

