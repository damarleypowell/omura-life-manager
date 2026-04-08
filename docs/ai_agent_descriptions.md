# Omura AI Agent Descriptions

## Agent Architecture

All agents share a common pattern:
- Accept a database session for data access
- Log all actions for accountability
- Use a pluggable `_call_ai()` method for LLM integration (Claude/OpenAI/Ollama)
- Return structured outputs for dashboard display

---

## 1. Inbox AI (`inbox_ai.py`)
**Role:** Email and DM triage across all platforms.

| Method | Input | Output |
|--------|-------|--------|
| `triage_messages` | List of messages | Categorized messages with urgency levels |
| `summarize_message` | Single message | Concise summary |
| `suggest_response` | Single message | Draft reply |
| `flag_urgent` | List of messages | Flagged urgent items |
| `process_inbox` | None (fetches from DB) | Full triage results |

---

## 2. Content AI (`content_ai.py`)
**Role:** Content creation, editing, scheduling, and performance analysis.

| Method | Input | Output |
|--------|-------|--------|
| `generate_draft` | Topic, platform | Draft with caption + hashtags |
| `edit_content` | Content, instructions | Refined content |
| `generate_hashtags` | Content text, platform | Relevant hashtag list |
| `schedule_post` | Content ID, datetime | Scheduling confirmation |
| `analyze_performance` | Content ID | Engagement analysis |
| `suggest_content_ideas` | Recent trends | List of content ideas |

---

## 3. Project AI (`project_ai.py`)
**Role:** Project pipeline management and task prioritization.

| Method | Input | Output |
|--------|-------|--------|
| `analyze_pipeline` | None | Pipeline overview |
| `predict_bottlenecks` | Project ID | List of predicted blockers |
| `suggest_task_priority` | Task list | AI-prioritized list |
| `generate_daily_agenda` | None | Prioritized daily agenda |
| `estimate_completion` | Project ID | Completion prediction |

---

## 4. CRM AI (`crm_ai.py`)
**Role:** Lead management, scoring, and automated outreach.

| Method | Input | Output |
|--------|-------|--------|
| `score_lead` | Lead data | Score 0-100 |
| `suggest_followup` | Lead data | Follow-up action + message |
| `analyze_pipeline` | None | CRM pipeline metrics |
| `automate_outreach` | Lead list | Personalized messages |
| `classify_lead_source` | Communication | Source + intent |

---

## 5. Finance AI (`finance_ai.py`)
**Role:** Revenue tracking, KPI generation, anomaly detection.

| Method | Input | Output |
|--------|-------|--------|
| `calculate_kpis` | Period (days) | Revenue, expenses, margins |
| `detect_anomalies` | Metric list | Flagged anomalies |
| `generate_report` | Period (days) | Full financial summary |
| `suggest_optimizations` | None | Cost/revenue suggestions |
| `forecast_revenue` | Months ahead | Revenue projection |

---

## 6. Health AI (`health_ai.py`)
**Role:** Health data analysis and daily recommendations.

| Method | Input | Output |
|--------|-------|--------|
| `analyze_sleep` | Sleep entries | Sleep quality analysis |
| `analyze_workouts` | Workout entries | Workout analysis |
| `review_supplements` | Supplement entries | Stack review |
| `generate_daily_recommendation` | None | Daily health plan |
| `calculate_energy_score` | Health data | Score 0-100 |

---

## 7. Market AI (`market_ai.py`)
**Role:** Competitive intelligence and market analysis.

| Method | Input | Output |
|--------|-------|--------|
| `monitor_competitors` | Competitor list | Activity tracking |
| `identify_trends` | Industry | Emerging trends |
| `find_opportunities` | Market data | Business opportunities |
| `analyze_audience` | Platform | Demographics + behavior |
| `generate_market_report` | None | Full market summary |

---

## 8. Scenario AI (`scenario_ai.py`)
**Role:** What-if simulations for all life/business domains.

| Method | Input | Output |
|--------|-------|--------|
| `simulate_business` | Parameters | Business projections |
| `simulate_finance` | Parameters | Financial projections |
| `simulate_content` | Parameters | Content strategy projections |
| `simulate_life` | Parameters | Life optimization projections |
| `compare_scenarios` | Scenario IDs | Side-by-side comparison |
| `get_recommendation` | Results | AI recommendation |

---

## 9. Automation AI (`automation_ai.py`)
**Role:** Execute repetitive tasks and orchestrate workflows.

| Method | Input | Output |
|--------|-------|--------|
| `execute_email_task` | Task data | Execution result |
| `execute_posting_task` | Task data | Execution result |
| `execute_followup_task` | Task data | Execution result |
| `run_workflow` | Workflow name, params | Workflow result |

### Built-in Workflows:
1. **Lead Management:** Email → Triage → Score → Follow-up → Dashboard
2. **Content Publishing:** Idea → Draft → Schedule → Predict → Metrics
3. **Health Optimization:** Data → Analyze → Adjust → Energy Score
4. **Business Metrics:** Revenue → KPIs → Alerts → Optimizations
