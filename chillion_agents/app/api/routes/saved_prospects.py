"""Saved Prospects API Routes - Store and manage prospects for agent workflows"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import SavedProspect, SessionLocal, get_db

router = APIRouter()


class ProspectInput(BaseModel):
    """Input for creating/updating a prospect"""
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = "manual"


class ProspectOutput(BaseModel):
    """Output prospect with ID"""
    id: int
    name: str
    email: Optional[str]
    company: Optional[str]
    title: Optional[str]
    linkedin_url: Optional[str]
    industry: Optional[str]
    notes: Optional[str]
    source: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BulkProspectsInput(BaseModel):
    """Bulk input for multiple prospects"""
    prospects: List[ProspectInput]


@router.get("/", response_model=List[ProspectOutput])
async def list_saved_prospects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all saved prospects"""
    prospects = db.query(SavedProspect).order_by(SavedProspect.created_at.desc()).offset(skip).limit(limit).all()
    return prospects


@router.post("/", response_model=ProspectOutput)
async def create_prospect(prospect: ProspectInput, db: Session = Depends(get_db)):
    """Create a new prospect"""
    db_prospect = SavedProspect(
        name=prospect.name,
        email=prospect.email,
        company=prospect.company,
        title=prospect.title,
        linkedin_url=prospect.linkedin_url,
        industry=prospect.industry,
        notes=prospect.notes,
        source=prospect.source or "manual",
    )
    db.add(db_prospect)
    db.commit()
    db.refresh(db_prospect)
    return db_prospect


@router.post("/bulk", response_model=dict)
async def create_prospects_bulk(data: BulkProspectsInput, db: Session = Depends(get_db)):
    """Create multiple prospects at once"""
    created = 0
    errors = []
    
    for prospect in data.prospects:
        try:
            db_prospect = SavedProspect(
                name=prospect.name,
                email=prospect.email,
                company=prospect.company,
                title=prospect.title,
                linkedin_url=prospect.linkedin_url,
                industry=prospect.industry,
                notes=prospect.notes,
                source=prospect.source or "manual",
            )
            db.add(db_prospect)
            created += 1
        except Exception as e:
            errors.append(f"{prospect.name}: {str(e)}")
    
    db.commit()
    
    return {
        "success": True,
        "created": created,
        "errors": errors,
    }


@router.get("/{prospect_id}", response_model=ProspectOutput)
async def get_prospect(prospect_id: int, db: Session = Depends(get_db)):
    """Get a specific prospect"""
    prospect = db.query(SavedProspect).filter(SavedProspect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect


@router.put("/{prospect_id}", response_model=ProspectOutput)
async def update_prospect(prospect_id: int, data: ProspectInput, db: Session = Depends(get_db)):
    """Update a prospect"""
    prospect = db.query(SavedProspect).filter(SavedProspect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    prospect.name = data.name
    prospect.email = data.email
    prospect.company = data.company
    prospect.title = data.title
    prospect.linkedin_url = data.linkedin_url
    prospect.industry = data.industry
    prospect.notes = data.notes
    prospect.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(prospect)
    return prospect


@router.delete("/{prospect_id}")
async def delete_prospect(prospect_id: int, db: Session = Depends(get_db)):
    """Delete a prospect"""
    prospect = db.query(SavedProspect).filter(SavedProspect.id == prospect_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    db.delete(prospect)
    db.commit()
    return {"success": True, "message": "Prospect deleted"}


@router.delete("/")
async def delete_all_prospects(db: Session = Depends(get_db)):
    """Delete all prospects"""
    db.query(SavedProspect).delete()
    db.commit()
    return {"success": True, "message": "All prospects deleted"}

