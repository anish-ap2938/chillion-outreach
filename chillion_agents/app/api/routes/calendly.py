"""Calendly API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.services.calendly_service import (
    calendly_service,
    CalendlyEvent,
    CalendlyEventType,
    CalendlyUser,
)
from app.config import settings

router = APIRouter()


class CalendlyStatus(BaseModel):
    """Calendly connection status"""
    connected: bool
    user: Optional[CalendlyUser] = None
    message: str


class MeetingStats(BaseModel):
    """Meeting statistics"""
    upcoming_count: int
    today_count: int
    this_week_count: int
    past_30_days_count: int


@router.get("/status", response_model=CalendlyStatus)
async def get_calendly_status():
    """Check Calendly connection status"""
    if not calendly_service.is_configured():
        return CalendlyStatus(
            connected=False,
            user=None,
            message="Calendly not configured. Add CALENDLY_ACCESS_TOKEN to .env"
        )
    
    user = await calendly_service.get_current_user()
    if user:
        return CalendlyStatus(
            connected=True,
            user=user,
            message="Connected to Calendly"
        )
    
    return CalendlyStatus(
        connected=False,
        user=None,
        message="Invalid Calendly credentials"
    )


@router.get("/event-types", response_model=List[CalendlyEventType])
async def get_event_types():
    """Get all active event types"""
    if not calendly_service.is_configured():
        return []
    
    return await calendly_service.get_event_types()


@router.get("/meetings/upcoming", response_model=List[CalendlyEvent])
async def get_upcoming_meetings(days: int = Query(30, ge=1, le=90)):
    """Get upcoming meetings"""
    if not calendly_service.is_configured():
        return []
    
    return await calendly_service.get_upcoming_meetings(days=days)


@router.get("/meetings/past", response_model=List[CalendlyEvent])
async def get_past_meetings(days: int = Query(30, ge=1, le=90)):
    """Get past meetings"""
    if not calendly_service.is_configured():
        return []
    
    return await calendly_service.get_past_meetings(days=days)


@router.get("/meetings/today", response_model=List[CalendlyEvent])
async def get_today_meetings():
    """Get today's meetings"""
    if not calendly_service.is_configured():
        return []
    
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    return await calendly_service.get_scheduled_events(
        min_start_time=start_of_day,
        max_start_time=end_of_day,
        status="active",
    )


@router.get("/stats", response_model=MeetingStats)
async def get_meeting_stats():
    """Get meeting statistics"""
    if not calendly_service.is_configured():
        return MeetingStats(
            upcoming_count=0,
            today_count=0,
            this_week_count=0,
            past_30_days_count=0,
        )
    
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    end_of_week = start_of_day + timedelta(days=7)
    
    # Get all relevant meetings in one call (more efficient)
    upcoming = await calendly_service.get_upcoming_meetings(days=30)
    past = await calendly_service.get_past_meetings(days=30)
    
    today_count = sum(1 for m in upcoming if start_of_day <= m.start_time < end_of_day)
    this_week_count = sum(1 for m in upcoming if start_of_day <= m.start_time < end_of_week)
    
    return MeetingStats(
        upcoming_count=len(upcoming),
        today_count=today_count,
        this_week_count=this_week_count,
        past_30_days_count=len(past),
    )

