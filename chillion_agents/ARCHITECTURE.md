# Chillion Multi-Agent Outreach System - Architecture

## Overview
Production-grade multi-agent system for automated, compliant outreach across LinkedIn, Email, and Intent Listening channels.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   LinkedIn   │  │    Email     │  │    Intent    │     │
│  │  DM Agent    │  │ Conversation │  │   Listener   │     │
│  │              │  │    Agent     │  │    Agent     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                │                  │              │
│         └────────────────┼──────────────────┘              │
│                          │                                 │
│                  ┌───────▼────────┐                        │
│                  │  Orchestrator  │                        │
│                  │   (LangGraph)  │                        │
│                  └───────┬────────┘                        │
└──────────────────────────┼──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌─────▼─────┐    ┌─────▼─────┐
    │LinkedIn │      │   Email   │    │   Intent  │
    │ Service │      │  Service  │    │  Sources  │
    └─────────┘      └───────────┘    └───────────┘
         │                 │                 │
    ┌────▼─────────────────▼─────────────────▼────┐
    │         PostgreSQL Database                   │
    │  - prospects, companies, interactions        │
    │  - campaigns, agent_events                    │
    └───────────────────────────────────────────────┘
```

## Folder Structure

```
chillion_agents/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings and env vars
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseAgent abstract class
│   │   ├── linkedin_dm.py      # LinkedIn DM Agent
│   │   ├── email_conversation.py # Email Conversation Agent
│   │   └── intent_listener.py   # Intent Listener Agent
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy ORM models
│   │   └── schemas.py          # Pydantic schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── linkedin_service.py # LinkedIn connector interface
│   │   ├── email_service.py    # Email connector interface
│   │   └── intent_source.py    # Intent source base class
│   │
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── workflows.py        # LangGraph workflow definitions
│   │   └── state.py            # State management
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── linkedin_dm.py      # LinkedIn DM prompts
│   │   ├── email_conversation.py # Email prompts
│   │   └── intent_listener.py  # Intent classification prompts
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── vector_store.py     # Vector DB setup (Chroma/FAISS)
│   │   └── embeddings.py       # Embedding generation
│   │
│   └── api/
│       ├── __init__.py
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── agents.py        # Agent endpoints
│       │   ├── prospects.py    # Prospect management
│       │   └── campaigns.py    # Campaign orchestration
│       └── dependencies.py     # FastAPI dependencies
│
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_orchestration.py
│   └── fixtures/
│
├── scripts/
│   ├── init_db.py              # Database initialization
│   └── load_chillion_docs.py     # Load Chillion docs into RAG
│
├── docs/
│   └── chillion_products/        # Product documentation for RAG
│
├── requirements.txt
├── .env.example
└── README.md
```

## Core Components

### 1. Agents (`app/agents/`)

**BaseAgent** (`base.py`)
- Abstract base class with `process(input: AgentInput) -> AgentOutput`
- Shared utilities for prompt building, RAG retrieval, logging

**LinkedIn DM Agent** (`linkedin_dm.py`)
- Input: ProspectProfile, ConversationStage, OfferContext, PastThreadSummary
- Output: DraftMessage with personalization notes
- Behavior: Human-like, pain-point focused, non-spammy

**Email Conversation Agent** (`email_conversation.py`)
- Input: ProspectRecord, CompanyContext, ConversationStage, ThreadSummary
- Output: DraftEmail with subject, body (HTML/text), CTA
- Behavior: B2B professional, one idea per email, easy opt-out

**Intent Listener Agent** (`intent_listener.py`)
- Input: Keywords, FeedItems
- Output: IntentRecords with scores and product mappings
- Behavior: Classify, filter, score, create prospects

### 2. Services (`app/services/`)

**LinkedInService** (interface)
- `search_recent_engagers()` -> List[Profile]
- `fetch_profile(handle)` -> Profile
- `draft_connection_request(profile)` -> DraftPayload
- `draft_reply(thread_id, context)` -> DraftPayload
- All return payloads for human approval, never send directly

**EmailService** (interface)
- `send_email(draft)` -> DeliveryResult (after approval)
- `fetch_thread(email)` -> ThreadSummary
- `log_delivery(email_id, status)` -> None
- Abstract SMTP or SendGrid

**IntentSource** (base class)
- `fetch_feed(keywords, since)` -> List[FeedItem]
- Implementations: RSSFeedSource, TwitterSearchSource, LinkedInSearchSource, GoogleAlertsSource

### 3. Data Models (`app/models/`)

**Database Models** (SQLAlchemy)
- `Prospect`: id, name, email, linkedin_url, title, company_id, stage, created_at
- `Company`: id, name, industry, website, employee_count
- `Interaction`: id, prospect_id, channel, message_type, content, status, created_at
- `Campaign`: id, name, agent_type, status, created_at
- `AgentEvent`: id, agent_type, event_type, payload, created_at

**Pydantic Schemas**
- Input/Output schemas for each agent
- API request/response models
- Validation and serialization

### 4. Orchestration (`app/orchestration/`)

**LangGraph Workflows**
- `warm_engagement_to_dm`: Profile enrichment -> DM draft -> Review queue
- `intent_capture_to_prospect`: Feed items -> Intent scoring -> Prospect creation
- `mixed_cadence_flow`: State machine for stage transitions (not_contacted -> first_touch -> replied -> meeting_booked -> closed_won/lost)

### 5. RAG (`app/rag/`)

- Load Chillion product docs into vector store
- Retrieve relevant context for agent prompts
- Use embeddings (OpenAI/Cohere) + Chroma or FAISS

## Safety & Compliance

1. **Human-in-the-loop**: All outbound messages are drafts returned as JSON
2. **Rate limiting**: Configurable limits per channel per day
3. **Opt-out support**: Email templates include unsubscribe links
4. **Privacy**: Store only business contact info (CRM standard)
5. **Platform rules**: No rate limit evasion, respect ToS

## Next Steps

1. Scaffold FastAPI app with folder structure
2. Create database models and migrations
3. Implement base agent class and three concrete agents
4. Build service interfaces (LinkedIn, Email, Intent)
5. Set up LangGraph orchestration
6. Add RAG for Chillion docs
7. Create API endpoints for agent invocation and draft review
8. Write unit tests for core logic

