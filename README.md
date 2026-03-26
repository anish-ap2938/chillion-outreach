# CHILLION Outreach Command Center

Outreach dashboard for [Chillion IT & Consultancy Pvt. Ltd.](https://www.chillion.in) — intent discovery, lead research, LinkedIn/email campaigns, and meeting prep.

## Stack

- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Prisma (SQLite auth)
- **Backend agents:** FastAPI, LangChain/LangGraph, Chroma RAG (`chillion_agents/`)

## Quick start

### Frontend

```bash
npm install
npx prisma generate
npx prisma db push
npm run dev
```

Open http://localhost:3000 (or your chosen port).

### Backend agents

```bash
cd chillion_agents
pip install -r requirements.txt
cp .env.example .env   # if present
python scripts/init_db.py
uvicorn app.main:app --reload
```

API: http://localhost:8000

Set `NEXT_PUBLIC_AGENTS_API_URL=http://localhost:8000` in `.env`.

## Knowledge base

Add Chillion solution docs (PDF or Markdown) to:

`chillion_agents/docs/chillion_products/`

Then load into RAG:

```bash
cd chillion_agents
python scripts/load_chillion_docs.py
```

## Brand

This project is rebranded for **CHILLION** — IT infrastructure, cyber security, cloud, software licensing, and advanced engineering outreach. Legacy Emagia artifacts are excluded via `.gitignore`.
