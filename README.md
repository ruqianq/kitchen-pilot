# Kitchen Pilot — Agentic Weekly Planner + Nutrition Coach

A multi-agent personal assistant that generates weekly cooking plans tailored to household preferences, allergies, and nutrition goals. Computes macros, produces grocery lists, publishes cooking events to Google Calendar, and includes a chat interface with push-to-talk voice.

## Key Features

- **Chat UI** with SSE streaming — conversational planning and edits ("swap Wednesday to vegetarian")
- **Intent detection** — automatic routing to web search, plan preview, or nutrition coaching based on message content
- **Household context DB** — preferences, allergies, dietary rules, nutrition goals, biometrics, health conditions
- **Multi-agent architecture** — ContextAgent, PlanAgent, NutritionCoachAgent with typed I/O and shared context
- **RAG** over Google Drive recipe docs and notes (pgvector embeddings)
- **Nutrition Coach** — deterministic per-person recommendations based on age, gender, activity level, health conditions; includes macro splits, micronutrient limits, and dietary guidelines
- **7-day meal plan generator** — structured LLM output with allergy compliance checks, per-meal nutrition, and shopping lists
- **Grocery exporter** — normalized item list, persistent checklist, CSV export, retailer deep-links (Amazon/Instacart/Walmart)
- **Google Calendar publish** via OAuth 2.0
- **Voice** — push-to-talk with Whisper STT and OpenAI TTS
- **Web search** — recipe discovery via Brave or Tavily APIs
- **LLM routing** — GPT-4o-mini (primary) with Ollama local fallbacks via LiteLLM proxy

## Architecture

```
┌────────────┐       ┌──────────────┐       ┌──────────────────┐
│  Next.js   │──────▶│  FastAPI      │──────▶│  PostgreSQL      │
│  (port 3000)│  REST │  (port 8000)  │  async│  + pgvector      │
│             │◀──SSE─│               │       │  (port 5432)     │
└────────────┘       │  ┌──────────┐ │       └──────────────────┘
                     │  │ Agents   │ │
                     │  │ ├ Context│ │       ┌──────────────────┐
                     │  │ ├ Plan   │ │──────▶│  LiteLLM Proxy   │
                     │  │ └ Coach  │ │       │  (port 4000)     │
                     │  └──────────┘ │       │  ├ GPT-4o-mini   │
                     └──────────────┘       │  └ Ollama models  │
                                            └──────┬───────────┘
                                                   │
                                            ┌──────▼───────────┐
                                            │  Ollama          │
                                            │  (port 11434)    │
                                            │  qwen3:8b        │
                                            │  gemma3, llama3.1│
                                            └──────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, TypeScript |
| **Backend** | FastAPI, Python 3.12+, SQLAlchemy 2 (async), Pydantic |
| **Database** | PostgreSQL 16 + pgvector (1536-dim embeddings) |
| **LLM Routing** | LiteLLM proxy → GPT-4o-mini / Ollama local models |
| **Structured Output** | instructor (Pydantic model validation for LLM responses) |
| **Voice** | OpenAI Whisper STT, OpenAI TTS (nova voice) |
| **Search** | Brave Search API or Tavily API |
| **Calendar** | Google Calendar API via OAuth 2.0 |
| **Infrastructure** | Docker Compose (5 services) |

## Repo Structure

```
apps/
  api/
    src/kitchen_pilot/
      agents/           # Multi-agent framework
        base.py         #   BaseAgent protocol, AgentContext, AgentResult
        context_agent.py#   Loads household context (people, allergies, rules, goals)
        plan_agent.py   #   7-day meal plan generation
        nutrition_coach.py # Per-person nutrition recommendations
        registry.py     #   Agent registry
      routers/          # FastAPI route handlers
        auth.py         #   Google OAuth flow + token management
        chat.py         #   SSE streaming chat with intent detection
        health.py       #   Health check endpoint
        household.py    #   Household CRUD (people, allergies, rules, preferences, goals)
        nutrition.py    #   USDA nutrition lookup + caching
        plans.py        #   Plan CRUD + generation + shopping list + CSV export
        rag.py          #   Document ingestion + semantic search
        search.py       #   Web recipe search (Brave/Tavily)
        voice.py        #   Whisper STT + TTS endpoints
      services/         # Business logic layer
        llm.py          #   LiteLLM client, structured generation, SSE streaming
        household.py    #   Household context assembly
        plan.py         #   Plan generation with allergy compliance
        nutrition.py    #   USDA API integration + nutrition caching
        nutrition_coach.py # Deterministic calorie/macro calculations
        calendar_service.py # Google Calendar event publishing
        drive_service.py#   Google Drive document fetching
        embedding_service.py # pgvector embedding generation
        rag_service.py  #   RAG: chunk, embed, semantic search
        grocery_export.py #  Grocery list normalization + CSV
        token_service.py#   Fernet-encrypted OAuth token storage
        voice.py        #   Whisper transcription + TTS audio
        web_search.py   #   Brave/Tavily search abstraction
      db/
        engine.py       #   Async SQLAlchemy engine + session factory
        models.py       #   14 SQLAlchemy ORM models (see Database Schema)
      schemas/          #   Pydantic request/response models
      config.py         #   Settings from environment variables
      main.py           #   FastAPI app factory + CORS + router registration
  web/
    src/
      app/              # Next.js App Router pages
        page.tsx        #   Home / landing
        chat/page.tsx   #   Chat interface with SSE + suggestion chips
        onboarding/     #   4-step onboarding wizard
        plans/          #   Plan listing + detail with meal-type colors
        profile/        #   Household profile management
      components/       # Shared UI components
        Button.tsx, Input.tsx, Select.tsx, NavBar.tsx,
        PersonCard.tsx, StepIndicator.tsx, AllergyTag.tsx
      lib/
        api.ts          #   API client + TypeScript types
docs/
  spec.md               # Full specification
docker-compose.yml
litellm_config.yaml     # LLM model routing configuration
```

## Database Schema

14 SQLAlchemy ORM models backed by PostgreSQL + pgvector:

| Table | Description |
|-------|-----------|
| `household` | Top-level family unit (name, timezone) |
| `person` | Household member (name, role, age_band, gender, DOB, activity_level) |
| `allergy` | Per-person allergen with severity (mild/moderate/severe) |
| `dietary_rule` | Scoped to household or person (e.g., "vegetarian", "no pork") |
| `food_preference` | Like/dislike/avoid/favorite per item, scoped to household or person |
| `nutrition_goal` | Calorie ranges + macro targets (protein, carbs, fat, fiber, sodium, etc.) |
| `biometric` | Height, weight, BMI, waist measurements |
| `health_condition` | Medical conditions with severity and notes |
| `weekly_plan` | 7-day plan with status (draft→confirmed→published→archived), JSONB plan data |
| `meal` | Individual meal within a plan (title, type, ingredients, nutrition as JSONB) |
| `shopping_list` | Aggregated grocery list per plan (items + export history as JSONB) |
| `nutrition_cache` | Cached USDA lookups keyed by normalized food name |
| `audit_log` | Action log for publishing and sensitive operations |
| `oauth_tokens` | Fernet-encrypted Google OAuth tokens with scopes and expiry |
| `memory_documents` | RAG document store with 1536-dim pgvector embeddings |

Key constraints: `dietary_rule`, `food_preference`, and `nutrition_goal` use CHECK constraints to require either `household_id` or `person_id` (scoped rules).

## Multi-Agent System

All agents extend `BaseAgent[TInput, TOutput]` with typed Pydantic models and a shared `AgentContext` (household ID, async session, correlation ID).

### ContextAgent
Loads full household context from the database — people, allergies, dietary rules, food preferences, nutrition goals, biometrics, and health conditions. Used by both the chat router and other agents.

### PlanAgent
Generates a 7-day meal plan via structured LLM output. Accepts constraint overrides, max cook time, and free-text notes. Returns plan ID, markdown summary, and allergy compliance warnings.

### NutritionCoachAgent
Hybrid deterministic + LLM approach:
- **Tier 1 (always)**: Deterministic calorie/macro calculations based on Mifflin-St Jeor equations, adjusted for age, gender, activity level, and health conditions (diabetes, hypertension, heart disease, etc.)
- **Tier 2 (chat only)**: Natural-language summary for conversational responses

Outputs per-person: daily calories, macro split (protein/carbs/fat/fiber), micronutrient limits (sodium, sugar), dietary guidelines, foods to emphasize/limit, and warnings.

### Chat Intent Detection
The chat router uses regex-based intent detection to route messages:
- **Search intent** → triggers web recipe search (Brave/Tavily) and injects results into context
- **Plan intent** → generates a single-day meal preview via structured LLM output
- **Nutrition intent** → invokes NutritionCoachAgent for personalized health advice

All responses stream via SSE (Server-Sent Events).

## Prerequisites

- Docker + Docker Compose
- (Optional) Node 20+ and Python 3.12+ for local dev outside containers
- (Optional) `uv` (Python) and `pnpm` (Node) for local dev

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
   - LiteLLM proxy: http://localhost:4000

## Docker Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | Database with vector extension |
| `ollama` | `ollama/ollama` | 11434 | Local LLM inference |
| `litellm` | `ghcr.io/berriai/litellm:main-latest` | 4000 | LLM routing proxy (OpenAI + Ollama) |
| `api` | Custom Dockerfile | 8000 | FastAPI backend |
| `web` | Custom Dockerfile | 3000 | Next.js frontend |

## Environment Variables

See `.env.example` for all variables with documentation.

### Core
| Variable | Description | Required |
|----------|-----------|----------|
| `DATABASE_URL` | Postgres connection string | Yes (default provided in Docker) |
| `LITELLM_BASE_URL` | LiteLLM proxy URL | Yes (default: `http://localhost:4000`) |
| `OLLAMA_BASE_URL` | Ollama API URL | Yes (default: `http://localhost:11434`) |
| `DEFAULT_MODEL` | Primary LLM model | No (default: `gpt-4o-mini`) |
| `FALLBACK_MODELS` | Fallback model list (JSON array) | No (default: qwen3:8b, gemma3) |

### API Keys
| Variable | Description | Required |
|----------|-----------|----------|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o-mini, Whisper, TTS) | For cloud LLM + voice |
| `USDA_API_KEY` | USDA FoodData Central API key | For nutrition lookups |
| `BRAVE_API_KEY` | Brave Search API key | For web search (pick one) |
| `TAVILY_API_KEY` | Tavily Search API key | For web search (pick one) |

### Google OAuth
| Variable | Description | Required |
|----------|-----------|----------|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID | For Calendar integration |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret | For Calendar integration |
| `GOOGLE_OAUTH_REDIRECT_URL` | OAuth callback URL | No (default: `http://localhost:8000/auth/google/callback`) |

### Security
| Variable | Description | Required |
|----------|-----------|----------|
| `FERNET_KEY` | Encryption key for OAuth tokens at rest | For Calendar integration |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | No (default: `["http://localhost:3000"]`) |

## API Endpoints

### Health
- `GET /health` — health check

### Chat
- `POST /chat` — SSE streaming chat with intent detection (search, plan, nutrition)

### Household
- `GET /household` — get household
- `PUT /household/{id}` — update household
- `POST /household/people` — add person
- `DELETE /household/people/{id}` — remove person
- `GET /household/allergies` — list allergies
- `POST /household/allergies` — add allergy
- `DELETE /household/allergies/{id}` — remove allergy
- `GET /household/dietary-rules` — list dietary rules
- `POST /household/dietary-rules` — add rule
- `DELETE /household/dietary-rules/{id}` — remove rule
- `GET /household/preferences` — list food preferences
- `POST /household/preferences` — add preference
- `DELETE /household/preferences/{id}` — remove preference
- `GET /household/goals` — list nutrition goals
- `POST /household/goals` — add goal
- `DELETE /household/goals/{id}` — remove goal
- `GET /household/biometrics` — list biometrics
- `POST /household/biometrics` — add biometric
- `PUT /household/biometrics/{id}` — update biometric
- `GET /household/health-conditions` — list health conditions
- `POST /household/health-conditions` — add condition
- `DELETE /household/health-conditions/{id}` — remove condition

### Plans
- `GET /plans` — list plans
- `POST /plans/generate` — generate 7-day meal plan
- `GET /plans/{id}` — get plan detail with meals
- `PUT /plans/{id}/status` — update plan status
- `GET /plans/{id}/shopping-list` — get shopping list
- `GET /plans/{id}/shopping-list/csv` — export as CSV

### Nutrition
- `POST /nutrition/lookup` — USDA nutrition lookup (cached)

### Auth
- `GET /auth/google/login` — initiate OAuth flow
- `GET /auth/google/callback` — OAuth callback
- `GET /auth/google/status` — check connection status

### RAG
- `POST /rag/ingest` — ingest and embed a document
- `POST /rag/search` — semantic similarity search

### Voice
- `POST /voice/transcribe` — Whisper STT (audio → text)
- `POST /voice/synthesize` — TTS (text → audio)

### Search
- `POST /search/recipes` — web recipe search via Brave or Tavily

## LLM Configuration

LiteLLM acts as a unified proxy for all LLM calls:

```yaml
# litellm_config.yaml
model_list:
  - model_name: "gpt-4o-mini"          # Primary (cloud)
  - model_name: "ollama_chat/qwen3:8b"  # Fallback 1 (local)
  - model_name: "ollama_chat/gemma3:latest" # Fallback 2 (local)
  - model_name: "ollama_chat/llama3.1:8b"  # Additional local option

general_settings:
  drop_params: true  # Gracefully handle unsupported params
```

The API uses `instructor` for structured LLM output — responses are validated against Pydantic models with automatic retries.

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

## UI Design

The frontend uses a warm, food-inspired design system:

- **Primary (Terracotta)**: `#c2410c` — buttons, active nav, CTAs
- **Secondary (Sage Green)**: `#4d7c0f` — success states, nutrition, health indicators
- **Accent (Warm Gold)**: `#b45309` — highlights, badges, hover accents
- **Background**: warm peach-cream (`#fef7ee` light / `#292220` dark)
- Subtle SVG food pattern background (carrot, apple, broccoli, avocado, tomato, pear, etc.)
- Inline SVG nav icons (no external icon dependencies)
- Dark mode support via `prefers-color-scheme`

## Safety / Guardrails

- Allergy violations are hard blocks — the plan generator checks every ingredient against known allergens.
- Nutrition values are estimates; each includes a `confidence` field and `source`.
- Publishing actions (calendar/drive) require explicit confirmation.
- OAuth tokens are Fernet-encrypted at rest.
- Audit log tracks sensitive operations.

## Contributing

- Keep tool interfaces stable (Pydantic models).
- Add/replace MCP servers behind the tool router without changing agent logic.
- Include tests for any new tool or planner behavior.
- All agents must extend `BaseAgent[TInput, TOutput]` with typed Pydantic I/O models.
