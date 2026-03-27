"""LinkedIn service interface - abstract connector for LinkedIn operations"""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class Profile(BaseModel):
    """LinkedIn profile data"""
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    about_section: Optional[str] = None
    recent_posts: List[str] = []
    profile_url: str


class DraftPayload(BaseModel):
    """Draft message payload for human approval"""
    recipient: str
    message_type: str  # "connection_request", "dm", "reply"
    content: str
    metadata: dict = {}


class LinkedInService(ABC):
    """Abstract LinkedIn service interface"""
    
    @abstractmethod
    def search_recent_engagers(self, content_url: str, limit: int = 10) -> List[Profile]:
        """Search for profiles who recently engaged with Chillion content"""
        pass
    
    @abstractmethod
    def fetch_profile(self, handle: str) -> Optional[Profile]:
        """Fetch full profile by LinkedIn handle/URL"""
        pass
    
    @abstractmethod
    def draft_connection_request(self, profile: Profile, message: str = None) -> DraftPayload:
        """Draft a connection request (returns payload, does NOT send)"""
        pass
    
    @abstractmethod
    def draft_reply(self, thread_id: str, context: dict) -> DraftPayload:
        """Draft a reply to an existing conversation (returns payload, does NOT send)"""
        pass


class MockLinkedInService(LinkedInService):
    """Mock implementation for testing"""
    
    def search_recent_engagers(self, content_url: str, limit: int = 10) -> List[Profile]:
        return []
    
    def fetch_profile(self, handle: str) -> Optional[Profile]:
        return None
    
    def draft_connection_request(self, profile: Profile, message: str = None) -> DraftPayload:
        return DraftPayload(
            recipient=profile.name,
            message_type="connection_request",
            content=message or f"Hi {profile.name}, I'd like to connect.",
            metadata={"profile_url": profile.profile_url},
        )
    
    def draft_reply(self, thread_id: str, context: dict) -> DraftPayload:
        return DraftPayload(
            recipient="",
            message_type="reply",
            content="Thank you for your message...",
            metadata={"thread_id": thread_id},
        )

