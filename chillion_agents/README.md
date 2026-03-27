# Chillion Multi-Agent Outreach System

Production-grade multi-agent system for automated, compliant outreach across LinkedIn, Email, and Intent Listening channels — built for **Chillion IT & Consultancy Pvt. Ltd.**

## Features

- **LinkedIn DM Agent**: Personalized LinkedIn messages
- **Email Conversation Agent**: Professional B2B emails
- **Intent Listener Agent**: Finds and scores intent signals from web feeds
- **RAG Integration**: Retrieval-augmented generation from Chillion solution docs
- **Human-in-the-loop**: All outbound messages are drafts requiring approval
- **Lead generation**: Social, company, and contact discovery

## Quick Start

```bash
cd chillion_agents
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload
```

## Solution areas (default catalog)

- IT Infrastructure & Enterprise Solutions
- Cyber Security & Managed Services
- Cloud, Data Center, SaaS & PaaS
- Software Licensing & Digital Solutions
- Defense Technologies & Specialized Engineering
- Precision Engineering, Optics & Photonics
- RF, Microwave & Antenna Solutions

## Load knowledge base

Place PDF/Markdown files in `docs/chillion_products/`, then:

```bash
python scripts/load_chillion_docs.py
```

## License

Proprietary — Chillion IT & Consultancy Pvt. Ltd.
