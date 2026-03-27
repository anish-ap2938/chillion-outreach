"""CSV Upload API Routes - Process prospect CSVs"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from typing import List
from pydantic import BaseModel
from app.services.csv_processor import csv_processor, ProspectCSVRow, CSVProcessResult
from app.models.database import Prospect, Company, SessionLocal, ConversationStage

router = APIRouter()


class CSVUploadResponse(BaseModel):
    """Response after CSV upload"""
    success: bool
    message: str
    total_rows: int
    imported: int
    skipped: int
    errors: List[str]
    prospects: List[ProspectCSVRow]


@router.post("/upload", response_model=CSVUploadResponse)
async def upload_prospects_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file of prospects.
    Returns parsed prospects ready for outreach.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Process CSV
    result = csv_processor.process_csv(content_str)
    
    if not result.success:
        return CSVUploadResponse(
            success=False,
            message="Failed to process CSV",
            total_rows=result.total_rows,
            imported=0,
            skipped=result.invalid_rows,
            errors=result.errors,
            prospects=[],
        )
    
    return CSVUploadResponse(
        success=True,
        message=f"Successfully parsed {result.valid_rows} prospects",
        total_rows=result.total_rows,
        imported=result.valid_rows,
        skipped=result.invalid_rows,
        errors=result.errors,
        prospects=result.prospects,
    )


@router.post("/upload-and-save")
async def upload_and_save_prospects(file: UploadFile = File(...)):
    """
    Upload CSV and save prospects to database.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read and process
    content = await file.read()
    result = csv_processor.process_csv(content.decode('utf-8'))
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors[0] if result.errors else "Failed to parse CSV")
    
    # Save to database
    db = SessionLocal()
    saved_count = 0
    errors = []
    
    try:
        for prospect_data in result.prospects:
            try:
                # Find or create company
                company = None
                if prospect_data.company:
                    company = db.query(Company).filter(Company.name == prospect_data.company).first()
                    if not company:
                        company = Company(
                            name=prospect_data.company,
                            industry=prospect_data.industry,
                        )
                        db.add(company)
                        db.flush()
                
                # Check if prospect already exists
                existing = db.query(Prospect).filter(
                    Prospect.email == prospect_data.email
                ).first() if prospect_data.email else None
                
                if existing:
                    # Update existing
                    existing.name = prospect_data.name
                    existing.title = prospect_data.title
                    existing.linkedin_url = prospect_data.linkedin_url
                    existing.notes = prospect_data.notes
                    if company:
                        existing.company_id = company.id
                else:
                    # Create new
                    prospect = Prospect(
                        name=prospect_data.name,
                        email=prospect_data.email,
                        title=prospect_data.title,
                        linkedin_url=prospect_data.linkedin_url,
                        company_id=company.id if company else None,
                        notes=prospect_data.notes,
                        stage=ConversationStage.NOT_CONTACTED,
                    )
                    db.add(prospect)
                
                saved_count += 1
            except Exception as e:
                errors.append(f"Error saving {prospect_data.name}: {str(e)}")
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
    
    return {
        "success": True,
        "message": f"Saved {saved_count} prospects to database",
        "saved": saved_count,
        "errors": errors,
    }


@router.get("/template", response_class=PlainTextResponse)
async def get_csv_template():
    """
    Download a sample CSV template for prospect upload.
    """
    return csv_processor.generate_sample_csv()

