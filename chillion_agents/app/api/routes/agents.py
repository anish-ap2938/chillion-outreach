"""Agent API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.models.schemas import (
    LinkedInDMInput,
    LinkedInDMOutput,
    EmailConversationInput,
    EmailConversationOutput,
    IntentListenerInput,
    IntentListenerOutput,
)
from app.agents import LinkedInDMAgent, EmailConversationAgent, IntentListenerAgent
from app.rag.vector_store import VectorStore
from app.models.database import get_db
from app.prompts.templates import CHILLION_PRODUCTS, EMAIL_TEMPLATES, LINKEDIN_TEMPLATES

router = APIRouter()


def get_vector_store():
    """Dependency for vector store"""
    return VectorStore()


@router.get("/products")
async def list_products() -> List[Dict[str, Any]]:
    """List available Chillion products for selection"""
    return [
        {
            "key": key,
            "name": product["name"],
            "short_name": product["short_name"],
            "description": product["description"][:100] + "...",
        }
        for key, product in CHILLION_PRODUCTS.items()
    ]


@router.get("/email-templates")
async def list_email_templates() -> List[Dict[str, str]]:
    """List available email templates"""
    return [
        {"key": key, "name": template["name"]}
        for key, template in EMAIL_TEMPLATES.items()
    ]


@router.get("/linkedin-templates")
async def list_linkedin_templates() -> List[Dict[str, str]]:
    """List available LinkedIn message templates"""
    return [
        {"key": key, "name": template["name"]}
        for key, template in LINKEDIN_TEMPLATES.items()
    ]


@router.post("/linkedin-dm", response_model=LinkedInDMOutput)
async def generate_linkedin_dm(
    input_data: LinkedInDMInput,
    db: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Generate a personalized LinkedIn DM"""
    agent = LinkedInDMAgent(db=db, vector_store=vector_store)
    try:
        output = agent.process(input_data)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email-conversation", response_model=EmailConversationOutput)
async def generate_email(
    input_data: EmailConversationInput,
    db: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Generate a professional email"""
    agent = EmailConversationAgent(db=db, vector_store=vector_store)
    try:
        output = agent.process(input_data)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intent-listener", response_model=IntentListenerOutput)
async def process_intent(
    input_data: IntentListenerInput,
    db: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Process intent signals from feeds"""
    agent = IntentListenerAgent(db=db, vector_store=vector_store)
    try:
        output = agent.process(input_data)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

