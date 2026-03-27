"""Campaign API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.schemas import CampaignCreate, CampaignResponse
from app.models.database import Campaign, get_db

router = APIRouter()


@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all campaigns"""
    campaigns = db.query(Campaign).offset(skip).limit(limit).all()
    return campaigns


@router.post("/", response_model=CampaignResponse)
async def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
):
    """Create a new campaign"""
    db_campaign = Campaign(**campaign.model_dump())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

