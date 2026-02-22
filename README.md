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

### Agent Interconnection Diagram

```
                              ┌─────────────────────────────────────┐
                              │            Frontend (Next.js)        │
                              │                                     │
                              │   Chat Page        Plans Page       │
                              │      │                 │            │
                              └──────┼─────────────────┼────────────┘
                                     │                 │
                              POST /chat          POST /plans/generate
                                     │                 │
                              ┌──────▼─────────────────▼────────────┐
                              │          FastAPI Routers             │
                              │                                     │
                              │  ┌────────────┐  ┌──────────────┐   │
                              │  │ Chat Router│  │ Plans Router │   │
                              │  └─────┬──────┘  └──────┬───────┘   │
                              └────────┼────────────────┼───────────┘
                                       │                │
                         ┌─────────────┼────────────────┼──────────────┐
                         │             ▼                ▼              │
                         │  ┌─────────────────────────────────────┐   │
                         │  │          ① ContextAgent              │   │
                         │  │   Loads HouseholdContext from DB     │   │
                         │  │   (people, allergies, rules, goals,  │   │
                         │  │    biometrics, health conditions)    │   │
                         │  └──────────────┬──────────────────────┘   │
                         │                 │                          │
                         │                 │ HouseholdContext          │
                         │          ┌──────┴──────┐                   │
                         │          │             │                   │
                         │          ▼             ▼                   │
                         │  ┌──────────────┐  ┌───────────────────┐   │
                         │  │ ③ Nutrition  │  │  ② PlanAgent      │   │
                         │  │ CoachAgent   │  │                   │   │
                         │  │              │  │  7-day plan gen   │   │
                         │  │ Deterministic│  │  (structured LLM  │   │
                         │  │ calorie/macro│  │   output per day) │   │
                         │  │ calculations │  │                   │   │
                         │  │ per person   │  │  ┌─────────────┐  │   │
                         │  │              │  │  │ Per-day loop│  │   │
                         │  │  ┌────────┐  │  │  │ LLM call    │  │   │
                         │  │  │Mifflin │  │  │  │ Allergy chk │  │   │
                         │  │  │St Jeor │  │  │  │ USDA refine │  │   │
                         │  │  │BMR eq. │  │  │  └─────────────┘  │   │
                         │  │  └────────┘  │  │                   │   │
                         │  └──────┬───────┘  └────────┬──────────┘   │
                         │         │                   │              │
                         │         ▼                   ▼              │
                         │  Nutrition           WeeklyPlan + Meals    │
                         │  Recommendations     + ShoppingList        │
                         │                                            │
                         │           Agent Layer                      │
                         └────────────────────────────────────────────┘
                                       │                │
                              ┌────────▼────────────────▼───────────┐
                              │          External Services           │
                              │                                     │
                              │  ┌──────────┐  ┌─────────────────┐  │
                              │  │ LiteLLM  │  │  USDA FoodData  │  │
                              │  │ Proxy    │  │  Central API    │  │
                              │  │ (LLM)   │  │  (nutrition)    │  │
                              │  └──────────┘  └─────────────────┘  │
                              │  ┌──────────┐  ┌─────────────────┐  │
                              │  │ Brave /  │  │  Google Calendar│  │
                              │  │ Tavily   │  │  (OAuth)        │  │
                              │  │ (search) │  │                 │  │
                              │  └──────────┘  └─────────────────┘  │
                              └─────────────────────────────────────┘

Data flow summary:

  Chat Router ──▶ ContextAgent ──▶ NutritionCoachAgent
       │                │
       │                └──────────▶ (plan preview via LLM)
       │
       └──▶ WebSearchService (Brave/Tavily)

  Plans Router ──▶ PlanAgent ──▶ ContextAgent
                       │
                       ├──▶ LLM (structured DayPlan × 7)
                       ├──▶ Allergy compliance validator
                       └──▶ USDA nutrition refinement
```

### How the agents connect

| Agent | Called by | Depends on | Outputs |
|-------|----------|-----------|---------|
| **ContextAgent** | Chat Router, PlanAgent | PostgreSQL (household data) | `HouseholdContext` — normalized view of all household data |
| **PlanAgent** | Plans Router, Chat Router (preview) | ContextAgent, LLM, USDA API | `WeeklyPlan` + 21 Meals + ShoppingList |
| **NutritionCoachAgent** | Chat Router (nutrition intent) | ContextAgent (HouseholdContext) | Per-person calorie/macro recommendations |

- **ContextAgent is the shared foundation** — both PlanAgent and NutritionCoachAgent consume its `HouseholdContext` output
- **PlanAgent uses LLM + validation** — it calls the LLM 7 times (once per day), validates allergy compliance, and refines nutrition via USDA
- **NutritionCoachAgent is purely deterministic** — no LLM calls, just Mifflin-St Jeor equations adjusted for health conditions
- **The Chat Router is the orchestrator** — it decides which agents to invoke based on regex intent detection, then injects all results into the LLM context for the final streamed response

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

## Agentic Flows

### Flow 1: Chat Message (conversational)

The primary user-facing flow. A single chat message may trigger multiple agent pipelines depending on detected intent.

```
User sends message
       │
       ▼
┌─────────────────────┐
│  POST /chat          │
│  (chat router)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ContextAgent        │  Load household context from DB
│  (people, allergies, │  (people, allergies, dietary rules,
│   rules, goals,      │   preferences, goals, biometrics,
│   health profiles)   │   health conditions)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Build system prompt │  Inject household context into LLM
│  with full household │  system message (allergies marked
│  context             │  CRITICAL, rules, goals, etc.)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  Intent Detection (regex-based, parallel)    │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Search?  │  │  Plan?   │  │ Nutrition? │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │              │              │         │
└───────┼──────────────┼──────────────┼────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐  ┌──────────────┐
   │ Web      │   │ Plan     │  │ Nutrition    │
   │ Search   │   │ Agent    │  │ Coach Agent  │
   │ Service  │   │ (preview)│  │              │
   │ (Brave/  │   │ struct.  │  │ Deterministic│
   │ Tavily)  │   │ LLM call │  │ calorie/macro│
   └────┬─────┘   └────┬─────┘  │ calculations │
        │              │         └──────┬───────┘
        │              │                │
        ▼              ▼                ▼
┌─────────────────────────────────────────────┐
│  Augmented messages (context injected)       │
│  [system prompt + search results +           │
│   plan preview + nutrition analysis +        │
│   chat history + user message]               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  LLM Streaming (via LiteLLM proxy)           │
│  GPT-4o-mini → Ollama fallbacks              │
│  Response streamed as SSE to frontend        │
└─────────────────────────────────────────────┘
```

**Key behaviors:**
- Intents are **not mutually exclusive** — a message like "find me a high-protein dinner recipe" triggers both search and nutrition
- Plan intent generates a **single-day preview** in chat; full 7-day plans use the dedicated plan flow below
- All agent results are injected as additional system messages before the LLM generates the final response
- The LLM never sees raw DB models — everything passes through the `HouseholdContext` Pydantic schema

### Flow 2: Plan Generation (7-day meal plan)

Triggered from the Plans page via `POST /plans/generate`. This is the most complex pipeline.

```
User clicks "Generate Plan"
       │
       ▼
┌─────────────────────┐
│  POST /plans/generate│
│  (plans router)      │
│  week_start_date,    │
│  overrides, notes    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PlanAgent.run()     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 1: Load        │
│  ContextAgent        │──▶ HouseholdContext
│  (household context) │    (people, allergies, rules,
└──────────┬──────────┘     preferences, goals)
           │
           ▼
┌─────────────────────┐
│  Step 2: Build       │
│  system prompt       │──▶ Allergies marked CRITICAL
│  from context        │    Rules and preferences included
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Step 3: Loop 7 days (sequential)         │
│                                           │
│  For each day:                            │
│  ┌────────────────────────────────────┐   │
│  │ a. Build day prompt                │   │
│  │    (date, previous dinners for     │   │
│  │     variety, max cook time, notes) │   │
│  ├────────────────────────────────────┤   │
│  │ b. generate_structured(DayPlan)    │   │
│  │    LLM → Pydantic DayPlan model   │   │
│  │    (instructor validates schema,   │   │
│  │     retries up to 3x on failure)   │   │
│  ├────────────────────────────────────┤   │
│  │ c. Allergy compliance check        │   │
│  │    Every ingredient scanned for    │   │
│  │    allergens. False positives      │   │
│  │    handled (e.g. "dairy-free").    │   │
│  │    HARD BLOCK if violation found   │   │
│  │    (unless override provided).     │   │
│  ├────────────────────────────────────┤   │
│  │ d. USDA nutrition refinement       │   │
│  │    Cross-reference LLM estimates   │   │
│  │    with USDA FoodData Central.     │   │
│  │    Results cached in nutrition_    │   │
│  │    cache table.                    │   │
│  ├────────────────────────────────────┤   │
│  │ e. Track dinner titles for next    │   │
│  │    day's variety prompt            │   │
│  └────────────────────────────────────┘   │
│                                           │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 4: Post-processing                     │
│  ├─ Compute daily nutrition totals           │
│  │  (sum calories, protein, carbs, fat,      │
│  │   fiber across all meals per day)         │
│  ├─ Aggregate shopping list                  │
│  │  (merge duplicate ingredients across      │
│  │   7 days, categorize: produce, meat,      │
│  │   dairy, spices, pantry)                  │
│  └─ Generate markdown summary                │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 5: Persist to DB                       │
│  ├─ WeeklyPlan (status: DRAFT)               │
│  ├─ 21 Meal records (7 days × 3 meals)       │
│  │  (each with ingredients_json,             │
│  │   nutrition_json, flags_json)             │
│  └─ ShoppingList (aggregated items_json)     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
          Plan ready for review
          (DRAFT → CONFIRMED → PUBLISHED)
```

**Plan lifecycle:** `DRAFT` → `CONFIRMED` → `PUBLISHED` → `ARCHIVED`
- Publishing can trigger Google Calendar event creation (if OAuth connected)

### Flow 3: Nutrition Coach (health-aware recommendations)

Invoked automatically when the chat detects nutrition-related questions, or used internally by the plan generator.

```
Chat message with nutrition intent
(e.g. "how many calories should my family eat?")
       │
       ▼
┌──────────────────────┐
│  NutritionCoachAgent │
│  .run()              │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  For each person in household:            │
│                                           │
│  ┌────────────────────────────────────┐   │
│  │ Tier 1: Deterministic Calculations │   │
│  │                                    │   │
│  │ • Compute age from DOB             │   │
│  │ • Mifflin-St Jeor BMR equation     │   │
│  │   (gender + age + height + weight) │   │
│  │ • Activity level multiplier        │   │
│  │   (sedentary → very active)        │   │
│  │ • Health condition adjustments:    │   │
│  │   - Diabetes: lower carb %, lower  │   │
│  │     sugar limit                    │   │
│  │   - Hypertension: lower sodium     │   │
│  │   - Heart disease: lower sat. fat  │   │
│  │   - Kidney disease: lower protein  │   │
│  │ • Age-specific adjustments         │   │
│  │   (children, teens, seniors)       │   │
│  ├────────────────────────────────────┤   │
│  │ Output per person:                 │   │
│  │ • Daily calories (kcal)            │   │
│  │ • Macro split (protein/carbs/fat)  │   │
│  │ • Fiber target                     │   │
│  │ • Sodium & sugar limits            │   │
│  │ • Dietary guidelines list          │   │
│  │ • Foods to emphasize / limit       │   │
│  │ • Warnings                         │   │
│  └────────────────────────────────────┘   │
│                                           │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  Tier 2: Chat Summary (if from chat)      │
│  Build natural-language analysis from     │
│  all person recommendations.              │
│  Injected into LLM context so it can     │
│  answer conversationally.                 │
└──────────────────────────────────────────┘
```

### Flow 4: RAG Document Search

Used for recipe retrieval from ingested Google Drive documents.

```
Document Ingestion:              Semantic Search:
POST /rag/ingest                 POST /rag/search
       │                                │
       ▼                                ▼
┌──────────────┐                ┌──────────────┐
│ Chunk text   │                │ Embed query  │
│ into segments│                │ (1536-dim)   │
└──────┬───────┘                └──────┬───────┘
       │                               │
       ▼                               ▼
┌──────────────┐                ┌──────────────┐
│ Generate     │                │ pgvector     │
│ embeddings   │                │ cosine       │
│ (1536-dim)   │                │ similarity   │
└──────┬───────┘                │ search       │
       │                        └──────┬───────┘
       ▼                               │
┌──────────────┐                       ▼
│ Store in     │                Top-K results
│ memory_      │                with metadata
│ documents    │
│ table        │
└──────────────┘
```

### Agent Framework

All agents share this contract:

```python
class BaseAgent(ABC, Generic[TInput, TOutput]):
    name: str
    description: str

    async def run(self, input: TInput, context: AgentContext) -> AgentResult[TOutput]

class AgentContext:
    household_id: UUID
    session: AsyncSession      # DB session for queries
    correlation_id: str        # Request tracing

class AgentResult(Generic[TOutput]):
    success: bool
    data: TOutput | None       # Typed output
    error: str | None
    warnings: list[str]
    metadata: dict[str, Any]
```

Agents are registered in `AgentRegistry` (dict-based, supports discovery via `list_agents()`). The framework enforces typed I/O — every agent declares its Pydantic input/output models at the class level.

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
