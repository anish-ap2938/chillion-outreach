"""Prospect API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.schemas import ProspectCreate, ProspectUpdate, ProspectResponse
from app.models.database import Prospect, get_db

router = APIRouter()


@router.get("/", response_model=List[ProspectResponse])
async def list_prospects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all prospects"""
    prospects = db.query(Prospect).offset(skip).limit(limit).all()
    return prospects


@router.post("/", response_model=ProspectResponse)
async def create_prospect(
    prospect: ProspectCreate,
    db: Session = Depends(get_db),
):
    """Create a new prospect"""
    db_prospect = Prospect(**prospect.model_dump())
    db.add(db_prospect)
    db.commit()
    db.refresh(db_prospect)
    return db_prospect


@router.get("/{prospect_id}", response_model=ProspectResponse)
async def get_prospect(
    prospect_id: int,
    db: Session = Depends(get_db),
):
    """Get a prospect by ID"""
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect


@router.patch("/{prospect_id}", response_model=ProspectResponse)
async def update_prospect(
    prospect_id: int,
    prospect_update: ProspectUpdate,
    db: Session = Depends(get_db),
):
    """Update a prospect"""
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    update_data = prospect_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prospect, key, value)
    
    db.commit()
    db.refresh(prospect)
    return prospect

