# Omura Life Manager — Full Capabilities Reference

**Type:** Personal & Business Operating System  
**Architecture:** AI-driven, local-first, privacy-preserving  
**Tech Stack:** Python 3.14 / FastAPI · React 18 / Next.js 14 · PostgreSQL · Claude API (Anthropic)

---

## Table of Contents

1. [Core Design Principles](#1-core-design-principles)
2. [Data Models](#2-data-models)
3. [API Endpoints](#3-api-endpoints)
4. [AI Agents](#4-ai-agents)
5. [Platform Integrations](#5-platform-integrations)
6. [Dashboards & UI](#6-dashboards--ui)
7. [Automation Workflows](#7-automation-workflows)
8. [Background Scheduling](#8-background-scheduling)
9. [Security & Privacy](#9-security--privacy)
10. [Data Import / Export](#10-data-import--export)

---

## 1. Core Design Principles

- Runs entirely on localhost by default — no data leaves the machine without approval
- AI never accesses the internet without explicit user confirmation (Internet Guard)
- All credentials encrypted at rest with AES-256 (Fernet)
- Full audit trail of every AI agent action
- Conversation history and context persist across sessions
- Single unified interface: talk to Omura in natural language; it handles everything else

---

## 2. Data Models

| Model | Purpose |
|---|---|
| Communication | Unified inbox — Gmail, Instagram, Facebook, TikTok, WhatsApp, YouTube |
| Project | Projects with deadline, priority, progress, AI bottleneck prediction |
| Task | Tasks with status, priority, due date, project assignment |
| ContentItem | Content pipeline (idea → draft → review → scheduled → published) |
| Lead | CRM prospects — AI score, pipeline status, follow-up tracking |
| CalendarEvent | Google Calendar + manual events |
| Metric | KPIs, revenue, expenses, ad spend across platforms |
| HealthEntry | Sleep, workouts, supplements, nutrition |
| Note | Knowledge hub — markdown, tags, categories |
| Campaign | Marketing campaigns (outreach, content, ads, email) |
| Scenario | What-if simulation results |
| Conversation | Chat session container |
| ChatMessage | Full message history (user / assistant / system) |
| AgentLog | Audit trail of all AI agent actions |
| Credential | Encrypted OAuth tokens and API keys |
| InternetRequest | Internet access approval queue |
| ImportedContext | Parsed ChatGPT exports and external knowledge |

---

## 3. API Endpoints

### Communications
- `GET /api/communications` — List all messages (paginated)
- `GET /api/communications/unread` — Unread messages
- `GET /api/communications/flagged` — Flagged messages
- `GET /api/communications/urgent` — High / critical urgency messages
- `GET /api/communications/{id}` — Single message detail
- `POST /api/communications` — Create communication (manual)
- `PATCH /api/communications/{id}` — Update (read, flag, label)
- `POST /api/sync/emails` — Trigger Gmail sync + Inbox AI triage
- `POST /api/email/send` — Send email via Gmail API
- `POST /api/email/test` — Validate Gmail connection

### Projects
- `GET /api/projects` — List projects (paginated)
- `GET /api/projects/active` — Active projects only
- `GET /api/projects/{id}` — Project with all tasks
- `POST /api/projects` — Create project
- `PATCH /api/projects/{id}` — Update project
- `DELETE /api/projects/{id}` — Delete project (cascades tasks)

### Tasks
- `GET /api/tasks` — List tasks (paginated, filterable)
- `GET /api/tasks/today` — Due today
- `GET /api/tasks/overdue` — Overdue tasks
- `POST /api/tasks` — Create task
- `PATCH /api/tasks/{id}` — Update task
- `DELETE /api/tasks/{id}` — Delete task

### Content
- `GET /api/content` — List content items (paginated)
- `GET /api/content/pipeline` — Content grouped by status
- `GET /api/content/scheduled` — Scheduled content by platform
- `POST /api/content` — Create content item
- `PATCH /api/content/{id}` — Update content
- `DELETE /api/content/{id}` — Delete content

### Leads & CRM
- `GET /api/leads` — List leads (paginated, filterable)
- `GET /api/leads/hot` — Hot leads (score ≥ 70 by default)
- `GET /api/leads/followups` — Overdue follow-up leads
- `POST /api/leads` — Create lead
- `PATCH /api/leads/{id}` — Update lead

### Apollo Lead Intelligence
- `GET /api/apollo/search` — Search contacts (title, company, location)
- `GET /api/apollo/enrich/person` — Enrich person by email
- `GET /api/apollo/enrich/company` — Enrich company by domain
- `POST /api/apollo/sync-lead/{id}` — Sync lead with Apollo
- `GET /api/apollo/contacts` — Apollo sequence contacts

### Outreach Pipeline
- `POST /api/outreach/run-pipeline` — Full lead gen + outreach (find → research → verify → draft → send)
- `POST /api/outreach/verify-email` — MX record email verification
- `POST /api/outreach/send/{lead_id}` — Send personalized outreach email
- `POST /api/outreach/research` — Research a lead via web (with approval)

### Calendar
- `GET /api/calendar` — List events
- `GET /api/calendar/today` — Today's events
- `POST /api/calendar` — Create event
- `POST /api/sync/calendar` — Sync from Google Calendar

### Health
- `GET /api/health` — Get health entries
- `POST /api/health` — Log workout, sleep, supplement, or nutrition

### Metrics & KPIs
- `GET /api/metrics` — All metrics (paginated)
- `GET /api/metrics/kpis` — KPI summary (MRR, revenue, conversion, ROI)
- `POST /api/metrics` — Log metric

### Notes (Knowledge Hub)
- `GET /api/notes` — List notes (filterable by category / tag)
- `POST /api/notes` — Create note (markdown, tags, category)
- `PATCH /api/notes/{id}` — Update note
- `DELETE /api/notes/{id}` — Delete note

### Scenario Simulation
- `GET /api/scenarios` — List saved scenarios
- `POST /api/scenarios` — Run new simulation
- `GET /api/scenarios/{id}` — Get scenario with full results

### AI Chat
- `POST /api/chat` — Send message to Supervisor AI
- `GET /api/chat/history` — Chat history (last 50 by default)
- `DELETE /api/chat/clear` — Clear all chat history
- `GET /api/conversations` — List conversations
- `POST /api/conversations` — Create conversation
- `DELETE /api/conversations/{id}` — Delete conversation
- `GET /api/conversations/{id}/messages` — Messages in conversation
- `POST /api/conversations/{id}/chat` — Send message in conversation
- `POST /api/conversations/{id}/chat/stream` — Streamed response (SSE)

### Credentials
- `POST /api/credentials` — Store encrypted credential
- `GET /api/credentials` — List credentials (metadata only)
- `DELETE /api/credentials/{name}` — Delete credential

### Internet Access Control
- `GET /api/internet-requests` — Pending requests
- `POST /api/internet-requests/{id}/approve` — Approve request
- `POST /api/internet-requests/{id}/deny` — Deny request

### Agent & Automation
- `POST /api/ai/execute` — Run a specific agent (inbox, content, project, CRM, finance, health, market, scenario, automation)
- `POST /api/ai/workflow` — Execute a multi-step workflow
- `GET /api/agent-logs` — Agent action logs (filterable)
- `GET /api/scheduler/jobs` — List scheduled jobs
- `POST /api/scheduler/trigger/{job_id}` — Manually trigger job

### Import & Integration
- `POST /api/import/chatgpt` — Upload and parse ChatGPT conversations.json export
- `POST /api/import/context` — Manually add imported context
- `GET /api/import/contexts` — List imported contexts
- `GET /api/drive/files` — List Google Drive files in Omura folder
- `POST /api/drive/backup` — Backup Omura data to Google Drive
- `POST /api/sheets/export` — Export to Google Sheets
- `POST /api/sheets/import` — Import from Google Sheets

### Dashboard Aggregation
- `GET /api/dashboard/life-overview` — Calendar, tasks, habits, daily agenda
- `GET /api/dashboard/business-command` — Revenue, KPIs, projects, hot leads, agent logs
- `GET /api/dashboard/content-studio` — Content pipeline, scheduled posts, engagement
- `GET /api/dashboard/communication-center` — Unread/flagged/urgent message summary

### Auth & System
- `GET /auth/google` — Initiate Google OAuth
- `GET /auth/google/callback` — Handle OAuth callback
- `GET /auth/google/status` — Google connection status
- `POST /auth/google/disconnect` — Revoke Google credentials
- `GET /health` — System health check
- `GET /api/settings` — Get user settings
- `POST /api/settings` — Update settings

---

## 4. AI Agents

### Supervisor AI (Central Brain)
The primary AI interface powered by Claude. Orchestrates all other agents.

- Loads full system snapshot on every message (tasks, projects, leads, events, KPIs, health, imported context)
- Maintains 50-message conversation history
- Tool-use loop with up to 15 iterations per request
- Logs every action to AgentLog

**17 Tools Available:**

| Tool | Action |
|---|---|
| `create_task` | Create task with optional project assignment |
| `update_task` | Modify status, priority, due date, project |
| `create_project` | Create project with deadline and priority |
| `update_project` | Modify progress, status, deadline |
| `create_lead` | Save lead with enriched data and score |
| `update_lead` | Update status, score, notes, follow-up date |
| `create_content` | Create content item for social platforms |
| `update_content` | Modify status, scheduling, captions, hashtags |
| `create_event` | Create calendar event |
| `create_note` | Save markdown note with tags and category |
| `create_campaign` | Create marketing campaign |
| `update_campaign` | Modify campaign goals, budget, status |
| `create_metric` | Log KPI, revenue, expense, or ad metric |
| `create_health_entry` | Log workout, sleep, supplement, or nutrition |
| `search_records` | Query any model with filters |
| `get_next_steps` | Get AI-prioritized action plan |
| `request_internet` | Request approval to access external URL/API |

---

### Inbox AI
- Categorizes messages by urgency (critical / high / medium / low / informational)
- Assigns labels: client, invoice, support, scheduling, personal, marketing, legal, partnership, notification, spam
- Generates AI summaries of long messages
- Suggests contextual replies
- Detects spam and invalid messages
- Batch-triage multiple messages in one pass

### Content AI
- Generates platform-specific drafts (Instagram, TikTok, YouTube, Facebook, Twitter, LinkedIn, Threads)
- Optimizes hashtags for reach
- Creates video scripts and captions
- Suggests trending topics and content ideas
- Predicts engagement scores
- Recommends A/B test variations (copy, posting times)

### Project AI
- Detects bottlenecks blocking pipeline progress
- Generates daily agenda (prioritized, what to work on today)
- Estimates completion dates based on historical velocity
- Scores project health (0–100)
- Analyzes task distribution and resource allocation

### CRM AI
- Scores leads 0–100 based on engagement, fit, and communication
- Qualifies leads against ideal customer profile (ICP)
- Analyses pipeline by stage and conversion probability
- Suggests follow-up content and timing per lead
- Detects churn risk and estimates win probability

### Outreach AI
- Searches Apollo.io or web for matching leads
- Verifies email deliverability (MX record check + syntax)
- Researches prospects (company, LinkedIn, news, recent activity)
- Drafts hyper-personalized outreach emails (mentions specific company details)
- Manages follow-up sequences (day 3, 7, 14)
- Tracks open rate, click rate, and reply rate

### Finance AI
- Calculates KPIs: MRR, ARR, LTV, CAC, conversion rate, ROI, profit margin
- Detects financial anomalies (unusual spend, revenue drops)
- Generates monthly / quarterly reports with trends
- Projects revenue 30 / 60 / 90 days out
- Identifies cost-saving and revenue optimization opportunities
- Analyses ad spend ROI (cost per lead, cost per conversion)

### Health AI
- Scores sleep quality (0–100) — deep sleep %, REM %, consistency, wake patterns
- Analyses workout frequency, intensity, recovery, muscle balance
- Tracks supplement effectiveness
- Scores overall daily energy (0–100)
- Detects health trends (improving / declining)
- Predicts full recovery times

### Market AI
- Monitors competitor websites for changes (products, pricing, hiring)
- Assesses competitive threat level (high / medium / low)
- Identifies market gaps and opportunities
- Tracks trending topics in your niche
- Monitors brand sentiment vs competitors
- Generates weekly / monthly market intelligence reports

### Scenario AI
Runs what-if simulations across four domains:

- **Business** — pricing changes, expansion, hiring, partnerships
- **Finance** — revenue projections, cost changes, investment ROI
- **Content** — posting frequency, platform mix, content type performance
- **Life** — time allocation, health habits, learning investments

Each scenario outputs: projected metrics · risk assessment · best / likely / worst case · timeline · resource requirements · AI recommendation

### Automation AI
Orchestrates multi-step workflows:

1. **Lead Management** — email received → triage → score → auto follow-up → dashboard update
2. **Content Publishing** — idea → AI draft → schedule → predict engagement → track metrics
3. **Health Optimization** — data collection → analysis → schedule adjustment → energy score
4. **Business Metrics** — revenue/expense sync → KPI calc → anomaly alert → optimization suggestions

---

## 5. Platform Integrations

| Platform | Capabilities |
|---|---|
| **Gmail** | Fetch inbox, send email, manage labels, search, drafts, attachments, signatures, threads |
| **Google Calendar** | Fetch / create / update / delete events, recurring events, reminders, availability |
| **Google Drive** | List, upload, download files; create folders; backup Omura data |
| **Google Sheets** | Export/import leads, tasks, projects; live Kanban pipeline sheet |
| **Instagram** | DMs, post/reel/story publishing, feed analytics, follower data, hashtag research |
| **Facebook** | Page posts, Messenger, comments, page analytics, Ad campaign management |
| **TikTok** | Video upload/publish, analytics, trend tracking, follower analytics |
| **YouTube** | Video upload/schedule, comments, channel analytics, playlists, transcripts |
| **Apollo.io** | Contact search & enrichment, company enrichment, email verification, sequences |
| **Google Ads** | Campaign list, performance metrics, bid management, keyword performance |
| **Facebook Ads** | Campaign management, ad set/creative performance, audience analytics, spend tracking |
| **TikTok Ads** | Campaign creation, performance analytics, audience targeting |
| **QuickBooks Online** | Income statement, balance sheet, invoices, expenses, P&L, tax categories |
| **Todoist** | Fetch / create / update tasks, due dates, labels, priorities |
| **Notion** | Fetch databases, create/update pages, filtered queries |

---

## 6. Dashboards & UI

### Life Overview
Calendar view · today's tasks + overdue · habits completion · AI-prioritized daily agenda · energy/mood score · quick-add actions

### Business Command
Revenue KPI · MRR · customer count · hot leads · active projects with progress bars · bottleneck alerts · agent activity log

### Content Studio
Pipeline Kanban (idea → draft → review → scheduled → published) · platform-specific previews · engagement metrics · hashtag suggestions · draft editor

### Communication Center
Unified inbox across all platforms · unread count by platform · flagged & urgent messages · AI-suggested replies · email compose with signature

### Knowledge Hub
Searchable notes list · markdown editor · category/tag filters · full-text search · note linking

### Automation Control
Scheduled jobs list · manual triggers · agent logs (searchable, filterable) · workflow execution history · error logs

### Outreach Pipeline
Lead search form · research results · email verification status · personalized draft preview · follow-up sequence status · campaign metrics

### Scenario Simulator
Scenario type selector · parameter input · side-by-side comparison · results charts · risk assessment · save and export

### Health & Fitness
Sleep analytics (quality score, trends) · workout log · supplement tracker · energy score · health goals and progress

### AI Chat
Full conversation history · streaming responses · action cards (what the AI did) · internet approval cards (inline approve/deny) · file upload (ChatGPT .json, CSV) · quick-action buttons

---

## 7. Automation Workflows

### Email → Action
Gmail sync (every 15 min) → extract text → Inbox AI triage (urgency, labels, summary) → store → notify user → optionally create lead

### Lead Generation → Outreach
AI chat request → Apollo/web search → research each prospect → verify email → personalized AI draft → send → track → auto follow-up on days 3, 7, 14

### Content → Multi-Platform Publish
Create idea → AI drafts platform variants → user edits & schedules → scheduler publishes → monitor engagement → AI analyses performance → suggest improvements

### Health Data → Optimization
Daily logging (sleep, workout, supplements) → Health AI analysis → energy score → detect patterns → AI recommendations → user reviews → implements

### Financial Data → KPI Reporting
Daily sync (QuickBooks + ad platforms) → calculate KPIs → detect anomalies → Finance AI summary → real-time dashboard → alert on anomalies

### Chat Message → Multi-Tool Execution
User message → build system snapshot → load 50-message history → call Claude API → tool-use loop (up to 15 iterations) → save reply → log actions → show action cards + reply to user

### Internet Access Control
AI wants external data → create InternetRequest (pending) → surface to user in chat → user approves or denies → execute or skip → log result

---

## 8. Background Scheduling

All jobs run via APScheduler BackgroundScheduler.

| Job | Interval | What It Does |
|---|---|---|
| `sync_emails` | Every 15 min | Fetch Gmail, Inbox AI triage, update Communications |
| `sync_calendar` | Every 30 min | Fetch Google Calendar events, detect conflicts |
| `sync_social` | Every 60 min | Fetch DMs/comments/mentions from social platforms |
| `daily_report` | 7:00 AM UTC | Summarize previous day, prioritize today, email briefing |

Custom jobs can be registered, listed, and manually triggered via `/api/scheduler/*` endpoints.

---

## 9. Security & Privacy

| Layer | Implementation |
|---|---|
| Credential encryption | AES-256 Fernet, key derived from SHA-256 of ENCRYPTION_KEY setting |
| Authentication | JWT tokens for API; OAuth 2.0 for third-party services |
| Internet Guard | Every external request requires explicit user approval; all access logged |
| Data isolation | Runs on localhost by default; no third-party data sharing without OAuth |
| Audit trail | AgentLog (all AI actions) · ChatMessage (conversations) · InternetRequest (internet access) |
| Data deletion | Cascade deletes throughout — GDPR-compliant removal |

---

## 10. Data Import / Export

| Direction | Format / Source | Endpoint |
|---|---|---|
| Import | ChatGPT conversations.json export | `POST /api/import/chatgpt` |
| Import | Manual context (text) | `POST /api/import/context` |
| Import | CSV lead lists / bank data | `POST /api/import/*` |
| Export | Google Sheets (leads, tasks, projects) | `POST /api/sheets/export` |
| Import | Google Sheets | `POST /api/sheets/import` |
| Backup | Google Drive (full Omura data) | `POST /api/drive/backup` |
| Export | JSON (any model) | Via agent tools |

---

*Generated 2026-04-14 — reflects current codebase state.*
