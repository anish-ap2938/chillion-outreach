"""Gmail OAuth API Routes - Gmail authentication and draft creation with DB persistence"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.services.gmail_service import gmail_service, EmailDraft, GmailService, MockGmailService
from app.models.database import OAuthToken, SessionLocal, get_db
from app.config import settings

router = APIRouter()


class GmailAuthStatus(BaseModel):
    """Gmail authentication status"""
    connected: bool
    email: Optional[str] = None
    message: str


class CreateDraftsRequest(BaseModel):
    """Request to create email drafts"""
    drafts: List[EmailDraft]


class CreateDraftsResponse(BaseModel):
    """Response after creating drafts"""
    success: bool
    created: int
    failed: int
    drafts: List[EmailDraft]


def get_stored_token(db: Session) -> Optional[Dict[str, Any]]:
    """Get Gmail token from database"""
    token_record = db.query(OAuthToken).filter(OAuthToken.service == "gmail").first()
    if token_record and token_record.token:
        return {
            "token": token_record.token,
            "refresh_token": token_record.refresh_token,
            "token_uri": token_record.token_uri or "https://oauth2.googleapis.com/token",
            "client_id": token_record.client_id,
            "email": token_record.user_email,
        }
    return None


def save_token_to_db(db: Session, token_data: Dict[str, Any], email: str = None):
    """Save Gmail token to database"""
    token_record = db.query(OAuthToken).filter(OAuthToken.service == "gmail").first()
    
    if token_record:
        token_record.token = token_data.get("token")
        token_record.refresh_token = token_data.get("refresh_token")
        token_record.token_uri = token_data.get("token_uri")
        token_record.client_id = token_data.get("client_id")
        token_record.user_email = email
        token_record.updated_at = datetime.utcnow()
    else:
        token_record = OAuthToken(
            service="gmail",
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            user_email=email,
        )
        db.add(token_record)
    
    db.commit()


def delete_token_from_db(db: Session):
    """Delete Gmail token from database"""
    db.query(OAuthToken).filter(OAuthToken.service == "gmail").delete()
    db.commit()


@router.get("/status", response_model=GmailAuthStatus)
async def get_gmail_status(db: Session = Depends(get_db)):
    """Check if Gmail is connected"""
    token_data = get_stored_token(db)
    
    if token_data:
        try:
            # Try to get profile with stored token
            gmail_service.set_credentials(token_data)
            profile = gmail_service.get_user_profile()
            return GmailAuthStatus(
                connected=True,
                email=profile.get('emailAddress', token_data.get('email')),
                message="Gmail connected"
            )
        except Exception as e:
            # Token might be expired or invalid
            return GmailAuthStatus(
                connected=False,
                email=token_data.get('email'),
                message=f"Token expired or invalid. Please reconnect."
            )
    
    # Check mock service
    if isinstance(gmail_service, MockGmailService) and gmail_service.is_connected():
        return GmailAuthStatus(
            connected=True,
            email="mock@example.com",
            message="Gmail connected (mock mode)"
        )
    
    return GmailAuthStatus(
        connected=False,
        email=None,
        message="Gmail not connected. Please authenticate."
    )


@router.get("/connect")
async def start_gmail_auth():
    """Start Gmail OAuth flow"""
    try:
        auth_url = gmail_service.get_auth_url(state="gmail_connect")
        return {"auth_url": auth_url}
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Gmail OAuth not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def gmail_oauth_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Gmail OAuth callback"""
    try:
        token_data = gmail_service.handle_oauth_callback(code)
        gmail_service.set_credentials(token_data)
        
        # Get user email
        try:
            profile = gmail_service.get_user_profile()
            email = profile.get('emailAddress')
        except:
            email = None
        
        # Save to database
        save_token_to_db(db, token_data, email)
        
        return RedirectResponse(
            url=f"{settings.frontend_url}/agents?gmail_connected=true"
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/agents?gmail_error={str(e)}"
        )


@router.post("/drafts", response_model=CreateDraftsResponse)
async def create_gmail_drafts(request: CreateDraftsRequest, db: Session = Depends(get_db)):
    """Create email drafts in Gmail"""
    token_data = get_stored_token(db)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Gmail not connected. Please authenticate first.")
    
    try:
        gmail_service.set_credentials(token_data)
        results = gmail_service.create_drafts_batch(request.drafts)
        
        created = sum(1 for d in results if d.status == "created" or "created" in str(d.status))
        failed = len(results) - created
        
        return CreateDraftsResponse(
            success=created > 0,
            created=created,
            failed=failed,
            drafts=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts")
async def list_gmail_drafts(max_results: int = Query(10, le=50), db: Session = Depends(get_db)):
    """List existing Gmail drafts"""
    token_data = get_stored_token(db)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Gmail not connected")
    
    try:
        gmail_service.set_credentials(token_data)
        drafts = gmail_service.list_drafts(max_results)
        return {"drafts": drafts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_gmail(db: Session = Depends(get_db)):
    """Disconnect Gmail"""
    delete_token_from_db(db)
    return {"success": True, "message": "Gmail disconnected"}
