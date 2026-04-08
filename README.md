# Omura — Personal & Business Operating System

A fully integrated life and business management platform built for **Sir**. Omura combines AI agents, cross-platform integrations, and a unified dashboard to automate and optimize every aspect of life and business.

## Features

- **Life Overview** — Calendar, tasks, habits, AI-prioritized daily agenda
- **Business Command** — Projects, revenue, KPIs, lead tracking
- **Content Studio** — Kanban content pipeline with AI drafting and scheduling
- **Communication Center** — Unified inbox (Gmail, Instagram, Facebook, TikTok) with AI triage
- **Knowledge Hub** — Notes, research, and strategy documents
- **Automation Control** — 9 AI agents with workflow orchestration
- **Scenario Simulator** — What-if simulations for business, finance, content, and life
- **Health Dashboard** — Sleep, workouts, supplements, energy scoring

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python / FastAPI |
| Frontend | React / Next.js / Tailwind CSS |
| Database | PostgreSQL (structured) + Redis (cache) |
| AI | Claude / OpenAI / Ollama (pluggable) |
| Auth | OAuth 2.0 |
| Security | AES-256 encryption |
| Deployment | Docker / Kubernetes |

## Quick Start

### 1. Clone and configure
```bash
cd "Omura Life manager"
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### 2. Start with Docker (recommended)
```bash
cd deployments
docker-compose up -d
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

### 3. Start manually
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Project Structure

```
Omura/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point (all routes)
│   │   ├── config.py              # Environment config
│   │   ├── database/
│   │   │   ├── models.py          # 12 DB models (projects, emails, KPIs, etc.)
│   │   │   ├── crud.py            # CRUD operations + query helpers
│   │   │   └── session.py         # PostgreSQL + Redis session management
│   │   ├── api/
│   │   │   ├── email_api.py       # Gmail integration
│   │   │   ├── social_api.py      # Instagram, Facebook, TikTok, YouTube
│   │   │   ├── ads_api.py         # Ad campaign tracking
│   │   │   ├── calendar_api.py    # Google Calendar, Todoist, Notion
│   │   │   └── finance_api.py     # QuickBooks + health data
│   │   ├── ai_agents/
│   │   │   ├── inbox_ai.py        # Email/DM triage
│   │   │   ├── content_ai.py      # Content creation & scheduling
│   │   │   ├── project_ai.py      # Project pipeline management
│   │   │   ├── crm_ai.py          # Lead scoring & outreach
│   │   │   ├── finance_ai.py      # Revenue & KPI analysis
│   │   │   ├── health_ai.py       # Fitness & wellness optimization
│   │   │   ├── market_ai.py       # Competitor & trend analysis
│   │   │   ├── scenario_ai.py     # What-if simulations
│   │   │   └── automation_ai.py   # Workflow execution engine
│   │   └── utils/
│   │       ├── logging.py         # Centralized action logging
│   │       ├── security.py        # AES-256 encryption + JWT + OAuth
│   │       └── scheduler.py       # APScheduler task scheduling
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/Dashboard/  # 8 dashboard section components
│   │   ├── components/Shared/     # Header, Sidebar, Notifications
│   │   ├── pages/                 # index, login, settings
│   │   ├── services/              # API client + auth service
│   │   └── utils/                 # Formatting + push notifications
│   └── package.json
├── docs/                          # Workflow diagrams, agent docs, integration guide
├── deployments/                   # Docker Compose + Kubernetes manifests
└── README.md
```

## AI Agents

| Agent | Purpose |
|-------|---------|
| Inbox AI | Triage messages, summarize, suggest responses |
| Content AI | Draft posts, generate hashtags, schedule content |
| Project AI | Manage pipeline, predict bottlenecks, prioritize tasks |
| CRM AI | Score leads, automate follow-ups, personalize outreach |
| Finance AI | Track KPIs, detect anomalies, forecast revenue |
| Health AI | Analyze sleep/workouts, recommend supplements, energy scoring |
| Market AI | Monitor competitors, identify trends and opportunities |
| Scenario AI | Run what-if simulations across all domains |
| Automation AI | Execute workflows and repetitive tasks |

## Automation Workflows

1. **Lead Management:** Email → Inbox AI triage → CRM AI scores → Auto follow-up → Dashboard
2. **Content Publishing:** Idea → Content AI drafts → Schedule → Predict engagement → Metrics
3. **Health Optimization:** Data collection → Health AI analysis → Schedule adjustment → Energy score
4. **Business Metrics:** Revenue/expense → KPI calculation → Anomaly alerts → Optimization suggestions

## API Documentation

Interactive API docs available at `http://localhost:8000/docs` when the backend is running.

## Development Roadmap

- **Phase 1** ✅ Core data integrations + basic dashboard
- **Phase 2** ✅ AI Agents (Inbox, Project, Content) + automation
- **Phase 3** ✅ CRM, Finance, Health AI + cross-platform orchestration
- **Phase 4** ✅ Market AI, Scenario AI, simulation module
- **Phase 5** 🔄 Learning patterns, dashboard refinement, full automation

## Security

- OAuth 2.0 authentication for all external integrations
- AES-256 encrypted storage for sensitive data
- JWT-based session management
- All AI agent actions logged with timestamps
- Automated backups configurable via scheduler

---

Built for Sir. Powered by Omura.
