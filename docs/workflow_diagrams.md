# Omura Workflow Diagrams

## 1. Lead Management Workflow
```
Incoming Email/DM
       │
       ▼
  ┌─────────────┐
  │  Inbox AI   │ ── Summarize & categorize
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │   CRM AI    │ ── Score lead (0-100)
  └──────┬──────┘
         │
         ▼
  ┌──────────────────┐
  │  Automation AI   │ ── Schedule follow-up
  └──────┬───────────┘
         │
         ▼
  ┌─────────────┐
  │  Dashboard   │ ── User reviews & approves
  └─────────────┘
```

## 2. Content Publishing Workflow
```
New Content Idea
       │
       ▼
  ┌──────────────┐
  │  Content AI  │ ── Generate draft + captions + hashtags
  └──────┬───────┘
         │
         ▼
  ┌──────────────────┐
  │  Automation AI   │ ── Schedule posting at optimal time
  └──────┬───────────┘
         │
         ▼
  ┌──────────────┐
  │  Market AI   │ ── Predict engagement
  └──────┬───────┘
         │
         ▼
  ┌─────────────┐
  │  Dashboard   │ ── Track metrics + performance
  └─────────────┘
```

## 3. Health Optimization Workflow
```
Health Data (sleep, workouts, supplements)
       │
       ▼
  ┌──────────────┐
  │  Health AI   │ ── Analyze patterns
  └──────┬───────┘
         │
         ▼
  ┌───────────────┐
  │  Scenario AI  │ ── Adjust schedule recommendations
  └──────┬────────┘
         │
         ▼
  ┌─────────────┐
  │  Dashboard   │ ── Show energy score + suggestions
  └─────────────┘
```

## 4. Business Metrics Workflow
```
Revenue & Expense Data
       │
       ▼
  ┌───────────────┐
  │  Finance AI   │ ── Calculate KPIs + detect anomalies
  └──────┬────────┘
         │
         ▼
  ┌─────────────┐
  │  Dashboard   │ ── Display KPIs + alerts
  └──────┬──────┘
         │
         ▼
  ┌───────────────┐
  │  Scenario AI  │ ── Suggest optimizations
  └───────────────┘
```

## 5. Daily Briefing Workflow (scheduled)
```
  Every morning at 7:00 AM
         │
         ▼
  ┌───────────────┐
  │  Project AI   │ ── Generate prioritized agenda
  └──────┬────────┘
         │
         ▼
  ┌───────────────┐
  │  Health AI    │ ── Calculate energy score
  └──────┬────────┘
         │
         ▼
  ┌──────────────┐
  │  Inbox AI    │ ── Summarize overnight messages
  └──────┬───────┘
         │
         ▼
  ┌─────────────┐
  │  Dashboard   │ ── Life Overview with full daily brief
  └─────────────┘
```

## Data Flow Architecture
```
┌─────────────────────────────────────────────┐
│            External APIs                      │
│  Gmail  Calendar  Instagram  Facebook         │
│  TikTok  YouTube  Todoist  Notion  QuickBooks │
└──────────────────┬──────────────────────────┘
                   │ Fetch / Webhooks
                   ▼
┌──────────────────────────────────────────────┐
│          API Integration Layer                │
│  email_api  social_api  ads_api               │
│  calendar_api  finance_api                    │
└──────────────────┬───────────────────────────┘
                   │ Normalize
                   ▼
┌──────────────────────────────────────────────┐
│          Data Layer (PostgreSQL + Redis)       │
│  communications  projects  tasks  content     │
│  metrics  health_entries  leads  notes         │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│          AI Agent Layer                       │
│  Inbox  Content  Project  CRM  Finance        │
│  Health  Market  Scenario  Automation         │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│          FastAPI Backend (REST API)            │
│  /api/dashboard/*  /api/ai/*  /api/sync/*     │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│          Next.js Frontend (React)             │
│  Dashboard sections  Settings  Login          │
└──────────────────────────────────────────────┘
```
