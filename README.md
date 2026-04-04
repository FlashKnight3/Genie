# Genie — Autonomous Subcontractor Manager

Multi-agent AI system that manages subcontractors end-to-end, acting as an autonomous project manager.

## Agents

| Agent | Role |
|-------|------|
| **Project Manager** | Orchestrator — breaks down jobs, delegates to specialists, tracks progress |
| **Matching** | Finds and scores subcontractors based on skills, availability, rating, budget |
| **Communication** | Drafts and sends messages to subcontractors (email/SMS/Slack) |
| **Risk** | Assesses weather, reliability, schedule conflicts; scores and logs risks |
| **Rescheduling** | Recovers disrupted jobs — finds new slots or backup subcontractors |

Each agent is powered by `claude-sonnet-4-6` with tool_use (function calling) and has a focused system prompt and curated tool set.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run the end-to-end demo
python demo.py

# 4. Start the API server (also serves the web UI)
python3 -m uvicorn main:app --reload
```

## Frontend

There is no separate frontend dev server. Static assets under `frontend/` are mounted by FastAPI at `/app`.

With Uvicorn running on the default host and port:

- **Web UI:** [http://localhost:8000/app/](http://localhost:8000/app/)
- **API docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

The browser client uses `http://localhost:8000` as the API base URL (`frontend/js/api.js`). If you run the API on another host or port, update the `BASE` constant there (or add a small config) so requests still reach the backend.

## API

Once running, visit `http://localhost:8000/docs` for the interactive Swagger UI.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs` | Create a new job |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Job detail + subcontractor |
| `POST` | `/orchestrate` | Trigger PM Agent on a job |
| `GET` | `/orchestrate/logs` | Agent activity log |
| `GET` | `/orchestrate/risks` | All risk records |
| `GET` | `/subcontractors` | List subcontractors (filterable) |
| `GET` | `/schedule` | Full schedule view |

## Architecture

```
POST /orchestrate
       │
       ▼
 ProjectManagerAgent
       │
       ├── delegate_to_agent("matching") ──► MatchingAgent
       │                                         └── search_subcontractors
       │                                         └── assign_subcontractor
       │
       ├── delegate_to_agent("communication") ──► CommunicationAgent
       │                                              └── send_message
       │
       ├── delegate_to_agent("risk") ──► RiskAgent
       │                                    └── calculate_risk_score
       │                                    └── create_risk_record
       │
       └── delegate_to_agent("rescheduling") ──► ReschedulingAgent
                                                     └── find_available_slots
                                                     └── update_schedule
```

## Tech Stack

- Python 3.11+ / asyncio
- Anthropic SDK (`claude-sonnet-4-6`)
- FastAPI + Uvicorn
- SQLAlchemy (async) + SQLite + aiosqlite
- Pydantic v2
- Frontend: vanilla ES modules + Tailwind (CDN), served as static files
