"""FastAPI application entry point"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import agents, prospects, campaigns
from app.api.routes import intent_search, csv_upload, gmail_auth, saved_prospects, calendly
from app.api.routes import settings as settings_routes
from app.api.routes import lead_generation
from app.models.database import Base, engine
from app.config import settings
import logging
import uuid

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Chillion Multi-Agent Outreach System",
    description="Production-grade multi-agent system for LinkedIn, Email, and Intent-based outreach",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID middleware
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = correlation_id
    return response

# Include routers
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["prospects"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(intent_search.router, prefix="/api/v1/intent", tags=["intent"])
app.include_router(csv_upload.router, prefix="/api/v1/csv", tags=["csv"])
app.include_router(gmail_auth.router, prefix="/api/v1/gmail", tags=["gmail"])
app.include_router(saved_prospects.router, prefix="/api/v1/saved-prospects", tags=["saved-prospects"])
app.include_router(calendly.router, prefix="/api/v1/calendly", tags=["calendly"])
app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(lead_generation.router, prefix="/api/v1/lead-gen", tags=["lead-generation"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Chillion Multi-Agent Outreach System",
        "version": "1.0.0",
        "llm_provider": settings.llm_provider,
        "ollama_model": settings.ollama_model,
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "llm_provider": settings.llm_provider,
        "ollama_model": settings.ollama_model,
        "gmail_configured": bool(settings.google_oauth_client_id),
        "search_configured": bool(settings.google_api_key and settings.google_search_cx),
    }

# Simple metrics endpoint (in-memory counters placeholder)
metrics_counters = {
    "requests_total": 0,
    "errors_total": 0,
}

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    metrics_counters["requests_total"] += 1
    response = await call_next(request)
    if response.status_code >= 500:
        metrics_counters["errors_total"] += 1
    return response

@app.get("/metrics")
async def metrics():
    return metrics_counters
