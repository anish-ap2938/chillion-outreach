"""Data models"""
from app.models.database import (
    Base,
    Prospect,
    Company,
    Interaction,
    Campaign,
    AgentEvent,
)
from app.models.schemas import (
    # Prospect schemas
    ProspectCreate,
    ProspectUpdate,
    ProspectResponse,
    # Company schemas
    CompanyCreate,
    CompanyResponse,
    # Interaction schemas
    InteractionCreate,
    InteractionResponse,
    # Campaign schemas
    CampaignCreate,
    CampaignResponse,
    # Agent input/output schemas
    LinkedInDMInput,
    LinkedInDMOutput,
    EmailConversationInput,
    EmailConversationOutput,
    IntentListenerInput,
    IntentListenerOutput,
)

__all__ = [
    "Base",
    "Prospect",
    "Company",
    "Interaction",
    "Campaign",
    "AgentEvent",
    "ProspectCreate",
    "ProspectUpdate",
    "ProspectResponse",
    "CompanyCreate",
    "CompanyResponse",
    "InteractionCreate",
    "InteractionResponse",
    "CampaignCreate",
    "CampaignResponse",
    "LinkedInDMInput",
    "LinkedInDMOutput",
    "EmailConversationInput",
    "EmailConversationOutput",
    "IntentListenerInput",
    "IntentListenerOutput",
]

