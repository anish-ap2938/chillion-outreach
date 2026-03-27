"""Email service interface - abstract connector for email operations"""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class EmailDraft(BaseModel):
    """Email draft for human approval"""
    to: EmailStr
    subject: str
    body_html: str
    body_text: str
    metadata: dict = {}


class DeliveryResult(BaseModel):
    """Email delivery result"""
    email_id: str
    status: str  # "sent", "delivered", "bounced", "failed"
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None


class ThreadSummary(BaseModel):
    """Email thread summary"""
    thread_id: str
    subject: str
    message_count: int
    last_message_at: datetime
    summary: str


class EmailService(ABC):
    """Abstract email service interface"""
    
    @abstractmethod
    def send_email(self, draft: EmailDraft) -> DeliveryResult:
        """Send email (after human approval)"""
        pass
    
    @abstractmethod
    def fetch_thread(self, email: EmailStr) -> Optional[ThreadSummary]:
        """Fetch email thread summary"""
        pass
    
    @abstractmethod
    def log_delivery(self, email_id: str, status: str, metadata: dict = None):
        """Log email delivery status"""
        pass


class MockEmailService(EmailService):
    """Mock implementation for testing"""
    
    def send_email(self, draft: EmailDraft) -> DeliveryResult:
        return DeliveryResult(
            email_id="mock-123",
            status="sent",
            delivered_at=datetime.utcnow(),
        )
    
    def fetch_thread(self, email: EmailStr) -> Optional[ThreadSummary]:
        return None
    
    def log_delivery(self, email_id: str, status: str, metadata: dict = None):
        pass

