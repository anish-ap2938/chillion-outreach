"""Pydantic schemas for API requests/responses and agent I/O"""
from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.database import ConversationStage, InteractionChannel, InteractionStatus, CampaignStatus


# ========== Prospect Schemas ==========

class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    employee_count: Optional[str] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    industry: Optional[str]
    website: Optional[str]
    employee_count: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProspectCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    linkedin_url: Optional[str] = None
    title: Optional[str] = None
    company_id: Optional[int] = None
    problem_category: Optional[str] = None
    related_product: Optional[str] = None
    notes: Optional[str] = None


class ProspectUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    linkedin_url: Optional[str] = None
    title: Optional[str] = None
    company_id: Optional[int] = None
    stage: Optional[ConversationStage] = None
    intent_score: Optional[float] = Field(None, ge=1, le=5)
    problem_category: Optional[str] = None
    related_product: Optional[str] = None
    notes: Optional[str] = None


class ProspectResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    linkedin_url: Optional[str]
    title: Optional[str]
    company_id: Optional[int]
    stage: ConversationStage
    intent_score: Optional[float]
    problem_category: Optional[str]
    related_product: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyResponse] = None
    
    class Config:
        from_attributes = True


# ========== Interaction Schemas ==========

class InteractionCreate(BaseModel):
    prospect_id: int
    campaign_id: Optional[int] = None
    channel: InteractionChannel
    message_type: str
    subject: Optional[str] = None
    content: str
    content_html: Optional[str] = None
    status: InteractionStatus = InteractionStatus.DRAFT
    metadata: Optional[Dict[str, Any]] = None


class InteractionResponse(BaseModel):
    id: int
    prospect_id: int
    campaign_id: Optional[int]
    channel: InteractionChannel
    message_type: str
    subject: Optional[str]
    content: str
    content_html: Optional[str]
    status: InteractionStatus
    metadata: Optional[Dict[str, Any]]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    replied_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Campaign Schemas ==========

class CampaignCreate(BaseModel):
    name: str
    agent_type: str
    config: Optional[Dict[str, Any]] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    agent_type: str
    status: CampaignStatus
    config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ========== LinkedIn DM Agent Schemas ==========

class ProspectProfile(BaseModel):
    """LinkedIn prospect profile data"""
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    about_section: Optional[str] = None
    recent_posts: Optional[List[str]] = None  # List of recent post themes/text


class OfferContext(BaseModel):
    """Chillion product offer context"""
    product_name: str  # e.g., "Gia Docs", "Order to Cash Automation"
    value_propositions: List[str]  # Bullet points of value


class LinkedInDMInput(BaseModel):
    """Input schema for LinkedIn DM Agent"""
    prospect_profile: ProspectProfile
    conversation_stage: str  # Accept string for flexibility
    offer_context: OfferContext
    past_thread_summary: Optional[str] = None  # Summary of previous messages
    product_key: Optional[str] = None  # e.g., "it_infrastructure", "collections_management"
    template_key: Optional[str] = None  # e.g., "connection_request", "ar_pain_point", "custom"
    custom_message: Optional[str] = None  # User's custom context or message


class LinkedInDMOutput(BaseModel):
    """Output schema for LinkedIn DM Agent"""
    channel: str = "linkedin_dm"
    stage: str  # Return string for simplicity
    persona: str = "helpful finance automation advisor"
    message_type: str  # "new_outreach" or "reply"
    message_text: str
    personalization_notes: str  # Explains why certain personalization was used
    suggested_follow_up_window_days: int = Field(default=3, ge=1, le=14)


# ========== Email Conversation Agent Schemas ==========

class CompanyContext(BaseModel):
    """Company context for email personalization"""
    name: str
    industry: Optional[str] = None
    employee_count: Optional[str] = None


class SimpleProspectRecord(BaseModel):
    """Simplified prospect record for API input"""
    id: Optional[int] = 0
    name: str
    email: Optional[str] = None
    title: Optional[str] = None
    company_id: Optional[int] = None
    problem_category: Optional[str] = None
    related_product: Optional[str] = None


class EmailConversationInput(BaseModel):
    """Input schema for Email Conversation Agent"""
    prospect_record: SimpleProspectRecord
    company_context: CompanyContext
    conversation_stage: str  # Accept string instead of enum for flexibility
    last_email_thread_summary: Optional[str] = None
    channel_preferences: Optional[Dict[str, Any]] = None
    product_key: Optional[str] = None  # e.g., "it_infrastructure", "cash_application"
    template_key: Optional[str] = None  # e.g., "ar_visibility", "multi_erp_risk", "custom"
    custom_message: Optional[str] = None  # User's custom context or what they want to convey
    opt_out_note: Optional[str] = None
    validate_before_send: bool = False


class EmailConversationOutput(BaseModel):
    """Output schema for Email Conversation Agent"""
    channel: str = "email"
    subject_line: str
    body_html: str
    body_text: str
    call_to_action: str
    follow_up_suggestion_days: int = Field(default=3, ge=1, le=14)
    variant_label: Optional[str] = None  # For A/B testing


# ========== Intent Listener Agent Schemas ==========

class FeedItem(BaseModel):
    """Item from an intent source feed"""
    url: str
    text_snippet: str
    author: Optional[str] = None
    author_handle: Optional[str] = None
    platform: str  # "linkedin", "twitter", "rss", etc.
    timestamp: datetime
    engagement_metrics: Optional[Dict[str, Any]] = None  # likes, shares, etc.


class IntentListenerInput(BaseModel):
    """Input schema for Intent Listener Agent"""
    keywords: List[str]
    feed_items: List[FeedItem]


class IntentRecord(BaseModel):
    """Intent record output"""
    source_platform: str
    url: str
    author_name: Optional[str] = None
    author_handle: Optional[str] = None
    company_if_detectable: Optional[str] = None
    raw_text: str
    intent_score_one_to_five: int = Field(ge=1, le=5)
    problem_category: str
    related_product: str
    urgency_tag: Optional[str] = None  # "high", "medium", "low"
    notes_for_sales: Optional[str] = None


class IntentListenerOutput(BaseModel):
    """Output schema for Intent Listener Agent"""
    intent_records: List[IntentRecord]
    total_processed: int
    relevant_count: int

