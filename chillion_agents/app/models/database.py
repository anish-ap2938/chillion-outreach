"""SQLAlchemy database models"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Float,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from datetime import datetime
import enum
from app.config import settings

Base = declarative_base()

# Database engine and session
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConversationStage(str, enum.Enum):
    """Prospect conversation stage"""
    NOT_CONTACTED = "not_contacted"
    FIRST_TOUCH_SENT = "first_touch_sent"
    REPLIED = "replied"
    MEETING_BOOKED = "meeting_booked"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class InteractionChannel(str, enum.Enum):
    """Interaction channel"""
    LINKEDIN_DM = "linkedin_dm"
    EMAIL = "email"
    INTENT_SIGNAL = "intent_signal"


class InteractionStatus(str, enum.Enum):
    """Interaction status"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"


class CampaignStatus(str, enum.Enum):
    """Campaign status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Company(Base):
    """Company model"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(100))
    website = Column(String(255))
    employee_count = Column(String(50))  # e.g., "1000-5000"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    prospects = relationship("Prospect", back_populates="company")


class Prospect(Base):
    """Prospect model"""
    __tablename__ = "prospects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True)
    linkedin_url = Column(String(500))
    title = Column(String(255))
    company_id = Column(Integer, ForeignKey("companies.id"))
    stage = Column(SQLEnum(ConversationStage), default=ConversationStage.NOT_CONTACTED)
    intent_score = Column(Float)  # 1-5 scale
    problem_category = Column(String(100))
    related_product = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = relationship("Company", back_populates="prospects")
    interactions = relationship("Interaction", back_populates="prospect")


class Interaction(Base):
    """Interaction model - tracks all messages and touchpoints"""
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    channel = Column(SQLEnum(InteractionChannel), nullable=False)
    message_type = Column(String(50))  # e.g., "new_outreach", "reply", "follow_up"
    subject = Column(String(500))  # For emails
    content = Column(Text, nullable=False)  # Message body
    content_html = Column(Text)  # HTML version for emails
    status = Column(SQLEnum(InteractionStatus), default=InteractionStatus.DRAFT)
    extra_data = Column(JSON)  # Store personalization notes, CTA, etc. (renamed from metadata to avoid SQLAlchemy conflict)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prospect = relationship("Prospect", back_populates="interactions")
    campaign = relationship("Campaign", back_populates="interactions")


class Campaign(Base):
    """Campaign model"""
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    agent_type = Column(String(50))  # "linkedin_dm", "email", "intent_listener"
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    config = Column(JSON)  # Campaign-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    interactions = relationship("Interaction", back_populates="campaign")


class AgentEvent(Base):
    """Agent event log for debugging and monitoring"""
    __tablename__ = "agent_events"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_type = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50))  # e.g., "draft_created", "error", "rag_retrieved"
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class OAuthToken(Base):
    """Store OAuth tokens for Gmail and other services"""
    __tablename__ = "oauth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    service = Column(String(50), nullable=False, unique=True, index=True)  # "gmail", "linkedin"
    token = Column(Text)  # Encrypted token JSON
    refresh_token = Column(Text)
    token_uri = Column(String(500))
    client_id = Column(String(500))
    expiry = Column(DateTime)
    user_email = Column(String(255))  # For display purposes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SavedProspect(Base):
    """Saved prospects for agent workflows"""
    __tablename__ = "saved_prospects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True)
    company = Column(String(255))
    title = Column(String(255))
    linkedin_url = Column(String(500))
    industry = Column(String(100))
    notes = Column(Text)
    source = Column(String(50))  # "manual", "csv", "intent"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
