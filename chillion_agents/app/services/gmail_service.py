"""Gmail Service - Create drafts via Gmail API"""
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.config import settings


class EmailDraft(BaseModel):
    """Email draft model"""
    id: Optional[str] = None
    to: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    thread_id: Optional[str] = None
    status: str = "created"


class GmailService:
    """Service for Gmail API integration"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.readonly',
    ]
    
    def __init__(self):
        self.client_id = settings.google_oauth_client_id
        self.client_secret = settings.google_oauth_client_secret
        self.redirect_uri = settings.google_oauth_redirect_uri or "http://localhost:8000/api/v1/gmail/callback"
        self._credentials: Optional[Credentials] = None
        self._service = None
    
    def get_auth_url(self, state: str = "") -> str:
        """
        Get OAuth2 authorization URL for user consent
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )
        return auth_url
    
    def handle_oauth_callback(self, code: str) -> Dict[str, Any]:
        """
        Handle OAuth2 callback and get credentials
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )
        
        flow.fetch_token(code=code)
        self._credentials = flow.credentials
        
        return {
            "token": self._credentials.token,
            "refresh_token": self._credentials.refresh_token,
            "token_uri": self._credentials.token_uri,
            "client_id": self._credentials.client_id,
            "client_secret": self._credentials.client_secret,
            "expiry": self._credentials.expiry.isoformat() if self._credentials.expiry else None,
        }
    
    def set_credentials(self, token_data: Dict[str, Any]):
        """
        Set credentials from stored token data
        """
        self._credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id", self.client_id),
            client_secret=token_data.get("client_secret", self.client_secret),
        )
        
        # Refresh if expired
        if self._credentials.expired and self._credentials.refresh_token:
            self._credentials.refresh(Request())
        
        self._service = build('gmail', 'v1', credentials=self._credentials)
    
    def _get_service(self):
        """Get Gmail API service"""
        if not self._service:
            if not self._credentials:
                raise ValueError("Gmail not authenticated. Call set_credentials() first.")
            self._service = build('gmail', 'v1', credentials=self._credentials)
        return self._service
    
    def create_draft(self, draft: EmailDraft) -> EmailDraft:
        """
        Create a draft email in Gmail
        """
        service = self._get_service()
        
        # Create message
        if draft.body_html:
            message = MIMEMultipart('alternative')
            message['to'] = draft.to
            message['subject'] = draft.subject
            
            part1 = MIMEText(draft.body_text, 'plain')
            part2 = MIMEText(draft.body_html, 'html')
            message.attach(part1)
            message.attach(part2)
        else:
            message = MIMEText(draft.body_text)
            message['to'] = draft.to
            message['subject'] = draft.subject
        
        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Create draft
        body = {'message': {'raw': raw}}
        if draft.thread_id:
            body['message']['threadId'] = draft.thread_id
        
        result = service.users().drafts().create(userId='me', body=body).execute()
        
        draft.id = result['id']
        draft.status = "created"
        return draft
    
    def create_drafts_batch(self, drafts: List[EmailDraft]) -> List[EmailDraft]:
        """
        Create multiple drafts
        """
        results = []
        for draft in drafts:
            try:
                created = self.create_draft(draft)
                results.append(created)
            except Exception as e:
                draft.status = f"error: {str(e)}"
                results.append(draft)
        return results
    
    def list_drafts(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List existing drafts
        """
        service = self._get_service()
        result = service.users().drafts().list(userId='me', maxResults=max_results).execute()
        return result.get('drafts', [])
    
    def get_user_profile(self) -> Dict[str, Any]:
        """
        Get authenticated user's email profile
        """
        service = self._get_service()
        return service.users().getProfile(userId='me').execute()


# Mock service for testing without credentials
class MockGmailService:
    """Mock Gmail service for testing"""
    
    _drafts: List[EmailDraft] = []
    _connected: bool = False
    _user_email: str = "test@example.com"
    
    def get_auth_url(self, state: str = "") -> str:
        return f"http://localhost:3000/api/auth/google/mock-callback?state={state}"
    
    def handle_oauth_callback(self, code: str) -> Dict[str, Any]:
        self._connected = True
        return {"token": "mock_token", "email": self._user_email}
    
    def set_credentials(self, token_data: Dict[str, Any]):
        self._connected = True
        self._user_email = token_data.get("email", "test@example.com")
    
    def create_draft(self, draft: EmailDraft) -> EmailDraft:
        if not self._connected:
            raise ValueError("Not connected to Gmail")
        draft.id = f"draft_{len(self._drafts) + 1}"
        draft.status = "created (mock)"
        self._drafts.append(draft)
        return draft
    
    def create_drafts_batch(self, drafts: List[EmailDraft]) -> List[EmailDraft]:
        return [self.create_draft(d) for d in drafts]
    
    def list_drafts(self, max_results: int = 10) -> List[Dict[str, Any]]:
        return [{"id": d.id, "to": d.to, "subject": d.subject} for d in self._drafts[:max_results]]
    
    def get_user_profile(self) -> Dict[str, Any]:
        return {"emailAddress": self._user_email}
    
    def is_connected(self) -> bool:
        return self._connected


# Use mock service if credentials not configured
def get_gmail_service():
    if settings.google_oauth_client_id and settings.google_oauth_client_secret:
        return GmailService()
    return MockGmailService()


gmail_service = get_gmail_service()

