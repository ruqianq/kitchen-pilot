# Agentic Weekly Planner + Nutrition Coach — Specification

## 1. Overview

Build a personal assistant "agentic" app that generates a **weekly cooking plan** aligned with household preferences, allergies, diet goals, and schedule; produces a **shopping list**; and **publishes** cooking events to **Google Calendar**. The app supports **chat** + **voice** interaction, uses **RAG** over Google Drive recipes/notes, and integrates with **Google APIs** and **web search providers** via native Python clients.

---

## 2. Goals

- Chat or voice: "Plan dinners next week, 30 min max, high protein, avoid peanuts."
- Reads schedule availability to suggest cook times.
- Uses household constraints (hard + soft) to tailor meals.
- Retrieves recipes from Google Drive and optionally web search.
- Computes nutrition (calories/macros + confidence) and gives "nutrition coach" suggestions.
- Generates normalized grocery list and exports as:
  - in-app checklist + CSV
  - retailer search deep-links (Amazon/Instacart/Walmart)
- Publishes plan to Google Calendar (and optionally writes a summary doc to Drive).

---

## 3. Non-goals (initial releases)

- Fully automated "add to cart" for DoorDash/Amazon (keep as optional later).
- Hands-free always-on wake word voice (push-to-talk first).
- Medical-grade nutrition advice (we provide estimates + guardrails, not diagnosis).

---

## 4. High-level architecture

### Frontend

Next.js web app:
- Chat UI (threaded)
- Weekly plan view
- Household profile editor
- Grocery list exporter
- Push-to-talk voice UI

### Backend

FastAPI (Python):
- Orchestrator + agents runtime
- Tool routing (native Python tools)
- Plan validation and publishing
- Auth/OAuth token storage
- RAG ingestion pipeline
- Nutrition lookup + caching

### Data

- Postgres for structured data + audit logs
- pgvector for embeddings/RAG memory
- Redis optional (cache/job queue)

### LLM

- Ollama (v0.5+) for local models with grammar-constrained generation
- LiteLLM gateway (>=1.55) for routing + logging + budget control
- `instructor` library (>=1.7) for Pydantic validation + automatic retries

### External integrations (native Python)

All external services are accessed via native Python clients — no MCP sidecar containers. MCP can be introduced later if multi-app tool sharing becomes valuable.

- Google Calendar — `google-api-python-client` + `google-auth-oauthlib`
- Google Drive — `google-api-python-client` (read-only for recipe ingestion)
- Web Search — direct HTTP to Brave Search or Tavily REST APIs
- Household DB logic — native SQLAlchemy
- Nutrition tool — USDA API + caching + unit normalization
- Grocery normalization + exporter — native Python
- Voice STT/TTS — Whisper + TTS library
- Cart automation (optional later)

---

## 5. Key modules

### 5.1 Agent Orchestrator

Responsibilities:
- Build a task plan from user request.
- Load household context + schedule.
- Ask Recipe agent for candidates (RAG/web).
- Ask Nutrition agent to compute macros and confidence.
- Ask Grocery agent to compile list and export options.
- Ask Calendar agent to publish events (confirm required).
- Produce a final weekly plan JSON + narrative summary.

Implementation:
- **Deterministic pipeline** to start (not LangGraph). Explicit stages with retries. Move to a state machine only if dynamic routing or cycles are needed.
- Enforce schema validation (Pydantic) at every stage.

### 5.2 Agents

**A) Context Agent**
- Fetch structured truth: allergies, dietary rules, preferences, goals.
- Fetch vector memory: prior plans, ratings, notes ("kids hated quinoa texture").
- Output normalized `HouseholdContext` object.

**B) Calendar Agent (Google API)**
- Read events and free windows via `google-api-python-client`.
- Publish cooking events for meals:
  - title: `Cook: <Meal>`
  - description: recipe link + ingredients + nutrition summary
  - location optional
- Supports "replace existing plan" semantics:
  - tag events with extendedProperties (e.g., `weekly_plan_id`) so they can be updated/removed.

**C) Recipe Retrieval Agent (RAG + Search)**
- RAG over Drive recipe docs (fetched via Google Drive API) and saved notes.
- Optional web search for new recipe candidates via Brave/Tavily REST API (allowlist domains).
- Output ranked recipe candidates with metadata:
  - prep time, allergens, servings, source link

**D) Nutrition Coach Agent (Native tool + cache)**
- Use nutrition provider(s) (USDA first) and compute:
  - per meal macros
  - daily totals
  - alignment with household goals
- Mark results with confidence:
  - `exact` (API match)
  - `estimated` (ingredient heuristics)
- Produce "swap suggestions" if goals missed.

**E) Grocery Agent (Native)**
- Normalize ingredient list:
  - canonical item names
  - units and quantities
  - categorize (Produce/Meat/Dairy/Pantry/Spices)
- Generate exports:
  - checklist JSON, CSV
  - retailer search links (Amazon/Instacart/Walmart)
- Optional later: provider adapters for real cart creation where feasible.

### 5.3 Tool Router

- Tools are exposed to agents via a common interface: `tool_name`, `args`, `result`, `errors`
- All tools are native Python modules with strict Pydantic request/response models.
- Google APIs are wrapped as tools with the same interface (Calendar, Drive).
- Web search APIs (Brave/Tavily) are wrapped as tools with the same interface.
- All tool calls are logged to audit table + LiteLLM logs.
- **Future**: MCP can be introduced as an alternative transport for any tool if multi-app sharing is needed.

---

## 6. Data model (Postgres)

### Core tables

```
household(id UUID PK, name, timezone, created_at, updated_at)
person(id UUID PK, household_id FK, name, role, age_band, created_at, updated_at)
allergy(id UUID PK, person_id FK, allergen, severity, notes, created_at)
```

**dietary_rule** — uses nullable FKs (not polymorphic scope_type/scope_id):
```
dietary_rule(
  id UUID PK,
  household_id FK NULL,
  person_id FK NULL,
  rule, notes, created_at,
  CHECK (household_id IS NOT NULL OR person_id IS NOT NULL)
)
```

**food_preference** — same pattern:
```
food_preference(
  id UUID PK,
  household_id FK NULL,
  person_id FK NULL,
  item, preference [like|dislike|avoid|favorite], notes, created_at
)
```

**nutrition_goal** — same pattern:
```
nutrition_goal(
  id UUID PK,
  household_id FK NULL,
  person_id FK NULL,
  calories_min, calories_max, protein_g, carbs_g, fat_g, fiber_g, created_at, updated_at
)
```

```
biometric(id UUID PK, person_id FK, height_cm, weight_kg, created_at, updated_at)
  -- treat as sensitive; encrypted optional

weekly_plan(
  id UUID PK, household_id FK, week_start_date,
  status [draft|confirmed|published|archived],
  plan_json JSONB, summary_md, created_at, updated_at, model_info_json JSONB
)

meal(
  id UUID PK, weekly_plan_id FK, date, meal_type, title,
  recipe_source_url, cook_time_min, servings,
  ingredients_json JSONB, nutrition_json JSONB, flags_json JSONB,
  created_at
)

shopping_list(id UUID PK, weekly_plan_id FK, items_json JSONB, exports_json JSONB, created_at)

nutrition_cache(
  id UUID PK, query, normalized_food, nutrition_json JSONB,
  source, confidence, fetched_at
)

audit_log(id UUID PK, household_id FK, action, payload_json JSONB, status, created_at)

oauth_tokens(
  id UUID PK, household_id FK,
  provider VARCHAR(50),
  encrypted_access_token BYTEA,
  encrypted_refresh_token BYTEA,
  token_expiry TIMESTAMPTZ,
  scopes TEXT[],
  created_at, updated_at
)
```

### RAG memory (pgvector)

```
memory_documents(
  id UUID PK, household_id FK, doc_type, text,
  metadata_json JSONB, embedding VECTOR(1536),
  created_at
)
  doc_type: drive_recipe | note | feedback | substitution | pantry | plan_summary
```

### Index strategy

- `person(household_id)`
- `allergy(person_id)`
- `dietary_rule(household_id)`, `dietary_rule(person_id)`
- `food_preference(household_id)`, `food_preference(person_id)`
- `weekly_plan(household_id, week_start_date)`
- `nutrition_cache(normalized_food)` — for lookup deduplication
- `memory_documents` — HNSW index on embedding column for ANN search
- `oauth_tokens(household_id, provider)` — unique constraint

---

## 7. APIs (FastAPI)

### Auth
- `POST /auth/google/start`
- `GET /auth/google/callback`
- `GET /auth/status`

### Household
- `GET /household`
- `POST /household`
- `PUT /household/{id}`
- `GET /household/people`
- `POST /household/people`
- `PUT /household/people/{id}`
- `DELETE /household/people/{id}`
- `POST /household/preferences`
- `PUT /household/preferences/{id}`
- `DELETE /household/preferences/{id}`
- `POST /household/allergies`
- `PUT /household/allergies/{id}`
- `DELETE /household/allergies/{id}`
- `POST /household/goals`
- `PUT /household/goals/{id}`
- `DELETE /household/goals/{id}`

### Chat + planning
- `POST /chat` — streaming SSE
- `POST /plan/generate` — body includes week_start_date, constraints override
- `POST /plan/publish` — plan_id -> calendar
- `GET /plan` — list plans (paginated)
- `GET /plan/{id}`
- `GET /plan/{id}/shopping-list`
- `DELETE /plan/{id}`

### RAG
- `POST /rag/ingest/drive` — trigger ingestion job
- `GET /rag/search?q=...&limit=&offset=`

### Nutrition
- `POST /nutrition/lookup` — ingredient/food query
- `POST /nutrition/recipe/estimate`

### Voice
- `POST /voice/stt` — audio -> text (accepts webm, wav; max 25MB)
- `POST /voice/tts` — text -> audio (returns audio stream)

### Health
- `GET /health` — DB connectivity + service status

---

## 8. Plan schema (Pydantic)

### Generation strategy: per-day decomposition

Instead of generating a full WeeklyPlan in one LLM call (~50 fields, 3+ nesting levels), decompose into **7 DayPlan calls** (~15 fields each). This dramatically improves reliability with 7-8B local models.

```
WeeklyPlan = assemble(DayPlan × 7) + daily_totals + shopping_list + publishing
```

### DayPlan schema (LLM-generated)

```python
class DayPlan(BaseModel):
    date: str
    meals: list[Meal]  # min_length=1

class Meal(BaseModel):
    meal_type: MealType  # enum: breakfast|lunch|dinner|snack
    title: str  # min_length=1, max_length=100
    cook_time_min: int  # ge=0, le=480
    servings: int  # ge=1, le=20
    recipe: RecipeRef
    ingredients: list[Ingredient]  # min_length=1
    nutrition: NutritionInfo
    flags: MealFlags

class Ingredient(BaseModel):
    name: str
    quantity: float  # gt=0
    unit: str
    substitutions: list[str] = []

class NutritionInfo(BaseModel):
    calories: int  # ge=0, le=5000
    protein_g: float  # ge=0
    carbs_g: float  # ge=0
    fat_g: float  # ge=0
    fiber_g: float  # ge=0
    confidence: NutritionConfidence  # enum: exact|estimated
    source: str

class MealFlags(BaseModel):
    allergen_warnings: list[str] = []
    rule_conflicts: list[str] = []
    estimated_values: list[str] = []
```

### WeeklyPlan schema (assembled server-side)

```python
class WeeklyPlan(BaseModel):
    week_start_date: str
    days: list[DayPlan]  # length=7
    daily_totals: list[DailyTotal]
    shopping_list: ShoppingList
    publishing: PublishingSpec
```

### Validation gates

- **Allergy compliance**: hard block unless user overrides explicitly. Override mechanism: `overrides[]` field with `{ constraint_type, description, acknowledged_at }`.
- **Cooking time constraints**: soft warnings allowed.
- **Nutrition goals**: best-effort with suggestions.

---

## 9. LLM reliability

### Stack

| Component | Choice |
|-----------|--------|
| Primary model | GPT-4o-mini via OpenAI API (fast, cheap, reliable structured output) |
| Local fallback | Ollama v0.5+ — Qwen3 8B, Gemma3 (for offline/cost-free dev) |
| Routing | LiteLLM >= 1.55 (unified API across OpenAI + Ollama) |
| Validation + retry | `instructor` >= 1.7 (Pydantic validation, auto error-fed retries) |

### LLM call pattern

```python
client = instructor.from_litellm(litellm.acompletion)
day_plan = await client(
    model="gpt-4o-mini",
    messages=[...],
    response_model=DayPlan,
    max_retries=3,
    temperature=0,
)
```

### 3-layer retry strategy

1. **Instructor auto-retry**: Feeds Pydantic ValidationError back to the model (max_retries=3).
2. **Model escalation**: gpt-4o-mini -> ollama_chat/qwen3:8b -> ollama_chat/gemma3:latest.
3. **Graceful degradation**: Return partial plan with confidence flags rather than blocking entirely.

### Known constraints

- Application-level validation needed for: realistic nutrition values, no repeated recipes, correct array lengths.
- Set `max_tokens` high enough for output (~1000 tokens per DayPlan).
- temperature=0 for structured output, temperature=0.7 for chat.

---

## 10. Authentication & authorization

### Google OAuth 2.0

**Flow**: Authorization Code with `access_type=offline`, `prompt=consent`, CSRF `state` parameter.

**Redirect URIs** (register both in Google Cloud Console):
- `http://localhost:8000/auth/google/callback`
- `http://127.0.0.1:8000/auth/google/callback`

**Scopes**:
| Purpose | Scope | Sensitivity |
|---------|-------|-------------|
| Calendar read/write | `calendar.events` | Sensitive |
| Drive read-only | `drive.readonly` | Restricted |

**Granular consent** (Jan 2026): Users can deselect individual scopes. App must check which scopes were actually granted and handle partial access gracefully.

**Library**: `authlib` or `google-auth-oauthlib`

### Token lifecycle

| Scenario | Behavior |
|----------|----------|
| Testing mode consent screen | Refresh token expires in 7 days |
| Production mode | Refresh token does not expire |
| Token unused 6 months | Revoked by Google |
| User changes password | All tokens revoked |
| >100 refresh tokens per client ID per user | Oldest silently invalidated |

Always handle `invalid_grant` by triggering re-auth flow.

### Token storage

Fernet-encrypted (AES-128-CBC + HMAC-SHA256) in Postgres `oauth_tokens` table. Encryption key stored in `FERNET_KEY` environment variable, never in the database.

### App-level auth

For initial local single-user deployment, the household is implicitly the authenticated user. Multi-user auth (session-based or JWT) deferred to cloud deployment milestone.

---

## 11. External integrations

All external services are accessed via **native Python clients** within the FastAPI process. No sidecar containers or MCP servers are needed. This keeps Docker Compose simple and debugging straightforward. MCP can be layered on later if multi-app tool sharing becomes valuable.

### Google Calendar

| Item | Detail |
|------|--------|
| Library | `google-api-python-client` + `google-auth-oauthlib` |
| Auth | OAuth 2.0 tokens managed by FastAPI (see Section 10) |
| Operations | Read events (free window detection), create/update/delete cooking events |
| Event tagging | `extendedProperties.private.kitchen_pilot_plan_id` for replace/remove semantics |

### Google Drive

| Item | Detail |
|------|--------|
| Library | `google-api-python-client` |
| Auth | Same OAuth tokens (Drive read-only scope) |
| Operations | List files, download text content for recipe ingestion into pgvector |
| Scope | `drive.readonly` — no writes to user's Drive |

### Web Search

| Item | Detail |
|------|--------|
| Providers | Brave Search REST API and/or Tavily REST API |
| Library | `httpx` (direct HTTP calls) |
| Auth | API key via env var (`BRAVE_API_KEY` / `TAVILY_API_KEY`) |
| Operations | Search for recipe candidates; results fed to Recipe agent |

### Resilience

All external API calls wrapped with:
- `asyncio.wait_for()` timeout (30s default)
- Exponential backoff retry (3 attempts, `tenacity` library)
- Graceful degradation (calendar/drive features disabled if OAuth not configured)

### Future: MCP migration path

If MCP becomes useful (e.g., sharing tools across multiple AI apps), any native integration can be wrapped as an MCP server:
- Wrap the existing Python tool module as an MCP server using `fastmcp`
- Deploy as a sidecar container with Streamable HTTP transport
- No changes to agent logic — only the tool router transport layer changes

---

## 12. Security & privacy

- OAuth tokens Fernet-encrypted at rest in Postgres.
- Sensitive fields (biometrics) encrypted and optional.
- Allowlist domains for web recipe sources.
- Action confirmation required for: calendar writes.
- Audit log for all tool actions.
- Postgres bound to 127.0.0.1 in Docker Compose (not exposed to host network).
- Rate limiting on `/chat` endpoint (deferred to cloud deployment).
- Row-level access control for multi-user (deferred to cloud deployment).

---

## 13. Observability

- LiteLLM request logging (model used, tokens, latency, agent tag).
- App `audit_log` table for: tool invocation traces, publish actions.
- Structured logging with correlation IDs across agent calls.
- Optional OpenTelemetry tracing later.

---

## 14. Milestones

### M0 — Foundation (done)
- Monorepo structure (uv + pnpm)
- Docker Compose: Postgres + pgvector, Ollama, LiteLLM, FastAPI, Next.js
- Pydantic core schemas (DayPlan, WeeklyPlan, HouseholdContext)
- SQLAlchemy ORM models + Alembic migrations configured
- Basic chat endpoint (streaming SSE via instructor + LiteLLM)
- Health check endpoint (DB + service status)
- Linting (ruff for Python, ESLint for TypeScript)
- `.env.example` with all vars documented

### M1 — Household DB + UI (done)
- Profile editor, CRUD API endpoints
- Context Agent implemented
- Household onboarding flow in Next.js
- Plan generation pipeline (per-day decomposition)
- Plan storage + status management
- Plan list/detail UI with shopping list

### M2 — Chat UI + polish
- Chat page in Next.js consuming SSE `/chat` endpoint
- Chat message history display (threaded)
- Alembic initial migration
- Profile page inline add/edit (not just delete)
- Navigation bar across all pages

### M3 — Google OAuth + Calendar (native)
- Google OAuth 2.0 flow (`/auth/google/start`, `/auth/google/callback`)
- Token storage (Fernet-encrypted in Postgres)
- Calendar service using `google-api-python-client`
- Read events + free windows
- Publish/update/remove cooking events
- Replace existing `calendar_mcp.py` with native Google API client

### M4 — Nutrition coach
- USDA-based lookup + caching
- Nutrition agent computes totals and suggestions
- Confidence field + swap suggestions
- `/nutrition/lookup` and `/nutrition/recipe/estimate` endpoints

### M5 — RAG over Google Drive (native)
- Drive ingestion via `google-api-python-client` (uses OAuth tokens from M3)
- Ingestion pipeline: Drive docs → text extraction → embeddings → pgvector
- Recipe agent uses RAG with citations/links
- `/rag/ingest/drive` and `/rag/search` endpoints

### M6 — Grocery exporter
- Normalization + checklist + CSV + retailer search links

### M7 — Voice push-to-talk
- Whisper STT + TTS
- Shared chat thread

### M8 — Optional / future
- Web search integration (Brave/Tavily) for recipe discovery
- MCP migration for any integration (if multi-app sharing needed)
- Additional providers / cart automation experiments
- Cloud deployment
- Multi-user auth
