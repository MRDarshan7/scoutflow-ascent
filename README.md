# ScoutFlow

**Autonomous Market Intelligence & Monitoring System**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-1F2937?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-Enhanced%20Reasoning-4285F4?style=flat-square&logo=google&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Persistence-003B57?style=flat-square&logo=sqlite&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-Automation-334155?style=flat-square)
![Hackathon](https://img.shields.io/badge/Hackathon-Project-7C3AED?style=flat-square)

ScoutFlow turns a natural-language monitoring goal into a long-running intelligence workflow. It plans what to track, researches live sources, validates noisy findings, generates contextual insights, and keeps monitoring for meaningful signal changes.

The system is built as a multi-agent backend with FastAPI, LangGraph, Gemini-enhanced reasoning, SQLite persistence, APScheduler automation, alert generation, and webhook delivery.

## Problem Statement

Modern teams operate in an environment of constant information overload. Funding announcements, product launches, competitor movement, engineering activity, hiring patterns, and market shifts are scattered across news feeds, GitHub, websites, and public updates.

Manual monitoring is slow and easy to miss. Analysts and founders often need to repeatedly ask:

- Which startups are gaining momentum?
- Which competitors are launching or hiring?
- Which market signals changed recently?
- Which updates are credible enough to act on?
- What should we monitor next?

ScoutFlow solves this by converting a plain-English goal into an autonomous research and monitoring loop. Instead of being a one-time search tool, it keeps track of saved goals, reruns research over time, compares new signals against previous snapshots, and raises alerts when something changes.

## Key Features

| Feature | What ScoutFlow Does |
| --- | --- |
| Multi-Agent Intelligence | Splits work across Planner, Research, Validation, and Insight agents instead of relying on one broad prompt. |
| Autonomous Monitoring | Saved goals can be monitored continuously with APScheduler jobs. |
| Long-Running Execution | Monitoring jobs rerun the workflow over time and persist snapshots for comparison. |
| Contextual Signal Detection | Extracts signals such as funding growth, hiring expansion, product movement, engineering momentum, and market consolidation. |
| Gemini-Enhanced Insights | Uses Gemini reasoning when configured, with deterministic fallback behavior when unavailable. |
| Real-Time Alerts | Generates alerts when monitoring detects new or removed signals. |
| Webhooks | Sends alert payloads to generic webhook URLs or Discord webhooks. |
| Live Web Research | Uses Google News RSS, RSS feeds, GitHub API, and scraper tooling. |
| LangGraph Orchestration | Runs the agent pipeline as a LangGraph workflow. |
| Grounded Recommendations | Produces recommendations and recommended actions from validated findings. |
| Fallback Logic | The backend still works when Gemini is unavailable or quota-limited. |
| SQLite Persistence | Stores goals, alerts, feedback, reports metadata, events, webhooks, and monitoring snapshots locally. |

## Architecture Overview

```text
User Goal
   |
   v
PlannerAgent
   |
   v
ResearchAgent
   |
   v
ValidationAgent
   |
   v
InsightAgent
   |
   v
Gemini Enhancement
   |
   v
Monitoring Snapshots
   |
   v
Alert Generation
   |
   v
Webhook Notifications
```

### PlannerAgent

**Input:** user query and optional preferences.

**Responsibility:** converts the goal into a structured research plan with targets, sources, monitoring focus, source priority, and research queries.

**Output:** a plan used by the research workflow.

### ResearchAgent

**Input:** structured plan.

**Responsibility:** collects raw findings from Google News RSS, general RSS feeds, and GitHub repository search. It filters noisy candidates before passing them forward.

**Output:** research findings with source metadata.

### ValidationAgent

**Input:** raw research findings.

**Responsibility:** deduplicates findings, scores source credibility, filters low-quality results, and keeps the strongest validated findings.

**Output:** validated findings with confidence metadata.

### InsightAgent

**Input:** validated findings.

**Responsibility:** detects business signals, generates implications, recommendations, and recommended actions. Gemini can refine the output when configured.

**Output:** final intelligence brief used by `/insights` and monitoring snapshots.

## Multi-Agent Workflow

ScoutFlow is not a single LLM retry loop. Each agent has a narrow responsibility and hands structured output to the next step.

The workflow is orchestrated with LangGraph:

- PlannerAgent decides what should be tracked.
- ResearchAgent calls external tools and gathers candidate evidence.
- ValidationAgent removes duplicates and low-confidence items.
- InsightAgent reasons over validated findings and creates recommendations.
- Monitoring jobs rerun the graph for saved goals.
- Alerts are generated when signal state changes between snapshots.
- Webhooks deliver real side effects outside the API.

This specialization makes the system easier to debug, safer to extend, and better aligned with autonomous-agent hackathon requirements.

## Tooling & Integrations

### Research Sources

- Google News RSS
- RSS feeds
- GitHub public API
- Web scraping utilities

### Infrastructure

- FastAPI for the backend API
- SQLite for local persistence
- APScheduler for recurring autonomous jobs
- LangGraph for workflow orchestration

### AI

- Gemini 2.5 Flash is used for optional insight refinement when `GEMINI_API_KEY` is configured.
- Deterministic fallback logic keeps the pipeline usable without Gemini.

ScoutFlow intentionally uses a lightweight stack: no queues, no external database, and no complex deployment requirements. That keeps the hackathon demo easy to run while still showing real autonomy.

## Workflow Example

Example goal:

```text
Track AI startups in India
```

ScoutFlow processes it like this:

| Step | What Happens |
| --- | --- |
| Goal Creation | The goal is saved in SQLite with preferences such as funding, hiring, and GitHub. |
| Planning | PlannerAgent selects relevant targets, sources, and research queries. |
| Research | ResearchAgent searches Google News RSS, RSS feeds, and GitHub. |
| Validation | ValidationAgent deduplicates and filters low-confidence results. |
| Insight Generation | InsightAgent detects signals and creates recommendations. |
| Monitoring | APScheduler reruns the workflow for the saved goal. |
| Alert Generation | New or removed signals are compared against the previous snapshot. |
| Webhook Notification | Discord or generic webhooks receive alert payloads. |

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check API and database health. |
| `POST` | `/goal` | Create a monitoring goal. |
| `GET` | `/goals` | List saved goals. |
| `POST` | `/plan` | Run only the planning step. |
| `POST` | `/research` | Run planning and research. |
| `POST` | `/validate` | Run planning, research, and validation. |
| `POST` | `/insights` | Run the full LangGraph intelligence workflow. |
| `POST` | `/monitor/start/{goal_id}` | Start recurring monitoring for a saved goal. |
| `POST` | `/monitor/stop/{goal_id}` | Stop monitoring for a goal. |
| `GET` | `/monitor/active` | View active monitoring jobs. |
| `GET` | `/alerts` | List generated alerts. |
| `GET` | `/alerts/{goal_id}` | List alerts for a specific goal. |
| `POST` | `/webhook/register` | Register a generic or Discord webhook. |
| `GET` | `/webhook/{goal_id}` | List webhooks for a goal. |
| `POST` | `/webhook/toggle/{webhook_id}` | Enable or disable a webhook. |

## Autonomous Monitoring

ScoutFlow supports long-running autonomous monitoring through APScheduler.

When monitoring starts for a goal:

1. The scheduler runs the LangGraph workflow immediately.
2. The generated insights are saved as a monitoring snapshot.
3. Later runs compare the latest signals against the previous snapshot.
4. Added or removed signals become alerts.
5. Alerts can be delivered through registered webhooks.

This turns ScoutFlow from a one-time research API into a lightweight autonomous monitoring system.

## Hackathon Requirement Mapping

| Requirement | How ScoutFlow Satisfies It |
| --- | --- |
| Multi-Agent | PlannerAgent, ResearchAgent, ValidationAgent, and InsightAgent have separate responsibilities. |
| Autonomy | Saved goals can be monitored continuously without repeated user prompts. |
| Long-Running | APScheduler reruns monitoring jobs over time and stores snapshots. |
| Deep Reasoning | InsightAgent and Gemini enhancement generate implications, recommendations, and actions from validated evidence. |
| Tool Calling | ResearchAgent uses RSS, Google News, GitHub, and scraper tools. |
| Web Search | Google News RSS and RSS ingestion provide live web research. |
| Webhooks | Alerts can be sent to Discord or generic webhook endpoints. |
| Async Orchestration | LangGraph coordinates the agent workflow; APScheduler coordinates recurring execution. |
| Real Side Effects | SQLite persistence, alert creation, monitoring jobs, and webhook delivery create observable system effects. |

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend | FastAPI |
| Language | Python |
| Orchestration | LangGraph |
| LLM Enhancement | Gemini 2.5 Flash |
| Database | SQLite |
| Scheduler | APScheduler |
| Research Tools | Google News RSS, RSS feeds, GitHub API, web scraping |
| Notifications | Generic webhooks, Discord webhooks |
| Testing | pytest, FastAPI TestClient |

## Project Structure

```text
scoutflow/
  agents/
    planner.py
    researcher.py
    validator.py
    insight.py
  backend/
    main.py
    database.py
    config.py
    webhook_routes.py
  models/
    webhook_models.py
  scheduler/
    monitor.py
  storage/
    webhook_store.py
    scoutflow.db
  tests/
    test_webhooks.py
  tools/
    rss_reader.py
    github_monitor.py
    scraper.py
    gemini_helper.py
    webhook_sender.py
  workflow/
    graph.py
    state.py
  tracing/
    omium.py
  requirements.txt
  run.py
```

| Folder | Purpose |
| --- | --- |
| `agents/` | Multi-agent intelligence modules. |
| `backend/` | FastAPI app, routes, configuration, and database logic. |
| `models/` | Pydantic request/response models. |
| `scheduler/` | APScheduler monitoring jobs and signal diffing. |
| `storage/` | Local persistence helpers and SQLite database files. |
| `tests/` | Automated API, webhook, and monitoring tests. |
| `tools/` | Research, Gemini, scraping, and webhook delivery utilities. |
| `workflow/` | LangGraph state and workflow orchestration. |
| `tracing/` | Placeholder for future observability integration. |

## Setup & Installation

### 1. Clone the Repository

```powershell
git clone <repository-url>
cd scoutflow
```

### 2. Create a Virtual Environment

```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment

Windows:

```powershell
venv\Scripts\activate
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file:

```env
APP_ENV=development
LOG_LEVEL=INFO
GEMINI_API_KEY=your_gemini_api_key_here
```

`GEMINI_API_KEY` is recommended for enhanced reasoning. If it is missing, ScoutFlow still runs with deterministic fallback logic.

### 6. Run the Backend

```powershell
python run.py
```

The backend runs locally at:

```text
http://127.0.0.1:8000
```

Swagger UI is available at:

```text
http://127.0.0.1:8000/docs
```

## Using ScoutFlow

ScoutFlow can be used entirely through Swagger UI. No frontend is required.

Open:

```text
http://127.0.0.1:8000/docs
```

### Step 1 — Start Backend

Create a virtual environment:

```powershell
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the backend:

```powershell
python run.py
```

Expected result:

- Backend runs locally.
- Swagger UI is available at `http://127.0.0.1:8000/docs`.

### Step 2 — Health Check

Use:

```text
GET /health
```

Expected result:

- API status is healthy.
- SQLite database connection is working.

### Step 3 — Create a Goal

Use:

```text
POST /goal
```

Example body:

```json
{
  "query": "Track AI startups in India",
  "preferences": [
    "funding",
    "hiring",
    "github"
  ]
}
```

This defines what ScoutFlow should monitor and stores the goal in SQLite.

### Step 4 — View Saved Goals

Use:

```text
GET /goals
```

This returns all saved monitoring goals. Note the `id` value for the goal you created; that `goal_id` is used for monitoring and webhook setup.

### Step 5 — Generate Insights

Use:

```text
POST /insights
```

Example body:

```json
{
  "query": "Track AI startups in India"
}
```

This runs the full multi-agent pipeline:

- planning
- research
- validation
- insight generation
- Gemini enhancement when configured

The output can include:

- summary
- detected signals
- business implications
- recommendations
- recommended actions
- supporting findings

### Step 6 — Register Webhook

Use:

```text
POST /webhook/register
```

ScoutFlow supports:

- Discord webhooks
- generic webhook URLs

Example body:

```json
{
  "goal_id": 1,
  "type": "discord",
  "url": "YOUR_DISCORD_WEBHOOK_URL"
}
```

When important monitoring updates are detected, ScoutFlow can notify the registered webhook.

### Step 7 — Start Monitoring

Use:

```text
POST /monitor/start/{goal_id}
```

Example body:

```json
{
  "interval_minutes": 0.2
}
```

ScoutFlow will continuously rerun research for that saved goal. `0.2` minutes is approximately 12 seconds, which is useful for a short demo.

### Step 8 — Monitor Active Jobs

Use:

```text
GET /monitor/active
```

This shows currently running autonomous monitoring tasks.

### Step 9 — View Alerts

Use:

```text
GET /alerts
```

This returns generated monitoring alerts, including signal changes detected across monitoring snapshots.

## Recommended Demo Flow

For a clean judge demo, use Swagger UI in this order:

1. `POST /goal`
2. `GET /goals`
3. `POST /insights`
4. `POST /webhook/register`
5. `POST /monitor/start/{goal_id}`
6. `GET /monitor/active`
7. Wait for the scheduler to run and detect a change.
8. `GET /alerts`

This demonstrates the complete autonomous workflow: goal creation, multi-agent intelligence generation, webhook setup, long-running monitoring, and alert retrieval.

## Current Limitations

- Frontend dashboard is not implemented yet.
- Omium tracing is not implemented yet.
- Feedback learning is planned but not currently wired into the active ranking loop.
- The scheduler runs in-process with FastAPI, which is appropriate for the hackathon demo but not a distributed production deployment.
- Research quality depends on public source availability, API limits, and Gemini quota when enhancement is enabled.

## Future Roadmap

- Frontend dashboard for goals, insights, alerts, monitoring, and webhooks.
- Observability and trace visualization.
- Stronger feedback learning loop.
- More integrations such as Slack, email, and additional market data sources.
- Richer trend memory across longer monitoring windows.

## Team / Credits

ScoutFlow was built as a hackathon project focused on autonomous agents, tool calling, long-running workflows, and real-world monitoring side effects.
