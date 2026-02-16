# Kitchen Pilot — Agentic Weekly Planner + Nutrition Coach

A multi-agent personal assistant that generates a weekly cooking plan tailored to household preferences/allergies/goals, computes nutrition, produces a grocery list, and publishes cooking events to Google Calendar. Includes chat + push-to-talk voice.

## Key Features

- **Chat UI** for planning and edits ("swap Wednesday to vegetarian")
- **Household context DB**: preferences, allergies, diet goals (optional vitals)
- **RAG** over Google Drive recipe docs + notes (pgvector)
- **Nutrition Coach**: macros + daily totals + suggestions (with confidence)
- **Grocery exporter**: normalized list + CSV + retailer deep-links (Amazon/Instacart/Walmart)
- **Google Calendar publish** (via MCP where mature)
- **Low/no-cost LLM**: Ollama local models + LiteLLM routing/logging

## Architecture

- **Web**: Next.js (chat, plan view, household profile, grocery exports, voice)
- **API**: FastAPI (agents, tools, publishing, ingestion)
- **DB**: Postgres + pgvector
- **LLM**: Ollama + LiteLLM + instructor (structured output validation)
- **Selective MCP**:
  - Google Calendar MCP
  - Google Drive MCP
  - Search MCP (Brave/Tavily)
  - Native tools for nutrition/grocery/voice

## Repo Structure

```
apps/
  web/              # Next.js UI
  api/              # FastAPI backend (agents, tools, routes)
docs/
  spec.md           # Full specification
docker-compose.yml
litellm_config.yaml
```

## Prerequisites

- Docker + Docker Compose
- (Optional) Node 20+ and Python 3.12+ for local dev outside containers
- (Optional) uv (Python) and pnpm (Node) for local dev

## Quick Start (Docker)

1. Copy env template:
   ```bash
   cp .env.example .env
   ```

2. Start services:
   ```bash
   docker compose up --build
   ```

3. Pull an Ollama model (first time only):
   ```bash
   docker compose exec ollama ollama pull qwen3:8b
   ```

4. Open:
   - Web UI: http://localhost:3000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Environment Variables

See `.env.example` for all variables with documentation.

### Core
- `DATABASE_URL` — Postgres connection string
- `LITELLM_BASE_URL` — LiteLLM proxy URL
- `OLLAMA_BASE_URL` — Ollama API URL

### Google / MCP
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URL`

### Nutrition
- `USDA_API_KEY`

### Search (optional)
- `BRAVE_API_KEY` or `TAVILY_API_KEY`

### Security
- `FERNET_KEY` — encryption key for OAuth tokens at rest

## Development (Local)

### API
```bash
cd apps/api
uv sync
uv run uvicorn kitchen_pilot.main:app --reload --port 8000
```

### Web
```bash
cd apps/web
pnpm install
pnpm dev
```

### Tests
```bash
cd apps/api
uv run pytest
```

### Lint
```bash
cd apps/api
uv run ruff check src/
```

## Safety / Guardrails

- Allergy violations are hard blocks unless user explicitly overrides.
- Nutrition values are estimates; each includes a `confidence` field and `source`.
- Publishing actions (calendar/drive) require explicit confirmation.
- OAuth tokens are Fernet-encrypted at rest.

## Roadmap

- **M0**: Foundation (compose + LLM + basic chat) — current
- **M1**: Household profile + DB
- **M2**: Plan schema + calendar publish (MCP)
- **M3**: Drive RAG ingestion (MCP)
- **M4**: Nutrition coach + caching
- **M5**: Grocery exporter + retailer deep-links
- **M6**: Voice push-to-talk (STT/TTS)
- **M7**: Optional cart automation / cloud deployment

## Contributing

- Keep tool interfaces stable (Pydantic models)
- Add/replace MCP servers behind the tool router without changing agent logic
- Include tests for any new tool or planner behavior
