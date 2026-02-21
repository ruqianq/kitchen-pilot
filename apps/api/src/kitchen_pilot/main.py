from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kitchen_pilot.config import settings
from kitchen_pilot.db.engine import engine
from kitchen_pilot.routers import auth, chat, health, household, nutrition, plans


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Kitchen Pilot API",
    description="Agentic weekly meal planner + nutrition coach",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(household.router)
app.include_router(nutrition.router)
app.include_router(plans.router)
