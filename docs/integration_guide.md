# Omura Integration Guide

## Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker (optional, for containerized deployment)

---

## 1. OAuth Setup

### Google (Gmail + Calendar + YouTube)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project named "Omura"
3. Enable APIs: Gmail API, Google Calendar API, YouTube Data API v3
4. Create OAuth 2.0 credentials (Web application)
5. Set redirect URI: `http://localhost:8000/auth/google/callback`
6. Copy Client ID and Secret to `.env`

### Facebook + Instagram
1. Go to [Facebook Developers](https://developers.facebook.com)
2. Create a new app (Business type)
3. Add Facebook Login product
4. Add Instagram Graph API permissions
5. Copy App ID and Secret to `.env`

### TikTok
1. Go to [TikTok for Developers](https://developers.tiktok.com)
2. Create a new app
3. Add Login Kit and Content Posting API
4. Copy Client Key and Secret to `.env`

---

## 2. API Keys

### AI Providers
- **OpenAI:** Get key from [platform.openai.com](https://platform.openai.com)
- **Anthropic (Claude):** Get key from [console.anthropic.com](https://console.anthropic.com)
- **Ollama (local):** Install from [ollama.ai](https://ollama.ai), runs on localhost:11434

### External Services
- **Todoist:** Settings → Integrations → Developer → API token
- **Notion:** [notion.so/my-integrations](https://notion.so/my-integrations) → New integration
- **QuickBooks:** [developer.intuit.com](https://developer.intuit.com) → Create app

---

## 3. Database Setup

```bash
# Create PostgreSQL database
createdb omura
# Or via psql:
psql -c "CREATE DATABASE omura;"
psql -c "CREATE USER omura WITH PASSWORD 'omura';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE omura TO omura;"
```

Tables are auto-created on first backend startup via SQLAlchemy.

---

## 4. Environment Configuration

```bash
cd backend
cp .env.example .env
# Edit .env with your credentials
```

---

## 5. Running Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### With Docker
```bash
cd deployments
docker-compose up -d
```

---

## 6. API Endpoints Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/life-overview` | GET | Life dashboard data |
| `/api/dashboard/business-command` | GET | Business dashboard data |
| `/api/dashboard/content-studio` | GET | Content pipeline data |
| `/api/dashboard/communication-center` | GET | Inbox summary |
| `/api/communications` | GET/POST | Messages CRUD |
| `/api/projects` | GET/POST | Projects CRUD |
| `/api/tasks` | GET/POST | Tasks CRUD |
| `/api/content` | GET/POST | Content items CRUD |
| `/api/leads` | GET/POST | CRM leads CRUD |
| `/api/metrics` | GET/POST | Business metrics |
| `/api/health` | GET/POST | Health entries |
| `/api/calendar` | GET/POST | Calendar events |
| `/api/notes` | GET/POST | Knowledge hub notes |
| `/api/scenarios` | GET/POST | What-if simulations |
| `/api/ai/execute` | POST | Run AI agent action |
| `/api/ai/workflow` | POST | Run automation workflow |
| `/api/agent-logs` | GET | AI agent activity logs |

---

## 7. Deployment (Cloud)

### AWS
- Backend: ECS Fargate or EC2
- Database: RDS PostgreSQL
- Cache: ElastiCache Redis
- Frontend: Amplify or S3 + CloudFront

### GCP
- Backend: Cloud Run or GKE
- Database: Cloud SQL PostgreSQL
- Cache: Memorystore Redis
- Frontend: Firebase Hosting

### Heroku
```bash
heroku create omura-backend
heroku addons:create heroku-postgresql
heroku addons:create heroku-redis
git push heroku main
```
