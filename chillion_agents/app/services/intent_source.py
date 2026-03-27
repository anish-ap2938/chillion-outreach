"""Intent source interface - abstract connector for web/social listening"""
from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from app.models.schemas import FeedItem


class IntentSource(ABC):
    """Abstract base class for intent sources"""
    
    @abstractmethod
    def fetch_feed(self, keywords: List[str], since: datetime = None) -> List[FeedItem]:
        """Fetch feed items matching keywords since a given time"""
        pass


class MockIntentSource(IntentSource):
    """Mock implementation for testing"""
    
    def fetch_feed(self, keywords: List[str], since: datetime = None) -> List[FeedItem]:
        """Return mock feed items"""
        return [
            FeedItem(
                url="https://example.com/post1",
                text_snippet="Looking for solutions to automate our AR process and reduce DSO...",
                author="John Doe",
                author_handle="@johndoe",
                platform="linkedin",
                timestamp=datetime.utcnow(),
                engagement_metrics={"likes": 10, "comments": 2},
            ),
        ]

