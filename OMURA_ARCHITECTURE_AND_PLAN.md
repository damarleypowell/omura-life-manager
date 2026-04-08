# Omura Life Manager — Architecture & Implementation Plan

**Owner:** Damarley
**Date:** 2026-03-29
**Status:** Core built, needs wiring + frontend upgrade + startup fixes

---

## 1. WHAT OMURA IS

A fully local personal & business operating system with an AI supervisor (Claude) as the central brain. Damarley talks to it in natural language, and it delegates, manages, tracks, and optimizes everything — tasks, projects, CRM, content, campaigns, health, finances, and calendar.

**Key principles:**
- Runs 100% on Damarley's laptop (localhost)
- AI NEVER accesses internet without explicit user approval + explanation
- All credentials stored with AES-256 encryption (Fernet)
- Claude API is the only external service used (with Damarley's own key)

---

## 2. TECH STACK

| Layer | Tech | Notes |
|-------|------|-------|
| Backend | FastAPI (Python 3.14) | Port 8001 |
| Frontend | Next.js 14 / React 18 / Tailwind | Port 3001 |
| Database | PostgreSQL 18 | localhost:5432, db=omura, user=omura, pass=omura |
| AI | Claude API (anthropic SDK) | Sonnet 4 model, tool-use loop |
| Encryption | cryptography/Fernet (AES-256) | SHA-256 derived key |
| Scheduler | APScheduler | Background thread pool |
| Cache | Redis (optional, graceful fallback) | Not required |

**Python path:** `C:\Users\damar\AppData\Local\Programs\Python\Python314\python.exe`
**PostgreSQL path:** `C:\Program Files\PostgreSQL\18\`
**PostgreSQL superuser:** postgres / Damarpow187699
**Node:** v22.20.0, npm 11.7.0

---

## 3. FILE STRUCTURE & STATUS

```
Omura Life manager/
├── backend/
│   ├── .env                          ✅ DONE (has DB URL + Claude API key)
│   ├── requirements.txt              ✅ DONE (pip installed on Python 3.14)
│   ├── app/
│   │   ├── config.py                 ✅ DONE — Pydantic Settings, loads .env
│   │   ├── main.py                   ⚠️ NEEDS UPDATE — missing chat, credential, import, campaign, internet-request endpoints
│   │   ├── database/
│   │   │   ├── session.py            ✅ DONE — SQLAlchemy engine + session + optional Redis
│   │   │   ├── models.py             ✅ DONE — 17 models including ChatMessage, Credential, InternetRequest, Campaign, ImportedContext
│   │   │   └── crud.py               ⚠️ NEEDS UPDATE — missing CRUD helpers for new models (ChatMessage, Campaign, Credential, etc.)
│   │   ├── ai_agents/
│   │   │   ├── supervisor_ai.py      ✅ DONE — Full Claude tool-use loop with 17 tools, system prompt, context loading, conversation history
│   │   │   ├── inbox_ai.py           ⚠️ PLACEHOLDER — needs real implementation
│   │   │   ├── content_ai.py         ⚠️ PLACEHOLDER
│   │   │   ├── project_ai.py         ⚠️ PLACEHOLDER
│   │   │   ├── crm_ai.py             ⚠️ PLACEHOLDER
│   │   │   ├── finance_ai.py         ⚠️ PLACEHOLDER
│   │   │   ├── health_ai.py          ⚠️ PLACEHOLDER
│   │   │   ├── market_ai.py          ⚠️ PLACEHOLDER
│   │   │   ├── scenario_ai.py        ⚠️ PLACEHOLDER
│   │   │   └── automation_ai.py      ⚠️ PLACEHOLDER
│   │   ├── api/
│   │   │   ├── email_api.py          ⚠️ PLACEHOLDER — Gmail client (no credentials wired)
│   │   │   ├── social_api.py         ⚠️ PLACEHOLDER — Instagram/FB/TikTok/YouTube clients
│   │   │   ├── ads_api.py            ⚠️ PLACEHOLDER
│   │   │   ├── calendar_api.py       ⚠️ PLACEHOLDER
│   │   │   └── finance_api.py        ⚠️ PLACEHOLDER
│   │   └── utils/
│   │       ├── credential_store.py   ✅ DONE — AES-256 encrypt/decrypt, CRUD for Credential model, upsert support
│   │       ├── internet_guard.py     ✅ DONE — Full approval workflow: request → approve/deny → execute
│   │       ├── scheduler.py          ✅ DONE — APScheduler wrapper with 4 default jobs (placeholder implementations)
│   │       ├── security.py           ⚠️ PLACEHOLDER — JWT + OAuth helpers
│   │       └── logging.py            ✅ DONE — OmuraLogger
├── frontend/
│   ├── package.json                  ✅ DONE (npm installed)
│   ├── tailwind.config.js            ✅ DONE — Custom dark theme
│   ├── src/
│   │   ├── services/
│   │   │   ├── apiService.js         ⚠️ NEEDS UPDATE — missing chat, credentials, import, campaigns, internet-requests API methods
│   │   │   └── authService.js        ✅ DONE
│   │   ├── pages/
│   │   │   ├── index.jsx             ⚠️ NEEDS UPDATE — missing AI Chat section in navigation
│   │   │   ├── _app.jsx              ✅ DONE
│   │   │   ├── login.jsx             ✅ DONE
│   │   │   └── settings.jsx          ⚠️ NEEDS UPDATE — should include credential management
│   │   ├── components/
│   │   │   ├── Shared/
│   │   │   │   ├── Sidebar.jsx       ⚠️ NEEDS UPDATE — add "AI Chat" and "Settings/Credentials" links
│   │   │   │   ├── Header.jsx        ✅ DONE
│   │   │   │   └── Notifications.jsx ✅ DONE
│   │   │   └── Dashboard/
│   │   │       ├── LifeOverview.jsx      ✅ DONE but displays fake data — needs to fetch real data and have add/edit forms
│   │   │       ├── BusinessCommand.jsx   ✅ DONE but fake data
│   │   │       ├── ContentStudio.jsx     ✅ DONE but fake data
│   │   │       ├── CommunicationCenter.jsx ✅ DONE but fake data
│   │   │       ├── KnowledgeHub.jsx      ✅ DONE but fake data
│   │   │       ├── AutomationControl.jsx ✅ DONE but fake data
│   │   │       ├── ScenarioSimulator.jsx ✅ DONE but fake data
│   │   │       └── HealthDashboard.jsx   ✅ DONE but fake data
│   │   │       ├── AIChat.jsx            ❌ MISSING — needs to be created
│   │   │       └── CredentialManager.jsx ❌ MISSING — needs to be created
│   │   └── styles/globals.css        ✅ DONE
├── deployments/                      ✅ DONE (docker-compose + k8s)
└── docs/                             ✅ DONE
```

---

## 4. WHAT'S DONE (Working)

### Database Models (17 total) — `backend/app/database/models.py`
All defined with SQLAlchemy ORM:
1. Communication, Project, Task, ContentItem, Metric, HealthEntry, Lead, CalendarEvent, Note, AgentLog, Scenario (original 11)
2. ChatMessage — conversation history with AI supervisor
3. Credential — AES-256 encrypted credential storage
4. InternetRequest — AI internet access approval queue
5. Campaign — marketing campaign management
6. ImportedContext — parsed ChatGPT exports and other imported data

### Supervisor AI — `backend/app/ai_agents/supervisor_ai.py`
- **Fully implemented** Claude tool-use loop with 17 tools:
  - `create_task`, `update_task`, `create_project`, `update_project`
  - `create_lead`, `update_lead`, `create_content`, `update_content`
  - `create_event`, `create_note`, `create_campaign`, `update_campaign`
  - `create_metric`, `create_health_entry`
  - `search_records` (queries any model with filters)
  - `get_next_steps` (prioritized action plan from current state)
  - `request_internet` (creates approval request, never connects directly)
- System prompt includes full operational state snapshot (tasks, projects, leads, events, content, KPIs, health)
- Loads conversation history from ChatMessage table (last 50 messages)
- Loads imported context from ImportedContext table
- Handles tool-use loop with max 15 iterations
- Full error handling for Anthropic API errors
- Logs all actions to AgentLog table

### Credential Vault — `backend/app/utils/credential_store.py`
- AES-256 encryption via Fernet (SHA-256 derived key from settings.ENCRYPTION_KEY)
- `store_credential()` — encrypt + save (upsert behavior)
- `get_credential()` — decrypt + return single credential
- `list_credentials()` — returns metadata only (never exposes secrets)
- `delete_credential()` — remove by name
- `get_service_credentials()` — get all credentials for a service (e.g., all Google creds)

### Internet Guard — `backend/app/utils/internet_guard.py`
- `request_access()` — creates pending approval with purpose, target, data description, precautions
- `approve_request()` / `deny_request()` — user decision
- `execute_approved_request()` — only runs if approved
- `get_pending_requests()` — list awaiting approval
- `format_request_for_user()` — human-readable summary for the chat UI

### Scheduler — `backend/app/utils/scheduler.py`
- APScheduler BackgroundScheduler wrapper
- 4 default jobs: sync_emails (15min), sync_calendar (30min), sync_social (60min), daily_report (7am UTC)
- All jobs are currently placeholders — they log but don't do real work yet
- Supports add_job, remove_job, list_jobs at runtime

---

## 5. WHAT NEEDS TO BE BUILT (Priority Order)

### PRIORITY 1: Wire Backend Endpoints + Start Services

**A. Update `main.py`** to add these endpoint groups:

```python
# ── AI Chat ──
POST /api/chat              # Send message to supervisor AI, get response
GET  /api/chat/history      # Get chat history (paginated)
DELETE /api/chat/history     # Clear chat history

# ── Credentials ──
POST   /api/credentials           # Store new credential (encrypted)
GET    /api/credentials           # List all credentials (metadata only, no values)
DELETE /api/credentials/{name}    # Delete a credential

# ── Internet Requests ──
GET  /api/internet-requests              # List pending internet requests
POST /api/internet-requests/{id}/approve # Approve a request
POST /api/internet-requests/{id}/deny    # Deny a request

# ── Campaigns ──
GET    /api/campaigns            # List campaigns
POST   /api/campaigns            # Create campaign
PATCH  /api/campaigns/{id}       # Update campaign
DELETE /api/campaigns/{id}       # Delete campaign

# ── ChatGPT Import ──
POST /api/import/chatgpt         # Upload and parse ChatGPT JSON export
POST /api/import/context         # Manually add context (title, content, category, tags)
GET  /api/import/contexts        # List imported contexts

# ── Calendar Events (add update/delete) ──
PATCH  /api/calendar/{id}       # Update event
DELETE /api/calendar/{id}       # Delete event

# ── Health Entries (add update/delete) ──
PATCH  /api/health/{id}        # Update health entry
DELETE /api/health/{id}        # Delete health entry
```

**B. Add Pydantic schemas** for:
- `ChatRequest` (message: str)
- `ChatResponse` (reply: str, actions_taken: list, internet_requested: bool)
- `CredentialCreate` (name, service, credential_type, value, description)
- `CampaignCreate` / `CampaignUpdate`
- `CalendarEventCreate` / `CalendarEventUpdate`
- `ContextImportCreate` (source, title, content, category, tags)

**C. ChatGPT Import Parser** — Parse the `conversations.json` format from ChatGPT exports:
- Each conversation has `title` and `mapping` with messages
- Extract user/assistant message pairs
- Store as ImportedContext rows categorized by topic
- The AI uses this context to understand Damarley's goals, preferences, and history

**D. Update `crud.py`** — Add missing helpers:
- `get_chat_history(db, limit)` — recent ChatMessages
- `save_chat_message(db, role, content, ...)`
- Campaign CRUD (list, create, update, delete)
- Calendar event update/delete
- Health entry update/delete

**E. Update `.env`** — The `ENCRYPTION_KEY` is currently the default placeholder. Generate a real 32-byte key:
```python
import secrets; print(secrets.token_hex(32))
```

### PRIORITY 2: Build Frontend AI Chat UI

**File: `frontend/src/components/Dashboard/AIChat.jsx`**

This is the most important UI component — it's the central command interface.

Features needed:
- Full-screen chat interface with message history
- Real-time message streaming (or polling)
- Display tool actions the AI took (collapsible cards)
- Internet access request approval cards (inline approve/deny buttons)
- Typing indicator while AI is thinking
- Support for file upload (ChatGPT export .json)
- Quick action buttons: "What should I focus on?", "Daily briefing", "Content ideas"

**Wire to backend:** `POST /api/chat` with `{message: "..."}`, display the `reply` and `actions_taken`

### PRIORITY 3: Build Frontend Credential Manager

**File: `frontend/src/components/Dashboard/CredentialManager.jsx`** (also usable from Settings page)

Features needed:
- List stored credentials (name, service, type — never show values)
- Add new credential form: service dropdown (Google, Facebook, Instagram, TikTok, YouTube, Stripe, custom), type dropdown (client_id, client_secret, api_key, oauth_token), value input (password field), description
- Delete credential button with confirmation
- Group by service (collapsible sections)

### PRIORITY 4: Make All Dashboard Components Use Real Data + Add/Edit Forms

Every dashboard component currently shows hardcoded fake data. Each needs:
1. `useEffect` to fetch real data from the API on mount
2. "Add" button/modal with a form
3. Inline edit / "Edit" button for existing items
4. Delete button with confirmation

Components to update:
- **LifeOverview** — Calendar events + tasks (add/edit/complete)
- **BusinessCommand** — Projects + leads + KPIs (add/edit)
- **ContentStudio** — Content pipeline (add/edit, drag between stages)
- **CommunicationCenter** — Messages (mark read, flag, archive)
- **KnowledgeHub** — Notes (add/edit/delete with markdown)
- **AutomationControl** — Agent controls + logs (real data from agent_logs)
- **ScenarioSimulator** — Scenario forms (type params, get AI analysis)
- **HealthDashboard** — Health entries (add workouts, sleep, supplements)

### PRIORITY 5: Update apiService.js

Add the new API methods:
```javascript
// AI Chat
export const chat = {
  send: (message) => api.post('/api/chat', { message }),
  getHistory: (limit) => api.get('/api/chat/history', { params: { limit } }),
  clearHistory: () => api.delete('/api/chat/history'),
};

// Credentials
export const credentials = {
  list: () => api.get('/api/credentials'),
  store: (data) => api.post('/api/credentials', data),
  delete: (name) => api.delete(`/api/credentials/${name}`),
};

// Internet Requests
export const internetRequests = {
  getPending: () => api.get('/api/internet-requests'),
  approve: (id) => api.post(`/api/internet-requests/${id}/approve`),
  deny: (id) => api.post(`/api/internet-requests/${id}/deny`),
};

// Campaigns
export const campaigns = {
  list: (params) => api.get('/api/campaigns', { params }),
  create: (data) => api.post('/api/campaigns', data),
  update: (id, data) => api.patch(`/api/campaigns/${id}`, data),
  delete: (id) => api.delete(`/api/campaigns/${id}`),
};

// Context Import
export const imports = {
  chatgpt: (file) => { const fd = new FormData(); fd.append('file', file); return api.post('/api/import/chatgpt', fd); },
  addContext: (data) => api.post('/api/import/context', data),
  listContexts: () => api.get('/api/import/contexts'),
};
```

### PRIORITY 6: Add AI Chat to Navigation

- Update `Sidebar.jsx` — Add "AI Chat" as the FIRST nav item (this is the primary interface)
- Update `index.jsx` — Add `AIChat` to SECTION_COMPONENTS and SECTION_TITLES, set as default active section
- Optionally add "Credentials" under Settings

### PRIORITY 7: Background Scheduler Enhancements

Replace placeholder jobs with real implementations that:
- Query the AI supervisor for optimization suggestions
- Check for overdue tasks and create reminders
- Run campaign optimization (analyze metrics, suggest changes)
- Generate daily briefing notes

---

## 6. HOW TO START THE SERVERS

### Start PostgreSQL (if not running):
```bash
"/c/Program Files/PostgreSQL/18/bin/pg_ctl.exe" -D "/c/Program Files/PostgreSQL/18/data" start
```

### Start Backend:
```bash
cd "c:/Users/damar/OneDrive/Desktop/Omura Life manager"
"/c/Users/damar/AppData/Local/Programs/Python/Python314/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Start Frontend:
```bash
cd "c:/Users/damar/OneDrive/Desktop/Omura Life manager/frontend"
npx next dev -p 3001
```

### Important Notes:
- The frontend `apiService.js` currently defaults to `http://localhost:8000` — needs to be changed to `http://localhost:8001`
- The `next.config.js` may also proxy to the wrong port
- Use Python 3.14 specifically (the 3.13 installation doesn't have the pip packages)

---

## 7. KNOWN ISSUES TO FIX

1. **apiService.js API_BASE** — Points to port 8000, should be 8001
2. **next.config.js rewrites** — May proxy to wrong backend port
3. **ENCRYPTION_KEY** — Using default placeholder, needs a real key
4. **config.py GOOGLE_REDIRECT_URI** — Points to port 8000, should be 8001
5. **supervisor_ai.py line 542** — Uses `enum_base` before it's defined (import is at line 549). Needs reordering.
6. **crud.py** — Missing imports for new models (ChatMessage, Campaign, Credential, ImportedContext, InternetRequest)
7. **All 9 specialized AI agents** — Are placeholder classes, not yet functional
8. **All 5 API integration files** — Are placeholder classes, not yet functional
9. **Frontend dashboard components** — All show hardcoded fake data, no API calls

---

## 8. DATA FLOW: How the AI Chat Works

```
User types message in AIChat.jsx
    ↓
POST /api/chat {message: "..."}
    ↓
main.py → SupervisorAI.chat(message)
    ↓
1. Save user message to ChatMessage table
2. Build system prompt with current state snapshot
   - Queries: tasks due today, overdue, active projects, hot leads, events, content pipeline, KPIs, health
   - Loads imported context from ImportedContext table
3. Load last 50 chat messages for conversation history
4. Call Claude API with system prompt + tools + messages
    ↓
5. Claude responds — may include tool_use blocks
   - If tool_use: execute tool → return result → call Claude again
   - If text only: that's the final response
6. Save assistant response to ChatMessage table
7. Log to AgentLog table
    ↓
Return {reply: "...", actions_taken: [...], internet_requested: bool}
    ↓
Frontend displays reply + action cards
```

---

## 9. DATA FLOW: Credential Storage

```
User enters Google Client ID in CredentialManager.jsx
    ↓
POST /api/credentials {name: "google_client_id", service: "google", credential_type: "client_id", value: "..."}
    ↓
credential_store.store_credential() →
    SHA-256(ENCRYPTION_KEY) → Fernet key
    Fernet.encrypt(value) → encrypted bytes
    Save to Credential table (encrypted_value column)
    ↓
When an agent needs Google credentials:
    credential_store.get_service_credentials(db, "google")
    → Decrypts all Google creds → returns {"google_client_id": "...", "google_client_secret": "..."}
```

---

## 10. DATA FLOW: Internet Access Guard

```
AI supervisor decides it needs to check Instagram API
    ↓
Calls request_internet tool → creates InternetRequest(status="pending")
    ↓
AI tells user: "I need to access Instagram's API to check your post engagement. [APPROVE] [DENY]"
    ↓
User clicks APPROVE → POST /api/internet-requests/{id}/approve
    ↓
Backend: internet_guard.approve_request() → status = "approved"
    ↓
Agent can now call: internet_guard.execute_approved_request(id, executor_func)
    → Only executes if status == "approved"
    → Stores result on the request row
```

---

## 11. CHATGPT IMPORT FORMAT

ChatGPT exports a `conversations.json` file. Structure:
```json
[
  {
    "title": "Marketing Strategy Discussion",
    "create_time": 1711000000,
    "mapping": {
      "uuid1": {
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["I want to grow my Instagram to 10k..."]}
        }
      },
      "uuid2": {
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Here's a 90-day growth plan..."]}
        }
      }
    }
  }
]
```

The import parser should:
1. Accept file upload (multipart form)
2. Parse conversations.json
3. For each conversation, concatenate all messages into a single text
4. Categorize by topic (goals, preferences, history, knowledge, business, personal)
5. Store as ImportedContext rows
6. The supervisor AI system prompt includes these in its context

---

## 12. BANK DATA (No Direct Access Needed)

Damarley wants to track finances without giving the app direct bank access. Solution:
1. **CSV Import** — Most banks let you export transactions as CSV
2. Add an endpoint: `POST /api/import/bank-csv` that parses bank CSV files
3. Creates Metric records (category: "expense" or "revenue") from each transaction
4. The AI can then analyze spending patterns, create budgets, etc.
5. No API keys, no OAuth, no direct bank connection needed

---

## 13. GOOGLE CALENDAR INTEGRATION (Future)

When Damarley adds Google OAuth credentials through the credential manager:
1. Store client_id + client_secret encrypted
2. Implement OAuth flow: redirect to Google → get auth code → exchange for tokens → store refresh token encrypted
3. Use refresh token to sync events every 30 minutes (scheduler job)
4. Internet guard approves the first connection, then auto-approves recurring syncs from same service

---

## 14. 24/7 OPERATION

The scheduler runs as a background thread inside the FastAPI process. As long as the backend is running, it's running. To keep it running 24/7:
- Keep the terminal window open, or
- Run as a Windows service (future enhancement)
- Or use PM2/supervisor to manage the process

Current scheduled jobs (all placeholders, need real implementations):
- Sync emails: every 15 minutes
- Sync calendar: every 30 minutes
- Sync social: every 60 minutes
- Daily report: 7:00 AM UTC daily

---

## 15. WHAT TO TELL YOUR NEXT CHAT

Copy-paste this to your next Claude session:

---

**I'm building Omura — my personal AI operating system. Read the file `OMURA_ARCHITECTURE_AND_PLAN.md` in the project root for full architecture and what needs to be done. The priorities are:**

1. **Fix `apiService.js`** — change API_BASE to `http://localhost:8001`
2. **Add all missing endpoints to `main.py`** — chat, credentials, import, campaigns, internet-requests (see Priority 1 in the doc)
3. **Build `AIChat.jsx`** — full chat interface as the main UI (Priority 2)
4. **Build `CredentialManager.jsx`** — for storing Google/social OAuth secrets securely (Priority 3)
5. **Update all dashboard components** to fetch real data and have add/edit forms (Priority 4)
6. **Add AI Chat to sidebar navigation** as the first/default section (Priority 6)
7. **Build the ChatGPT import parser** — I have a large ChatGPT export to feed it

**Environment:**
- Python 3.14: `C:\Users\damar\AppData\Local\Programs\Python\Python314\python.exe`
- PostgreSQL 18: localhost:5432, db=omura, user=omura, pass=omura (superuser: postgres/Damarpow187699)
- Backend port: 8001, Frontend port: 3001
- Claude API key is in `backend/.env`
- Privacy first: AI never accesses internet without my approval

**Start backend:** `"/c/Users/damar/AppData/Local/Programs/Python/Python314/python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload`
**Start frontend:** `cd frontend && npx next dev -p 3001`

---
