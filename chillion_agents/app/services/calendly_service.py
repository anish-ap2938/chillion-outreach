"""Calendly Service - Fetch meetings and event types from Calendly"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.config import settings


class CalendlyEvent(BaseModel):
    """Calendly scheduled event"""
    uri: str
    name: str
    status: str  # "active", "canceled"
    start_time: datetime
    end_time: datetime
    event_type: str
    location: Optional[str] = None
    invitee_name: Optional[str] = None
    invitee_email: Optional[str] = None
    invitee_company: Optional[str] = None
    created_at: datetime
    cancel_url: Optional[str] = None
    reschedule_url: Optional[str] = None


class CalendlyEventType(BaseModel):
    """Calendly event type (meeting type)"""
    uri: str
    name: str
    slug: str
    duration_minutes: int
    scheduling_url: str
    active: bool
    color: Optional[str] = None
    description: Optional[str] = None


class CalendlyUser(BaseModel):
    """Calendly user/organization"""
    uri: str
    name: str
    email: str
    scheduling_url: str
    timezone: str
    avatar_url: Optional[str] = None


class CalendlyService:
    """Service for Calendly API integration"""
    
    BASE_URL = "https://api.calendly.com"
    
    def __init__(self, access_token: str = None, user_uri: str = None):
        self.access_token = access_token or settings.calendly_access_token
        self.user_uri = user_uri or settings.calendly_user_uri
        self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client
    
    def is_configured(self) -> bool:
        """Check if Calendly is configured"""
        return bool(self.access_token and self.user_uri)
    
    async def get_current_user(self) -> Optional[CalendlyUser]:
        """Get current authenticated user"""
        if not self.access_token:
            return None
        
        try:
            response = await self.client.get("/users/me")
            response.raise_for_status()
            data = response.json()["resource"]
            return CalendlyUser(
                uri=data["uri"],
                name=data["name"],
                email=data["email"],
                scheduling_url=data["scheduling_url"],
                timezone=data["timezone"],
                avatar_url=data.get("avatar_url"),
            )
        except Exception as e:
            print(f"Calendly get_current_user error: {e}")
            return None
    
    async def get_event_types(self) -> List[CalendlyEventType]:
        """Get all event types for the user"""
        if not self.is_configured():
            return []
        
        try:
            response = await self.client.get(
                "/event_types",
                params={"user": self.user_uri, "active": "true"}
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                CalendlyEventType(
                    uri=et["uri"],
                    name=et["name"],
                    slug=et["slug"],
                    duration_minutes=et["duration"],
                    scheduling_url=et["scheduling_url"],
                    active=et["active"],
                    color=et.get("color"),
                    description=et.get("description_plain"),
                )
                for et in data.get("collection", [])
            ]
        except Exception as e:
            print(f"Calendly get_event_types error: {e}")
            return []
    
    async def get_scheduled_events(
        self,
        min_start_time: datetime = None,
        max_start_time: datetime = None,
        status: str = None,  # "active", "canceled"
        count: int = 50,
    ) -> List[CalendlyEvent]:
        """Get scheduled events (meetings)"""
        if not self.is_configured():
            return []
        
        try:
            params = {
                "user": self.user_uri,
                "count": min(count, 100),
                "sort": "start_time:asc",
            }
            
            if min_start_time:
                params["min_start_time"] = min_start_time.isoformat()
            else:
                # Default to today
                params["min_start_time"] = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat() + "Z"
            
            if max_start_time:
                params["max_start_time"] = max_start_time.isoformat()
            
            if status:
                params["status"] = status
            
            response = await self.client.get("/scheduled_events", params=params)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for event in data.get("collection", []):
                # Get invitee info
                invitee = await self._get_event_invitee(event["uri"])
                
                events.append(CalendlyEvent(
                    uri=event["uri"],
                    name=event["name"],
                    status=event["status"],
                    start_time=datetime.fromisoformat(event["start_time"].replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(event["end_time"].replace("Z", "+00:00")),
                    event_type=event.get("event_type", ""),
                    location=event.get("location", {}).get("location") if event.get("location") else None,
                    invitee_name=invitee.get("name") if invitee else None,
                    invitee_email=invitee.get("email") if invitee else None,
                    invitee_company=invitee.get("company") if invitee else None,
                    created_at=datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")),
                    cancel_url=event.get("cancel_url"),
                    reschedule_url=event.get("reschedule_url"),
                ))
            
            return events
        except Exception as e:
            print(f"Calendly get_scheduled_events error: {e}")
            return []
    
    async def _get_event_invitee(self, event_uri: str) -> Optional[Dict[str, Any]]:
        """Get invitee for an event"""
        try:
            # Extract event UUID from URI
            event_uuid = event_uri.split("/")[-1]
            response = await self.client.get(f"/scheduled_events/{event_uuid}/invitees")
            response.raise_for_status()
            data = response.json()
            
            if data.get("collection"):
                invitee = data["collection"][0]
                return {
                    "name": invitee.get("name"),
                    "email": invitee.get("email"),
                    "company": invitee.get("questions_and_answers", [{}])[0].get("answer") if invitee.get("questions_and_answers") else None,
                }
            return None
        except Exception as e:
            print(f"Calendly get_event_invitee error: {e}")
            return None
    
    async def get_upcoming_meetings(self, days: int = 30) -> List[CalendlyEvent]:
        """Get upcoming meetings for the next N days"""
        now = datetime.utcnow()
        return await self.get_scheduled_events(
            min_start_time=now,
            max_start_time=now + timedelta(days=days),
            status="active",
        )
    
    async def get_past_meetings(self, days: int = 30) -> List[CalendlyEvent]:
        """Get past meetings from the last N days"""
        now = datetime.utcnow()
        events = await self.get_scheduled_events(
            min_start_time=now - timedelta(days=days),
            max_start_time=now,
        )
        return sorted(events, key=lambda x: x.start_time, reverse=True)
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()


# Singleton instance
calendly_service = CalendlyService()

